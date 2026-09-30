# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Real git-worktree lifecycle for BUILD work items (M6 task 6.2).

Every mutating call is preceded by a self-healing step (`git worktree
prune` plus removing any leftover directory at the target path) rather than
trusting prior state, because the property that matters is: a `create()`
call always succeeds in leaving a clean, usable worktree, even if the
previous attempt for the same item was killed mid-operation. That is what
makes "SIGKILL mid-create leaves no orphan worktree" true -- not a
best-effort cleanup step someone has to remember to call, but every create
healing whatever it finds first.

Self-healing never reaches past the project, though. Every name comes from the
project's `WorktreeNaming`, and a branch is reused, based on or merged only when its
ownership record (`GitBranchOwnership`) proves this project created it. That check runs
first, before anything is wiped: a branch the project cannot prove is its own raises
`ForeignBranchRefused` with nothing on disk or in the refs touched. A branch the manager
creates is recorded -- project and base commit -- before it exists, so a create killed
half-way leaves a branch that still proves whose it is, and the replay reuses it.
"""

import shutil
from pathlib import Path

from vibey.domain.interfaces.worktree_interface import WorktreeNamingInterface
from vibey.infrastructure.git.branch_ownership import GitBranchOwnership
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.git.errors import WorktreeError
from vibey.infrastructure.git.interfaces import RepositoryConfigGuardInterface
from vibey.infrastructure.git.interfaces.branch_ownership_interface import (
    GitBranchOwnershipInterface,
)
from vibey.infrastructure.git.interfaces.worktree_manager_interface import (
    GitWorktreeManagerInterface,
)
from vibey.infrastructure.git.repository_config_guard import RepositoryConfigGuard
from vibey.infrastructure.interfaces import CommandExecutor

__all__ = ["GitWorktreeManager", "WorktreeError"]


class GitWorktreeManager:
    def __init__(
        self,
        repo_root: Path,
        *,
        naming: WorktreeNamingInterface,
        executor: CommandExecutor | None = None,
        guard: RepositoryConfigGuardInterface | None = None,
        ownership: GitBranchOwnershipInterface | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._naming = naming
        self._executor = executor or CleanGitEnvSubprocessExecutor()
        # A checkout runs the filter drivers the repository's config names; an engine
        # can write that config from its linked worktree (clean_env.py).
        self._guard = guard if guard is not None else RepositoryConfigGuard(self._executor)
        self._ownership = (
            ownership
            if ownership is not None
            else GitBranchOwnership(repo_root, executor=self._executor)
        )

    @property
    def naming(self) -> WorktreeNamingInterface:
        return self._naming

    def path_for(self, item_id: str) -> Path:
        """No I/O, no mutation: where this item's worktree lives (or would
        live), for callers like build.verify that must operate on an
        already-created worktree without create()'s self-healing wipe."""
        return self._repo_root / self._naming.worktree_subpath(item_id)

    async def create(self, item_id: str, *, base_ref: str = "HEAD") -> Path:
        path = self._repo_root / self._naming.worktree_subpath(item_id)
        branch = self._naming.branch(item_id)

        # Whose the branch is, and where a new one starts, are settled before anything
        # is wiped: a refusal leaves the repository exactly as it was found.
        existing = await self._branch_exists(branch)
        base = ""
        if existing:
            await self._ownership.verify(branch, self._naming.project_id)
        else:
            base = await self._base_commit(base_ref)

        if path.exists():
            shutil.rmtree(path)
        await self._prune()

        path.parent.mkdir(parents=True, exist_ok=True)
        await self._guard.check(self._repo_root)
        if existing:
            await self._git("worktree", "add", str(path), branch)
        else:
            # Recorded before the branch exists: a create killed between here and the
            # branch landing leaves a record for a branch that is not there (the replay
            # records again), never a branch with no record (which would be refused).
            await self._ownership.record(branch, project_id=self._naming.project_id, base=base)
            await self._git("worktree", "add", "-b", branch, str(path), base)
        return path

    async def ensure(self, item_id: str, *, base_ref: str = "HEAD") -> Path:
        """Like create(), but never wipes an already-registered worktree --
        for callers (the integration branch) that accumulate state across
        many calls and must not have create()'s self-healing wipe undo a
        prior successful merge."""
        path = self._repo_root / self._naming.worktree_subpath(item_id)
        if path.exists() and path.resolve() in {
            Path(p).resolve() for p in await self._list_worktree_paths()
        }:
            # Returned untouched, but not unexamined: a worktree accumulating merges
            # must still be on a branch this project can prove it created.
            await self._ownership.verify(self._naming.branch(item_id), self._naming.project_id)
            return path
        return await self.create(item_id, base_ref=base_ref)

    async def remove(self, item_id: str) -> None:
        path = self._repo_root / self._naming.worktree_subpath(item_id)
        if path.exists():
            await self._git("worktree", "remove", str(path), "--force")
        await self._prune()

    async def reclaim_orphans(self) -> tuple[Path, ...]:
        """Prunes stale git administrative state, then removes any directory
        under this project's managed worktree root for the cycle that git no
        longer recognizes as a registered worktree -- the leftover of a create
        that died before `git worktree add` completed, or a remove that died
        after git dropped its registration but before the directory was
        deleted. Another project's worktrees live under another root and are
        never looked at."""
        await self._prune()
        registered = {Path(p).resolve() for p in await self._list_worktree_paths()}

        managed_root = self._repo_root / self._naming.managed_root
        if not managed_root.exists():
            return ()

        removed = []
        for entry in sorted(managed_root.iterdir()):
            if entry.resolve() not in registered:
                shutil.rmtree(entry, ignore_errors=True)
                removed.append(entry)
        return tuple(removed)

    async def _base_commit(self, base_ref: str) -> str:
        """The commit a new branch is cut from, resolved once and recorded with it.

        base_ref is a preference, not a hard requirement: callers ask for the project's
        integration branch so item branches stack on already-integrated code, but before
        the first integrate that branch does not exist yet -- fall back to HEAD (the
        project's own checkout, which the delivery bridge detaches at its base) rather
        than failing every early item. A branch in vibey's namespace that does exist is
        used only once it is proved this project's, and an old job's cycle-keyed base is
        read as the project's own integration branch, never looked up as written."""
        ref = self._naming.resolve_base(base_ref)
        if ref != "HEAD" and not await self._ref_exists(ref):
            ref = "HEAD"
        if ref != "HEAD" and self._naming.is_managed(ref):
            await self._ownership.verify(ref, self._naming.project_id)
        argv = ("git", "-C", str(self._repo_root), "rev-parse", "--verify", f"{ref}^{{commit}}")
        result = await self._executor.execute(argv)
        if result.returncode != 0:
            raise WorktreeError(argv, result.stderr)
        return result.stdout.strip()

    async def _branch_exists(self, branch: str) -> bool:
        """Whether the local branch exists -- only `refs/heads/`, so a tag or a remote
        ref that happens to share the name is never taken for the project's branch."""
        return await self._ref_exists(f"refs/heads/{branch}")

    async def _ref_exists(self, ref: str) -> bool:
        result = await self._executor.execute(
            ("git", "-C", str(self._repo_root), "rev-parse", "--verify", "--quiet", ref)
        )
        return result.returncode == 0

    async def _list_worktree_paths(self) -> tuple[str, ...]:
        result = await self._executor.execute(
            ("git", "-C", str(self._repo_root), "worktree", "list", "--porcelain")
        )
        if result.returncode != 0:
            raise WorktreeError(("worktree", "list", "--porcelain"), result.stderr)
        return tuple(
            line.removeprefix("worktree ")
            for line in result.stdout.splitlines()
            if line.startswith("worktree ")
        )

    async def _prune(self) -> None:
        await self._git("worktree", "prune")
        # Removing/pruning worktrees can leave the primary checkout marked
        # core.bare=true (observed live during the expansion-13 build;
        # same class as scripts/fleet/land.sh's guard). The primary
        # checkout is never actually bare, so reasserting is always safe --
        # and _prune() runs inside every mutating path (create, ensure,
        # remove, reclaim_orphans), so no lifecycle escapes the guard.
        await self._git("config", "core.bare", "false")

    async def _git(self, *args: str) -> None:
        argv = ("git", "-C", str(self._repo_root), *args)
        result = await self._executor.execute(argv)
        if result.returncode != 0:
            raise WorktreeError(argv, result.stderr)


_SEAM: type[GitWorktreeManagerInterface] = GitWorktreeManager
"""Annotated so `mypy --strict` checks the class against its declared seam."""
