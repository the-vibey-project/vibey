# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey budget`.

Mirrors `vibey/cli/budget.py` (ADR-0016). Interfaces declare; they never consume. The
types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from vibey.application.dto import BudgetChange, ProjectBudget


@runtime_checkable
class BudgetPresenterInterface(Protocol):
    """Renders a budget and a change to one: for a person first, a program second."""

    def budget(self, budget: ProjectBudget) -> list[str]:
        """One short plain block: the caps, this cycle's spend against them, whether a
        cap is reached, and the latest change."""
        ...

    def budgets(self, budgets: Sequence[ProjectBudget]) -> list[str]:
        """One block per project, newest first -- or, with none, how to create one."""
        ...

    def document(self, budget: ProjectBudget) -> dict[str, object]:
        """The JSON object the VS Code extension reads: `project_id`, `name`, `cycle`,
        `caps`, `spend`, `exhausted`, `history` -- a fixed contract."""
        ...

    def budget_json(self, budget: ProjectBudget) -> str: ...

    def budgets_json(self, budgets: Sequence[ProjectBudget]) -> str:
        """An array of `document`s, newest project first."""
        ...

    def change(self, change: BudgetChange) -> list[str]:
        """What changed and who changed it, the budget as it now stands, and any job
        still parked on a budget gate."""
        ...


@runtime_checkable
class BudgetCommandInterface(Protocol):
    """Runs `vibey budget`, `budget set` and `budget clear` through the one budget
    service."""

    async def show(self, project_id: UUID | None, *, all_projects: bool, as_json: bool) -> None:
        """`project_id`, or the latest project -- or, with `all_projects`, every one."""
        ...

    async def set(
        self,
        project_id: UUID | None,
        *,
        max_dollars: float | None,
        max_turns: int | None,
        by: str | None,
    ) -> None:
        """Exits 2, changing nothing, for a value that is not a cap."""
        ...

    async def clear(
        self,
        project_id: UUID | None,
        *,
        dollars: bool,
        turns: bool,
        both: bool,
        by: str | None,
    ) -> None:
        """Exits 2, changing nothing, when no cap is named."""
        ...
