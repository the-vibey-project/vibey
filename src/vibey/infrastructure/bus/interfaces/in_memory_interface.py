# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory bus seam.

Mirrors `vibey/infrastructure/bus/in_memory.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.bus import BusPort
from vibey.application.interfaces.queue_reap import BusInspectorPort

if TYPE_CHECKING:
    from datetime import datetime


@runtime_checkable
class InMemoryMessageInterface(Protocol):
    """One in-memory message and what a broker would know about it."""

    @property
    def payload(self) -> dict[str, object]: ...

    @property
    def published_at(self) -> datetime: ...

    @property
    def message_id(self) -> str: ...

    @property
    def died_on(self) -> str | None: ...

    @property
    def reason(self) -> str | None: ...


@runtime_checkable
class InMemoryBusInterface(BusPort, BusInspectorPort, Protocol):
    """The in-memory implementation of the Bus port, and of the reaper's view of it."""

    async def reject(self, queue: str, *, reason: str = "rejected") -> bool:
        """Dead-letter the head of `queue`, as `basic.reject(requeue=false)` does."""
        ...

    def policy(self, name: str) -> dict[str, object] | None:
        """The policy document kept under `name`."""
        ...
