#!/usr/bin/env python3
"""Reconcile GitHub's triaged issues into PostgreSQL's durable priority queue."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime

import asyncpg

PRIORITIES = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TRIAGED = "vibey-gh:triaged"
BUMPED = "vibey-gh:priority-bumped"


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


def github_tickets(repository: str) -> list[Ticket]:
    raw = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repository,
            "--state",
            "open",
            "--label",
            TRIAGED,
            "--limit",
            "1000",
            "--json",
            "number,title,body,url,labels,updatedAt",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tickets: list[Ticket] = []
    for item in json.loads(raw):
        labels = {label["name"] for label in item.get("labels", [])}
        priority = next(
            (PRIORITIES[name] for name in PRIORITIES if f"vibey-gh:priority-{name}" in labels),
            PRIORITIES["low"],
        )
        tickets.append(
            Ticket(
                repository=repository,
                number=int(item["number"]),
                title=str(item.get("title") or ""),
                body=str(item.get("body") or ""),
                url=str(item["url"]),
                priority=priority,
                bumped=BUMPED in labels,
                updated_at=datetime.fromisoformat(str(item["updatedAt"]).replace("Z", "+00:00")),
            )
        )
    return tickets


async def reconcile(database_url: str, tickets: list[Ticket]) -> int:
    async with (
        asyncpg.create_pool(database_url, min_size=1, max_size=1) as pool,
        pool.acquire() as conn,
        conn.transaction(),
    ):
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
    return len(tickets)


async def claim(
    database_url: str, repository: str, owner: str, lease_seconds: int
) -> dict[str, object] | None:
    async with (
        asyncpg.create_pool(database_url, min_size=1, max_size=1) as pool,
        pool.acquire() as conn,
        conn.transaction(),
    ):
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
                              priority_rank, project_id, lease_expires_at
                    """,
            repository,
            owner,
            lease_seconds,
        )
    return dict(row) if row else None


async def reap(database_url: str) -> int:
    async with asyncpg.create_pool(database_url, min_size=1, max_size=1) as pool:
        return await pool.execute(
            """UPDATE triaged_ticket SET state = 'ready', lease_owner = NULL,
               lease_expires_at = NULL, updated_at = now()
               WHERE state = 'leased' AND lease_expires_at < now()"""
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--claim-owner")
    parser.add_argument("--lease-seconds", type=int, default=900)
    parser.add_argument("--reap", action="store_true")
    args = parser.parse_args()
    if args.reap:
        print(asyncio.run(reap(args.database_url)))
    count = asyncio.run(reconcile(args.database_url, github_tickets(args.repository)))
    print(json.dumps({"reconciled": count}))
    if args.claim_owner:
        claimed = asyncio.run(
            claim(args.database_url, args.repository, args.claim_owner, args.lease_seconds)
        )
        print(json.dumps({"claimed": claimed}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
