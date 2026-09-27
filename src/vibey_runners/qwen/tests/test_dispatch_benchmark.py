# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from pathlib import Path

import pytest

from qwenloop.domain.model import Backend, ServerInfo
from qwenloop.infrastructure import dispatch_benchmark
from qwenloop.infrastructure.dispatch_benchmark import DispatchBenchmark, DispatchBenchmarkResult


class _Server:
    async def chat_stream(self, _info: ServerInfo, _messages: object):
        yield type("Chunk", (), {"text": "ok"})()


def _info() -> ServerInfo:
    return ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )


@pytest.mark.asyncio
async def test_benchmark_measures_both_modes_and_selects_hybrid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter((0.0, 2.0, 2.0, 3.0))
    monkeypatch.setattr(dispatch_benchmark.time, "perf_counter", lambda: next(ticks))
    result = await DispatchBenchmark().run(_Server(), _info(), samples=2, concurrency=2)
    assert result == DispatchBenchmarkResult("hybrid", 1.0, 2.0, 2, 2)


@pytest.mark.asyncio
async def test_benchmark_selects_direct_on_tie_or_when_faster(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticks = iter((0.0, 1.0, 1.0, 3.0))
    monkeypatch.setattr(dispatch_benchmark.time, "perf_counter", lambda: next(ticks))
    result = await DispatchBenchmark().run(_Server(), _info(), samples=2, concurrency=2)
    assert result.winner == "direct"


@pytest.mark.asyncio
async def test_benchmark_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        await DispatchBenchmark().run(_Server(), _info(), samples=0)
    with pytest.raises(ValueError):
        await DispatchBenchmark().run(_Server(), _info(), concurrency=0)


def test_benchmark_persists_and_loads_winner(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "benchmark.json"
    result = DispatchBenchmarkResult("hybrid", 1.0, 2.0, 3, 2)
    DispatchBenchmark.save(result, path)
    assert DispatchBenchmark.load(path) == "hybrid"
    assert json.loads(path.read_text(encoding="utf-8"))["samples"] == 3


def test_benchmark_load_returns_none_for_missing_or_invalid_data(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not json", encoding="utf-8")
    unknown = tmp_path / "unknown.json"
    unknown.write_text('{"winner": "rabbitmq"}', encoding="utf-8")
    assert DispatchBenchmark.load(missing) is None
    assert DispatchBenchmark.load(invalid) is None
    assert DispatchBenchmark.load(unknown) is None
