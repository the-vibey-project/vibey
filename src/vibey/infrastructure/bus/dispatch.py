# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Dispatch policies for the orchestration service bus."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from vibey.application.interfaces.bus import BusPort


class BusDispatchAdapter(BusPort):
    """Apply the selected concurrency policy without changing bus semantics."""

    def __init__(self, delegate: BusPort, mode: str, *, hybrid_concurrency: int = 4) -> None:
        if mode not in {"singleton", "multiplexer", "hybrid"}:
            raise ValueError(f"unsupported bus dispatch mode: {mode}")
        if hybrid_concurrency <= 0:
            raise ValueError("hybrid_concurrency must be positive")
        self._delegate = delegate
        self.mode = mode
        self._gate = asyncio.Semaphore(1 if mode == "singleton" else hybrid_concurrency)
        self._unbounded = mode == "multiplexer"

    async def _run(self, operation: Callable[[], Awaitable[object]]) -> object:
        if self._unbounded:
            return await operation()
        async with self._gate:
            return await operation()

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        await self._run(lambda: self._delegate.declare_queue(queue, dead_letter=dead_letter))

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        await self._run(lambda: self._delegate.publish(queue, payload))

    async def consume(self, queue: str) -> dict[str, object] | None:
        return await self._run(lambda: self._delegate.consume(queue))  # type: ignore[return-value]


class BusDispatchSelection:
    """Load a measured local winner for `auto` mode."""

    VALID = frozenset({"singleton", "multiplexer", "hybrid"})

    @classmethod
    def from_cache(cls, path: Path) -> str | None:
        try:
            winner = json.loads(path.read_text(encoding="utf-8")).get("winner")
        except (OSError, TypeError, ValueError):
            return None
        return winner if winner in cls.VALID else None
