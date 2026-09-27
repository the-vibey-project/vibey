# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Dispatch policies for the orchestration service bus."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
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


class BusDispatchBenchmark:
    """Measure the three bus policies using an isolated queue."""

    def __init__(self, *, messages: int = 8, hybrid_concurrency: int = 4) -> None:
        if messages <= 0 or hybrid_concurrency <= 0:
            raise ValueError("messages and hybrid_concurrency must be positive")
        self._messages = messages
        self._hybrid_concurrency = hybrid_concurrency

    async def run(self, bus: BusPort) -> dict[str, object]:
        rates: dict[str, float] = {}
        for mode in ("singleton", "multiplexer", "hybrid"):
            queue = f"vibey.dispatch.benchmark.{uuid.uuid4().hex}"
            policy = BusDispatchAdapter(bus, mode, hybrid_concurrency=self._hybrid_concurrency)
            await policy.declare_queue(queue, dead_letter=False)
            started = time.perf_counter()
            await asyncio.gather(
                *(self._round_trip(policy, queue, i) for i in range(self._messages))
            )
            rates[mode] = self._messages / max(time.perf_counter() - started, 1e-9)
        return {
            "winner": max(rates, key=rates.__getitem__),
            "rates": rates,
            "messages": self._messages,
        }

    async def _round_trip(self, bus: BusPort, queue: str, index: int) -> None:
        await bus.publish(queue, {"index": index})
        while await bus.consume(queue) is None:
            await asyncio.sleep(0)

    @staticmethod
    def save(result: dict[str, object], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


class WeeklyBusDispatchRecomputer:
    """Recompute a bus winner at most once per seven days."""

    WEEK_SECONDS = 7 * 24 * 60 * 60

    def __init__(self, bus: BusPort, path: Path, *, hybrid_concurrency: int = 4) -> None:
        self._bus = bus
        self._path = path
        self._benchmark = BusDispatchBenchmark(hybrid_concurrency=hybrid_concurrency)

    async def run_once_if_due(self) -> bool:
        try:
            due = time.time() - self._path.stat().st_mtime >= self.WEEK_SECONDS
        except OSError:
            due = True
        if not due:
            return False
        result = await self._benchmark.run(self._bus)
        self._benchmark.save(result, self._path)
        return True
