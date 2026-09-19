# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for turning a finished run into what the process prints and exits with."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FinishedRun(Protocol):
    """The two facts about a finished run that decide how the process ends.

    ``agyloop.application.dto.RunResult`` satisfies it structurally, so the seam
    names no type from the tree it sits in.
    """

    @property
    def success(self) -> bool:
        """Whether the run completed its plan."""
        ...

    @property
    def reason(self) -> str:
        """Why the run ended, as the runner phrased it."""
        ...


@runtime_checkable
class RunOutcomeReporterInterface(Protocol):
    """Reports a finished run and ends the command with the matching exit code."""

    def is_wind_down(self, result: FinishedRun) -> bool:
        """Whether the run stopped early on purpose, leaving a successor its work."""
        ...

    def exit_code_for(self, result: FinishedRun) -> int:
        """The process exit code a supervisor reads for this result."""
        ...

    def conclude(self, result: FinishedRun) -> None:
        """Print the outcome; end the command with a non-zero exit unless it succeeded."""
        ...
