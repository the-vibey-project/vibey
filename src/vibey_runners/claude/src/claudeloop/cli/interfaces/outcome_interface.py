# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of `cli/outcome.py`: how a finished run becomes an exit status."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from claudeloop.application.dto import RunResult


@runtime_checkable
class RunOutcomeReporterInterface(Protocol):
    def report(
        self, result: RunResult, *, handoff_marker: Path, stop_summary: Path, profile: str
    ) -> None:
        """Print the outcome; raise ``typer.Exit`` with its status unless it succeeded."""
        ...
