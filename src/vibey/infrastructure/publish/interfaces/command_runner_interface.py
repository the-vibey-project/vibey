# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for running one program with a bounded, allow-listed environment."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.infrastructure.engines.claudeloop_process import CommandResult


@runtime_checkable
class ProgramRunnerInterface(Protocol):
    """Runs `argv` (never through a shell) in `cwd` and answers with what it said."""

    async def run(self, argv: tuple[str, ...], *, cwd: Path | None = None) -> CommandResult:
        """Exit 127 when the program is not there and 124 when it ran out of time: the
        publisher words those, so no caller catches an exception for them."""
        ...
