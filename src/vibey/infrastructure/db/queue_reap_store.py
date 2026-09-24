# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The PostgreSQL side of queue reaping (ADR-0056).

**Leases.** An expired lease is judged by `QueueReapPolicy` -- the same judgement the
broker's held deliveries get, so both backends reap identically. While attempts remain the
job goes back to `ready`, its attempt already counted by the claim that took it; that is
the reap vibey always did. Once its attempts are spent it is **parked** with a
`delivery_exhausted` gate instead: a job that kills its worker on every attempt never
reaches the worker's own failure path, so without this bound it was re-claimed forever --
the unbounded ladder ADR-0024 rules out, and the latent gap ADR-0044 §8 names. The park
refunds one attempt, exactly as the worker's own park does, so each answer buys one more
delivery.

Each reap is one transaction: the expired rows are locked (`FOR UPDATE SKIP LOCKED`, so
two reapers split the work instead of doubling it), judged against the database's own
`now()`, moved, and each move's `QueueReaped` event appended on the same connection. A
reap and its record never part, and a crash leaves neither.

A row whose phase this vibey does not know is left alone: a newer vibey wrote it and a
newer vibey reaps it (vibey#287), the same rule the claim follows.

**Ready work** that has been claimable for longer than the declared age is measured here
for the reaper to surface. **Dead letters** each become a `bus.dead_letter` job parked in
`awaiting_human`, a `bus_dead_lettered` gate, and a `QueueReaped` event -- in one
transaction, idempotent by the dead letter's identity, so a second pass over the same dead
letter changes nothing.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.bus_dead_letter_handler import BUS_DEAD_LETTER_GATE, BUS_DEAD_LETTER_KIND
from vibey.application.dto import HumanGateRequest
from vibey.application.interfaces.queue_reap import (
    BusDeadLetterGateInterface,
    DeliveryExhaustedGateInterface,
)
from vibey.application.queue_reaper import DELIVERY_EXHAUSTED_GATE
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.interfaces.queue_reap_interface import (
    QueueReapPolicyInterface,
    ReapThresholdsInterface,
)
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.queue_reap import (
    QUEUE_REAP_POLICY,
    DeadLetter,
    HeldWork,
    HolderState,
    QueueDepth,
    ReapAction,
    ReapThresholds,
    ReapVerdict,
)
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    ReapEventDraftBuilderInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.engines.tailer import LedgerEventDraft

type _Connection = asyncpg.pool.PoolConnectionProxy | asyncpg.Connection

KNOWN_PHASES: Final = tuple(phase.value for phase in Phase)

_EXPIRED: Final = """
SELECT id, project_id, cycle, phase, kind, attempts, max_attempts, lease_expires_at
FROM job
WHERE state = 'leased' AND lease_expires_at < now() AND phase::text = ANY($1::text[])
ORDER BY lease_expires_at, id
"""

_EXPIRED_LOCKED: Final = _EXPIRED + "FOR UPDATE SKIP LOCKED\n"

_REQUEUE: Final = """
UPDATE job SET state = 'ready', lease_owner = NULL, lease_expires_at = NULL, updated_at = now()
WHERE id = $1
"""

# Refunds one attempt, as `PostgresJobRepository.park` does: each answer buys exactly one
# more delivery (ADR-0044 §8).
_PARK_LEASED: Final = """
UPDATE job SET state = 'awaiting_human', lease_owner = NULL, lease_expires_at = NULL,
               attempts = greatest(attempts - 1, 0), updated_at = now()
WHERE id = $1
"""

_RAISE_GATE: Final = """
INSERT INTO human_gate (project_id, job_id, kind, prompt, options, default_answer, timeout_at)
VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
RETURNING gate_id
"""

# Claimable now: ready, due, every dependency succeeded, a phase this vibey knows -- the
# claim's own filter. Claimable since the latest of: when it became due, when the job last
# changed state, and when its last dependency succeeded.
_READY: Final = """
SELECT count(*) AS ready,
       min(greatest(
           j.run_after,
           j.updated_at,
           coalesce((SELECT max(p.updated_at) FROM job_dependency d
                     JOIN job p ON p.id = d.depends_on_job_id
                     WHERE d.job_id = j.id), j.run_after)
       )) AS since,
       now() AS observed_at
FROM job j
WHERE j.project_id = $1
  AND j.state = 'ready'
  AND j.run_after <= now()
  AND j.phase::text = ANY($2::text[])
  AND NOT EXISTS (
      SELECT 1 FROM job_dependency d
      JOIN job p ON p.id = d.depends_on_job_id
      WHERE d.job_id = j.id AND p.state <> 'succeeded'
  )
"""

_PROJECT: Final = "SELECT cycle, phase FROM project WHERE id = $1"

_PARK_DEAD_LETTER: Final = """
INSERT INTO job (project_id, cycle, phase, kind, state, idempotency_key, payload)
VALUES ($1, $2, $3, $4, 'awaiting_human', $5, $6::jsonb)
ON CONFLICT (project_id, idempotency_key) DO NOTHING
RETURNING id
"""


class ReapEventDraftBuilder:
    """Turns a verdict into its `QueueReaped` ledger draft.

    A lease or ready-work verdict is vibey's own measurement and is `trusted`. A dead
    letter's verdict carries the queue and reason its message's headers claimed, which a
    publisher can write, so it is `untrusted`: data to record, never instruction (SD-01 §4).
    """

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def draft(
        self,
        verdict: ReapVerdict,
        *,
        project_id: UUID,
        cycle: int,
        phase: Phase,
        job_id: UUID | None,
        at: datetime,
        provenance: Provenance = Provenance.TRUSTED,
    ) -> LedgerEventDraft:
        payload = verdict.payload()
        return LedgerEventDraft(
            project_id=project_id,
            cycle=cycle,
            phase=phase,
            kind=EventKind.QUEUE_REAPED,
            engine_id=None,
            job_id=job_id,
            causation_id=None,
            correlation_id=self._correlation.for_project(project_id).value,
            provenance=provenance,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )


REAP_EVENT_DRAFTS: Final[ReapEventDraftBuilderInterface] = ReapEventDraftBuilder()

DEFAULT_THRESHOLDS: Final = ReapThresholds()
"""The `[queue.reap]` defaults, for a store composed without a configuration."""


class PostgresQueueReapStore:
    """Reaps the job queue's leases, measures its ready work and parks dead letters,
    each write in one transaction with its ledger event."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        thresholds: ReapThresholdsInterface = DEFAULT_THRESHOLDS,
        policy: QueueReapPolicyInterface = QUEUE_REAP_POLICY,
        drafts: ReapEventDraftBuilderInterface = REAP_EVENT_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        exhausted_gate: DeliveryExhaustedGateInterface = DELIVERY_EXHAUSTED_GATE,
        dead_letter_gate: BusDeadLetterGateInterface = BUS_DEAD_LETTER_GATE,
    ) -> None:
        self._pool = pool
        self._thresholds = thresholds
        self._policy = policy
        self._drafts = drafts
        self._appender = appender
        self._exhausted_gate = exhausted_gate
        self._dead_letter_gate = dead_letter_gate

    async def preview_leases(self) -> tuple[ReapVerdict, ...]:
        async with self._pool.acquire() as conn:
            now = await conn.fetchval("SELECT now()")
            rows = await conn.fetch(_EXPIRED, list(KNOWN_PHASES))
        return tuple(verdict for row in rows if (verdict := self._judge(row, now)) is not None)

    async def reap_leases(self) -> tuple[ReapVerdict, ...]:
        reaped: list[ReapVerdict] = []
        async with self._pool.acquire() as conn, conn.transaction():
            now = await conn.fetchval("SELECT now()")
            for row in await conn.fetch(_EXPIRED_LOCKED, list(KNOWN_PHASES)):
                verdict = self._judge(row, now)
                if verdict is None:
                    continue
                if verdict.action is ReapAction.REQUEUE:
                    await conn.execute(_REQUEUE, row["id"])
                else:
                    await conn.execute(_PARK_LEASED, row["id"])
                    request = self._exhausted_gate.request(kind=row["kind"], verdict=verdict)
                    await self._raise_gate(conn, row["project_id"], row["id"], request)
                await self._appender.append(
                    conn,
                    self._drafts.draft(
                        verdict,
                        project_id=row["project_id"],
                        cycle=row["cycle"],
                        phase=Phase(row["phase"]),
                        job_id=row["id"],
                        at=now,
                    ),
                )
                reaped.append(verdict)
        return tuple(reaped)

    def _judge(self, row: asyncpg.Record, now: datetime) -> ReapVerdict | None:
        return self._policy.judge_held(
            HeldWork(
                subject=str(row["id"]),
                queue=f"job:{row['project_id']}",
                deadline_at=row["lease_expires_at"],
                attempts=row["attempts"],
                attempt_limit=row["max_attempts"],
                holder=HolderState.UNKNOWN,
            ),
            now=now,
            thresholds=self._thresholds,
        )

    async def ready_depths(self, project_id: UUID) -> tuple[QueueDepth, ...]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(_READY, project_id, list(KNOWN_PHASES))
        if row is None or not row["ready"]:
            return ()
        return (
            QueueDepth(
                queue=f"job:{project_id}",
                ready=row["ready"],
                unacked=0,
                consumers=None,
                oldest_ready_age_seconds=max(
                    0.0, (row["observed_at"] - row["since"]).total_seconds()
                ),
            ),
        )

    async def park_dead_letter(
        self, project_id: UUID, item: DeadLetter, verdict: ReapVerdict
    ) -> UUID | None:
        payload = self._dead_letter_payload(item)
        key = "bus.dead_letter:" + hashlib.sha256(item.identity.encode("utf-8")).hexdigest()
        async with self._project(project_id) as (conn, cycle, phase, now):
            job_id: UUID | None = await conn.fetchval(
                _PARK_DEAD_LETTER,
                project_id,
                cycle,
                phase.value,
                BUS_DEAD_LETTER_KIND,
                key,
                json.dumps(payload),
            )
            if job_id is None:
                return None
            await self._raise_gate(
                conn, project_id, job_id, self._dead_letter_gate.request(payload)
            )
            await self._appender.append(
                conn,
                self._drafts.draft(
                    verdict,
                    project_id=project_id,
                    cycle=cycle,
                    phase=phase,
                    job_id=job_id,
                    at=now,
                    provenance=Provenance.UNTRUSTED,
                ),
            )
            return job_id

    async def record(self, project_id: UUID, verdict: ReapVerdict) -> None:
        async with self._project(project_id) as (conn, cycle, phase, now):
            await self._appender.append(
                conn,
                self._drafts.draft(
                    verdict, project_id=project_id, cycle=cycle, phase=phase, job_id=None, at=now
                ),
            )

    @asynccontextmanager
    async def _project(
        self, project_id: UUID
    ) -> AsyncIterator[tuple[_Connection, int, Phase, datetime]]:
        """One transaction, and the project's current cycle and phase to file under."""
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(_PROJECT, project_id)
            if row is None:
                raise LookupError(f"no project {project_id} to record a reap under")
            now = await conn.fetchval("SELECT now()")
            yield conn, row["cycle"], Phase(row["phase"]), now

    async def _raise_gate(
        self, conn: _Connection, project_id: UUID, job_id: UUID, request: HumanGateRequest
    ) -> None:
        gate_id = await conn.fetchval(
            _RAISE_GATE,
            project_id,
            job_id,
            request.kind,
            request.prompt,
            json.dumps(list(request.options)),
            request.default_answer,
            request.timeout_at,
        )
        # The payload cannot be a bind parameter; gate_id is a UUID the insert returned.
        await conn.execute(f"NOTIFY vibey_gate_raised, '{gate_id}'")

    @staticmethod
    def _dead_letter_payload(item: DeadLetter) -> dict[str, object]:
        body = item.payload_object()
        payload: dict[str, object] = {
            "queue": item.queue,
            "origin_queue": item.origin_queue,
            "reason": item.reason,
            "identity": item.identity,
            "first_death_at": item.first_death_at,
            "truncated": item.truncated,
            "payload": body,
        }
        if body is None:
            # Kept as text only when it is not a replayable object, so a person can
            # still read what died.
            payload["body"] = item.body
        return payload
