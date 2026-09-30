# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/git/branch_ownership.py` (ADR-0016). Interfaces declare;
they never consume."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.interfaces.worktree_interface import BranchOwnershipInterface


@runtime_checkable
class GitBranchOwnershipInterface(Protocol):
    """Records, in the repository itself, which project created a BUILD branch and the
    commit it was cut from; reads that record back and proves a branch is a project's."""

    async def record(self, branch: str, *, project_id: UUID, base: str) -> None:
        """Writes the record. Called before the branch is created, so a create killed
        half-way still leaves a branch that proves whose it is."""
        ...

    async def read(self, branch: str) -> BranchOwnershipInterface:
        """The record as written; absent values read as `None`. Raises `WorktreeError`
        when the repository's config cannot be read."""
        ...

    async def verify(self, branch: str, project_id: UUID) -> str:
        """The branch's recorded base when the record names `project_id` and that base
        is still in the branch's history. Raises `ForeignBranchRefused` otherwise."""
        ...
