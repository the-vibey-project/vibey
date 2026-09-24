# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey projects`.

Mirrors `vibey/cli/projects.py` (ADR-0016). Interfaces declare; they never consume. The types
the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from vibey.application.dto import ProjectRecord


@runtime_checkable
class ProjectsPresenterInterface(Protocol):
    """Renders the project list: for a person first, a program second. `open_gates` counts
    each project's unanswered gates; a project it does not name has none."""

    def projects(
        self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]
    ) -> list[str]:
        """A small table, newest project first, or one line saying how to make one."""
        ...

    def projects_json(
        self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]
    ) -> str:
        """A JSON array, newest first, with the keys the VS Code extension reads."""
        ...


@runtime_checkable
class ProjectsCommandInterface(Protocol):
    """Runs `vibey projects`."""

    async def run(self, *, as_json: bool) -> None: ...
