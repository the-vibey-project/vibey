# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey engines` (ADR-0016).

Mirrors `vibey/cli/engines.py`. Interfaces declare; they never consume. The types the seams
are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from vibey.application.dto import EngineHealthRecord


@runtime_checkable
class EnginesPresenterInterface(Protocol):
    """Renders engine health: a table for a person, a document for a program."""

    def document(self, record: EngineHealthRecord) -> dict[str, object]:
        """One engine as `vibey status --json` carries it in `circuits` and the hub returns it."""
        ...

    def table(self, records: Sequence[EngineHealthRecord]) -> list[str]:
        """The header, a rule and one row per engine."""
        ...

    def engines_json(self, project_id: UUID, records: Sequence[EngineHealthRecord]) -> str:
        """`{"project_id": ..., "engines": [...]}`, an empty list when none are recorded."""
        ...


@runtime_checkable
class EnginesCommandInterface(Protocol):
    """Runs `vibey engines`."""

    async def run(self, project_id: UUID | None, *, as_json: bool) -> None: ...
