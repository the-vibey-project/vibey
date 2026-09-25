# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed human gates (ADR-0009): raised by a parked job, answered once.

An answer is a compare-and-set on `answered_at IS NULL` in one transaction that:

1. writes the answer, who gave it and the id of the request that gave it -- only while
   the gate is still open, so of two answers racing for one gate exactly one lands;
2. appends one `GateAnswered` event on the same connection, so a gate is never answered
   without its record, and a refused or replayed answer writes none;
3. returns the gate's job to `ready` and notifies the workers.

When the gate was not open, nothing is written. The same request replayed with the same
answer is a no-op success (`GateAnswerOutcome.replayed`); any other answer is refused
with `GateAlreadyAnswered`, and a gate that does not exist with `UnknownGate`. The
application role holds `UPDATE` on `human_gate`, `SELECT` on `project` and `INSERT` on
the ledger (`ledger_guard.APP_ROLE_GRANTS`): everything this needs, and the ledger stays
append-only.
"""

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Final
from uuid import UUID, uuid4

import asyncpg

from vibey.application.dto import (
    GateAnswerOutcome,
    HumanGateRecord,
    HumanGateRequest,
    ProjectRecord,
)
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import GateAlreadyAnswered, UnknownGate, WrongPhase
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.job import QUEUE_GATE_KINDS
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase, StoredPhase
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    GateAnsweredDraftBuilderInterface,
    ProjectRowMapperInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

# Written only while the gate is open: the compare-and-set. Under READ COMMITTED a racing
# second UPDATE waits on the first's row lock, re-reads the row once it commits, finds
# `answered_at` set, and updates nothing.
_ANSWER_ONCE: Final = """
UPDATE human_gate SET
    answer = $2::jsonb, answered_at = now(), answered_by = $3, answer_request_id = $4
WHERE gate_id = $1 AND answered_at IS NULL
RETURNING *
"""

_PROJECT: Final = "SELECT * FROM project WHERE id = $1"


def _require(row: asyncpg.Record | None, *, context: str) -> asyncpg.Record:
    if row is None:
        raise LookupError(f"{context}: expected a row but got none")
    return row


def _row_to_record(row: asyncpg.Record) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=row["gate_id"],
        project_id=row["project_id"],
        job_id=row["job_id"],
        kind=row["kind"],
        prompt=row["prompt"],
        options=tuple(json.loads(row["options"])),
        default_answer=row["default_answer"],
        answer=json.loads(row["answer"]) if row["answer"] is not None else None,
        raised_at=row["raised_at"],
        timeout_at=row["timeout_at"],
        answered_at=row["answered_at"],
        answered_by=row["answered_by"],
        answer_request_id=row["answer_request_id"],
    )


class GateAnsweredDraftBuilder:
    """Turns one answered gate into its `GateAnswered` ledger draft.

    Filed under the project's cycle and phase as they stand when the answer lands, with
    no engine and no job of its own (the gate's job is in the payload): a person
    answered, through vibey's own command or a client of it. `trusted` for that reason --
    `by` is a label the caller chose, and `account`, the operating system's name for who
    ran the command, is recorded beside it.
    """

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def build(
        self,
        project: ProjectRecord,
        gate: HumanGateRecord,
        *,
        account: str | None,
        at: datetime,
    ) -> LedgerEventDraft:
        phase = self._recordable(project.project_id, project.phase)
        payload: dict[str, object] = {
            "gate_id": str(gate.gate_id),
            "gate_kind": gate.kind,
            "job_id": str(gate.job_id) if gate.job_id is not None else None,
            "request_id": gate.answer_request_id,
            "by": gate.answered_by,
            "account": account,
            "answer": dict(gate.answer or {}),
        }
        return LedgerEventDraft(
            project_id=gate.project_id,
            cycle=project.cycle,
            phase=phase,
            kind=EventKind.GATE_ANSWERED,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=self._correlation.for_project(gate.project_id).value,
            provenance=Provenance.TRUSTED,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )

    @staticmethod
    def _recordable(project_id: UUID, phase: StoredPhase) -> Phase:
        """The phase to file an answer under. Writers stay strict (vibey#287): nothing is
        recorded under a phase this vibey cannot vouch for, so the answer is refused and
        the transaction that wrote it rolls back with it."""
        if not isinstance(phase, Phase):
            raise WrongPhase(
                f"project {project_id} is in phase {phase.value!r}, which this vibey does "
                "not know; it will not record an answer there"
            )
        return phase


GATE_ANSWERED_DRAFTS: Final[GateAnsweredDraftBuilderInterface] = GateAnsweredDraftBuilder()
"""The builder every answer shares. Stateless, so one instance serves."""


class PostgresHumanGateRepository:
    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        drafts: GateAnsweredDraftBuilderInterface = GATE_ANSWERED_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: ProjectRowMapperInterface = PROJECT_ROWS,
    ) -> None:
        self._pool = pool
        self._drafts = drafts
        self._appender = appender
        self._rows = rows

    async def raise_gate(
        self, project_id: UUID, job_id: UUID | None, request: HumanGateRequest
    ) -> HumanGateRecord:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO human_gate (
                    project_id, job_id, kind, prompt, options, default_answer, timeout_at
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                RETURNING *
                """,
                project_id,
                job_id,
                request.kind,
                request.prompt,
                json.dumps(list(request.options)),
                request.default_answer,
                request.timeout_at,
            )
            row = _require(row, context="raise_gate insert")
            await conn.execute(f"NOTIFY vibey_gate_raised, '{row['gate_id']}'")
            return _row_to_record(row)

    async def answer(
        self,
        gate_id: UUID,
        *,
        answer: Mapping[str, object],
        answered_by: str,
        account: str | None = None,
        request_id: str | None = None,
    ) -> HumanGateRecord:
        outcome = await self.answer_once(
            gate_id,
            answer=answer,
            answered_by=answered_by,
            account=account,
            request_id=request_id if request_id is not None else str(uuid4()),
        )
        return outcome.record

    async def answer_once(
        self,
        gate_id: UUID,
        *,
        answer: Mapping[str, object],
        answered_by: str,
        account: str | None,
        request_id: str,
    ) -> GateAnswerOutcome:
        # Round-tripped through JSON, so the answer compared with a stored one is the
        # answer as stored: `(1, 2)` and `[1, 2]` are the same answer once written.
        given = json.loads(json.dumps(dict(answer)))
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                _ANSWER_ONCE, gate_id, json.dumps(given), answered_by, request_id
            )
            if row is None:
                stored = await conn.fetchrow("SELECT * FROM human_gate WHERE gate_id = $1", gate_id)
                return self._settled(gate_id, stored, given=given, request_id=request_id)
            gate = _row_to_record(row)
            await self._record(conn, gate, account=account, at=row["answered_at"])
            if gate.job_id is not None:
                await conn.execute(
                    """
                    UPDATE job SET state = 'ready', updated_at = now()
                    WHERE id = $1 AND state = 'awaiting_human'
                    """,
                    gate.job_id,
                )
                await conn.execute(f"NOTIFY vibey_job_ready, '{gate.project_id}'")
            return GateAnswerOutcome(record=gate)

    async def _record(
        self,
        conn: asyncpg.Connection,
        gate: HumanGateRecord,
        *,
        account: str | None,
        at: datetime,
    ) -> None:
        # The gate's foreign key holds the project row for as long as this transaction
        # holds the gate's, so the project is there to be read.
        project_row = _require(
            await conn.fetchrow(_PROJECT, gate.project_id),
            context=f"answer: no project {gate.project_id}",
        )
        project = self._rows.to_record(project_row)
        await self._appender.append(conn, self._drafts.build(project, gate, account=account, at=at))

    @staticmethod
    def _settled(
        gate_id: UUID,
        stored: asyncpg.Record | None,
        *,
        given: Mapping[str, object],
        request_id: str,
    ) -> GateAnswerOutcome:
        """The gate was not open: a replay of this request, or a refusal."""
        if stored is None:
            raise UnknownGate(f"no gate {gate_id}")
        gate = _row_to_record(stored)
        same_request = gate.answer_request_id == request_id
        if same_request and gate.answer == given:
            return GateAnswerOutcome(record=gate, replayed=True)
        raise GateAlreadyAnswered(
            gate_id,
            answered_by=gate.answered_by,
            answered_at=gate.answered_at,
            same_request=same_request,
        )

    async def get(self, gate_id: UUID) -> HumanGateRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM human_gate WHERE gate_id = $1", gate_id)
            return _row_to_record(row) if row is not None else None

    async def open_for_project(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM human_gate
                WHERE project_id = $1 AND answered_at IS NULL
                ORDER BY raised_at ASC, gate_id ASC
                """,
                project_id,
            )
            return tuple(_row_to_record(r) for r in rows)

    async def open_all(self) -> tuple[HumanGateRecord, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM human_gate
                WHERE answered_at IS NULL
                ORDER BY raised_at ASC, gate_id ASC
                """
            )
            return tuple(_row_to_record(r) for r in rows)

    async def latest_for_job(
        self, job_id: UUID, *, include_queue_gates: bool = False
    ) -> HumanGateRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM human_gate
                WHERE job_id = $1 AND ($2 OR kind <> ALL($3::text[]))
                ORDER BY raised_at DESC, gate_id DESC
                LIMIT 1
                """,
                job_id,
                include_queue_gates,
                sorted(QUEUE_GATE_KINDS),
            )
            return _row_to_record(row) if row is not None else None
