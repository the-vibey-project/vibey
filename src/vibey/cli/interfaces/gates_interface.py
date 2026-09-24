# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey gates`.

Mirrors `vibey/cli/gates.py` (ADR-0016). Interfaces declare; they never consume. The types
the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from vibey.application.dto import HumanGateRecord


@runtime_checkable
class GatesPresenterInterface(Protocol):
    """Renders open gates: for a person first, a program second. `names` holds the name of
    every gate's project."""

    def gates(
        self,
        gates: Sequence[HumanGateRecord],
        names: Mapping[UUID, str],
        *,
        scope: str | None = None,
    ) -> list[str]:
        """One paragraph per gate, oldest first: its project, kind, prompt, and the command
        that answers it. `scope` is the one project's name when the list is that project's."""
        ...

    def gates_json(self, gates: Sequence[HumanGateRecord], names: Mapping[UUID, str]) -> str:
        """`{"gates": [...]}`: one object per gate, with the keys the VS Code extension reads."""
        ...


@runtime_checkable
class GatesCommandInterface(Protocol):
    """Runs `vibey gates`: every project's open gates, or one project's."""

    async def run(self, project_id: UUID | None, *, as_json: bool) -> None:
        """Exits 1 when `project_id` names no project, saying so on stderr."""
        ...
