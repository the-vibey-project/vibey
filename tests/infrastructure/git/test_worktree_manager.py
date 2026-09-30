# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Real-git integration tests -- no mocking of git itself, per this
project's own rule about not faking the property that matters. Runs
against a real repo created fresh in tmp_path for every test; the real
repository's refs are never touched."""

import asyncio
import os
from pathlib import Path
from uuid import UUID

import pytest

from vibey.domain.errors import ForeignBranchRefused
from vibey.domain.worktree import WorktreeNaming
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.git.branch_ownership import BASE_KEY, PROJECT_KEY, GitBranchOwnership
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.git.interfaces import GitWorktreeManagerInterface
from vibey.infrastructure.git.worktree_manager import GitWorktreeManager, WorktreeError

PROJECT = UUID("893c4fc1-542e-411e-a10a-3aef784b1540")
OTHER = UUID("11111111-2222-3333-4444-555555555555")
NAMING = WorktreeNaming(PROJECT, 1)


async def _run(*argv: str) -> CommandResult:
    return await CleanGitEnvSubprocessExecutor().execute(argv)


async def _sha(repo: Path, ref: str) -> str:
    return (await _run("git", "-C", str(repo), "rev-parse", ref)).stdout.strip()


async def _config(repo: Path, key: str) -> str:
    return (await _run("git", "-C", str(repo), "config", "--get", key)).stdout.strip()


def _clean_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def _manager(repo: Path, naming: WorktreeNaming = NAMING) -> GitWorktreeManager:
    return GitWorktreeManager(repo, naming=naming)


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    await _run("git", "-C", str(tmp_path), "init", "-q", "-b", "main")
    await _run("git", "-C", str(tmp_path), "config", "user.email", "test@example.com")
    await _run("git", "-C", str(tmp_path), "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("hello\n")
    await _run("git", "-C", str(tmp_path), "add", "README.md")
    await _run("git", "-C", str(tmp_path), "commit", "-q", "-m", "initial")
    return tmp_path


async def _plant_stale_history(repo: Path, *branches: str) -> str:
    """Another project's branches, on history of its own (an orphan root), as an earlier
    delivery left them in the live repository. Returns their commit."""
    await _run("git", "-C", str(repo), "checkout", "-q", "--orphan", "stale")
    (repo / "README.md").write_text("an unrelated project\n")
    await _run("git", "-C", str(repo), "add", "README.md")
    await _run("git", "-C", str(repo), "commit", "-q", "-m", "unrelated project")
    for branch in branches:
        await _run("git", "-C", str(repo), "branch", branch)
    await _run("git", "-C", str(repo), "checkout", "-q", "main")
    return await _sha(repo, "stale")


async def test_create_adds_a_worktree_on_a_new_project_scoped_branch(repo: Path) -> None:
    manager = _manager(repo)

    path = await manager.create("item-1")

    assert path == repo / ".vibey" / "worktrees" / "893c4fc1" / "1" / "item-1"
    assert path.exists()
    assert (path / "README.md").exists()
    listed = await _run("git", "-C", str(repo), "branch", "--list", "vibey/893c4fc1/1/item-1")
    assert "vibey/893c4fc1/1/item-1" in listed.stdout
    assert isinstance(manager, GitWorktreeManagerInterface)
    assert manager.naming is NAMING


async def test_create_records_the_project_and_the_base_commit_it_cut_from(repo: Path) -> None:
    head = await _sha(repo, "HEAD")

    await _manager(repo).create("item-1")

    assert await _config(repo, f"branch.vibey/893c4fc1/1/item-1.{PROJECT_KEY}") == str(PROJECT)
    assert await _config(repo, f"branch.vibey/893c4fc1/1/item-1.{BASE_KEY}") == head


async def test_create_is_idempotent_after_a_prior_successful_create(repo: Path) -> None:
    manager = _manager(repo)
    first = await manager.create("item-1")
    (first / "scratch.txt").write_text("uncommitted work")

    second = await manager.create("item-1")

    assert second == first
    assert second.exists()
    # create() self-heals by removing and recreating -- uncommitted scratch
    # files in an existing worktree do not survive a second create() for the
    # same item, which is the correct behavior for recovering from a bad
    # prior attempt, not a data-loss bug: nothing here was ever committed.
    assert not (second / "scratch.txt").exists()


async def test_create_reuses_the_projects_own_branch_and_its_commits(repo: Path) -> None:
    manager = _manager(repo)
    first = await manager.create("item-1")
    (first / "work.txt").write_text("committed work\n")
    await _run("git", "-C", str(first), "add", "work.txt")
    await _run("git", "-C", str(first), "commit", "-q", "-m", "work")

    again = await manager.create("item-1")

    assert (again / "work.txt").read_text() == "committed work\n"


async def test_create_recovers_from_a_dangling_branch_left_by_a_killed_attempt(repo: Path) -> None:
    # Simulate the branch half of a create() that died before `git worktree add`
    # finished: the ownership record is written first, so the branch exists and proves
    # whose it is, but no worktree or directory does.
    await GitBranchOwnership(repo, executor=CleanGitEnvSubprocessExecutor()).record(
        "vibey/893c4fc1/1/item-1", project_id=PROJECT, base=await _sha(repo, "HEAD")
    )
    await _run("git", "-C", str(repo), "branch", "vibey/893c4fc1/1/item-1")

    path = await _manager(repo).create("item-1")

    assert path.exists()
    assert (path / "README.md").exists()


async def test_create_removes_a_leftover_directory_with_no_git_registration(repo: Path) -> None:
    manager = _manager(repo)
    orphan_dir = repo / NAMING.worktree_subpath("item-1")
    orphan_dir.mkdir(parents=True)
    (orphan_dir / "partial-checkout-fragment").write_text("leftover from a killed create")

    path = await manager.create("item-1")

    assert path.exists()
    assert not (path / "partial-checkout-fragment").exists()
    assert (path / "README.md").exists()


# -- the collision: projects sharing one repository ------------------------------------


async def test_a_stale_cycle_keyed_branch_of_another_project_is_never_adopted(
    repo: Path,
) -> None:
    """The live defect (project 893c4fc1 delivering #963): an August project's `vibey/1/ws`
    and `vibey/1/integration` were in the repository, and cycle 1's BUILD checked out
    `vibey/1/ws` and edited that project's codebase. Now the item gets its own branch, cut
    from the project's base, and the stale branches are left exactly as they were."""
    stale = await _plant_stale_history(repo, "vibey/1/ws", "vibey/1/integration")

    # The base an old job recorded -- the cycle-keyed integration branch -- included.
    path = await _manager(repo).create("ws", base_ref="vibey/1/integration")

    head = await _run("git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD")
    assert head.stdout.strip() == "vibey/893c4fc1/1/ws"
    assert (path / "README.md").read_text() == "hello\n"
    assert await _sha(repo, "vibey/1/ws") == stale
    assert await _sha(repo, "vibey/1/integration") == stale


async def test_two_projects_in_cycle_one_each_get_their_own_branches_and_worktrees(
    repo: Path,
) -> None:
    ours, theirs = _manager(repo), _manager(repo, WorktreeNaming(OTHER, 1))
    our_path = await ours.create("ws")
    (our_path / "scratch.txt").write_text("our uncommitted work")

    their_path = await theirs.create("ws")

    assert our_path != their_path
    assert (our_path / "scratch.txt").exists()  # the other project wiped nothing of ours
    assert await _config(repo, f"branch.vibey/893c4fc1/1/ws.{PROJECT_KEY}") == str(PROJECT)
    assert await _config(repo, f"branch.vibey/11111111/1/ws.{PROJECT_KEY}") == str(OTHER)
    with pytest.raises(ForeignBranchRefused):
        await GitBranchOwnership(repo, executor=CleanGitEnvSubprocessExecutor()).verify(
            "vibey/11111111/1/ws", PROJECT
        )


async def test_a_branch_with_the_projects_name_but_no_record_is_refused_untouched(
    repo: Path,
) -> None:
    """Defence in depth: the name is not the proof. A branch someone else created under
    this project's name -- a person, a tool, a project whose id shares eight digits -- is
    refused before anything on disk or in the refs is touched."""
    await _plant_stale_history(repo, "vibey/893c4fc1/1/ws")
    before = await _sha(repo, "vibey/893c4fc1/1/ws")
    leftover = repo / NAMING.worktree_subpath("ws")
    leftover.mkdir(parents=True)
    (leftover / "keep.txt").write_text("not ours to wipe")

    with pytest.raises(ForeignBranchRefused, match="records no creating project"):
        await _manager(repo).create("ws")

    assert await _sha(repo, "vibey/893c4fc1/1/ws") == before
    assert (leftover / "keep.txt").exists()


async def test_a_branch_recording_another_project_is_refused(repo: Path) -> None:
    await _run("git", "-C", str(repo), "branch", "vibey/893c4fc1/1/ws")
    await GitBranchOwnership(repo, executor=CleanGitEnvSubprocessExecutor()).record(
        "vibey/893c4fc1/1/ws", project_id=OTHER, base=await _sha(repo, "HEAD")
    )

    with pytest.raises(ForeignBranchRefused, match=f"records project {OTHER}"):
        await _manager(repo).create("ws")


async def test_a_branch_moved_off_its_recorded_base_is_refused(repo: Path) -> None:
    """The record alone is not enough: a branch reset onto other history keeps its config."""
    await _manager(repo).create("ws")
    await _manager(repo).remove("ws")
    stale = await _plant_stale_history(repo)
    await _run("git", "-C", str(repo), "branch", "-f", "vibey/893c4fc1/1/ws", stale)

    with pytest.raises(ForeignBranchRefused, match="is not in its history"):
        await _manager(repo).create("ws")


async def test_a_foreign_branch_in_vibeys_namespace_is_never_used_as_a_base(repo: Path) -> None:
    await _plant_stale_history(repo, "vibey/1/ws")

    with pytest.raises(ForeignBranchRefused, match="records no creating project"):
        await _manager(repo).create("item-2", base_ref="vibey/1/ws")

    missing = await _run("git", "-C", str(repo), "rev-parse", "--verify", NAMING.branch("item-2"))
    assert missing.returncode != 0  # refused before any branch was cut


async def test_a_base_outside_vibeys_namespace_is_used_as_given(repo: Path) -> None:
    await _run("git", "-C", str(repo), "branch", "develop")
    (repo / "later.txt").write_text("after develop\n")
    await _run("git", "-C", str(repo), "add", "later.txt")
    await _run("git", "-C", str(repo), "commit", "-q", "-m", "later")

    path = await _manager(repo).create("item-1", base_ref="develop")

    assert not (path / "later.txt").exists()
    assert await _config(repo, f"branch.{NAMING.branch('item-1')}.{BASE_KEY}") == await _sha(
        repo, "develop"
    )


async def test_create_uses_the_projects_own_integration_branch_as_base(repo: Path) -> None:
    manager = _manager(repo)
    await manager.create("integration")
    marker = repo / "integrated.txt"
    marker.write_text("integrated\n")
    await _run("git", "-C", str(repo), "add", "integrated.txt")
    await _run("git", "-C", str(repo), "commit", "-q", "-m", "integrated state")
    # The integration branch is BEHIND main now; a worktree from it must
    # not contain the marker, proving base_ref was honored over HEAD.

    worktree = await manager.create("late-item", base_ref=NAMING.integration_branch)

    assert not (worktree / "integrated.txt").exists()


async def test_create_falls_back_to_head_when_base_ref_is_missing(repo: Path) -> None:
    """Item branches prefer the project's integration branch, which does not
    exist before the first integrate -- early items must still build."""
    worktree = await _manager(repo).create("early-item", base_ref=NAMING.integration_branch)

    head = await _run("git", "-C", str(worktree), "rev-parse", "--abbrev-ref", "HEAD")
    assert head.stdout.strip() == "vibey/893c4fc1/1/early-item"


# -- the rest of the lifecycle ----------------------------------------------------------


async def test_remove_deletes_the_worktree_and_its_registration(repo: Path) -> None:
    manager = _manager(repo)
    path = await manager.create("item-1")
    assert path.exists()

    await manager.remove("item-1")

    assert not path.exists()
    listed = await _run("git", "-C", str(repo), "worktree", "list", "--porcelain")
    assert str(path) not in listed.stdout


async def test_remove_of_an_already_gone_worktree_is_a_no_op(repo: Path) -> None:
    await _manager(repo).remove("never-created")  # must not raise


async def test_reclaim_orphans_removes_directories_git_does_not_recognize(repo: Path) -> None:
    manager = _manager(repo)
    kept = await manager.create("item-1")
    orphan = repo / NAMING.worktree_subpath("item-2")
    orphan.mkdir(parents=True)
    (orphan / "junk").write_text("not a real worktree")
    # Another project's directory is under another root, and is never looked at.
    theirs = repo / WorktreeNaming(OTHER, 1).worktree_subpath("item-2")
    theirs.mkdir(parents=True)

    removed = await manager.reclaim_orphans()

    assert removed == (orphan,)
    assert not orphan.exists()
    assert kept.exists()
    assert theirs.exists()


async def test_reclaim_orphans_is_empty_when_nothing_is_orphaned(repo: Path) -> None:
    manager = _manager(repo)
    await manager.create("item-1")

    assert await manager.reclaim_orphans() == ()


async def test_reclaim_orphans_on_a_project_that_never_built_returns_empty(repo: Path) -> None:
    assert await _manager(repo).reclaim_orphans() == ()


async def test_sigkill_mid_create_leaves_no_orphan_and_the_next_create_succeeds(repo: Path) -> None:
    """The literal 6.2 exit condition: SIGKILL mid-create leaves no orphan
    worktree. We can't SIGKILL our own coroutine, so we simulate the
    observable effect directly -- `git worktree add` starts, is killed after
    it has written its administrative state but before it finishes the
    checkout -- by killing the real `git worktree add` subprocess ourselves,
    then proving the *next* create() for the same item heals it. The
    ownership record is written before `git worktree add`, as create() does."""
    branch = NAMING.branch("item-1")
    target = repo / NAMING.worktree_subpath("item-1")
    target.parent.mkdir(parents=True)
    await GitBranchOwnership(repo, executor=CleanGitEnvSubprocessExecutor()).record(
        branch, project_id=PROJECT, base=await _sha(repo, "HEAD")
    )

    process = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo),
        "worktree",
        "add",
        "-b",
        branch,
        str(target),
        "HEAD",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=_clean_env(),
    )
    process.kill()
    await process.wait()

    path = await _manager(repo).create("item-1")

    assert path == target
    assert path.exists()
    assert (path / "README.md").exists()
    listed = await _run("git", "-C", str(repo), "worktree", "list", "--porcelain")
    assert str(target) in listed.stdout
    # exactly one registration for this path -- no duplicate/orphan entry
    assert listed.stdout.count(f"worktree {target}") == 1


async def test_git_failure_raises_worktree_error_with_argv_and_stderr(
    tmp_path: Path,
) -> None:
    # A directory that is not a git repository: every git call fails, and
    # the error must carry the argv and stderr for the operator. (A missing
    # base_ref is no longer an error -- create() falls back to HEAD.)
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()

    with pytest.raises(WorktreeError) as excinfo:
        await _manager(not_a_repo).create("item-1")

    assert excinfo.value.argv
    assert excinfo.value.stderr


async def test_a_failing_lifecycle_command_raises_worktree_error(repo: Path) -> None:
    class FailingPruneExecutor:
        async def execute(self, argv: tuple[str, ...]) -> CommandResult:
            if "prune" in argv:
                return CommandResult(128, "", "fatal: cannot prune\n")
            return await CleanGitEnvSubprocessExecutor().execute(argv)

    manager = GitWorktreeManager(repo, naming=NAMING, executor=FailingPruneExecutor())

    with pytest.raises(WorktreeError, match="cannot prune") as excinfo:
        await manager.remove("item-1")
    assert "prune" in excinfo.value.argv


async def test_ensure_creates_a_worktree_that_does_not_exist_yet(repo: Path) -> None:
    path = await _manager(repo).ensure("integration")

    assert path.exists()
    assert (path / "README.md").exists()


async def test_list_worktree_paths_failure_raises_worktree_error(repo: Path) -> None:
    manager = _manager(repo)
    path = await manager.create("item-1")
    assert path.exists()

    class FailingListExecutor:
        async def execute(self, argv: tuple[str, ...]) -> CommandResult:
            if "list" in argv and "--porcelain" in argv:
                return CommandResult(128, "", "fatal: unable to list worktrees\n")
            return await CleanGitEnvSubprocessExecutor().execute(argv)

    manager._executor = FailingListExecutor()
    with pytest.raises(WorktreeError, match="worktree"):
        await manager.ensure("item-1")


async def test_ensure_does_not_wipe_an_already_registered_worktree(repo: Path) -> None:
    manager = _manager(repo)
    first = await manager.create("integration")
    (first / "accumulated-state.txt").write_text("a prior merge's result")

    second = await manager.ensure("integration")

    assert second == first
    assert (second / "accumulated-state.txt").exists()


async def test_ensure_refuses_a_registered_worktree_whose_branch_is_no_longer_proved(
    repo: Path,
) -> None:
    manager = _manager(repo)
    await manager.create("integration")
    await _run(
        "git",
        "-C",
        str(repo),
        "config",
        f"branch.{NAMING.integration_branch}.{PROJECT_KEY}",
        str(OTHER),
    )

    with pytest.raises(ForeignBranchRefused, match=f"records project {OTHER}"):
        await manager.ensure("integration")


async def test_an_unresolvable_base_raises_worktree_error(repo: Path) -> None:
    """HEAD always resolves in a repository with a commit; one that cannot resolve its
    base -- an unborn branch -- must say so rather than cut a branch from nothing."""
    empty = repo / "empty"
    empty.mkdir()
    await _run("git", "-C", str(empty), "init", "-q", "-b", "main")

    with pytest.raises(WorktreeError, match="rev-parse"):
        await _manager(empty).create("item-1")


async def test_lifecycle_reasserts_core_bare_false(repo: Path) -> None:
    """Live finding from the expansion-13 build: worktree removal/prune can
    leave the primary checkout marked core.bare=true, breaking git status,
    checkout, and commit hooks there. Every mutating lifecycle path must
    heal it -- the checkout is never actually bare."""
    manager = _manager(repo)
    await manager.create("item-1")

    await _run("git", "-C", str(repo), "config", "core.bare", "true")
    await manager.remove("item-1")

    result = await _run("git", "-C", str(repo), "config", "core.bare")
    assert result.stdout.strip() == "false"

    await _run("git", "-C", str(repo), "config", "core.bare", "true")
    await manager.create("item-2")

    result = await _run("git", "-C", str(repo), "config", "core.bare")
    assert result.stdout.strip() == "false"
