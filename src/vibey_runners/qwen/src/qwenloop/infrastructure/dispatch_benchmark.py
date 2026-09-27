# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Measured selection of the local direct and hybrid turn schedulers."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from qwenloop.application.interfaces import InferenceServer
from qwenloop.domain.model import ChatMessage, ServerInfo
from qwenloop.infrastructure.turn_dispatch import (
    DirectTurnDispatcher,
    HybridTurnMultiplexer,
    RabbitMqTurnDispatcher,
)


@dataclass(frozen=True, slots=True)
class DispatchBenchmarkResult:
    winner: str
    direct_turns_per_second: float
    hybrid_turns_per_second: float
    rabbitmq_turns_per_second: float | None
    samples: int
    concurrency: int


class DispatchBenchmark:
    """Runs the same prompt workload through direct and hybrid local dispatch."""

    async def run(
        self,
        server: InferenceServer,
        info: ServerInfo,
        *,
        samples: int = 3,
        concurrency: int = 2,
        rabbitmq: RabbitMqTurnDispatcher | None = None,
    ) -> DispatchBenchmarkResult:
        if samples <= 0 or concurrency <= 0:
            raise ValueError("samples and concurrency must be positive")
        messages = [ChatMessage(role="user", content="Reply with one short word.")]
        dispatchers: list[tuple[str, Any]] = [
            ("direct", DirectTurnDispatcher()),
            ("hybrid", HybridTurnMultiplexer(concurrency=concurrency)),
        ]
        if rabbitmq is not None:
            dispatchers.append(("rabbitmq", rabbitmq))

        async def one(dispatcher: Any) -> None:
            async for _ in dispatcher.dispatch(server, info, messages):
                pass

        rates: dict[str, float] = {}
        for name, dispatcher in dispatchers:
            started = time.perf_counter()
            await asyncio.gather(*(one(dispatcher) for _ in range(samples)))
            rates[name] = samples / max(time.perf_counter() - started, 1e-9)
        winner = max(rates, key=rates.__getitem__)
        return DispatchBenchmarkResult(
            winner,
            rates["direct"],
            rates["hybrid"],
            rates.get("rabbitmq"),
            samples,
            concurrency,
        )

    @staticmethod
    def save(result: DispatchBenchmarkResult, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def load(path: Path) -> str | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            winner = data.get("winner")
        except (OSError, ValueError, TypeError):
            return None
        return winner if winner in {"direct", "hybrid", "rabbitmq"} else None
