# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind how a command with an optional PROJECT_ID finds its project (ADR-0016).

Mirrors `vibey/cli/project_target.py`. Interfaces declare; they never consume. The types the
seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from vibey.application.dto import ProjectRecord
    from vibey.bootstrap import AppResources


@runtime_checkable
class ProjectTargetInterface(Protocol):
    """Finds the project a command acts on, or says why there is none and exits 1."""

    async def latest(self, resources: AppResources, *, as_json: bool) -> ProjectRecord:
        """The newest project; with none, says so and exits 1."""
        ...

    async def get(
        self, resources: AppResources, project_id: UUID, *, as_json: bool
    ) -> ProjectRecord:
        """The named project; if it does not exist, says so and exits 1."""
        ...
