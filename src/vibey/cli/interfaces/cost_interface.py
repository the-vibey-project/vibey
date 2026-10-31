# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey cost` (ADR-0016).

Mirrors `vibey/cli/cost.py`. Interfaces declare; they never consume. The types the seams are
declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from vibey.application.dto import EngineHealthRecord, ProjectBudget


@runtime_checkable
class CostPresenterInterface(Protocol):
    """Renders a project's spend against its caps: lines for a person, a document for a program."""

    def lines(self, budget: ProjectBudget, records: Sequence[EngineHealthRecord]) -> list[str]:
        """The cycle's spend and caps, then each engine's BUILD spend across all cycles."""
        ...

    def cost_json(self, budget: ProjectBudget, records: Sequence[EngineHealthRecord]) -> str:
        """The same facts as one JSON document."""
        ...


@runtime_checkable
class CostCommandInterface(Protocol):
    """Runs `vibey cost`."""

    async def run(self, project_id: UUID | None, *, as_json: bool) -> None: ...
