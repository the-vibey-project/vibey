# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey's own git calls never run what a repository planted, and never carry its DSN.

The attack, as reproduced in review: an engine session works in a LINKED worktree, so
it can write to the repository's shared plumbing -- `$(git rev-parse --git-common-dir)
/hooks/post-checkout`, or `core.hooksPath`, `core.fsmonitor`, `filter.*` and
`merge.*.driver` in the shared config. vibey's next `git worktree add` (post-checkout)
or integration `git merge` (pre-merge-commit, prepare-commit-msg, commit-msg,
post-merge) then ran the planted program -- with the worker's whole environment,
`VIBEY_PG_URL` included, because vibey's git executor copied `os.environ` minus
`GIT_*`.

These tests plant each of those, run vibey's real worktree and integration plumbing
against a real repository, and watch every child through a `git` shim on PATH that
records the NAMES of the variables it was started with. No real git is faked.
"""

import os
import shutil
import stat
from pathlib import Path

import pytest

from vibey.domain.worktree import branch_name
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.git.integration_branch import IntegrationBranch
from vibey.infrastructure.git.repository_config_guard import RepositoryExecutionRefused
from vibey.infrastructure.git.worktree_manager import GitWorktreeManager

# What a worker's environment really carries beside what git needs.
_WORKER_SECRETS = {
    "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
    "VIBEY_TRACKER_TOKEN": "tracker-secret",
    "PGPASSWORD": "secret",
    "PGHOST": "db",
    "GH_TOKEN": "ghp_secret",
    "AWS_SECRET_ACCESS_KEY": "aws-secret",
}

_HOOKS = (
    "post-checkout",
    "pre-merge-commit",
    "prepare-commit-msg",
    "commit-msg",
    "post-merge",
    "pre-commit",
    "reference-transaction",
)


def _executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _recorder(marker: Path) -> str:
    """A program that, if it ever runs, leaves its name and its environment's names."""
    return f'#!/bin/sh\necho "ran: $0" >> "{marker}"\nenv | sed "s/=.*//" >> "{marker}"\ncat\n'


@pytest.fixture
def watched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every git process vibey starts goes through a shim that records its variables'
    names; the worker holds its DSN and credentials the whole time."""
    real_git = shutil.which("git")
    assert real_git is not None
    log = tmp_path / "git-children.log"
    shim = tmp_path / "shim"
    _executable(
        shim / "git",
        f'#!/bin/sh\nenv | sed "s/=.*//" >> "{log}"\necho "--" >> "{log}"\n'
        f'exec "{real_git}" "$@"\n',
    )
    monkeypatch.setenv("PATH", f"{shim}{os.pathsep}{os.environ['PATH']}")
    for name, value in _WORKER_SECRETS.items():
        monkeypatch.setenv(name, value)
    return log


async def _git(*argv: str) -> str:
    result = await CleanGitEnvSubprocessExecutor().execute(("git", *argv))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    await _git("-C", str(root), "init", "-q", "-b", "main")
    await _git("-C", str(root), "config", "user.email", "test@example.com")
    await _git("-C", str(root), "config", "user.name", "Test")
    (root / "README.md").write_text("hello\n")
    await _git("-C", str(root), "add", "README.md")
    await _git("-C", str(root), "commit", "-q", "-m", "initial")
    return root


async def _item(repo: Path, item_id: str, filename: str) -> Path:
    """An engine's linked worktree with one commit on its branch."""
    path = await GitWorktreeManager(repo, cycle=1).create(item_id)
    (path / filename).write_text(f"from {item_id}\n")
    await _git("-C", str(path), "add", filename)
    await _git("-C", str(path), "commit", "-q", "-m", f"add {filename}")
    return path


def _children(log: Path) -> list[set[str]]:
    blocks = log.read_text().split("--\n") if log.exists() else []
    return [set(block.split()) for block in blocks if block.strip()]


def _assert_no_secret_reached_a_child(log: Path) -> None:
    children = _children(log)
    assert children, "the shim saw no git process -- the test watched nothing"
    for names in children:
        leaked = sorted(n for n in names if n.startswith(("VIBEY_", "PG")) or n in _WORKER_SECRETS)
        assert leaked == [], f"a git child was started with {leaked}"


async def _plant_in_common_dir(engine_worktree: Path, marker: Path) -> None:
    # From inside the engine's own linked worktree -- all it needs.
    common = Path(await _git("-C", str(engine_worktree), "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = engine_worktree / common
    for hook in _HOOKS:
        _executable(common / "hooks" / hook, _recorder(marker))


async def _plant_hooks_path(engine_worktree: Path, marker: Path) -> None:
    hooks = engine_worktree.parent / "planted-hooks"
    for hook in _HOOKS:
        _executable(hooks / hook, _recorder(marker))
    await _git("-C", str(engine_worktree), "config", "core.hooksPath", str(hooks))


@pytest.mark.parametrize("plant", [_plant_in_common_dir, _plant_hooks_path])
async def test_a_planted_hook_never_runs_in_worktree_add_or_the_integration_merge(
    repo: Path, watched: Path, tmp_path: Path, plant: object
) -> None:
    marker = tmp_path / "hook-ran.log"
    engine_worktree = await _item(repo, "item-1", "a.txt")
    await _item(repo, "item-2", "b.txt")
    await plant(engine_worktree, marker)  # type: ignore[operator]
    watched.unlink(missing_ok=True)

    # post-checkout, on the next item's worktree.
    await GitWorktreeManager(repo, cycle=1).create("item-3")
    # item-1 fast-forwards (post-merge); item-2 then needs a real merge commit
    # (pre-merge-commit, prepare-commit-msg, commit-msg, post-merge).
    integration = IntegrationBranch(repo, cycle=1)
    first = await integration.merge_item("item-1")
    second = await integration.merge_item("item-2")

    assert first.ok and second.ok, (first.detail, second.detail)
    assert not marker.exists(), marker.read_text()
    merged = await integration.ensure()
    assert (merged / "a.txt").exists() and (merged / "b.txt").exists()
    _assert_no_secret_reached_a_child(watched)


async def test_the_merge_really_created_a_merge_commit_so_the_commit_hooks_were_in_play(
    repo: Path, watched: Path
) -> None:
    await _item(repo, "item-1", "a.txt")
    await _item(repo, "item-2", "b.txt")
    integration = IntegrationBranch(repo, cycle=1)
    await integration.merge_item("item-1")
    await integration.merge_item("item-2")

    parents = await _git("-C", str(await integration.ensure()), "log", "-1", "--format=%P")
    assert len(parents.split()) == 2


async def test_a_planted_fsmonitor_never_runs(repo: Path, watched: Path, tmp_path: Path) -> None:
    marker = tmp_path / "fsmonitor-ran.log"
    engine_worktree = await _item(repo, "item-1", "a.txt")
    monitor = tmp_path / "fsmonitor"
    _executable(monitor, _recorder(marker))
    await _git("-C", str(engine_worktree), "config", "core.fsmonitor", str(monitor))
    watched.unlink(missing_ok=True)

    await GitWorktreeManager(repo, cycle=1).create("item-2")
    outcome = await IntegrationBranch(repo, cycle=1).merge_item("item-1")

    assert outcome.ok, outcome.detail
    assert not marker.exists(), marker.read_text()
    _assert_no_secret_reached_a_child(watched)


async def test_a_filter_driver_in_the_shared_config_is_refused_before_checkout(
    repo: Path, watched: Path, tmp_path: Path
) -> None:
    marker = tmp_path / "filter-ran.log"
    engine_worktree = await _item(repo, "item-1", "a.txt")
    (engine_worktree / ".gitattributes").write_text("* filter=planted\n")
    await _git("-C", str(engine_worktree), "add", ".gitattributes")
    await _git("-C", str(engine_worktree), "commit", "-q", "-m", "attributes")
    smudge = tmp_path / "smudge"
    _executable(smudge, _recorder(marker))
    await _git("-C", str(engine_worktree), "config", "filter.planted.smudge", str(smudge))

    with pytest.raises(RepositoryExecutionRefused, match=r"filter\.planted\.smudge"):
        # Checking the item's branch out again would run the smudge filter.
        await GitWorktreeManager(repo, cycle=1).create("item-1")
    with pytest.raises(RepositoryExecutionRefused, match=r"filter\.planted\.smudge"):
        await IntegrationBranch(repo, cycle=1).merge_item("item-1")

    assert not marker.exists(), marker.read_text()
    _assert_no_secret_reached_a_child(watched)


async def test_a_merge_driver_in_the_shared_config_is_refused_before_the_merge(
    repo: Path, watched: Path, tmp_path: Path
) -> None:
    marker = tmp_path / "driver-ran.log"
    integration = IntegrationBranch(repo, cycle=1)
    await integration.ensure()
    engine_worktree = await _item(repo, "item-1", "a.txt")
    (engine_worktree / ".gitattributes").write_text("* merge=planted\n")
    await _git("-C", str(engine_worktree), "add", ".gitattributes")
    await _git("-C", str(engine_worktree), "commit", "-q", "-m", "attributes")
    driver = tmp_path / "driver"
    _executable(driver, _recorder(marker))
    await _git("-C", str(engine_worktree), "config", "merge.planted.driver", f"{driver} %O %A %B")

    with pytest.raises(RepositoryExecutionRefused, match=r"merge\.planted\.driver"):
        await integration.merge_item("item-1")

    assert not marker.exists(), marker.read_text()
    branch = await _git("-C", str(await integration.ensure()), "log", "-1", "--format=%s")
    assert branch == "initial"  # nothing was merged
    _assert_no_secret_reached_a_child(watched)


async def test_a_filter_the_operator_declares_in_their_own_global_config_is_not_refused(
    repo: Path, watched: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Global config is the operator's, not the repository's: `git lfs install` puts its
    filter there, and refusing it would refuse every LFS user."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(
        '[filter "lfs"]\n\tclean = cat\n\tsmudge = cat\n\tprocess = \n\trequired = false\n'
    )
    monkeypatch.setenv("HOME", str(home))

    await _item(repo, "item-1", "a.txt")
    outcome = await IntegrationBranch(repo, cycle=1).merge_item("item-1")

    assert outcome.ok, outcome.detail
    _assert_no_secret_reached_a_child(watched)


async def test_the_item_branch_names_are_the_ones_the_domain_mints(repo: Path) -> None:
    await _item(repo, "item-1", "a.txt")
    assert await _git("-C", str(repo), "rev-parse", "--verify", branch_name(1, "item-1"))
