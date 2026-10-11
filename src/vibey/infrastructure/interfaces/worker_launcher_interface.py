# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for starting a `vibey worker` that outlives the command that started it.

Mirrors `vibey/infrastructure/worker_launcher.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class WorkerLauncherInterface(Protocol):
    """Starts a detached `vibey` process and hands back its pid."""

    def start(self, args: Sequence[str], *, log: Path) -> int:
        """Runs `vibey ARGS...` in its own session with its output appended to `log`, so it
        survives the terminal and the command that started it. Returns the pid."""
        ...
