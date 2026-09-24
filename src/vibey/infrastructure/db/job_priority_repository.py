# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed queue priority (ADR-0054): bump, un-bump, refuse, and list.

Every write is one transaction that (1) finds the closure the change can reach --
the target's dependencies for a bump, its dependents for an un-bump -- (2) locks
those rows `FOR UPDATE` in id order and reads their state only after the locks are
held, (3) asks the pure domain planner what to move, (4) writes `job.bump_seq`, and
(5) appends the ledger event on the same connection. A worker's claim takes its row
`FOR UPDATE SKIP LOCKED`, so while a bump holds a row the claim passes over it and
takes the next; a bump that meets a row a claim holds waits for the claim to commit,
then sees the job running and moves it without touching the lease.

Dependencies are written once, at enqueue, and never change, so the closure found
before the locks is the closure that holds once they are taken.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import QueueEntry
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import NotReorderable, UnknownJob
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.interfaces.queue_priority_interface import (
    BumpPlannerInterface,
    UnbumpPlannerInterface,
)
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import PHASE_PARSER, Phase, UnrecognizedPhase
from vibey.domain.queue_priority import (
    BUMP_PLANNER,
    UNBUMP_PLANNER,
    MovedJob,
    PriorityAction,
    PriorityChange,
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

_DEPENDENCY_CLOSURE: Final = """
WITH RECURSIVE closure(id) AS (
    SELECT $1::uuid
  UNION
    SELECT d.depends_on_job_id FROM job_dependency d JOIN closure c ON d.job_id = c.id
)
SELECT id FROM closure
"""

_DEPENDENT_CLOSURE: Final = """
WITH RECURSIVE closure(id) AS (
    SELECT $1::uuid
  UNION
    SELECT d.job_id FROM job_dependency d JOIN closure c ON d.depends_on_job_id = c.id
)
SELECT id FROM closure
"""

# Locked in id order, so two changes over overlapping closures take their locks in
# the same order and one waits for the other instead of deadlocking.
_LOCK: Final = """
SELECT id, project_id, cycle, phase, state, priority, run_after, bump_seq
FROM job WHERE id = ANY($1::uuid[])
ORDER BY id
FOR UPDATE
"""

_EDGES: Final = """
SELECT job_id, depends_on_job_id FROM job_dependency WHERE job_id = ANY($1::uuid[])
"""

# Running work first, then waiting work in the claim's own order. The claim reads
# `bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC` too
# (job_repository.py); a job still waiting on a dependency is listed where it will
# stand once the dependency succeeds, with what it waits on beside it.
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
    """Turns a queue-priority change or refusal into its ledger draft.

    The actor is the source that asked, carried in the payload; `engine_id` is None
    because no engine acted. A change the grant admitted is `trusted`; a refusal is
    `untrusted`, because the request came from outside the grant and everything in it
    is data to record, never instruction to follow (12.j, SD-01 §4).
    """

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def changed(
        self,
        change: PriorityChange,
        *,
        project_id: UUID,
        cycle: int,
        phase: Phase,
        at: datetime,
    ) -> LedgerEventDraft:
        kind = (
            EventKind.JOB_PRIORITY_UNBUMPED
            if change.action is PriorityAction.UNBUMP
            else EventKind.JOB_PRIORITY_BUMPED
        )
        payload: dict[str, object] = {
            "action": change.action.value,
            "source": change.source,
            "target": str(change.target),
            "moved": [
                {"job_id": str(m.job_id), "bump_seq": m.bump_seq, "previous": m.previous}
                for m in change.moved
            ],
            "kept": [str(job_id) for job_id in change.kept],
            "blocked_by": [str(job_id) for job_id in change.blocked_by],
        }
        return self._draft(
            project_id, cycle, phase, kind, change.target, Provenance.TRUSTED, at, payload
        )

    def refused(self, refusal: PriorityRefusal, *, at: datetime) -> LedgerEventDraft:
        payload: dict[str, object] = {
            "action": refusal.action.value,
            "source": refusal.source,
            "target": str(refusal.job_id) if refusal.job_id is not None else None,
            "reason": refusal.reason,
        }
        return self._draft(
            refusal.project_id,
            refusal.cycle,
            refusal.phase,
            EventKind.JOB_PRIORITY_REFUSED,
            refusal.job_id,
            Provenance.UNTRUSTED,
            at,
            payload,
        )

    def _draft(
        self,
        project_id: UUID,
        cycle: int,
        phase: Phase,
        kind: EventKind,
        job_id: UUID | None,
        provenance: Provenance,
        at: datetime,
        payload: dict[str, object],
    ) -> LedgerEventDraft:
        return LedgerEventDraft(
            project_id=project_id,
            cycle=cycle,
            phase=phase,
            kind=kind,
            engine_id=None,
            job_id=job_id,
            causation_id=None,
            correlation_id=self._correlation.for_project(project_id).value,
            provenance=provenance,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )


PRIORITY_EVENT_DRAFTS: Final[PriorityEventDraftBuilderInterface] = PriorityEventDraftBuilder()
"""The builder every priority write shares. Stateless, so one instance serves."""


class PostgresJobPriorityStore:
    """Reorders a project's queue atomically with its ledger record (ADR-0054)."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        bumps: BumpPlannerInterface = BUMP_PLANNER,
        unbumps: UnbumpPlannerInterface = UNBUMP_PLANNER,
        drafts: PriorityEventDraftBuilderInterface = PRIORITY_EVENT_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: JobRowMapperInterface = JOB_ROWS,
        phases: StoredValueParserInterface[Phase, UnrecognizedPhase] = PHASE_PARSER,
    ) -> None:
        self._pool = pool
        self._bumps = bumps
        self._unbumps = unbumps
        self._drafts = drafts
        self._appender = appender
        self._rows = rows
        self._phases = phases

    async def bump(
        self,
        job_id: UUID,
        *,
        source: str,
        at: datetime,
        action: PriorityAction = PriorityAction.BUMP,
    ) -> PriorityChange:
        async with self._pool.acquire() as conn, conn.transaction():
            snapshot, locked = await self._lock(conn, _DEPENDENCY_CLOSURE, job_id)
            phase = self._phase(job_id, locked[job_id])
            plan = self._bumps.plan(job_id, snapshot)
            moved: list[MovedJob] = []
            for moving in plan.moved:
                seq = await conn.fetchval(
                    """UPDATE job SET bump_seq = nextval('job_bump_seq'), updated_at = now()
                       WHERE id = $1 RETURNING bump_seq""",
                    moving,
                )
                moved.append(MovedJob(job_id=moving, bump_seq=seq, previous=None))
            change = PriorityChange(
                action=action,
                source=source,
                target=job_id,
                moved=tuple(moved),
                kept=plan.kept,
                blocked_by=plan.blocked_by,
            )
            await self._record(conn, change, locked[job_id], phase, at)
            return change

    async def unbump(self, job_id: UUID, *, source: str, at: datetime) -> PriorityChange:
        async with self._pool.acquire() as conn, conn.transaction():
            snapshot, locked = await self._lock(conn, _DEPENDENT_CLOSURE, job_id)
            phase = self._phase(job_id, locked[job_id])
            plan = self._unbumps.plan(job_id, snapshot)
            await conn.execute(
                "UPDATE job SET bump_seq = NULL, updated_at = now() WHERE id = ANY($1::uuid[])",
                list(plan.moved),
            )
            change = PriorityChange(
                action=PriorityAction.UNBUMP,
                source=source,
                target=job_id,
                moved=tuple(
                    MovedJob(job_id=moving, bump_seq=None, previous=snapshot[moving].bump_seq)
                    for moving in plan.moved
                ),
            )
            await self._record(conn, change, locked[job_id], phase, at)
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

    async def _lock(
        self, conn: _Connection, closure: str, job_id: UUID
    ) -> tuple[Mapping[UUID, QueuedJob], Mapping[UUID, asyncpg.Record]]:
        """Lock the closure and read it, target first to fail. Returns the planner's
        snapshot and the locked rows by id."""
        ids = [row["id"] for row in await conn.fetch(closure, job_id)]
        locked = {row["id"]: row for row in await conn.fetch(_LOCK, ids)}
        if job_id not in locked:
            raise UnknownJob(job_id)
        edges: dict[UUID, list[UUID]] = {}
        for edge in await conn.fetch(_EDGES, ids):
            edges.setdefault(edge["job_id"], []).append(edge["depends_on_job_id"])
        snapshot = {
            row_id: QueuedJob(
                id=row_id,
                state=self._rows.state(row["state"]),
                priority=row["priority"],
                run_after=row["run_after"],
                bump_seq=row["bump_seq"],
                depends_on=tuple(sorted(edges.get(row_id, ()))),
            )
            for row_id, row in locked.items()
        }
        return snapshot, locked

    def _phase(self, job_id: UUID, row: asyncpg.Record) -> Phase:
        """The phase the event is filed under. Writers stay strict (vibey#287): a job
        in a phase this vibey does not know is one it will not reorder or ledger."""
        phase = self._phases.parse(row["phase"])
        if not isinstance(phase, Phase):
            raise NotReorderable(
                job_id, f"its phase {phase.value!r} is one this vibey does not know"
            )
        return phase

    async def _record(
        self,
        conn: _Connection,
        change: PriorityChange,
        target: asyncpg.Record,
        phase: Phase,
        at: datetime,
    ) -> None:
        """Append the change's event -- only when something moved. A replay that
        moved nothing is not a second bump, and the ledger does not say it was."""
        if not change.changed:
            return
        draft = self._drafts.changed(
            change,
            project_id=target["project_id"],
            cycle=target["cycle"],
            phase=phase,
            at=at,
        )
        await self._appender.append(conn, draft)
