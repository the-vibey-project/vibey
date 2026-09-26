# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Project budgets' seams (`vibey budget`): the store that changes a project's caps
atomically with their ledger record, the gates a changed cap waits on, and the one
service every entry point reads and changes a budget through.

Mirrors `vibey/application/project_budget.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import (
    BudgetChange,
    CapChangeOutcome,
    HumanGateRecord,
    ProjectBudget,
)
from vibey.domain.budget_caps import CapField
from vibey.domain.interfaces.budget_caps_interface import CapRequestInterface


@runtime_checkable
class ProjectBudgetStore(Protocol):
    """Changes one project's caps. Reached only through
    `ProjectBudgetServiceInterface`, which checks the request first."""

    async def apply(
        self,
        project_id: UUID,
        request: CapRequestInterface,
        *,
        by: str,
        account: str,
        at: datetime,
    ) -> CapChangeOutcome:
        """Locks the project's row, plans `request` against the caps its config holds,
        writes the new caps into the config and appends one `BudgetCapChanged` event per
        changed cap -- in ONE transaction, so a crash leaves the caps and their history
        as they were. A request that changes nothing writes nothing. Raises
        `UnknownProject` for no such project, and `WrongPhase` for a project in a phase
        this vibey does not know, under which it will not record anything."""
        ...


@runtime_checkable
class OpenGateReader(Protocol):
    """The gates a project is parked on."""

    async def open_for_project(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        """Gates raised for this project and not yet answered, oldest first."""
        ...


@runtime_checkable
class ProjectBudgetServiceInterface(Protocol):
    """Reads a project's budget the way the brake does, and changes its caps."""

    async def show(self, project_id: UUID) -> ProjectBudget:
        """Raises `UnknownProject` for no such project."""
        ...

    async def show_all(self) -> tuple[ProjectBudget, ...]:
        """Every project's budget, newest project first."""
        ...

    async def set_caps(
        self,
        project_id: UUID,
        *,
        max_dollars: float | None = None,
        max_turns: int | None = None,
        by: str | None = None,
    ) -> BudgetChange:
        """Sets one cap or both. `by` names who is changing it, for the record -- a
        label, not an authority -- and defaults to the account running the command.
        Raises `InvalidBudgetChange` before anything is written for a value that is not
        a cap, for neither cap, or for a label that cannot be recorded."""
        ...

    async def clear_caps(
        self, project_id: UUID, caps: Iterable[CapField], *, by: str | None = None
    ) -> BudgetChange:
        """Removes caps: the project is uncapped for each, as if never set."""
        ...
