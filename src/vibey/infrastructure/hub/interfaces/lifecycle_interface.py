# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of `infrastructure/hub/lifecycle.py` (ADR-0016, ADR-0091). Interfaces declare; they
never consume."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.hub.lifecycle import CommandResult


@runtime_checkable
class VibeyCommandRunnerInterface(Protocol):
    """Runs one `vibey` command line on this host and says what it printed and how it ended."""

    def run(self, args: Sequence[str]) -> CommandResult: ...


@runtime_checkable
class ProjectFoldersInterface(Protocol):
    """Makes the folder a new project works in."""

    def make(self, path: Path) -> None:
        """Create `path` as a git repository with one commit. Raises `FileExistsError` when
        something is already there, and `OSError` when it cannot be made."""
        ...
