# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed project budgets: a project's caps changed with their history.

Every change is one transaction that:

1. locks the project's row `FOR NO KEY UPDATE`, so two changes to one project's caps
   never interleave and each reads the caps the other left. `NO KEY` because only
   `config` and `updated_at` change: the `KEY SHARE` an event or a job takes on the row
   through its foreign key is never blocked, so a running worker keeps writing its
   ledger while a cap changes;
2. reads the caps from the locked row's config through the brake's own parser, and asks
   the pure planner what the request changes;
3. writes only the changed keys -- a set cap as a JSON number, a cleared one removed, so
   an uncapped project's config is as if the cap had never been set -- and appends one
   `BudgetCapChanged` event per changed cap on the same connection.

A request that changes nothing writes nothing, so a replayed change is a no-op. The
application role holds `SELECT` and `UPDATE` on `project` and `INSERT` on the ledger
(`ledger_guard.APP_ROLE_GRANTS`), which is everything this needs; the ledger stays
append-only, and a cap is never changed without its event.
"""

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.dto import CapChangeOutcome, ProjectRecord
from vibey.domain.budget_caps import CAP_CHANGE_PLANNER, CycleCaps
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.interfaces.budget_caps_interface import (
    CapChangeInterface,
    CapChangePlannerInterface,
    CapRequestInterface,
)
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase, StoredPhase
from vibey.infrastructure.db.interfaces import (
    BudgetCapDraftBuilderInterface,
    EventAppenderInterface,
    ProjectRowMapperInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.db.project_repository import PROJECT_ROWS
from vibey.infrastructure.engines.tailer import LedgerEventDraft

type CapsParser = Callable[[Mapping[str, object]], tuple[float | None, int | None]]
"""Reads `(max_dollars, max_turns)` from a project's config: the brake's own parser."""

_LOCK_PROJECT: Final = "SELECT * FROM project WHERE id = $1 FOR NO KEY UPDATE"

# Cleared keys removed, set keys merged in; nothing else in the config is touched.
_WRITE_CAPS: Final = """
UPDATE project
SET config = (config - $2::text[]) || $3::jsonb, updated_at = now()
WHERE id = $1
RETURNING *
"""


class BudgetCapDraftBuilder:
    """Turns one changed cap into its `BudgetCapChanged` ledger draft.

    Filed under the project's cycle and phase as its locked row holds them, with no
    engine and no job: a person changed the cap, through vibey's own command. `trusted`
    for that reason -- the `by` it carries is a label the caller chose, and `account`,
    the operating system's name for who ran the command, is recorded beside it.
    """

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def build(
        self,
        project: ProjectRecord,
        change: CapChangeInterface,
        *,
        by: str,
        account: str,
        at: datetime,
    ) -> LedgerEventDraft:
        phase = self._recordable(project.project_id, project.phase)
        payload = change.payload(by=by, account=account)
        return LedgerEventDraft(
            project_id=project.project_id,
            cycle=project.cycle,
            phase=phase,
            kind=EventKind.BUDGET_CAP_CHANGED,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=self._correlation.for_project(project.project_id).value,
            provenance=Provenance.TRUSTED,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )

    @staticmethod
    def _recordable(project_id: UUID, phase: StoredPhase) -> Phase:
        """The phase to file a change under. Writers stay strict (vibey#287): nothing
        is recorded under a phase this vibey cannot vouch for, so the change is refused
        and the transaction that wrote the config rolls back with it."""
        if not isinstance(phase, Phase):
            raise WrongPhase(
                f"project {project_id} is in phase {phase.value!r}, which this vibey does "
                "not know; it will not record a budget change there"
            )
        return phase


BUDGET_CAP_DRAFTS: Final[BudgetCapDraftBuilderInterface] = BudgetCapDraftBuilder()
"""The builder every cap change shares. Stateless, so one instance serves."""


class PostgresProjectBudgetStore:
    """Changes a project's caps atomically with their ledger record. Built only inside
    `bootstrap.build_app`, and handed only to the budget service."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        planner: CapChangePlannerInterface = CAP_CHANGE_PLANNER,
        caps: CapsParser = LedgerBudgetSource.caps_from_config,
        drafts: BudgetCapDraftBuilderInterface = BUDGET_CAP_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
        rows: ProjectRowMapperInterface = PROJECT_ROWS,
    ) -> None:
        self._pool = pool
        self._planner = planner
        self._caps = caps
        self._drafts = drafts
        self._appender = appender
        self._rows = rows

    async def apply(
        self,
        project_id: UUID,
        request: CapRequestInterface,
        *,
        by: str,
        account: str,
        at: datetime,
    ) -> CapChangeOutcome:
        async with self._pool.acquire() as conn, conn.transaction():
            project = self._project(project_id, await conn.fetchrow(_LOCK_PROJECT, project_id))
            max_dollars, max_turns = self._caps(project.config)
            changes = self._planner.plan(CycleCaps(max_dollars, max_turns), request)
            if not changes:
                return CapChangeOutcome(project=project)
            cleared = [change.field.value for change in changes if change.new is None]
            written = {
                change.field.value: change.new for change in changes if change.new is not None
            }
            settled = self._project(
                project_id,
                await conn.fetchrow(_WRITE_CAPS, project_id, cleared, json.dumps(written)),
            )
            for change in changes:
                await self._appender.append(
                    conn, self._drafts.build(settled, change, by=by, account=account, at=at)
                )
            return CapChangeOutcome(project=settled, changes=changes)

    def _project(self, project_id: UUID, row: asyncpg.Record | None) -> ProjectRecord:
        if row is None:
            raise UnknownProject(f"unknown project {project_id}")
        return self._rows.to_record(row)
