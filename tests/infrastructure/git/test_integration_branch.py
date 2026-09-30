# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Real-git integration tests for IntegrationBranch -- no mocking, same
rule as the rest of infrastructure/git/'s tests."""

from pathlib import Path
from uuid import UUID

import pytest

from vibey.domain.errors import ForeignBranchRefused
from vibey.domain.worktree import WorktreeNaming
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.git.integration_branch import IntegrationBranch
from vibey.infrastructure.git.interfaces import GitIntegrationBranchInterface
from vibey.infrastructure.git.worktree_manager import GitWorktreeManager

PROJECT = UUID("893c4fc1-542e-411e-a10a-3aef784b1540")
OTHER = UUID("11111111-2222-3333-4444-555555555555")


def _naming(cycle: int = 1, project: UUID = PROJECT) -> WorktreeNaming:
    return WorktreeNaming(project, cycle)


async def _run(*argv: str) -> None:
    result = await CleanGitEnvSubprocessExecutor().execute(argv)
    assert result.returncode == 0, result.stderr


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    await _run("git", "-C", str(tmp_path), "init", "-q", "-b", "main")
    await _run("git", "-C", str(tmp_path), "config", "user.email", "test@example.com")
    await _run("git", "-C", str(tmp_path), "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("hello\n")
    await _run("git", "-C", str(tmp_path), "add", "README.md")
    await _run("git", "-C", str(tmp_path), "commit", "-q", "-m", "initial")
    return tmp_path


async def _make_item_branch(
    repo: Path, cycle: int, item_id: str, filename: str, *, project: UUID = PROJECT
) -> None:
    worktrees = GitWorktreeManager(repo, naming=_naming(cycle, project))
    path = await worktrees.create(item_id)
    (path / filename).write_text(f"content from {item_id}\n")
    await _run("git", "-C", str(path), "add", filename)
    await _run("git", "-C", str(path), "commit", "-q", "-m", f"add {filename}")


async def test_merge_item_accumulates_multiple_non_conflicting_items(repo: Path) -> None:
    await _make_item_branch(repo, 1, "item-1", "a.txt")
    await _make_item_branch(repo, 1, "item-2", "b.txt")
    integration = IntegrationBranch(repo, naming=_naming())

    first = await integration.merge_item("item-1")
    second = await integration.merge_item("item-2")

    assert first.ok
    assert second.ok
    path = await integration.ensure()
    assert (path / "a.txt").exists()
    assert (path / "b.txt").exists()
    assert isinstance(integration, GitIntegrationBranchInterface)


async def test_merge_item_detects_a_real_conflict_and_leaves_a_clean_worktree(repo: Path) -> None:
    await _make_item_branch(repo, 1, "item-1", "shared.txt")
    # item-2 branches from the same original HEAD and edits the same new
    # path differently -- a genuine conflict, not simulated.
    worktrees = GitWorktreeManager(repo, naming=_naming())
    item_2_path = await worktrees.create("item-2")
    (item_2_path / "shared.txt").write_text("conflicting content from item-2\n")
    await _run("git", "-C", str(item_2_path), "add", "shared.txt")
    await _run("git", "-C", str(item_2_path), "commit", "-q", "-m", "add shared.txt differently")

    integration = IntegrationBranch(repo, naming=_naming())
    first = await integration.merge_item("item-1")
    second = await integration.merge_item("item-2")

    assert first.ok
    assert not second.ok
    assert second.detail

    # the worktree is left clean -- no merge in progress -- so the next
    # merge_item() call (a repair, or the next item) isn't blocked by it.
    path = await integration.ensure()
    status = await CleanGitEnvSubprocessExecutor().execute(
        ("git", "-C", str(path), "status", "--porcelain=v1")
    )
    assert "UU" not in status.stdout
    merge_head = path / ".git"
    assert merge_head.exists()  # sanity: still a real worktree
    in_progress = await CleanGitEnvSubprocessExecutor().execute(
        ("git", "-C", str(path), "rev-parse", "--verify", "-q", "MERGE_HEAD")
    )
    assert in_progress.returncode != 0  # no merge in progress


async def test_ensure_does_not_wipe_prior_merges(repo: Path) -> None:
    await _make_item_branch(repo, 1, "item-1", "a.txt")
    integration = IntegrationBranch(repo, naming=_naming())
    await integration.merge_item("item-1")

    path = await integration.ensure()

    assert (path / "a.txt").exists()


async def test_integration_branch_name_matches_the_domain_scheme(repo: Path) -> None:
    naming = _naming(cycle=3)
    integration = IntegrationBranch(repo, naming=naming)
    path = await integration.ensure()

    branches = await CleanGitEnvSubprocessExecutor().execute(
        ("git", "-C", str(repo), "branch", "--list", naming.integration_branch)
    )
    assert "vibey/893c4fc1/3/integration" in branches.stdout
    assert path == repo / ".vibey" / "worktrees" / "893c4fc1" / "3" / "integration"


async def test_another_projects_item_branch_is_never_merged(repo: Path) -> None:
    """Two projects in one repository, cycle 1 each: an item branch under this project's
    name that another project created is refused before the merge -- and before this
    project's integration worktree is even created."""
    await _make_item_branch(repo, 1, "item-1", "theirs.txt", project=OTHER)
    await GitWorktreeManager(repo, naming=_naming(1, OTHER)).remove("item-1")
    # Their branch, renamed to our name: `git branch -m` carries their ownership record.
    theirs = _naming(1, OTHER).branch("item-1")
    await _run("git", "-C", str(repo), "branch", "-m", theirs, _naming().branch("item-1"))
    integration = IntegrationBranch(repo, naming=_naming())

    with pytest.raises(ForeignBranchRefused, match=f"records project {OTHER}"):
        await integration.merge_item("item-1")

    assert not (repo / _naming().worktree_subpath("integration")).exists()
