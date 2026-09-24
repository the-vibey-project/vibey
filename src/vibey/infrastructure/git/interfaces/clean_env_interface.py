# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the executor every one of vibey's own git calls goes through.

Mirrors `vibey/infrastructure/git/clean_env.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.infrastructure.interfaces import CommandExecutor


@runtime_checkable
class GitExecutorInterface(CommandExecutor, Protocol):
    """Runs one `git` command for vibey itself: an allow-listed environment, and none of
    the repository's hooks or file-system monitor."""

    def neutralised(self, argv: tuple[str, ...]) -> tuple[str, ...]:
        """`argv` as it is actually run: git's own options that switch off
        repository-controlled execution, placed before the subcommand. Raises ValueError
        for anything that is not a git command."""
        ...
