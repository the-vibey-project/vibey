# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for refusing a repository that declares programs for vibey's git to run.

Mirrors `vibey/infrastructure/git/repository_config_guard.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class RepositoryConfigGuardInterface(Protocol):
    """Checks a repository's own config before vibey checks out or merges in it."""

    async def check(self, directory: Path) -> None:
        """Raise `RepositoryExecutionRefused` when the repository-scope config seen from
        `directory` declares a filter or merge driver, or cannot be read."""
        ...

    def offending(self, listing: str) -> tuple[str, ...]:
        """The refused keys in a `git config --list --show-scope -z` listing."""
        ...
