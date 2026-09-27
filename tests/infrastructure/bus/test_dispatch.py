# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import json
from pathlib import Path

import pytest

from vibey.infrastructure.bus.dispatch import BusDispatchAdapter, BusDispatchSelection


class _Bus:
    def __init__(self) -> None:
        self.values: list[dict[str, object]] = []

    async def declare_queue(self, _queue: str, *, dead_letter: bool = True) -> None:
        del dead_letter

    async def publish(self, _queue: str, payload: dict[str, object]) -> None:
        self.values.append(payload)

    async def consume(self, _queue: str) -> dict[str, object] | None:
        return self.values.pop(0) if self.values else None


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["singleton", "multiplexer", "hybrid"])
async def test_dispatch_adapter_preserves_bus_operations(mode: str) -> None:
    bus = _Bus()
    adapter = BusDispatchAdapter(bus, mode, hybrid_concurrency=2)
    await adapter.declare_queue("q")
    await asyncio.gather(*(adapter.publish("q", {"i": i}) for i in range(3)))
    assert await adapter.consume("q") is not None


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
    assert BusDispatchSelection.from_cache(valid) == "multiplexer"
    assert BusDispatchSelection.from_cache(invalid) is None
    assert BusDispatchSelection.from_cache(unknown) is None
    assert BusDispatchSelection.from_cache(tmp_path / "missing.json") is None
