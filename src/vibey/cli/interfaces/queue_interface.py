# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey queue` (ADR-0054).

Mirrors `vibey/cli/queue.py` (ADR-0016). Interfaces declare; they never consume. The
types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from uuid import UUID

    from vibey.application.dto import QueueEntry
    from vibey.application.interfaces import QueuePriorityServiceInterface
    from vibey.bootstrap import AppResources
    from vibey.domain.interfaces.queue_priority_interface import PriorityChangeInterface


@runtime_checkable
class QueuePresenterInterface(Protocol):
    """Renders the queue and a change to it: for a person first, a program second."""

    def entries(self, entries: Sequence[QueueEntry]) -> list[str]:
        """One line per unfinished job, running work first, then claim order, with
        every bumped job marked by its place."""
        ...

    def entries_json(self, project_id: UUID, entries: Sequence[QueueEntry]) -> str: ...

    def change(self, change: PriorityChangeInterface) -> list[str]:
        """What moved, what was already ahead, and what the job still waits on."""
        ...

    def change_json(self, change: PriorityChangeInterface) -> str: ...


@runtime_checkable
class QueueCommandInterface(Protocol):
    """Runs `vibey queue bump`, `unbump` and `list`."""

    def service(self, resources: AppResources, config: Path) -> QueuePriorityServiceInterface:
        """The priority service, its grant read from `[queue.priority]` in `config`."""
        ...

    async def bump(self, job_id: UUID, *, source: str, config: Path, as_json: bool) -> None: ...

    async def unbump(self, job_id: UUID, *, source: str, config: Path, as_json: bool) -> None: ...

    async def list(self, project_id: UUID | None, *, as_json: bool) -> None:
        """`project_id`, or the latest project."""
        ...
