# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which project created a BUILD branch, recorded in the repository beside the branch.

The record is two keys in the repository's own config, under the branch's section:
`branch.<name>.vibey-project` (the full project id) and `branch.<name>.vibey-base` (the
commit the branch was cut from). Git keeps a branch's config section with the branch --
`git branch -m` carries it, `git branch -D` drops it -- and every linked worktree of a
repository reads the one config, exactly as it reads the one set of refs. That is the
property the defect needed: the delivery bridge's worktrees share the main checkout's
refs, so the proof of whose a branch is has to be shared the same way.

Why not the ledger: the proof must travel with the branch, not with vibey's database. A
branch someone else created -- another project, a person, a tool -- has no ledger row to
contradict it, and a missing row proves nothing. A branch with no record here is refused.
"""

from pathlib import Path
from typing import Final
from uuid import UUID

from vibey.domain.errors import ForeignBranchRefused
from vibey.domain.worktree import BranchOwnership
from vibey.infrastructure.git.errors import WorktreeError
from vibey.infrastructure.git.interfaces.branch_ownership_interface import (
    GitBranchOwnershipInterface,
)
from vibey.infrastructure.interfaces import CommandExecutor

PROJECT_KEY: Final = "vibey-project"
"""The config key, under `branch.<name>`, naming the project that created the branch."""

BASE_KEY: Final = "vibey-base"
"""The config key, under `branch.<name>`, naming the commit the branch was cut from."""

_MISSING = 1
"""`git config --get`'s exit code for a key that is not set."""


class GitBranchOwnership:
    """Records and proves whose a BUILD branch is, in one repository."""

    def __init__(self, repo_root: Path, *, executor: CommandExecutor) -> None:
        self._repo_root = repo_root
        self._executor = executor

    async def record(self, branch: str, *, project_id: UUID, base: str) -> None:
        await self._set(branch, PROJECT_KEY, str(project_id))
        await self._set(branch, BASE_KEY, base)

    async def read(self, branch: str) -> BranchOwnership:
        return BranchOwnership(
            branch=branch,
            project_id=await self._get(branch, PROJECT_KEY),
            base=await self._get(branch, BASE_KEY),
        )

    async def verify(self, branch: str, project_id: UUID) -> str:
        base = (await self.read(branch)).verify(project_id)
        # The record alone is not enough: a branch reset or force-moved onto other history
        # keeps its config. The base it was cut from must still be in its history.
        ancestry = await self._executor.execute(
            (
                "git",
                "-C",
                str(self._repo_root),
                "merge-base",
                "--is-ancestor",
                base,
                f"refs/heads/{branch}",
            )
        )
        if ancestry.returncode != 0:
            raise ForeignBranchRefused(
                branch, project_id, f"its recorded base {base} is not in its history"
            )
        return base

    async def _set(self, branch: str, key: str, value: str) -> None:
        argv = ("git", "-C", str(self._repo_root), "config", "--local", _key(branch, key), value)
        result = await self._executor.execute(argv)
        if result.returncode != 0:
            raise WorktreeError(argv, result.stderr)

    async def _get(self, branch: str, key: str) -> str | None:
        argv = ("git", "-C", str(self._repo_root), "config", "--local", "--get", _key(branch, key))
        result = await self._executor.execute(argv)
        if result.returncode == _MISSING:
            return None
        if result.returncode != 0:
            raise WorktreeError(argv, result.stderr)
        return result.stdout.strip() or None


# Module-level rather than a method (ADR-0016's written reason): a pure spelling of one
# git config key, shared by both the reader and the writer and holding no state.
def _key(branch: str, key: str) -> str:
    return f"branch.{branch}.{key}"


_SEAM: type[GitBranchOwnershipInterface] = GitBranchOwnership
"""Annotated so `mypy --strict` checks the class against its declared seam."""
