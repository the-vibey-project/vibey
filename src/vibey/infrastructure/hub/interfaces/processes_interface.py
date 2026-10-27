# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the hub's process calls.

Mirrors `vibey/infrastructure/hub/processes.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class HubProcessesInterface(Protocol):
    """Starting, probing and stopping the hub as an operating-system process."""

    def alive(self, pid: int) -> bool:
        """Whether a process with this id exists."""
        ...

    def terminate(self, pid: int) -> bool:
        """Asks the process to stop cleanly; False when it is already gone."""
        ...

    def spawn(self, argv: Sequence[str], log: Path) -> int:
        """Starts `argv` detached, output to `log`, and returns its process id."""
        ...
