# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed queue priority (ADR-0054): bump, un-bump, refuse, and list.

Every change is one transaction that:

1. takes a transaction-scoped advisory lock on the project, so two reorders of one
   project never interleave -- an un-bump's "does any other bumped job still need this?"
   is then a question about a queue nobody else is reordering;
2. finds the rows the change can reach -- a bump's dependency closure, which stops at
   finished rows; an un-bump's bumped jobs -- and locks them `FOR NO KEY UPDATE` in id
   order. `NO KEY` because only `bump_seq` and `bump_named` change: an enqueue naming one
   of these jobs as a dependency takes `KEY SHARE` on it, which this lock never blocks;
3. reads each row's state only once its lock is held, so a row that finished while the
   closure was being found is judged as finished;
4. asks the pure planner what to move, writes it, and appends the request's event on
   the same connection -- whether it moved something or nothing.

A worker's claim takes its row `FOR UPDATE SKIP LOCKED`, which conflicts with these locks,
so the claim passes over a row a reorder holds and takes the next. A reorder that meets a
row a claim holds waits for the claim to commit, then sees the job running and moves it
without touching the lease. Should the database still abort a reorder to break a lock
cycle -- with the reaper's multi-row update, say -- it surfaces as `ReorderConflict`, a
clean refusal the caller records, never a traceback: nothing moved, and a retry is safe.
"""

import hashlib
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import QueueEntry
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import ReorderConflict, UnknownJob
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.interfaces.queue_priority_interface import (
    BumpPlannerInterface,
    UnbumpPlannerInterface,
)
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import (
    BUMP_PLANNER,
    FINISHED_STATES,
    UNBUMP_PLANNER,
    MovedJob,
    PriorityAction,
    PriorityChange,
    PriorityContext,
    PriorityRefusal,
    QueuedJob,
)
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    JobRowMapperInterface,
    PriorityEventDraftBuilderInterface,
)
from vibey.infrastructure.db.job_repository import JOB_ROWS
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.engines.tailer import LedgerEventDraft

type _Connection = asyncpg.pool.PoolConnectionProxy | asyncpg.Connection

# Every statement below is a constant with no interpolation: the finished states and the
# locked columns are spelled out in each, so nothing is ever built from a string.

# The target, scoped to the project the request named, and every job it depends on,
# transitively -- expanding only through unfinished rows: a finished dependency is read
# (the planner must know it succeeded, or that it never will) but not walked past.
_DEPENDENCY_CLOSURE: Final = """
WITH RECURSIVE closure(id) AS (
    SELECT j.id FROM job j WHERE j.id = $1 AND j.project_id = $2
  UNION
    SELECT d.depends_on_job_id
    FROM closure c
    JOIN job cj ON cj.id = c.id
    JOIN job_dependency d ON d.job_id = c.id
    WHERE cj.state NOT IN ('succeeded', 'failed', 'cancelled')
)
SELECT id FROM closure
"""

# Locked in id order, so overlapping reorders take their locks in the same order.
_LOCK_CLOSURE: Final = """
SELECT id, phase, state, priority, run_after, bump_seq, bump_named FROM job WHERE id = ANY($1::uuid[]) ORDER BY id FOR NO KEY UPDATE
"""

# An un-bump writes only the target and bumped jobs, so only those are locked.
_LOCK_BUMPED: Final = """
SELECT id, phase, state, priority, run_after, bump_seq, bump_named FROM job
WHERE project_id = $2
  AND (id = $1 OR (bump_seq IS NOT NULL AND state NOT IN ('succeeded', 'failed', 'cancelled')))
ORDER BY id
FOR NO KEY UPDATE
"""

_UNFINISHED: Final = """
SELECT id, phase, state, priority, run_after, bump_seq, bump_named FROM job
WHERE project_id = $1 AND state NOT IN ('succeeded', 'failed', 'cancelled') AND NOT (id = ANY($2::uuid[]))
"""

_EDGES: Final = """
SELECT job_id, depends_on_job_id FROM job_dependency
WHERE job_id = ANY($1::uuid[]) AND depends_on_job_id = ANY($1::uuid[])
"""

# Running work first, then waiting work in the claim's own order. The claim reads
# `bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC` too
# (job_repository.py); a job still waiting on a dependency is listed where it will stand
# once the dependency succeeds, with what it waits on beside it.
_QUEUE: Final = """
SELECT j.*,
       ARRAY(
           SELECT d.depends_on_job_id FROM job_dependency d
           JOIN job p ON p.id = d.depends_on_job_id
           WHERE d.job_id = j.id AND p.state <> 'succeeded'
           ORDER BY d.depends_on_job_id
       ) AS waiting_on
FROM job j
WHERE j.project_id = $1 AND j.state NOT IN ('succeeded', 'failed', 'cancelled')
ORDER BY (j.state = 'leased') DESC, j.bump_seq ASC NULLS LAST, j.priority DESC,
         j.run_after ASC, j.id ASC
"""


class PriorityEventDraftBuilder:
    """Turns a reorder request's outcome into its ledger draft.

    Every request is filed under the project's current cycle and phase, with who asked
    in the payload (`by`) and the job it named as the event's `job_id`. `engine_id` is
    None because no engine acted. An admitted request is `trusted`; a refused one is
    `untrusted`, because what it carried came from outside the grant and is data to
    record, never instruction to follow (12.j, SD-01 §4).
    """

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def changed(
        self, change: PriorityChange, *, context: PriorityContext, at: datetime
    ) -> LedgerEventDraft:
        kind = (
            EventKind.JOB_PRIORITY_UNBUMPED
            if change.action is PriorityAction.UNBUMP
            else EventKind.JOB_PRIORITY_BUMPED
        )
        payload: dict[str, object] = {
            "action": change.action.value,
            "by": change.requested_by,
            "target": str(change.target),
            "moved": [
                {"job_id": str(m.job_id), "bump_seq": m.bump_seq, "previous": m.previous}
                for m in change.moved
            ],
            "kept": [str(job_id) for job_id in change.kept],
            "named": change.named,
            "note": change.note,
        }
        if change.action is PriorityAction.UNBUMP:
            # Exactly the jobs this un-bump cleared: the target, and every pulled job the
            # remaining named jobs no longer need (ADR-0054 item 6).
            payload["removed"] = [str(m.job_id) for m in change.moved]
        return self._draft(context, kind, change.target, Provenance.TRUSTED, at, payload)

    def refused(self, refusal: PriorityRefusal, *, at: datetime) -> LedgerEventDraft:
        payload: dict[str, object] = {
            "action": refusal.action.value,
            "by": refusal.context.requested_by,
            "target": str(refusal.job_id) if refusal.job_id is not None else None,
            "reason": refusal.reason,
        }
        return self._draft(
            refusal.context,
            EventKind.JOB_PRIORITY_REFUSED,
            refusal.job_id,
            Provenance.UNTRUSTED,
            at,
            payload,
        )

    def _draft(
        self,
        context: PriorityContext,
        kind: EventKind,
        job_id: UUID | None,
        provenance: Provenance,
        at: datetime,
        payload: dict[str, object],
    ) -> LedgerEventDraft:
        return LedgerEventDraft(
            project_id=context.project_id,
            cycle=context.cycle,
            phase=context.phase,
            kind=kind,
            engine_id=None,
            job_id=job_id,
            causation_id=None,
            correlation_id=self._correlation.for_project(context.project_id).value,
            provenance=provenance,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )


PRIORITY_EVENT_DRAFTS: Final[PriorityEventDraftBuilderInterface] = PriorityEventDraftBuilder()
"""The builder every priority write shares. Stateless, so one instance serves."""


class PostgresJobPriorityStore:
    """Reorders a project's queue atomically with its ledger record (ADR-0054). Built
    only inside `bootstrap.build_app`, and handed only to the priority service."""

    LOCK_NAMESPACE: Final = "vibey.queue_priority"
    """Folded into the advisory-lock key so it can never collide with another use.
    Not `advisory_lock.PostgresAdvisoryLock`: that holds a session-scoped try-lock on a
    (project, cycle) integration branch; this needs a transaction-scoped lock that waits."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        bumps: BumpPlannerInterface = BUMP_PLANNER,
        unbumps: UnbumpPlannerInterface = UNBUMP_PLANNER,
        drafts: PriorityEventDraftBuilderInterface = PRIORITY_EVENT_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: JobRowMapperInterface = JOB_ROWS,
    ) -> None:
        self._pool = pool
        self._bumps = bumps
        self._unbumps = unbumps
        self._drafts = drafts
        self._appender = appender
        self._rows = rows

    async def bump(
        self,
        job_id: UUID,
        *,
        context: PriorityContext,
        at: datetime,
        action: PriorityAction = PriorityAction.BUMP,
    ) -> PriorityChange:
        async with self._reordering(job_id, context.project_id) as conn:
            ids = [
                row["id"]
                for row in await conn.fetch(_DEPENDENCY_CLOSURE, job_id, context.project_id)
            ]
            snapshot = await self._snapshot(conn, job_id, await conn.fetch(_LOCK_CLOSURE, ids))
            target = snapshot[job_id]
            plan = self._bumps.plan(job_id, snapshot, finished_ok=action is PriorityAction.ENQUEUE)
            moved: list[MovedJob] = []
            for moving in plan.moved:
                seq = await conn.fetchval(
                    """UPDATE job SET bump_seq = nextval('job_bump_seq'), bump_named = $2,
                              updated_at = now()
                       WHERE id = $1 RETURNING bump_seq""",
                    moving,
                    moving == job_id,
                )
                moved.append(MovedJob(job_id=moving, bump_seq=seq, previous=None))
            if plan.named:
                await conn.execute(
                    "UPDATE job SET bump_named = true, updated_at = now() WHERE id = $1", job_id
                )
            note = ""
            if not moved and not plan.named:
                note = (
                    f"it is {target.state.value}; nothing to move"
                    if target.state in FINISHED_STATES
                    else "it is already bumped; nothing moved"
                )
            change = PriorityChange(
                action=action,
                requested_by=context.requested_by,
                target=job_id,
                moved=tuple(moved),
                kept=plan.kept,
                named=plan.named,
                note=note,
            )
            await self._appender.append(conn, self._drafts.changed(change, context=context, at=at))
            return change

    async def unbump(
        self, job_id: UUID, *, context: PriorityContext, at: datetime
    ) -> PriorityChange:
        async with self._reordering(job_id, context.project_id) as conn:
            locked = await conn.fetch(_LOCK_BUMPED, job_id, context.project_id)
            held = [row["id"] for row in locked]
            rest = await conn.fetch(_UNFINISHED, context.project_id, held)
            snapshot = await self._snapshot(conn, job_id, [*locked, *rest])
            plan = self._unbumps.plan(job_id, snapshot)
            await conn.execute(
                """UPDATE job SET bump_seq = NULL, bump_named = false, updated_at = now()
                   WHERE id = ANY($1::uuid[])""",
                list(plan.moved),
            )
            change = PriorityChange(
                action=PriorityAction.UNBUMP,
                requested_by=context.requested_by,
                target=job_id,
                moved=tuple(
                    MovedJob(job_id=moving, bump_seq=None, previous=snapshot[moving].bump_seq)
                    for moving in plan.moved
                ),
                note="" if plan.moved else "it is not bumped; nothing moved",
            )
            await self._appender.append(conn, self._drafts.changed(change, context=context, at=at))
            return change

    async def refuse(self, refusal: PriorityRefusal, *, at: datetime) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            await self._appender.append(conn, self._drafts.refused(refusal, at=at))

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(_QUEUE, project_id)
        return tuple(
            QueueEntry(job=self._rows.to_record(row), waiting_on=tuple(row["waiting_on"]))
            for row in rows
        )

    @asynccontextmanager
    async def _reordering(self, job_id: UUID, project_id: UUID) -> AsyncIterator[_Connection]:
        """One reorder's transaction, serialised per project, with a lock cycle the
        database broke by aborting this request turned into `ReorderConflict`."""
        try:
            async with self._pool.acquire() as conn, conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock($1)", self._key(project_id))
                yield conn
        except asyncpg.exceptions.DeadlockDetectedError as deadlock:
            raise ReorderConflict(job_id) from deadlock

    def _key(self, project_id: UUID) -> int:
        digest = hashlib.sha256(f"{self.LOCK_NAMESPACE}:{project_id}".encode()).digest()
        return int.from_bytes(digest[:8], "big", signed=True)

    async def _snapshot(
        self, conn: _Connection, job_id: UUID, rows: Sequence[asyncpg.Record]
    ) -> Mapping[UUID, QueuedJob]:
        """The planner's view of `rows`, read after their locks were taken. A target the
        rows lack is not in the project the request named."""
        by_id = {row["id"]: row for row in rows}
        if job_id not in by_id:
            raise UnknownJob(job_id)
        edges: dict[UUID, list[UUID]] = {}
        for edge in await conn.fetch(_EDGES, list(by_id)):
            edges.setdefault(edge["job_id"], []).append(edge["depends_on_job_id"])
        return {
            row_id: QueuedJob(
                id=row_id,
                state=self._rows.state(row["state"]),
                priority=row["priority"],
                run_after=row["run_after"],
                bump_seq=row["bump_seq"],
                depends_on=tuple(sorted(edges.get(row_id, ()))),
                bump_named=row["bump_named"],
                phase_known=isinstance(self._rows.phase(row["phase"]), Phase),
            )
            for row_id, row in by_id.items()
        }
