# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every read and every change of a project's budget takes (`vibey budget`).

A budget is read the way the brake reads it, never as a second opinion: the caps
through `LedgerBudgetSource.caps_from_config`, the spend through
`LedgerBudgetSource.current`, over the project's own ledger. That ledger is read once
per project, and the one read gives both the spend and the history of the caps.

A change is checked before anything is written -- a value that is not a cap, a request
that names no cap, a label that cannot be recorded -- and refused whole. The store then
writes the config and appends one `BudgetCapChanged` event per changed cap, in one
transaction. Who changed it is recorded twice: `by`, the name the caller gave (the
account's own when it gave none), and `account`, the operating system's name for the
account that ran the command. `by` is a label for the record, not an authority, and
nothing here admits or refuses on it: whoever can run vibey against this database can
already write a project's config, as `vibey new` does. The record is what makes every
change answerable.
"""

from collections.abc import Iterable
from typing import Final
from uuid import UUID

from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.dto import BudgetChange, ProjectBudget, ProjectRecord
from vibey.application.interfaces import (
    CallerIdentity,
    Clock,
    LedgerReader,
    OpenGateReader,
    ProjectBudgetStore,
    ProjectReader,
)
from vibey.domain.budget_caps import BUDGET_CAP_HISTORY, CAP_CHANGE_PLANNER, CapField
from vibey.domain.errors import UnknownProject
from vibey.domain.interfaces.budget_caps_interface import (
    BudgetCapHistoryInterface,
    CapChangePlannerInterface,
    CapRequestInterface,
)
from vibey.domain.interfaces.phase_timing_interface import LedgerSpendRuleInterface
from vibey.domain.ledger import LedgerEvent
from vibey.domain.phase_timing import LEDGER_SPEND_RULE

BUDGET_GATE_KIND: Final = "budget_exhausted"
"""The kind of gate the brake parks a BUILD session on (`build_implement_handler.py`)."""


class LedgerSnapshot:
    """One read of a project's ledger, handed to every reader that needs it, so the
    spend and the history of a budget come from the same events.

    Declared by `interfaces/ledger.py::LedgerReader`."""

    def __init__(self, events: tuple[LedgerEvent, ...]) -> None:
        self._events = events

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return self._events


class ProjectBudgetService:
    """Declared by `interfaces/project_budget.py::ProjectBudgetServiceInterface`."""

    def __init__(
        self,
        *,
        projects: ProjectReader,
        ledger: LedgerReader,
        store: ProjectBudgetStore,
        gates: OpenGateReader,
        caller: CallerIdentity,
        clock: Clock,
        planner: CapChangePlannerInterface = CAP_CHANGE_PLANNER,
        history: BudgetCapHistoryInterface = BUDGET_CAP_HISTORY,
        spend_rule: LedgerSpendRuleInterface = LEDGER_SPEND_RULE,
    ) -> None:
        self._projects = projects
        self._ledger = ledger
        self._store = store
        self._gates = gates
        self._caller = caller
        self._clock = clock
        self._planner = planner
        self._history = history
        self._spend_rule = spend_rule

    async def show(self, project_id: UUID) -> ProjectBudget:
        project = await self._projects.get(project_id)
        if project is None:
            raise UnknownProject(f"unknown project {project_id}")
        return await self._budget(project)

    async def show_all(self) -> tuple[ProjectBudget, ...]:
        return tuple([await self._budget(project) for project in await self._projects.list_all()])

    async def set_caps(
        self,
        project_id: UUID,
        *,
        max_dollars: float | None = None,
        max_turns: int | None = None,
        by: str | None = None,
    ) -> BudgetChange:
        request = self._planner.setting(max_dollars=max_dollars, max_turns=max_turns)
        return await self._change(project_id, request, by)

    async def clear_caps(
        self, project_id: UUID, caps: Iterable[CapField], *, by: str | None = None
    ) -> BudgetChange:
        request = self._planner.clearing(caps)
        return await self._change(project_id, request, by)

    async def _change(
        self, project_id: UUID, request: CapRequestInterface, label: str | None
    ) -> BudgetChange:
        account = self._caller.current().name
        by = self._planner.actor(label, account=account)
        outcome = await self._store.apply(
            project_id, request, by=by, account=account, at=self._clock.now()
        )
        parked = tuple(
            gate
            for gate in await self._gates.open_for_project(project_id)
            if gate.kind == BUDGET_GATE_KIND
        )
        return BudgetChange(
            after=await self._budget(outcome.project),
            by=by,
            changes=outcome.changes,
            parked=parked,
        )

    async def _budget(self, project: ProjectRecord) -> ProjectBudget:
        events = await self._ledger.all_for_project(project.project_id)
        max_dollars, max_turns = LedgerBudgetSource.caps_from_config(project.config)
        source = LedgerBudgetSource(
            LedgerSnapshot(events),
            max_dollars=max_dollars,
            max_turns=max_turns,
            spend_rule=self._spend_rule,
        )
        return ProjectBudget(
            project_id=project.project_id,
            name=project.name,
            cycle=project.cycle,
            budget=await source.current(project.project_id, project.cycle),
            history=self._history.entries(events),
        )
