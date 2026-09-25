# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/cli/driver.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path
    from typing import TextIO


@runtime_checkable
class UtcClockInterface(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class DriverCommandInterface(Protocol):
    def hook(self, stdin: TextIO, config: Path | None) -> int: ...

    def probe(self, cwd: Path, config: Path | None) -> int: ...

    def status(self, cwd: Path, config: Path | None) -> int: ...

    def timer(self, cwd: Path, platform: str, out: Path, config: Path | None) -> int: ...

    def hook_config(self) -> int: ...
