# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind listing the lanes on this computer.

Mirrors `vibey/infrastructure/hub/lanes.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LaneScannerInterface(Protocol):
    """Finds each lane's events file and reports what the files prove."""

    def lanes(self) -> list[dict[str, object]]:
        """Every recent lane, newest first, each with its byte offset."""
        ...

    def tail(self, events_path: str, after: int, *, max_bytes: int = ...) -> dict[str, object]:
        """A listed lane's complete lines after byte `after`; `UnknownLane` otherwise."""
        ...
