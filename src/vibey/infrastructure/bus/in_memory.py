# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Bus implementation of the service-bus port (ADR-0042)."""

from __future__ import annotations

from collections import deque

from vibey.application.interfaces.bus import BusPort


class InMemoryBus(BusPort):
    """Faked queues for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[dict[str, object]]] = {}
        self._dead: dict[str, deque[dict[str, object]]] = {}

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        self._queues.setdefault(queue, deque())
        if dead_letter:
            self._dead.setdefault(f"{queue}.dlq", deque())

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        await self.declare_queue(queue)
        self._queues[queue].append(dict(payload))

    async def consume(self, queue: str) -> dict[str, object] | None:
        pending = self._queues.get(queue)
        if not pending:
            return None
        return pending.popleft()
