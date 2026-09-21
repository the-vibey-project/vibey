# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seam for the OpenCode run orchestrator (ADR-0016)."""

from pathlib import Path
from typing import Protocol

from opencodeloop.domain.interfaces.model_interface import RunResultInterface


class RunnerInterface(Protocol):
    """The application service the CLI composes and drives."""

    def doctor(self) -> tuple[bool, str]:
        """Expose the external CLI preflight without adding provider assumptions."""

    def run(
        self,
        *,
        prompt: str,
        run_id: str,
        cwd: Path,
        session_id: str | None = None,
    ) -> RunResultInterface:
        """Run OpenCode and persist every normalized event in its worktree."""
