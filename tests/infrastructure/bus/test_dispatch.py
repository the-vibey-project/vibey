# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import json
from pathlib import Path

import pytest

from vibey.domain.config import QueueReapConfig
from vibey.infrastructure.bus.dispatch import (
    BusDispatchAdapter,
    BusDispatchBenchmark,
    BusDispatchSelection,
    WeeklyBusDispatchRecomputer,
)
from vibey.infrastructure.bus.in_memory import InMemoryBus
from vibey.infrastructure.bus.interfaces.dispatch_interface import (
    BusDispatchAdapterInterface,
    BusDispatchBenchmarkInterface,
    BusDispatchSelectionInterface,
    WeeklyBusDispatchRecomputerInterface,
)


class _Bus:
    def __init__(self, *, empty_once: bool = False) -> None:
        self.values: list[dict[str, object]] = []
        self.empty_once = empty_once

    async def declare_queue(self, _queue: str, *, dead_letter: bool = True) -> None:
        del dead_letter

    async def publish(self, _queue: str, payload: dict[str, object]) -> None:
        self.values.append(payload)

    async def consume(self, _queue: str) -> dict[str, object] | None:
        if self.empty_once:
            self.empty_once = False
            return None
        return self.values.pop(0) if self.values else None

    async def delete_queue(self, _queue: str) -> None:
        return None


class _RecordingBus(_Bus):
    """Records the queues the benchmark declares and deletes; can fail a publish."""

    def __init__(self, *, fail_publish: bool = False) -> None:
        super().__init__()
        self.declared: list[str] = []
        self.deleted: list[str] = []
        self.fail_publish = fail_publish

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        del dead_letter
        self.declared.append(queue)

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        if self.fail_publish:
            raise RuntimeError("broker refused the publish")
        await super().publish(queue, payload)

    async def delete_queue(self, queue: str) -> None:
        self.deleted.append(queue)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["singleton", "multiplexer", "hybrid"])
async def test_dispatch_adapter_preserves_bus_operations(mode: str) -> None:
    bus = _Bus()
    adapter = BusDispatchAdapter(bus, mode, hybrid_concurrency=2)
    assert isinstance(adapter, BusDispatchAdapterInterface)
    await adapter.declare_queue("q")
    await asyncio.gather(*(adapter.publish("q", {"i": i}) for i in range(3)))
    assert await adapter.consume("q") is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["singleton", "multiplexer", "hybrid"])
async def test_dispatch_adapter_deletes_through_its_delegate(mode: str) -> None:
    bus = _RecordingBus()
    await BusDispatchAdapter(bus, mode, hybrid_concurrency=2).delete_queue("q")
    assert bus.deleted == ["q"]


def test_dispatch_adapter_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        BusDispatchAdapter(_Bus(), "invalid")
    with pytest.raises(ValueError):
        BusDispatchAdapter(_Bus(), "hybrid", hybrid_concurrency=0)


def test_dispatch_selection_loads_only_valid_winners(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    valid.write_text(json.dumps({"winner": "multiplexer"}), encoding="utf-8")
    invalid = tmp_path / "invalid.json"
    invalid.write_text("bad", encoding="utf-8")
    unknown = tmp_path / "unknown.json"
    unknown.write_text(json.dumps({"winner": "other"}), encoding="utf-8")
    assert isinstance(BusDispatchSelection(), BusDispatchSelectionInterface)
    assert BusDispatchSelection.from_cache(valid) == "multiplexer"
    assert BusDispatchSelection.from_cache(invalid) is None
    assert BusDispatchSelection.from_cache(unknown) is None
    assert BusDispatchSelection.from_cache(tmp_path / "missing.json") is None


@pytest.mark.asyncio
async def test_benchmark_and_weekly_recomputer_persist_winner(tmp_path: Path) -> None:
    bus = _Bus(empty_once=True)
    benchmark = BusDispatchBenchmark(messages=1, hybrid_concurrency=1)
    assert isinstance(benchmark, BusDispatchBenchmarkInterface)
    result = await benchmark.run(bus)
    assert result["winner"] in {"singleton", "multiplexer", "hybrid"}
    path = tmp_path / "winner.json"
    recomputer = WeeklyBusDispatchRecomputer(bus, path, hybrid_concurrency=1)
    assert isinstance(recomputer, WeeklyBusDispatchRecomputerInterface)
    assert await recomputer.run_once_if_due() is True
    assert await recomputer.run_once_if_due() is False


def test_benchmark_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        BusDispatchBenchmark(messages=0)
    with pytest.raises(ValueError):
        BusDispatchBenchmark(hybrid_concurrency=0)


@pytest.mark.asyncio
async def test_a_benchmark_run_leaves_no_queue_on_the_bus() -> None:
    """Every run used to leave three durable `vibey.dispatch.benchmark.<uuid>` queues on
    the broker for good -- weekly, and at every fresh pod start (the cache is empty)."""
    bus = InMemoryBus()
    await BusDispatchBenchmark(messages=3, hybrid_concurrency=2).run(bus)
    assert await bus.depths() == ()


@pytest.mark.asyncio
async def test_a_benchmark_deletes_each_queue_it_declared() -> None:
    bus = _RecordingBus()
    await BusDispatchBenchmark(messages=2, hybrid_concurrency=1).run(bus)
    assert len(bus.declared) == 3
    assert len(set(bus.declared)) == 3
    assert bus.deleted == bus.declared


@pytest.mark.asyncio
async def test_a_failed_round_trip_still_deletes_its_queue() -> None:
    bus = _RecordingBus(fail_publish=True)
    with pytest.raises(RuntimeError, match="refused"):
        await BusDispatchBenchmark(messages=1, hybrid_concurrency=1).run(bus)
    assert bus.declared
    assert bus.deleted == bus.declared


@pytest.mark.asyncio
async def test_a_benchmark_queue_is_outside_the_reap_policy() -> None:
    """The reap verifier holds every queue the policy owns to its policy. A benchmark
    queue declared seconds earlier still reads 'no policy' in the broker's statistics, so
    `vibey queue reap` failed whenever one was alive (the #1244 cluster-smoke flake)."""
    policy = QueueReapConfig().broker_policy()
    bus = _RecordingBus()
    await BusDispatchBenchmark(messages=1, hybrid_concurrency=1).run(bus)
    assert bus.declared
    for queue in bus.declared:
        assert queue.startswith(BusDispatchBenchmark.QUEUE_PREFIX)
        assert not policy.owns(queue)
        assert not policy.owns(f"{queue}.dlq")
    for queue in ("vibey.jobs", "vibey.jobs.p1", "vibey.jobs.dlq", "vibey.dispatch.x"):
        assert policy.owns(queue)


@pytest.mark.asyncio
async def test_a_benchmark_queue_prefix_is_configurable() -> None:
    bus = _RecordingBus()
    await BusDispatchBenchmark(messages=1, hybrid_concurrency=1, queue_prefix="lab.").run(bus)
    assert all(queue.startswith("lab.") for queue in bus.declared)


def test_a_benchmark_refuses_an_empty_queue_prefix() -> None:
    with pytest.raises(ValueError, match="queue_prefix"):
        BusDispatchBenchmark(queue_prefix=" ")
