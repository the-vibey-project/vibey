# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed hybrid engine dispatch (ADR-0079): what the queue and the ledger say,
and the three trusted events dispatch records.

**Slots in use** are the job table's own: unexpired leases (`lease_expires_at > now()`, the
database's clock) on rows with an assigned engine, across every project, because an
engine's slots belong to its backend -- one Ollama serves every project on the host. A
lease that expired is not a slot in use: its worker is gone and the reaper will requeue it,
which is what makes the count idempotent under replay.

**The cap** is counted from the ledger, never from process memory: the project's
`EngineOverflowSelected` events since the start of the UTC day. A reservation takes the
project's row `FOR NO KEY UPDATE`, counts again, and appends one more event only while
the count is below the cap -- all in one transaction, so two workers can never both take
the last overflow, and a restart forgets nothing. (`NO KEY UPDATE`, as the ULTRA control
store explains, so it never blocks a running worker's ledger writes.)

**Holds** are recorded once per job and attempt, under the same lock, so the wait's start
survives the job leaving the queue and coming back. **Measurements** are appended under it
too, filed under the project's cycle and phase.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import JobRecord
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.engine import ENGINE_ID_PARSER, EngineId
from vibey.domain.engine_dispatch import LocalSession
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import EventAppenderInterface, ProjectRowMapperInterface
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

_LOCK_PROJECT: Final = "SELECT * FROM project WHERE id = $1 FOR NO KEY UPDATE"

_IN_FLIGHT: Final = """
SELECT assigned_engine, count(*) AS taken FROM job
WHERE state = 'leased' AND lease_expires_at > now()
  AND assigned_engine IS NOT NULL AND id <> $1
GROUP BY assigned_engine
"""

_WAIT_STARTED: Final = """
SELECT min(produced_at) FROM event
WHERE project_id = $1 AND kind = $2 AND job_id = $3 AND payload->>'attempt' = $4
"""

_COUNT_SINCE: Final = """
SELECT count(*) FROM event WHERE project_id = $1 AND kind = $2 AND produced_at >= $3
"""

_LATEST: Final = """
SELECT payload FROM event WHERE project_id = $1 AND kind = $2 ORDER BY seq DESC LIMIT 1
"""

_SESSIONS: Final = """
SELECT engine_id, min(produced_at) AS started_at, max(produced_at) AS ended_at
FROM event
WHERE project_id = $1 AND phase = $2::phase AND job_id IS NOT NULL
  AND engine_id = ANY($3::text[]) AND produced_at >= $4 AND produced_at < $5
GROUP BY job_id, engine_id
"""


class PostgresEngineDispatchStore:
    """Declared by `interfaces/engine_dispatch_store_interface.py`; the application's
    `EngineDispatchStorePort`."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: ProjectRowMapperInterface = PROJECT_ROWS,
        correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
    ) -> None:
        self._pool = pool
        self._appender = appender
        self._rows = rows
        self._correlation = correlation

    async def in_flight(self, *, excluding: UUID) -> Mapping[EngineId, int]:
        async with self._pool.acquire() as conn:
            found = await conn.fetch(_IN_FLIGHT, excluding)
        taken: dict[EngineId, int] = {}
        for row in found:
            # An engine a newer vibey assigned is not one this worker can count against.
            engine = ENGINE_ID_PARSER.known(str(row["assigned_engine"]))
            if engine is not None:
                taken[engine] = int(row["taken"])
        return taken

    async def slot_wait_started(
        self, project_id: UUID, job_id: UUID, attempt: int
    ) -> datetime | None:
        async with self._pool.acquire() as conn:
            started: datetime | None = await conn.fetchval(
                _WAIT_STARTED,
                project_id,
                EventKind.ENGINE_SLOT_WAIT_STARTED.value,
                job_id,
                str(attempt),
            )
            return started

    async def record_slot_wait(
        self, job: JobRecord, *, payload: Mapping[str, object], at: datetime
    ) -> datetime:
        phase = self._job_phase(job)
        async with self._pool.acquire() as conn, conn.transaction():
            await self._lock(conn, job.project_id)
            started: datetime | None = await conn.fetchval(
                _WAIT_STARTED,
                job.project_id,
                EventKind.ENGINE_SLOT_WAIT_STARTED.value,
                job.id,
                str(job.attempts),
            )
            if started is not None:
                return started
            await self._append(
                conn,
                job.project_id,
                cycle=job.cycle,
                phase=phase,
                kind=EventKind.ENGINE_SLOT_WAIT_STARTED,
                engine_id=None,
                job_id=job.id,
                payload=dict(payload),
                at=at,
            )
            return at

    async def paid_overflow_count(self, project_id: UUID, *, since: datetime) -> int:
        async with self._pool.acquire() as conn:
            return await self._count(conn, project_id, since)

    async def reserve_overflow(
        self,
        job: JobRecord,
        *,
        engine_id: EngineId,
        payload: Mapping[str, object],
        cap: int,
        since: datetime,
        at: datetime,
    ) -> bool:
        phase = self._job_phase(job)
        async with self._pool.acquire() as conn, conn.transaction():
            await self._lock(conn, job.project_id)
            today = await self._count(conn, job.project_id, since)
            if today >= cap:
                return False
            await self._append(
                conn,
                job.project_id,
                cycle=job.cycle,
                phase=phase,
                kind=EventKind.ENGINE_OVERFLOW_SELECTED,
                engine_id=engine_id,
                job_id=job.id,
                # The count this reservation was granted on, read under the lock: it
                # supersedes the planner's earlier reading.
                payload={
                    **payload,
                    "paid_overflow_today": today,
                    "cap_remaining": cap - today,
                    "cap_remaining_after": cap - today - 1,
                },
                at=at,
            )
            return True

    async def latest_measurement(self, project_id: UUID) -> Mapping[str, object] | None:
        async with self._pool.acquire() as conn:
            raw = await conn.fetchval(_LATEST, project_id, EventKind.ENGINE_DISPATCH_MEASURED.value)
        if raw is None:
            return None
        # Only `record_measurement` writes this kind, and it writes an object.
        payload: dict[str, object] = json.loads(raw)
        return payload

    async def local_sessions(
        self,
        project_id: UUID,
        engines: Sequence[EngineId],
        *,
        since: datetime,
        until: datetime,
    ) -> tuple[LocalSession, ...]:
        async with self._pool.acquire() as conn:
            found = await conn.fetch(
                _SESSIONS,
                project_id,
                Phase.BUILD.value,
                [engine.value for engine in engines],
                since,
                until,
            )
        return tuple(
            LocalSession(
                engine_id=EngineId(row["engine_id"]),
                started_at=row["started_at"],
                ended_at=row["ended_at"],
            )
            for row in found
        )

    async def record_measurement(
        self, project_id: UUID, *, payload: Mapping[str, object], at: datetime
    ) -> None:
        async with self._pool.acquire() as conn, conn.transaction():
            project = self._rows.to_record(await self._lock(conn, project_id))
            if not isinstance(project.phase, Phase):
                raise WrongPhase(
                    f"project {project_id} is in phase {project.phase.value!r}, which this "
                    "vibey does not know; it will not record a dispatch measurement there"
                )
            await self._append(
                conn,
                project_id,
                cycle=project.cycle,
                phase=project.phase,
                kind=EventKind.ENGINE_DISPATCH_MEASURED,
                engine_id=None,
                job_id=None,
                payload=dict(payload),
                at=at,
            )

    @staticmethod
    def _job_phase(job: JobRecord) -> Phase:
        if not isinstance(job.phase, Phase):
            raise WrongPhase(
                f"job {job.id} is in phase {job.phase.value!r}, which this vibey does not "
                "know; dispatch records nothing for it"
            )
        return job.phase

    @staticmethod
    async def _lock(
        conn: asyncpg.pool.PoolConnectionProxy | asyncpg.Connection, project_id: UUID
    ) -> asyncpg.Record:
        row = await conn.fetchrow(_LOCK_PROJECT, project_id)
        if row is None:
            raise UnknownProject(f"unknown project {project_id}")
        return row

    @staticmethod
    async def _count(
        conn: asyncpg.pool.PoolConnectionProxy | asyncpg.Connection,
        project_id: UUID,
        since: datetime,
    ) -> int:
        counted = await conn.fetchval(
            _COUNT_SINCE, project_id, EventKind.ENGINE_OVERFLOW_SELECTED.value, since
        )
        return int(counted)

    async def _append(
        self,
        conn: asyncpg.pool.PoolConnectionProxy | asyncpg.Connection,
        project_id: UUID,
        *,
        cycle: int,
        phase: Phase,
        kind: EventKind,
        engine_id: EngineId | None,
        job_id: UUID | None,
        payload: dict[str, object],
        at: datetime,
    ) -> None:
        await self._appender.append(
            conn,
            LedgerEventDraft(
                project_id=project_id,
                cycle=cycle,
                phase=phase,
                kind=kind,
                engine_id=engine_id,
                job_id=job_id,
                causation_id=None,
                correlation_id=self._correlation.for_project(project_id).value,
                provenance=Provenance.TRUSTED,
                produced_at=at,
                payload=payload,
                digest=digest_event(payload),
            ),
        )


__all__ = ["PostgresEngineDispatchStore"]
