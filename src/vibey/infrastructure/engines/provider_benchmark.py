# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Common benchmark execution through the existing EngineAdapter seam."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from vibey.application.dto import RunSpec
from vibey.application.interfaces.engines import EngineAdapter
from vibey.domain.effort import Effort
from vibey.domain.engine import IsolationLevel
from vibey.infrastructure.engines.paid_benchmark_budget import PaidBenchmarkBudgetStore


@dataclass(frozen=True, slots=True)
class ProviderBenchmarkResult:
    engine: str
    turns_per_second: float
    cost_usd: float
    complete: bool


class ProviderBenchmarkExecutor:
    """Run one bounded provider probe and charge only reported usage."""

    def __init__(self, budget: PaidBenchmarkBudgetStore) -> None:
        self._budget = budget

    async def run(self, adapter: EngineAdapter, worktree: Path) -> ProviderBenchmarkResult:
        started = time.perf_counter()
        handle = await adapter.start(
            RunSpec(
                run_id=uuid4(),
                worktree_path=worktree,
                prompt="Reply with exactly: benchmark-ready",
                effort=Effort.TRIVIAL,
                isolation=IsolationLevel.WORKTREE,
            )
        )
        complete = False
        input_tokens = output_tokens = 0
        try:
            async for event in adapter.tail(handle):
                payload = event.payload
                if event.kind == "budget_spent":
                    input_value = payload.get("input_tokens", 0)
                    output_value = payload.get("output_tokens", 0)
                    input_tokens += int(input_value) if isinstance(input_value, int | float) else 0
                    output_tokens += (
                        int(output_value) if isinstance(output_value, int | float) else 0
                    )
                if payload.get("complete") is True:
                    complete = True
        finally:
            await adapter.stop(handle)
        elapsed = max(time.perf_counter() - started, 1e-9)
        descriptor = adapter.descriptor
        cost = (input_tokens / 1_000_000 * descriptor.cost_per_mtok_in) + (
            output_tokens / 1_000_000 * descriptor.cost_per_mtok_out
        )
        if cost > 0:
            self._budget.charge(cost)
        return ProviderBenchmarkResult(
            descriptor.engine_id.value,
            1 / elapsed if complete else 0.0,
            cost,
            complete,
        )
