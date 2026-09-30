# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of `infrastructure/git/worktree_manager.py` and
`infrastructure/git/integration_branch.py` (ADR-0016). Interfaces declare; they never
consume."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.interfaces import MergeOutcome
from vibey.domain.interfaces.worktree_interface import WorktreeNamingInterface


@runtime_checkable
class GitWorktreeManagerInterface(Protocol):
    """One project's BUILD worktrees for one cycle, each on a branch the project can
    prove it created."""

    @property
    def naming(self) -> WorktreeNamingInterface:
        """The project's names for this cycle."""
        ...

    def path_for(self, item_id: str) -> Path:
        """Where the item's worktree lives. No I/O."""
        ...

    async def create(self, item_id: str, *, base_ref: str = "HEAD") -> Path:
        """A clean worktree on the item's branch: reused when the project can prove the
        branch is its own, otherwise cut from `base_ref` and recorded. Raises
        `ForeignBranchRefused` -- before anything is wiped -- for a branch it cannot."""
        ...

    async def ensure(self, item_id: str, *, base_ref: str = "HEAD") -> Path:
        """Like `create`, but returns an already-registered worktree on the item's own
        branch untouched."""
        ...

    async def remove(self, item_id: str) -> None:
        """Removes the item's worktree, if there is one."""
        ...

    async def reclaim_orphans(self) -> tuple[Path, ...]:
        """Removes directories under this cycle's managed root git no longer knows."""
        ...


@runtime_checkable
class GitIntegrationBranchInterface(Protocol):
    """The branch one project's cycle integrates its verified items into."""

    async def ensure(self, *, base_ref: str = "HEAD") -> Path:
        """The integration worktree, created if it is not there yet."""
        ...

    async def merge_item(self, item_id: str) -> MergeOutcome:
        """Merges the item's branch -- after proving it is this project's -- into the
        integration branch."""
        ...
