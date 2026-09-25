# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams for keeping the Sabbath on this host (sub-doctrine 8.i; vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Protocol

from vibey_gh.interfaces.sabbath_location_interface import ResolvedLocationInterface
from vibey_gh.interfaces.sabbath_window_interface import (
    RestWindowInterface,
    SabbathWindowInterface,
)


class SabbathGuardInterface(Protocol):
    """The window built for this machine, and whether it holds now."""

    def zone_name(self) -> str: ...

    def location(self) -> ResolvedLocationInterface | None: ...

    def window(self) -> SabbathWindowInterface: ...

    def hold(self, at: datetime | None = None) -> RestWindowInterface | None: ...

    def describe(self) -> list[str]: ...


class SabbathLanesInterface(Protocol):
    """Lanes paused for the Sabbath, each with the command that resumes it."""

    def register(self, name: str, command: Sequence[str], cwd: str | None = None) -> Path: ...

    def pending(self) -> list[tuple[str, list[str], str | None]]: ...

    def resume(self) -> list[str]: ...
