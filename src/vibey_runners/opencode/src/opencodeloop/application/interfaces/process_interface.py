# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ports used by the application runner."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from opencodeloop.domain.model import RunResult


class ProcessInterface(Protocol):
    """The external OpenCode process boundary."""

    def doctor(self) -> tuple[bool, str]:
        """Check the external CLI contract without starting a run."""

    def execute(
        self,
        *,
        prompt: str,
        cwd: Path,
        session_id: str | None,
        emit: Callable[[dict[str, object]], None],
    ) -> RunResult:
        """Execute one run and emit normalized events as they arrive."""
