# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application port for reading time, so a run's timing is measured, never guessed."""

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockInterface(Protocol):
    def now(self) -> datetime:
        """The current wall-clock time, timezone-aware, in UTC."""
        ...

    def monotonic(self) -> float:
        """Seconds on a clock that never goes backwards; only differences mean anything."""
        ...
