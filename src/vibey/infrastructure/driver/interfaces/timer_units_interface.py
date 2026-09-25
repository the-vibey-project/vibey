# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/driver/timer_units.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence


@runtime_checkable
class TimerUnitRendererInterface(Protocol):
    def label(self, cwd: str) -> str: ...

    def launchd(self, *, argv: Sequence[str], cwd: str, interval_seconds: int) -> str: ...

    def systemd(
        self, *, argv: Sequence[str], cwd: str, interval_seconds: int
    ) -> tuple[str, str]: ...
