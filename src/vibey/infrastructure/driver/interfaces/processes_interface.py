# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/driver/processes.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vibey.application.dto import ProcessResult


@runtime_checkable
class SubprocessPortInterface(Protocol):
    def spawn(self, argv: Sequence[str], *, cwd: str) -> None: ...

    def run(self, argv: Sequence[str], *, cwd: str, timeout: float) -> ProcessResult: ...
