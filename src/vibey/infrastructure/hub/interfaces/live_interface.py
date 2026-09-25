# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind hearing the ledger grow.

Mirrors `vibey/infrastructure/hub/live.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncio
    from contextlib import AbstractContextManager
    from uuid import UUID


@runtime_checkable
class LedgerAnnouncementsInterface(Protocol):
    """Wakes a project's live feeds when its ledger grows."""

    async def start(self) -> None:
        """Starts listening."""
        ...

    async def stop(self) -> None:
        """Stops listening; nothing when not started."""
        ...

    def subscribe(self, project_id: UUID) -> AbstractContextManager[asyncio.Queue[int]]:
        """A queue woken with the new seq whenever `project_id`'s ledger grows."""
        ...
