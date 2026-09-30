# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The integration branch/worktree that build.integrate merges verified work
items into, one at a time (M6 task 6.8). Reuses GitWorktreeManager's scheme
with a reserved item_id, "integration", rather than inventing a second
worktree mechanism -- it accumulates state across many merges the same way
create()/ensure() already distinguish "wipe and recreate" from "return what's
already there".

The branch is the project's own (`WorktreeNaming.integration_branch`), and so is every
item branch merged into it: `merge_item` proves the item branch's ownership record
names this project before merging, so another project's branch can never be folded
into this one's delivery."""

from pathlib import Path

from vibey.application.build_integrate_handler import MergeOutcome
from vibey.domain.interfaces.worktree_interface import WorktreeNamingInterface
from vibey.domain.worktree import INTEGRATION_ITEM_ID
from vibey.infrastructure.git.branch_ownership import GitBranchOwnership
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.git.interfaces import RepositoryConfigGuardInterface
from vibey.infrastructure.git.interfaces.branch_ownership_interface import (
    GitBranchOwnershipInterface,
)
from vibey.infrastructure.git.interfaces.worktree_manager_interface import (
    GitIntegrationBranchInterface,
)
from vibey.infrastructure.git.repository_config_guard import RepositoryConfigGuard
from vibey.infrastructure.git.worktree_manager import GitWorktreeManager
from vibey.infrastructure.interfaces import CommandExecutor

__all__ = ["INTEGRATION_ITEM_ID", "IntegrationBranch"]


class IntegrationBranch:
    def __init__(
        self,
        repo_root: Path,
        *,
        naming: WorktreeNamingInterface,
        executor: CommandExecutor | None = None,
        guard: RepositoryConfigGuardInterface | None = None,
        ownership: GitBranchOwnershipInterface | None = None,
    ) -> None:
        self._naming = naming
        self._executor = executor or CleanGitEnvSubprocessExecutor()
        self._guard = guard if guard is not None else RepositoryConfigGuard(self._executor)
        self._ownership = (
            ownership
            if ownership is not None
            else GitBranchOwnership(repo_root, executor=self._executor)
        )
        self._worktrees = GitWorktreeManager(
            repo_root,
            naming=naming,
            executor=self._executor,
            guard=self._guard,
            ownership=self._ownership,
        )

    async def ensure(self, *, base_ref: str = "HEAD") -> Path:
        return await self._worktrees.ensure(INTEGRATION_ITEM_ID, base_ref=base_ref)

    async def merge_item(self, item_id: str) -> MergeOutcome:
        branch = self._naming.branch(item_id)
        await self._ownership.verify(branch, self._naming.project_id)
        path = await self.ensure()
        # A merge runs the merge and filter drivers the repository's config names.
        await self._guard.check(path)
        # `--no-verify` here is NOT skipping a gate: vibey's gates run separately, in
        # SubprocessGateRunner, before an item reaches integration. It switches off hooks
        # the REPOSITORY planted -- pre-merge-commit and commit-msg -- in vibey's own
        # internal merge plumbing, where an engine could have written them from its
        # linked worktree. The executor's `core.hooksPath=/dev/null` already does; this
        # says so at the call, and holds if the executor ever changes (clean_env.py).
        result = await self._executor.execute(
            ("git", "-C", str(path), "merge", "--no-edit", "--no-verify", branch)
        )
        if result.returncode == 0:
            return MergeOutcome(ok=True, detail="")

        # A merge conflict leaves the worktree mid-merge; abort so the next
        # attempt (this item's repair, or the next item entirely) starts
        # from a clean state rather than compounding on top of a half-merge.
        await self._executor.execute(("git", "-C", str(path), "merge", "--abort"))
        return MergeOutcome(ok=False, detail=(result.stderr.strip() or result.stdout.strip()))


_SEAM: type[GitIntegrationBranchInterface] = IntegrationBranch
"""Annotated so `mypy --strict` checks the class against its declared seam."""
