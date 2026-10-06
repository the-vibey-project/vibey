# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/vibey_remote.py` implements. Interfaces declare; they never consume.

The *runner* is the runner-side half of `vibey -w` (ADR-0085): it takes the command line a
caller dispatched, holds it to the domain's rules, prepares the database, runs the command and
writes the report the caller reads back.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol


class ProcessRunnerInterface(Protocol):
    """Runs one argument vector, never through a shell."""

    def run(
        self, argv: Sequence[str], env: Mapping[str, str], timeout_s: float
    ) -> tuple[int, str, str]:
        """Exit code, stdout, stderr. A timeout is exit 124 with the reason on stderr."""
        ...


class VibeyRemoteRunnerInterface(Protocol):
    """Runs one dispatched vibey command and writes its report."""

    def run(self, raw_argv: str, request: str, out: Path) -> dict[str, object]:
        """The report written to `out/result.json`: exit_code, stdout, stderr."""
        ...
