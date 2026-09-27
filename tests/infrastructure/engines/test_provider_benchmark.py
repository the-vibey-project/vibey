# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from vibey.application.dto import EngineEvent, RunHandle
from vibey.domain.engine import EngineId
from vibey.infrastructure.engines.paid_benchmark_budget import PaidBenchmarkBudgetStore
from vibey.infrastructure.engines.provider_benchmark import ProviderBenchmarkExecutor


class _Adapter:
    descriptor = SimpleNamespace(
        engine_id=EngineId.CLAUDELOOP,
        cost_per_mtok_in=2.0,
        cost_per_mtok_out=8.0,
    )

    async def start(self, _spec: object) -> RunHandle:
        return RunHandle(uuid4(), EngineId.CLAUDELOOP, Path("."), None)

    async def stop(self, _handle: RunHandle) -> object:
        return object()

    async def tail(self, _handle: RunHandle):
        yield EngineEvent(
            "budget_spent", datetime.now(UTC), {"input_tokens": 1_000_000, "output_tokens": 0}
        )
        yield EngineEvent("verdict_rendered", datetime.now(UTC), {"complete": True})


class _FreeAdapter(_Adapter):
    descriptor = SimpleNamespace(
        engine_id=EngineId.GPTOSSLOOP,
        cost_per_mtok_in=0.0,
        cost_per_mtok_out=0.0,
    )


@pytest.mark.asyncio
async def test_provider_benchmark_measures_and_charges_reported_usage(tmp_path: Path) -> None:
    result = await ProviderBenchmarkExecutor(
        PaidBenchmarkBudgetStore(tmp_path / "budget.json")
    ).run(_Adapter(), tmp_path)
    assert result.complete
    assert result.cost_usd == 2.0
    assert result.turns_per_second > 0


@pytest.mark.asyncio
async def test_provider_benchmark_does_not_charge_zero_cost_adapter(tmp_path: Path) -> None:
    result = await ProviderBenchmarkExecutor(
        PaidBenchmarkBudgetStore(tmp_path / "budget.json")
    ).run(_FreeAdapter(), tmp_path)
    assert result.cost_usd == 0.0
