# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed abandonment (`vibey abandon`): a project moved into abandoned with
everything it stops, in one transaction.

The transaction:

1. locks the project's row `FOR NO KEY UPDATE`, so two abandonments of one project
   serialise and the second reads the phase the first left. `NO KEY` because only
   `phase` and `updated_at` change: the `KEY SHARE` an event or a job takes on the row
   through its foreign key is never blocked, so a running worker keeps writing its
   ledger until its job is cancelled under it;
2. asks the pure policy (`domain/abandonment.py`) whether the phase machine allows the
   move. A project already abandoned is a no-op that writes nothing; a done project, or
   one in a phase with no edge to abandoned, is refused;
3. withdraws every open gate of the project: the row records the withdrawal as its
   answer, by whom and under a request id naming the abandonment, on the same
   compare-and-set `answered_at IS NULL` that `vibey answer` uses -- so of an answer
   and an abandonment racing for one gate exactly one lands, and a later answer is
   refused as a second one. Gates first, then jobs: `vibey answer` locks a gate and
   then its job, so taking them in the same order can never deadlock with it;
4. cancels every unsettled job -- ready, leased, awaiting a person or awaiting capacity
   -- and clears its lease, so a worker still running one finds its lease gone: its
   heartbeat, ack, nack or park matches no row, and nothing it reports revives the job;
5. moves the phase through the project repository's own guarded compare-and-set, whose
   `PhaseTransitioned` carries the reason, `by`, `account` and the ids of every job and
   gate it stopped, and appends one `GateWithdrawn` per withdrawn gate.

All of it is database time: `now()` is the transaction's start, so the move, its event,
every gate's `answered_at` and every cancelled job's `updated_at` are one instant. The
application role holds `UPDATE` on `project`, `job` and `human_gate` and `INSERT` on the
ledger (`ledger_guard.APP_ROLE_GRANTS`): everything this needs, and the ledger stays
append-only -- nothing here updates or deletes an event, and no row is deleted.
"""

import json
from collections.abc import Sequence
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import AbandonmentReport, HumanGateRecord, JobRecord, ProjectRecord
from vibey.domain.abandonment import ABANDONMENT_POLICY, AbandonmentVerdict
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import UnknownProject
from vibey.domain.interfaces.abandonment_interface import AbandonmentPolicyInterface
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase, PhaseState
from vibey.infrastructure.db.human_gate_repository import _row_to_record as gate_record
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    GateWithdrawnDraftBuilderInterface,
    JobRowMapperInterface,
    ProjectRowMapperInterface,
    ProjectTransitionOnConnectionInterface,
)
from vibey.infrastructure.db.job_repository import JOB_ROWS
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

_PROJECT: Final = "SELECT * FROM project WHERE id = $1"
_LOCK_PROJECT: Final = "SELECT * FROM project WHERE id = $1 FOR NO KEY UPDATE"

_UNSETTLED: Final = """
SELECT * FROM job
WHERE project_id = $1 AND state::text = ANY($2::text[])
ORDER BY created_at ASC, id ASC
"""
_LOCK_UNSETTLED: Final = _UNSETTLED + "FOR UPDATE"

_CANCEL: Final = """
UPDATE job SET
    state = 'cancelled', lease_owner = NULL, lease_expires_at = NULL, updated_at = now()
WHERE id = ANY($1::uuid[])
"""

_OPEN_GATES: Final = """
SELECT * FROM human_gate
WHERE project_id = $1 AND answered_at IS NULL
ORDER BY raised_at ASC, gate_id ASC
"""

# The compare-and-set `vibey answer` uses, for every open gate of the project at once.
_WITHDRAW: Final = """
UPDATE human_gate SET
    answer = $2::jsonb, answered_at = now(), answered_by = $3, answer_request_id = $4
WHERE project_id = $1 AND answered_at IS NULL
RETURNING *
"""


class GateWithdrawnDraftBuilder:
    """Turns one gate an abandonment closed into its `GateWithdrawn` ledger draft.

    Filed under abandoned -- the phase the same transaction moved the project into --
    and its cycle, with no engine and no job of its own (the gate's job is in the
    payload), at the transaction's own time. `trusted`: a person abandoned the project
    through vibey's own command; `by` is the label they chose and `account` the
    operating system's name for who ran it.
    """

    def __init__(
        self,
        policy: AbandonmentPolicyInterface = ABANDONMENT_POLICY,
        correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
    ) -> None:
        self._policy = policy
        self._correlation = correlation

    def build(
        self, settled: ProjectRecord, gate: HumanGateRecord, *, by: str, account: str
    ) -> LedgerEventDraft:
        payload = self._policy.withdrawal_payload(
            gate_id=gate.gate_id,
            gate_kind=gate.kind,
            job_id=gate.job_id,
            request_id=self._policy.request_id(settled.project_id),
            by=by,
            account=account,
        )
        return LedgerEventDraft(
            project_id=settled.project_id,
            cycle=settled.cycle,
            phase=Phase.ABANDONED,
            kind=EventKind.GATE_WITHDRAWN,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=self._correlation.for_project(settled.project_id).value,
            provenance=Provenance.TRUSTED,
            produced_at=settled.updated_at,
            payload=payload,
            digest=digest_event(payload),
        )


GATE_WITHDRAWN_DRAFTS: Final[GateWithdrawnDraftBuilderInterface] = GateWithdrawnDraftBuilder()
"""The builder every abandonment shares. Stateless, so one instance serves."""


class PostgresProjectAbandonmentStore:
    """Abandons a project atomically with everything it stops. Built only inside
    `bootstrap.build_app`, and handed only to the abandonment service."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        projects: ProjectTransitionOnConnectionInterface,
        policy: AbandonmentPolicyInterface = ABANDONMENT_POLICY,
        drafts: GateWithdrawnDraftBuilderInterface = GATE_WITHDRAWN_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: ProjectRowMapperInterface = PROJECT_ROWS,
        jobs: JobRowMapperInterface = JOB_ROWS,
    ) -> None:
        self._pool = pool
        self._projects = projects
        self._policy = policy
        self._drafts = drafts
        self._appender = appender
        self._rows = rows
        self._jobs = jobs

    async def preview(self, project_id: UUID) -> AbandonmentReport:
        async with self._pool.acquire() as conn:
            project = self._project(project_id, await conn.fetchrow(_PROJECT, project_id))
            if self._decide(project) is AbandonmentVerdict.ALREADY_ABANDONED:
                return self._unchanged(project)
            jobs = await conn.fetch(_UNSETTLED, project_id, self._states())
            gates = await conn.fetch(_OPEN_GATES, project_id)
            return AbandonmentReport(
                project=project,
                left=project.phase,
                already_abandoned=False,
                written=False,
                jobs=self._job_records(jobs),
                gates=tuple(gate_record(row) for row in gates),
            )

    async def abandon(
        self, project_id: UUID, *, reason: str, by: str, account: str
    ) -> AbandonmentReport:
        async with self._pool.acquire() as conn, conn.transaction():
            project = self._project(project_id, await conn.fetchrow(_LOCK_PROJECT, project_id))
            if self._decide(project) is AbandonmentVerdict.ALREADY_ABANDONED:
                return self._unchanged(project, reason=reason, by=by, account=account)
            # `decide` returned ABANDON, which the phase machine allows only from a phase
            # it knows, so this reads the stored phase back as its member and never fails.
            left = Phase(project.phase.value)
            withdrawn = sorted(
                (
                    gate_record(row)
                    for row in await conn.fetch(
                        _WITHDRAW,
                        project_id,
                        json.dumps(self._policy.withdrawn_answer()),
                        by,
                        self._policy.request_id(project_id),
                    )
                ),
                key=lambda gate: (gate.raised_at, gate.gate_id),
            )
            jobs = self._job_records(await conn.fetch(_LOCK_UNSETTLED, project_id, self._states()))
            await conn.execute(_CANCEL, [job.id for job in jobs])
            settled = await self._projects.transition_on(
                conn,
                project_id,
                expected=left,
                to=Phase.ABANDONED,
                guard=self._policy.guard,
                attribution=self._policy.transition_attribution(
                    reason=reason,
                    by=by,
                    account=account,
                    cancelled_jobs=[job.id for job in jobs],
                    withdrawn_gates=[gate.gate_id for gate in withdrawn],
                ),
            )
            for gate in withdrawn:
                await self._appender.append(
                    conn, self._drafts.build(settled, gate, by=by, account=account)
                )
        await self._projects.announce(settled, expected=left)
        return AbandonmentReport(
            project=settled,
            left=left,
            already_abandoned=False,
            written=True,
            jobs=jobs,
            gates=tuple(withdrawn),
            reason=reason,
            by=by,
            account=account,
        )

    def _decide(self, project: ProjectRecord) -> AbandonmentVerdict:
        return self._policy.decide(
            PhaseState(project.phase, project.cycle, project.max_cycles, project.updated_at)
        )

    def _states(self) -> list[str]:
        return sorted(self._policy.unsettled_states)

    def _job_records(self, rows: Sequence[asyncpg.Record]) -> tuple[JobRecord, ...]:
        return tuple(self._jobs.to_record(row) for row in rows)

    def _project(self, project_id: UUID, row: asyncpg.Record | None) -> ProjectRecord:
        if row is None:
            raise UnknownProject(f"unknown project {project_id}")
        return self._rows.to_record(row)

    @staticmethod
    def _unchanged(
        project: ProjectRecord,
        *,
        reason: str | None = None,
        by: str | None = None,
        account: str | None = None,
    ) -> AbandonmentReport:
        return AbandonmentReport(
            project=project,
            left=project.phase,
            already_abandoned=True,
            written=False,
            reason=reason,
            by=by,
            account=account,
        )
