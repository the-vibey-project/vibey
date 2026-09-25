# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/git/checkpoint.py` (ADR-0016). Interfaces declare; they
never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class GitCheckpointInterface(Protocol):
    """Commits everything in a worktree at an ULTRA checkpoint."""

    async def commit(self, worktree_path: Path, message: str) -> str | None:
        """The new commit's id, or `None` when there was nothing to commit. Raises
        `GitCheckpointError` when a git step fails."""
        ...
