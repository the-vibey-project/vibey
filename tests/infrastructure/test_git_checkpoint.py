# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ULTRA checkpoint commits a pass's work on the item's branch, and nothing when
there is nothing to commit (ADR-0063)."""

import subprocess
from pathlib import Path

import pytest

from vibey.infrastructure.git.checkpoint import GitCheckpoint, GitCheckpointError
from vibey.infrastructure.git.interfaces import GitCheckpointInterface


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "i"],
        check=True,
    )
    return repo


async def test_a_pass_with_changes_is_committed_and_one_without_is_not(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    checkpoint = GitCheckpoint()
    assert isinstance(checkpoint, GitCheckpointInterface)

    assert await checkpoint.commit(repo, "chore(ultra): pass 1 of item") is None

    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    sha = await checkpoint.commit(repo, "chore(ultra): pass 1 of item")
    head = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%H %an %s"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split(" ", 2)
    assert sha == head[0]
    assert head[1] == "vibey" and head[2].strip() == "chore(ultra): pass 1 of item"


async def test_a_failing_git_step_names_itself(tmp_path: Path) -> None:
    with pytest.raises(GitCheckpointError, match="add --all"):
        await GitCheckpoint().commit(tmp_path / "not-a-repo", "m")
