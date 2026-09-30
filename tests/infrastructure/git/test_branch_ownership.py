# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ownership record that ties a BUILD branch to the project that created it. Real git
for what the record proves; a scripted executor only for the failures real git will not
produce on demand."""

from pathlib import Path
from uuid import UUID

import pytest

from vibey.domain.errors import ForeignBranchRefused
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.git.branch_ownership import PROJECT_KEY, GitBranchOwnership
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.git.errors import WorktreeError
from vibey.infrastructure.git.interfaces import GitBranchOwnershipInterface

PROJECT = UUID("893c4fc1-542e-411e-a10a-3aef784b1540")
BRANCH = "vibey/893c4fc1/1/ws"


async def _run(*argv: str) -> CommandResult:
    return await CleanGitEnvSubprocessExecutor().execute(argv)


@pytest.fixture
async def repo(tmp_path: Path) -> Path:
    await _run("git", "-C", str(tmp_path), "init", "-q", "-b", "main")
    await _run("git", "-C", str(tmp_path), "config", "user.email", "test@example.com")
    await _run("git", "-C", str(tmp_path), "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("hello\n")
    await _run("git", "-C", str(tmp_path), "add", "README.md")
    await _run("git", "-C", str(tmp_path), "commit", "-q", "-m", "initial")
    return tmp_path


def _ownership(repo: Path) -> GitBranchOwnership:
    return GitBranchOwnership(repo, executor=CleanGitEnvSubprocessExecutor())


async def test_a_recorded_branch_is_proved_and_yields_its_base(repo: Path) -> None:
    head = (await _run("git", "-C", str(repo), "rev-parse", "HEAD")).stdout.strip()
    ownership = _ownership(repo)
    await ownership.record(BRANCH, project_id=PROJECT, base=head)
    await _run("git", "-C", str(repo), "branch", BRANCH)

    assert await ownership.verify(BRANCH, PROJECT) == head
    record = await ownership.read(BRANCH)
    assert (record.project_id, record.base) == (str(PROJECT), head)
    assert isinstance(ownership, GitBranchOwnershipInterface)


async def test_an_unrecorded_branch_reads_as_no_owner_and_is_refused(repo: Path) -> None:
    await _run("git", "-C", str(repo), "branch", BRANCH)
    ownership = _ownership(repo)

    record = await ownership.read(BRANCH)

    assert (record.project_id, record.base) == (None, None)
    with pytest.raises(ForeignBranchRefused, match="records no creating project"):
        await ownership.verify(BRANCH, PROJECT)


async def test_a_recorded_base_that_is_not_a_commit_is_refused(repo: Path) -> None:
    ownership = _ownership(repo)
    await ownership.record(BRANCH, project_id=PROJECT, base="0" * 40)
    await _run("git", "-C", str(repo), "branch", BRANCH)

    with pytest.raises(ForeignBranchRefused, match="is not in its history"):
        await ownership.verify(BRANCH, PROJECT)


async def test_the_record_moves_with_the_branch_and_goes_with_it(repo: Path) -> None:
    """Why the record lives in the branch's config section: `git branch -m` carries it and
    `git branch -D` drops it, so a branch recreated under the name proves nothing."""
    head = (await _run("git", "-C", str(repo), "rev-parse", "HEAD")).stdout.strip()
    ownership = _ownership(repo)
    await ownership.record(BRANCH, project_id=PROJECT, base=head)
    await _run("git", "-C", str(repo), "branch", BRANCH)

    await _run("git", "-C", str(repo), "branch", "-m", BRANCH, "moved-aside")
    assert (await ownership.read("moved-aside")).project_id == str(PROJECT)
    assert (await ownership.read(BRANCH)).project_id is None

    await _run("git", "-C", str(repo), "branch", "-D", "moved-aside")
    assert (await ownership.read("moved-aside")).project_id is None


class _Scripted:
    """Answers `git config` with a fixed result; the failures real git will not give."""

    def __init__(self, result: CommandResult) -> None:
        self._result = result

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        return self._result


async def test_an_unreadable_config_raises_rather_than_reading_as_no_owner(tmp_path: Path) -> None:
    ownership = GitBranchOwnership(
        tmp_path, executor=_Scripted(CommandResult(128, "", "fatal: bad config line 3\n"))
    )

    with pytest.raises(WorktreeError, match="bad config"):
        await ownership.read(BRANCH)


async def test_a_record_that_cannot_be_written_raises(tmp_path: Path) -> None:
    ownership = GitBranchOwnership(
        tmp_path, executor=_Scripted(CommandResult(255, "", "error: could not lock config\n"))
    )

    with pytest.raises(WorktreeError, match="could not lock config") as raised:
        await ownership.record(BRANCH, project_id=PROJECT, base="abc")
    assert f"branch.{BRANCH}.{PROJECT_KEY}" in raised.value.argv
