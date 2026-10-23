# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam behind the hub's project-lifecycle routes (ADR-0091). Interfaces declare; they never
consume.

The hub owns no write of its own (ADR-0067): starting, pausing, resuming and unwinding a project
are what `vibey new`, `recover`, `retry` and `abandon` already do, so an adapter runs those and
this is what it offers the hub service."""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class ProjectLifecycleInterface(Protocol):
    """Starts, pauses, resumes and unwinds projects on this host. Every method raises a
    `LifecycleRefused` subclass (never a bare error) when the host will not or cannot."""

    async def create(self, name: str, intake: str) -> Mapping[str, object]:
        """Make a folder for `name` where the host allows devices to start projects, create the
        project there with `intake` as what to build, and start its worker. The document is
        `vibey new --json`'s: `project_id`, `name`, `outcome`."""
        ...

    async def start_work(self, project_id: UUID) -> Mapping[str, object]:
        """Start, or start again, this project's own worker; `{"message": ...}`."""
        ...

    async def pause_work(self, project_id: UUID) -> Mapping[str, object]:
        """Stop this project's own workers and no one else's, as `vibey recover --project
        --stop-workers` does; `{"message": ...}`."""
        ...

    async def abandon(
        self, project_id: UUID, reason: str, *, by: str, dry_run: bool
    ) -> Mapping[str, object]:
        """Unwind the project for good, recorded under `by` with `reason`; with `dry_run`,
        only what would be cancelled. The document is `vibey abandon --json`'s."""
        ...
