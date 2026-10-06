# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey state`.

Mirrors `vibey/cli/state.py` (ADR-0016, ADR-0086). Interfaces declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StateCommandInterface(Protocol):
    """Keeps this database and its sealed copy on the repository's branch the same. Every
    method returns the exit code: 0 done or in sync, 1 a conflict or a refusal, 2 a setting
    that cannot be used."""

    def sync(self, *, push: bool = True, every: float | None = None, rounds: int = 0) -> int: ...

    def status(self, *, as_json: bool = False) -> int: ...

    def export(self, path: Path) -> int: ...

    def import_(self, path: Path) -> int: ...

    def forget(self) -> int: ...

    def key(self, *, new: bool = False, show: bool = False) -> int: ...
