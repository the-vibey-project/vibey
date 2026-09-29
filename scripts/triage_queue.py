#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reconcile GitHub's triaged issues into PostgreSQL's durable priority queue.

`reconcile` upserts every open, triaged issue and -- when the read provably covered all of
them -- retires a claimable row whose issue has been closed or has lost the triaged label, to
`blocked`, so a closed issue is never claimed. `reap` returns expired leases to `ready`.
`scripts/triaged_delivery.py` runs both at the start of every pass; `--reap` runs the reaper
by hand.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar

import asyncpg

try:
    from scripts.interfaces.triage_queue_interface import (
        ForgeInterface,
        TicketInterface,
        TicketListingInterface,
        TicketSourceInterface,
        TicketStoreInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.triage_queue_interface import (  # type: ignore[import-not-found,no-redef]
        ForgeInterface,
        TicketInterface,
        TicketListingInterface,
        TicketSourceInterface,
        TicketStoreInterface,
    )

PRIORITIES = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TRIAGED = "vibey-gh:triaged"
BUMPED = "vibey-gh:priority-bumped"
STATES = ("ready", "leased", "dispatched", "blocked", "completed")
T = TypeVar("T")


@dataclass(frozen=True)
class Ticket:
    repository: str
    number: int
    title: str
    body: str
    url: str
    priority: int
    bumped: bool
    updated_at: datetime


@dataclass(frozen=True)
class TicketListing:
    tickets: Sequence[TicketInterface] = field(default_factory=list)
    complete: bool = True


class GhCli:
    """GitHub through the `gh` binary. Declared by `ForgeInterface`."""

    def gh(self, *args: str) -> str:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "gh command failed")
        return result.stdout


class GithubTicketSource:
    """The open, triaged issues of one repository. Declared by `TicketSourceInterface`."""

    def __init__(self, repository: str, forge: ForgeInterface, *, limit: int = 1000) -> None:
        self._repository = repository
        self._forge = forge
        self._limit = limit

    def tickets(self) -> TicketListingInterface:
        raw = json.loads(
            self._forge.gh(
                "issue",
                "list",
                "--repo",
                self._repository,
                "--state",
                "open",
                "--label",
                TRIAGED,
                "--limit",
                str(self._limit),
                "--json",
                "number,title,body,url,labels,updatedAt",
            )
        )
        tickets: list[TicketInterface] = []
        for item in raw:
            labels = {label["name"] for label in item.get("labels", [])}
            priority = next(
                (PRIORITIES[name] for name in PRIORITIES if f"vibey-gh:priority-{name}" in labels),
                PRIORITIES["low"],
            )
            tickets.append(
                Ticket(
                    repository=self._repository,
                    number=int(item["number"]),
                    title=str(item.get("title") or ""),
                    body=str(item.get("body") or ""),
                    url=str(item["url"]),
                    priority=priority,
                    bumped=BUMPED in labels,
                    updated_at=datetime.fromisoformat(
                        str(item["updatedAt"]).replace("Z", "+00:00")
                    ),
                )
            )
        # A listing that reached its limit may have been cut off: an issue past the limit is
        # unknown, not closed, so nothing may be retired on its absence.
        return TicketListing(tickets=tickets, complete=len(raw) < self._limit)


class TriageQueue:
    """The `triaged_ticket` table for one repository. Declared by `TicketStoreInterface`.

    Synchronous on the outside -- its one caller is a synchronous supervisor loop -- and one
    short-lived connection per call on the inside."""

    def __init__(self, database_url: str, repository: str) -> None:
        self._database_url = database_url
        self._repository = repository

    def _run(self, work: Callable[[asyncpg.Connection], Awaitable[T]]) -> T:
        async def go() -> T:
            conn = await asyncpg.connect(self._database_url)
            try:
                return await work(conn)
            finally:
                await conn.close()

        return asyncio.run(go())

    def reap(self) -> int:
        async def work(conn: asyncpg.Connection) -> int:
            rows = await conn.fetch(
                """UPDATE triaged_ticket SET state = 'ready', lease_owner = NULL,
                   lease_expires_at = NULL, updated_at = now()
                   WHERE repository = $1 AND state = 'leased' AND lease_expires_at < now()
                   RETURNING issue_number""",
                self._repository,
            )
            return len(rows)

        return self._run(work)

    def reconcile(self, tickets: Sequence[TicketInterface], *, complete: bool) -> list[int]:
        async def work(conn: asyncpg.Connection) -> list[int]:
            async with conn.transaction():
                for ticket in tickets:
                    await conn.execute(
                        """
                        INSERT INTO triaged_ticket
                            (repository, issue_number, title, body, issue_url,
                             priority_rank, bump_seq, source_updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6,
                                CASE WHEN $7 THEN nextval('triaged_ticket_bump_seq') END, $8)
                        ON CONFLICT (repository, issue_number) DO UPDATE SET
                            title = EXCLUDED.title,
                            body = EXCLUDED.body,
                            issue_url = EXCLUDED.issue_url,
                            priority_rank = EXCLUDED.priority_rank,
                            source_updated_at = EXCLUDED.source_updated_at,
                            observed_at = now(),
                            updated_at = now(),
                            bump_seq = CASE
                                WHEN EXCLUDED.bump_seq IS NULL THEN NULL
                                ELSE COALESCE(triaged_ticket.bump_seq,
                                              nextval('triaged_ticket_bump_seq'))
                            END
                        """,
                        ticket.repository,
                        ticket.number,
                        ticket.title,
                        ticket.body,
                        ticket.url,
                        ticket.priority,
                        ticket.bumped,
                        ticket.updated_at,
                    )
                if not complete:
                    return []
                # Only claimable rows: a ready ticket, or a lease that has already run out.
                # A live lease belongs to a pass in progress, and a dispatched ticket has a
                # project in flight -- neither is this reconcile's to take away.
                retired = await conn.fetch(
                    """UPDATE triaged_ticket SET state = 'blocked', lease_owner = NULL,
                       lease_expires_at = NULL, updated_at = now()
                       WHERE repository = $1
                         AND (state = 'ready'
                              OR (state = 'leased' AND lease_expires_at < now()))
                         AND NOT (issue_number = ANY($2::integer[]))
                       RETURNING issue_number""",
                    self._repository,
                    [ticket.number for ticket in tickets],
                )
                return sorted(int(row["issue_number"]) for row in retired)

        return self._run(work)

    def claim(self, owner: str, lease_seconds: int) -> dict[str, object] | None:
        async def work(conn: asyncpg.Connection) -> dict[str, object] | None:
            row = await conn.fetchrow(
                """
                UPDATE triaged_ticket SET state = 'leased', lease_owner = $2,
                    lease_expires_at = now() + ($3 * interval '1 second'), updated_at = now()
                WHERE repository = $1 AND state = 'ready'
                  AND (bump_seq IS NULL OR bump_seq > 0)
                  AND issue_number = (
                    SELECT issue_number FROM triaged_ticket
                    WHERE repository = $1 AND state = 'ready'
                    ORDER BY (bump_seq IS NULL), bump_seq ASC NULLS LAST,
                             priority_rank ASC, source_updated_at ASC NULLS LAST,
                             issue_number ASC
                    FOR UPDATE SKIP LOCKED LIMIT 1
                  )
                RETURNING repository, issue_number, title, body, issue_url,
                          priority_rank, project_id::text AS project_id, lease_expires_at
                """,
                self._repository,
                owner,
                lease_seconds,
            )
            return dict(row) if row else None

        return self._run(work)

    def release(self, issue_number: int) -> None:
        async def work(conn: asyncpg.Connection) -> None:
            await conn.execute(
                """UPDATE triaged_ticket SET state = 'ready', lease_owner = NULL,
                   lease_expires_at = NULL, updated_at = now()
                   WHERE repository = $1 AND issue_number = $2 AND state = 'leased'""",
                self._repository,
                issue_number,
            )

        self._run(work)

    def set_state(self, issue_number: int, state: str, *, project_id: str | None = None) -> None:
        if state not in STATES:
            raise ValueError(f"invalid ticket state: {state}")

        async def work(conn: asyncpg.Connection) -> None:
            # `$3` is read twice, once as the enum and once as text. Uncast, PostgreSQL
            # deduces two types for one parameter and refuses the statement ("inconsistent
            # types deduced for parameter $3"), which is how every `set_state` failed before.
            await conn.execute(
                """UPDATE triaged_ticket SET state = $3::triaged_ticket_state,
                   lease_owner = CASE WHEN $3::text = 'leased' THEN lease_owner END,
                   lease_expires_at = CASE WHEN $3::text = 'leased' THEN lease_expires_at END,
                   project_id = COALESCE($4::uuid, project_id),
                   updated_at = now()
                   WHERE repository = $1 AND issue_number = $2""",
                self._repository,
                issue_number,
                state,
                project_id,
            )

        self._run(work)

    def in_flight(self) -> list[dict[str, object]]:
        async def work(conn: asyncpg.Connection) -> list[dict[str, object]]:
            rows = await conn.fetch(
                """SELECT issue_number, title, body, priority_rank,
                          project_id::text AS project_id
                   FROM triaged_ticket
                   WHERE repository = $1 AND state = 'dispatched'
                   ORDER BY (bump_seq IS NULL), bump_seq ASC NULLS LAST, priority_rank ASC,
                            source_updated_at ASC NULLS LAST, issue_number ASC""",
                self._repository,
            )
            return [dict(row) for row in rows]

        return self._run(work)


# Module-level rather than a method (ADR-0016's written reason): the script's entry point,
# which argparse and `python scripts/triage_queue.py` call by name.
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--claim-owner")
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--reap", action="store_true")
    parser.add_argument("--state", choices=STATES)
    parser.add_argument("--issue-number", type=int)
    args = parser.parse_args()
    store: TicketStoreInterface = TriageQueue(args.database_url, args.repository)
    source: TicketSourceInterface = GithubTicketSource(args.repository, GhCli())
    if args.reap:
        print(json.dumps({"reaped": store.reap()}))
    listing = source.tickets()
    retired = store.reconcile(listing.tickets, complete=listing.complete)
    print(
        json.dumps(
            {"reconciled": len(listing.tickets), "complete": listing.complete, "retired": retired}
        )
    )
    if args.claim_owner:
        claimed = store.claim(args.claim_owner, args.lease_seconds)
        print(json.dumps({"claimed": claimed}, default=str))
    if args.state is not None:
        if args.issue_number is None:
            parser.error("--state requires --issue-number")
        store.set_state(args.issue_number, args.state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
