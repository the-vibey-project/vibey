# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed JobRepository: the durable, crash-safe work queue.
Every method here is a thin, faithful translation of the SQL in
docs/plans/data-model.md section 3.4 -- no cleverness, so the queue's
correctness rests on Postgres's guarantees, not ours."""

import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.domain.engine import EngineId
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.job import JOB_STATE_PARSER, JobState, StoredJobState, UnrecognizedJobState
from vibey.domain.phase import PHASE_PARSER, Phase, UnrecognizedPhase
from vibey.infrastructure.db.interfaces import JobRowMapperInterface


class JobRowMapper:
    """Turns one `job` row into a `JobRecord`, one way for every reader.

    `phase` and `state` are Postgres enums a newer vibey widens with a migration,
    so both are read forward-compatibly (vibey#287): a value this vibey does not
    know comes back as its stored text, never a `ValueError`. The claim never
    hands a worker a job whose phase it does not know; `get`, `enqueue`'s
    read-back and `queue_depth` can still meet one, and must not crash on it.
    """

    def __init__(
        self,
        *,
        phases: StoredValueParserInterface[Phase, UnrecognizedPhase] = PHASE_PARSER,
        states: StoredValueParserInterface[JobState, UnrecognizedJobState] = JOB_STATE_PARSER,
    ) -> None:
        self._phases = phases
        self._states = states

    def state(self, raw: str) -> StoredJobState:
        """One stored `job.state`, read the way `to_record` reads it."""
        return self._states.parse(raw)

    def to_record(self, row: asyncpg.Record) -> JobRecord:
        return JobRecord(
            id=row["id"],
            project_id=row["project_id"],
            cycle=row["cycle"],
            phase=self._phases.parse(row["phase"]),
            kind=row["kind"],
            state=self.state(row["state"]),
            priority=row["priority"],
            work_item_id=row["work_item_id"],
            payload=json.loads(row["payload"]),
            requirement=json.loads(row["requirement"]),
            idempotency_key=row["idempotency_key"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            run_after=row["run_after"],
            lease_owner=row["lease_owner"],
            lease_expires_at=row["lease_expires_at"],
            assigned_engine=row["assigned_engine"],
            last_error=json.loads(row["last_error"]) if row["last_error"] is not None else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


JOB_ROWS: Final[JobRowMapperInterface] = JobRowMapper()
"""The one row mapper every reader of `job` shares. Stateless, so one instance serves."""


class PostgresJobRepository:
    """The queue. `phases` is the set of phases this worker claims jobs in, and
    whose projects it claims jobs from: by default every `Phase` this vibey knows
    (vibey#287). A job in a phase outside it -- one a newer vibey added -- or in a
    project that a newer vibey moved into such a phase is not claimed here; it
    waits, `ready`, for a worker that knows what the phase means. Narrowing the set
    confines a worker to part of the phase machine."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        rows: JobRowMapperInterface = JOB_ROWS,
        phases: frozenset[Phase] = frozenset(Phase),
    ) -> None:
        self._pool = pool
        self._rows = rows
        self._claimable_phases = sorted(phase.value for phase in phases)

    async def enqueue(self, request: EnqueueRequest) -> JobRecord:
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                INSERT INTO job (
                    project_id, cycle, phase, kind, priority, work_item_id,
                    payload, requirement, idempotency_key, max_attempts, run_after
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10,
                    COALESCE($11, now())
                )
                ON CONFLICT (project_id, idempotency_key) DO NOTHING
                RETURNING *
                """,
                request.project_id,
                request.cycle,
                request.phase.value,
                request.kind,
                request.priority,
                request.work_item_id,
                json.dumps(dict(request.payload)),
                json.dumps(dict(request.requirement)),
                request.idempotency_key,
                request.max_attempts,
                request.run_after,
            )

            if row is None:
                row = await conn.fetchrow(
                    "SELECT * FROM job WHERE project_id = $1 AND idempotency_key = $2",
                    request.project_id,
                    request.idempotency_key,
                )
                if row is None:
                    raise LookupError(
                        "enqueue: conflicting idempotency key but no existing row found "
                        f"(project_id={request.project_id}, key={request.idempotency_key!r})"
                    )
                return self._rows.to_record(row)

            job_id = row["id"]
            for dep_id in request.depends_on:
                await conn.execute(
                    """
                    INSERT INTO job_dependency (job_id, depends_on_job_id)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    job_id,
                    dep_id,
                )

            # NOTIFY's payload cannot be a bind parameter; project_id is a
            # UUID we generated/validated ourselves, never free text.
            await conn.execute(f"NOTIFY vibey_job_ready, '{request.project_id}'")
            return self._rows.to_record(row)

    async def claim(self, project_id: UUID, *, owner: str, lease: timedelta) -> JobRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE job SET
                    state            = 'leased',
                    lease_owner      = $1,
                    lease_expires_at = now() + $2::interval,
                    attempts         = attempts + 1,
                    updated_at       = now()
                WHERE id = (
                    SELECT j.id FROM job j
                    WHERE j.state = 'ready'
                      AND j.run_after <= now()
                      AND j.project_id = $3
                      AND j.phase::text = ANY($4::text[])
                      AND EXISTS (
                          SELECT 1 FROM project pr
                          WHERE pr.id = j.project_id AND pr.phase::text = ANY($4::text[])
                      )
                      AND NOT EXISTS (
                          SELECT 1 FROM job_dependency d
                          JOIN job p ON p.id = d.depends_on_job_id
                          WHERE d.job_id = j.id AND p.state <> 'succeeded'
                      )
                    ORDER BY j.priority DESC, j.run_after ASC, j.id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
                """,
                owner,
                lease,
                project_id,
                self._claimable_phases,
            )
            return self._rows.to_record(row) if row is not None else None

    async def heartbeat(self, job_id: UUID, *, owner: str, lease: timedelta) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET lease_expires_at = now() + $2::interval
                WHERE id = $1 AND lease_owner = $3 AND state = 'leased'
                """,
                job_id,
                lease,
                owner,
            )
            return _rowcount(result) == 1

    async def ack(self, job_id: UUID, *, owner: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET
                    state = 'succeeded', lease_owner = NULL,
                    lease_expires_at = NULL, updated_at = now()
                WHERE id = $1 AND lease_owner = $2
                """,
                job_id,
                owner,
            )
            return _rowcount(result) == 1

    async def nack(self, job_id: UUID, *, owner: str, error: Mapping[str, object]) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET
                    state = (CASE WHEN attempts >= max_attempts
                             THEN 'failed' ELSE 'ready' END)::job_state,
                    lease_owner      = NULL,
                    lease_expires_at = NULL,
                    run_after        = now() + (least(power(2, attempts) * interval '2 seconds',
                                                      interval '15 minutes') * random()),
                    last_error       = $3::jsonb,
                    updated_at       = now()
                WHERE id = $1 AND lease_owner = $2
                """,
                job_id,
                owner,
                json.dumps(dict(error)),
            )
            return _rowcount(result) == 1

    async def park(self, job_id: UUID, *, owner: str) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET
                    state = 'awaiting_human', lease_owner = NULL,
                    lease_expires_at = NULL,
                    attempts = greatest(attempts - 1, 0),
                    updated_at = now()
                WHERE id = $1 AND lease_owner = $2
                """,
                job_id,
                owner,
            )
            return _rowcount(result) == 1

    async def grant_attempts(self, job_id: UUID, *, owner: str, max_attempts: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET max_attempts = $3, updated_at = now()
                WHERE id = $1 AND lease_owner = $2 AND max_attempts < $3
                """,
                job_id,
                owner,
                max_attempts,
            )
            return _rowcount(result) == 1

    async def defer(
        self,
        job_id: UUID,
        *,
        owner: str,
        retry_at: datetime,
        error: Mapping[str, object],
    ) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET
                    state = 'ready', lease_owner = NULL, lease_expires_at = NULL,
                    attempts = greatest(attempts - 1, 0), run_after = $3,
                    last_error = $4::jsonb, updated_at = now()
                WHERE id = $1 AND lease_owner = $2 AND state = 'leased'
                """,
                job_id,
                owner,
                retry_at,
                json.dumps(dict(error)),
            )
            return _rowcount(result) == 1

    async def reap(self) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET
                    state='ready', lease_owner=NULL, lease_expires_at=NULL, updated_at=now()
                WHERE state='leased' AND lease_expires_at < now()
                """
            )
            return _rowcount(result)

    async def assign_engine(self, job_id: UUID, *, owner: str, engine_id: EngineId) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job SET assigned_engine = $3, updated_at = now()
                WHERE id = $1 AND lease_owner = $2 AND state = 'leased'
                """,
                job_id,
                owner,
                engine_id.value,
            )
            return _rowcount(result) == 1

    async def count_unsettled(
        self, project_id: UUID, *, cycle: int, phase: Phase, exclude: UUID | None = None
    ) -> int:
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT count(*) FROM job
                WHERE project_id = $1 AND cycle = $2 AND phase = $3
                  AND state NOT IN ('succeeded', 'failed', 'cancelled')
                  AND ($4::uuid IS NULL OR id <> $4)
                """,
                project_id,
                cycle,
                phase.value,
                exclude,
            )
            return int(count)

    async def queue_depth(self, project_id: UUID) -> dict[StoredJobState, int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT state, count(*) as count FROM job WHERE project_id = $1 GROUP BY state",
                project_id,
            )
            counts: dict[StoredJobState, int] = dict.fromkeys(JobState, 0)
            for row in rows:
                counts[self._rows.state(row["state"])] = row["count"]
            return counts

    async def get(self, job_id: UUID) -> JobRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM job WHERE id = $1", job_id)
            return self._rows.to_record(row) if row is not None else None


def _rowcount(command_tag: str) -> int:
    # asyncpg command tags look like "UPDATE 3" or "INSERT 0 1".
    return int(command_tag.rsplit(" ", 1)[-1])
