# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How a finished autonomous run becomes a process exit status.

Shared by `run` and `resume` so the two can never disagree about what a status
means — they did: `resume` used to report a deliberate wind-down as a failure
(exit 1) where `run` exits 75. A supervisor branches on these without parsing
text:

  0    done
  1    failed (blocked, budget or max-wait exhausted, authentication failed, …)
  75   wound down on purpose; ``handoff.json`` names what was produced
  78   the backend, as configured, cannot serve the run (unreachable, model
       missing, model failed to load) — a human must fix the profile or the server
  130  soft-stopped by an operator
"""

from __future__ import annotations

from pathlib import Path

import typer

from claudeloop.application.dto import RunResult
from claudeloop.domain.backend import BACKEND_MISCONFIGURED_PREFIX, EXIT_BACKEND_MISCONFIGURED
from claudeloop.domain.handoff_marker import EXIT_WIND_DOWN

WIND_DOWN_PREFIX = "wind-down:"
EXIT_FAILED = 1
EXIT_STOPPED = 130


class RunOutcomeReporter:
    def report(
        self, result: RunResult, *, handoff_marker: Path, stop_summary: Path, profile: str
    ) -> None:
        if result.success:
            typer.echo(f"Done: {result.reason}")
            return
        if result.reason.startswith(WIND_DOWN_PREFIX):
            # Not a failure: the run handed its work over on purpose.
            typer.echo(f"Wound down: {result.reason}", err=True)
            if handoff_marker.is_file():
                typer.echo(f"Handoff: {handoff_marker}", err=True)
            raise typer.Exit(code=EXIT_WIND_DOWN)
        typer.echo(f"Run failed: {result.reason}", err=True)
        if result.reason.startswith(BACKEND_MISCONFIGURED_PREFIX):
            typer.echo(
                f"Fix the backend, then check it with `claudeloop doctor --profile {profile}`.",
                err=True,
            )
            raise typer.Exit(code=EXIT_BACKEND_MISCONFIGURED)
        if "stopped" in result.reason:
            if stop_summary.is_file():
                typer.echo(f"Stop summary: {stop_summary}", err=True)
            raise typer.Exit(code=EXIT_STOPPED)
        raise typer.Exit(code=EXIT_FAILED)
