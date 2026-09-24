# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the PostgreSQL side of changing a project's caps (`vibey budget`).

Mirrors `vibey/infrastructure/db/project_budget_store.py` (ADR-0016). Interfaces declare;
they never consume. The domain and draft types are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.project_budget import ProjectBudgetStore

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.application.dto import ProjectRecord
    from vibey.domain.interfaces.budget_caps_interface import CapChangeInterface
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class BudgetCapDraftBuilderInterface(Protocol):
    """Builds the `BudgetCapChanged` ledger draft for one changed cap."""

    def build(
        self,
        project: ProjectRecord,
        change: CapChangeInterface,
        *,
        by: str,
        account: str,
        at: datetime,
    ) -> LedgerEventDraft:
        """Filed under the project's cycle and phase, `trusted`, with no engine and no
        job. Raises `WrongPhase` for a phase this vibey does not know."""
        ...


@runtime_checkable
class PostgresProjectBudgetStoreInterface(ProjectBudgetStore, Protocol):
    """Changes a project's caps and appends their `BudgetCapChanged` events in one
    transaction, under a lock on the project's row."""
