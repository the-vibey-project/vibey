# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed JobRepository: the durable, crash-safe work queue.
Every method here is a thin, faithful translation of the SQL in
docs/plans/data-model.md section 3.4 -- no cleverness, so the queue's
correctness rests on Postgres's guarantees, not ours."""

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.domain.engine import EngineId
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.job import JOB_STATE_PARSER, JobState, StoredJobState, UnrecognizedJobState
from vibey.domain.phase import PHASE_PARSER, Phase, StoredPhase, UnrecognizedPhase
from vibey.infrastructure.db.interfaces import JobRowMapperInterface


class JobRowMapper:
    """Maps one `job` row to a `JobRecord`.

    Two readings, chosen at construction. The worker path is strict: `claim`, `get`
    and every other `PostgresJobRepository` read take `Phase(...)` and `JobState(...)`
    as they always did, so a row this vibey cannot vouch for fails loudly instead of
    being handed on. The claim additionally never selects such a row (its phase filter),
    so a worker is never given one. `vibey queue list` and the priority store read
    forward-compatibly (vibey#287): a value a newer vibey wrote comes back as its stored
    text, so one row this vibey predates cannot make the queue unreadable.
    """

    def __init__(
        self,
        *,
        lenient: bool,
        states: StoredValueParserInterface[JobState, UnrecognizedJobState] = JOB_STATE_PARSER,
        phases: StoredValueParserInterface[Phase, UnrecognizedPhase] = PHASE_PARSER,
    ) -> None:
        self._lenient = lenient
        self._states = states
        self._phases = phases

    def state(self, raw: str) -> StoredJobState:
        return self._states.parse(raw) if self._lenient else JobState(raw)

    def phase(self, raw: str) -> StoredPhase:
        return self._phases.parse(raw) if self._lenient else Phase(raw)

    def to_record(self, row: asyncpg.Record) -> JobRecord:
        return JobRecord(
            id=row["id"],
            project_id=row["project_id"],
            cycle=row["cycle"],
            phase=self.phase(row["phase"]),
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
            bump_seq=row["bump_seq"],
            bump_origin=row["bump_origin"],
        )


JOB_ROWS: Final[JobRowMapperInterface] = JobRowMapper(lenient=True)
"""The forward-compatible reading: `vibey queue list` and the priority store."""

STRICT_JOB_ROWS: Final[JobRowMapperInterface] = JobRowMapper(lenient=False)
"""The strict reading every `PostgresJobRepository` read -- the worker path -- takes."""

KNOWN_PHASES: Final = tuple(phase.value for phase in Phase)
"""The phases this vibey can run. The claim selects only these (vibey#287)."""


class PostgresJobRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def enqueue(self, request: EnqueueRequest) -> JobRecord:
        async with self._pool.acquire() as conn, conn.transaction():
            return await self._enqueue_on(conn, request, {})

    async def enqueue_batch(self, requests: Sequence[EnqueueRequest]) -> tuple[JobRecord, ...]:
        # One transaction for the lot: an exception part-way through -- a
        # key that resolves to nothing, a constraint, a dropped connection,
        # a killed worker -- rolls back every row the batch already wrote.
        async with self._pool.acquire() as conn, conn.transaction():
            enqueued: dict[tuple[UUID, str], UUID] = {}
            records: list[JobRecord] = []
            for request in requests:
                record = await self._enqueue_on(conn, request, enqueued)
                enqueued[(record.project_id, record.idempotency_key)] = record.id
                records.append(record)
            return tuple(records)

    async def _enqueue_on(
        self,
        conn: asyncpg.Connection,
        request: EnqueueRequest,
        enqueued: Mapping[tuple[UUID, str], UUID],
    ) -> JobRecord:
        """One enqueue inside the caller's transaction. `enqueued` holds the
        ids this transaction has already made, so `depends_on_keys` can name
        a job that is not visible outside it yet."""
        depends_on = [*request.depends_on]
        for key in request.depends_on_keys:
            depends_on.append(await self._job_id(conn, request.project_id, key, enqueued))

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
            return STRICT_JOB_ROWS.to_record(row)

        job_id = row["id"]
        for dep_id in depends_on:
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
        # UUID we generated/validated ourselves, never free text. Inside a
        # transaction it is delivered at commit (and a rolled-back batch
        # announces nothing), with duplicates in one transaction folded.
        await conn.execute(f"NOTIFY vibey_job_ready, '{request.project_id}'")
        return STRICT_JOB_ROWS.to_record(row)

    async def _job_id(
        self,
        conn: asyncpg.Connection,
        project_id: UUID,
        key: str,
        enqueued: Mapping[tuple[UUID, str], UUID],
    ) -> UUID:
        """The id of the job `key` names: made earlier in this transaction,
        or already committed. A key that names neither is a caller bug, and
        raising is what rolls the batch back instead of enqueueing a job with
        a dependency silently missing."""
        made = enqueued.get((project_id, key))
        if made is not None:
            return made
        existing: UUID | None = await conn.fetchval(
            "SELECT id FROM job WHERE project_id = $1 AND idempotency_key = $2",
            project_id,
            key,
        )
        if existing is None:
            raise LookupError(
                f"enqueue: depends_on_keys names {key!r}, which is neither an earlier "
                f"request of this batch nor an enqueued job (project_id={project_id})"
            )
        return existing

    async def list_for_cycle(
        self, project_id: UUID, *, cycle: int, kind: str
    ) -> tuple[JobRecord, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM job
                WHERE project_id = $1 AND cycle = $2 AND kind = $3
                ORDER BY created_at ASC, id ASC
                """,
                project_id,
                cycle,
                kind,
            )
            return tuple(STRICT_JOB_ROWS.to_record(row) for row in rows)

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
                      AND NOT EXISTS (
                          SELECT 1 FROM job_dependency d
                          JOIN job p ON p.id = d.depends_on_job_id
                          WHERE d.job_id = j.id AND p.state <> 'succeeded'
                      )
                    ORDER BY j.bump_seq ASC NULLS LAST, j.priority DESC,
                             j.run_after ASC, j.id ASC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING *
                """,
                owner,
                lease,
                project_id,
                list(KNOWN_PHASES),
            )
            return STRICT_JOB_ROWS.to_record(row) if row is not None else None

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

    async def queue_depth(self, project_id: UUID) -> Mapping[StoredJobState, int]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT state, count(*) as count FROM job WHERE project_id = $1 GROUP BY state",
                project_id,
            )
            counts: dict[StoredJobState, int] = {state: 0 for state in JobState}
            for row in rows:
                counts[JOB_STATE_PARSER.parse(str(row["state"]))] = int(row["count"])
            return counts

    async def get(self, job_id: UUID) -> JobRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM job WHERE id = $1", job_id)
            return STRICT_JOB_ROWS.to_record(row) if row is not None else None


def _rowcount(command_tag: str) -> int:
    # asyncpg command tags look like "UPDATE 3" or "INSERT 0 1".
    return int(command_tag.rsplit(" ", 1)[-1])
