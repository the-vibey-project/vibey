# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The bus dispatch seam.

Mirrors `vibey/infrastructure/bus/dispatch.py` (ADR-0016, ADR-0074). Interfaces declare;
they never consume.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.interfaces.bus import BusPort


@runtime_checkable
class BusDispatchAdapterInterface(BusPort, Protocol):
    """A concurrency policy over a bus that leaves the bus's semantics unchanged."""

    @property
    def mode(self) -> str: ...


@runtime_checkable
class BusDispatchSelectionInterface(Protocol):
    """The measured local winner for `auto` mode, read from its cache."""

    @classmethod
    def from_cache(cls, path: Path) -> str | None: ...


@runtime_checkable
class BusDispatchBenchmarkInterface(Protocol):
    """A measurement of the three policies, on transient queues it deletes afterwards."""

    async def run(self, bus: BusPort) -> dict[str, object]: ...

    @staticmethod
    def save(result: dict[str, object], path: Path) -> None: ...


@runtime_checkable
class WeeklyBusDispatchRecomputerInterface(Protocol):
    """Recomputes the winner at most once per seven days."""

    async def run_once_if_due(self) -> bool: ...
