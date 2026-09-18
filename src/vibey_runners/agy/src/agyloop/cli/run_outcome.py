# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How a finished ``run`` or ``resume`` leaves the process: what it prints, what it exits with.

Both commands end the same way, so the mapping lives here once. The distinction
that matters is between a run that failed and one that wound down on purpose.
A wind-down exits ``EXIT_WIND_DOWN`` (75, EX_TEMPFAIL), which is the code a
supervisor -- vibey's BUILD handler among them -- gates its no-loss handoff
pipeline on. Exiting 1 for both made a deliberate handoff indistinguishable
from a crash, so the handoff could never fire (#208).
"""

from __future__ import annotations

import typer

from agyloop.cli.interfaces.run_outcome_interface import FinishedRun
from agyloop.domain.handoff_marker import EXIT_WIND_DOWN, WIND_DOWN_REASON_PREFIX

_EXIT_FAILURE = 1


class RunOutcomeReporter:
    """Reports a finished run and ends the command with the matching exit code.

    The codes and the prefix are constructor arguments so a test or a caller can
    substitute them, but their defaults are a wire contract, not a preference: a
    supervisor compares the exit code against its own ``75``, so a user-facing
    key that moved only this side would silently break the handoff again.
    """

    def __init__(
        self,
        *,
        wind_down_prefix: str = WIND_DOWN_REASON_PREFIX,
        wind_down_exit_code: int = EXIT_WIND_DOWN,
        failure_exit_code: int = _EXIT_FAILURE,
    ) -> None:
        self._wind_down_prefix = wind_down_prefix
        self._wind_down_exit_code = wind_down_exit_code
        self._failure_exit_code = failure_exit_code

    def is_wind_down(self, result: FinishedRun) -> bool:
        """A success is never a wind-down, whatever its reason happens to say."""
        return not result.success and result.reason.startswith(self._wind_down_prefix)

    def exit_code_for(self, result: FinishedRun) -> int:
        if result.success:
            return 0
        if self.is_wind_down(result):
            return self._wind_down_exit_code
        return self._failure_exit_code

    def conclude(self, result: FinishedRun) -> None:
        """Print the outcome, then raise ``typer.Exit`` for anything but success."""
        if result.success:
            typer.echo(f"Done: {result.reason}")
            return
        if self.is_wind_down(result):
            # Not a failure: the run handed its work over on purpose.
            typer.echo(f"Wound down: {result.reason}", err=True)
        else:
            typer.echo(f"Run failed: {result.reason}", err=True)
        raise typer.Exit(code=self.exit_code_for(result))
