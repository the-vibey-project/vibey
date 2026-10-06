# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/vibey_remote.py` implements. Interfaces declare; they never consume.

The *runner* is the runner-side half of `vibey -w` (ADR-0085): it takes the command line a
caller dispatched, holds it to the domain's rules, prepares the database, runs the command and
writes the report the caller reads back.
"""

from pathlib import Path
from typing import Protocol

# One process runner for both scripts: `vibey -w` uses the state action's (ADR-0086).
from .vibey_state_action_interface import ProcessRunnerInterface

__all__ = ["ProcessRunnerInterface", "VibeyRemoteRunnerInterface"]


class VibeyRemoteRunnerInterface(Protocol):
    """Runs one dispatched vibey command and writes its report."""

    def run(
        self, raw_argv: str, request: str, out: Path, state_out: Path | None = None
    ) -> dict[str, object]:
        """The report written to `out/result.json`: exit_code, stdout, stderr, and whether
        the synced state was exported to `state_out` for the `sync-back` job (ADR-0086)."""
        ...

    def sync_back(self, state: Path) -> tuple[int, str]:
        """Import the run's sealed export into an empty database and sync it with the
        branch: the exit code, and what was said. The state action's `write_back`."""
        ...
