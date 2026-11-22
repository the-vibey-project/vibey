# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for running `PostgresLocalService`'s commands from inside `vibey acp` (SP-ACP)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.postgres import PostgresCommandResult


@runtime_checkable
class AcpCommandRunnerInterface(Protocol):
    def __call__(self, argv: tuple[str, ...]) -> PostgresCommandResult:
        """Run one fixed argv in a process group of its own, with stdin closed, its output
        captured, a minimal environment and a bound on its time; a `sudo` never prompts
        (`sudo -n`). Past the bound the whole group is stopped (SIGTERM, then SIGKILL). A command
        that cannot start, overruns or may still be running is a result, never an exception."""
        ...

    @staticmethod
    def still_running(result: PostgresCommandResult) -> bool:
        """True when `result` is a command that overran and could not be confirmed stopped."""
        ...

    @staticmethod
    def password_refused(argv: tuple[str, ...], result: PostgresCommandResult) -> bool:
        """True when `argv` was a `sudo` that failed because it wanted a password."""
        ...
