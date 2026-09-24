# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading a project and moving it between phases."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import (
    ProjectRecord,
)
from vibey.domain.phase import (
    Phase,
)


@runtime_checkable
class ProjectStore(Protocol):
    async def get(self, project_id: UUID) -> ProjectRecord | None: ...

    async def transition(
        self, project_id: UUID, *, expected: Phase, to: Phase, guard: str | None = None
    ) -> ProjectRecord: ...


@runtime_checkable
class ProjectTransitioner(Protocol):
    async def transition(
        self,
        project_id: UUID,
        *,
        expected: Phase,
        to: Phase,
        cycle: int | None = None,
        guard: str | None = None,
    ) -> Any: ...


@runtime_checkable
class ProjectLookup(Protocol):
    """Reads one project as it is now. What the budget brake reads a project's caps
    through, at every BUILD session."""

    async def get(self, project_id: UUID) -> ProjectRecord | None: ...


@runtime_checkable
class ProjectReader(ProjectLookup, Protocol):
    """Reads projects and changes nothing: one, the latest, or every one."""

    async def get_latest(self) -> ProjectRecord | None: ...

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        """Every project, newest first: `created_at` descending, then id."""
        ...
