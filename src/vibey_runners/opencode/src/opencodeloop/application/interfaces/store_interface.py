# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Persistence port for normalized run state."""

from pathlib import Path
from typing import Protocol

from opencodeloop.domain.model import RunResult


class RunStoreInterface(Protocol):
    """The files consumed by Vibey's generic loop adapter."""

    def begin(self, run_dir: Path, run_id: str, cwd: Path, session_id: str | None) -> None:
        """Create the active run envelope."""

    def append_event(self, run_dir: Path, event: dict[str, object]) -> None:
        """Append one event without rewriting previous ledger entries."""

    def finish(self, run_dir: Path, result: RunResult) -> None:
        """Persist terminal metadata and the latest snapshot."""
