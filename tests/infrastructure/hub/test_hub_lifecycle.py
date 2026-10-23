# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starting, pausing, resuming and unwinding a project for a device (ADR-0091).

The adapter runs the audited `vibey` commands; these tests fake the process and the folder so
each says what was run, in what order, with which arguments, and how each failure reads."""

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

import pytest

from vibey.application.hub.interfaces.lifecycle_interface import ProjectLifecycleInterface
from vibey.domain.errors import (
    LifecycleConflict,
    LifecycleFailed,
    LifecycleInvalid,
    LifecycleUnavailable,
)
from vibey.infrastructure.hub.interfaces.lifecycle_interface import (
    ProjectFoldersInterface,
    VibeyCommandRunnerInterface,
)
from vibey.infrastructure.hub.lifecycle import (
    COMMAND_SECONDS,
    SHOWN_CHARS,
    CliProjectLifecycle,
    CommandResult,
    GitProjectFolders,
    SubprocessVibeyRunner,
    refusal,
)

PID = UUID("11111111-1111-4111-8111-111111111111")
CREATED = json.dumps({"project_id": str(PID), "name": "greeter", "outcome": "design job j1"})


class Runner:
    """Records every command line and answers each by its first word."""

    def __init__(self, **answers: CommandResult) -> None:
        self.answers = answers
        self.calls: list[list[str]] = []

    def run(self, args: Sequence[str]) -> CommandResult:
        self.calls.append(list(args))
        return self.answers.get(args[0], CommandResult(0, "", ""))


class Folders:
    def __init__(self, raises: Exception | None = None) -> None:
        self.raises = raises
        self.made: list[Path] = []

    def make(self, path: Path) -> None:
        if self.raises is not None:
            raise self.raises
        self.made.append(path)


def _lifecycle(runner: Runner, folders: Folders | None = None) -> CliProjectLifecycle:
    return CliProjectLifecycle(
        projects_root=Path("/srv/projects"), runner=runner, folders=folders or Folders()
    )


def test_the_adapters_meet_their_declared_seams() -> None:
    assert isinstance(_lifecycle(Runner()), ProjectLifecycleInterface)
    assert isinstance(Runner(), VibeyCommandRunnerInterface)
    assert isinstance(Folders(), ProjectFoldersInterface)
    assert isinstance(SubprocessVibeyRunner(executable="vibey"), VibeyCommandRunnerInterface)
    assert isinstance(GitProjectFolders(), ProjectFoldersInterface)


async def test_a_project_is_made_in_its_own_folder_then_created_and_given_a_worker() -> None:
    runner, folders = Runner(new=CommandResult(0, CREATED, "")), Folders()
    document = await _lifecycle(runner, folders).create("greeter", "a greeting page")

    assert document["project_id"] == str(PID)
    assert folders.made == [Path("/srv/projects/greeter")]
    assert runner.calls == [
        [
            "new",
            "greeter",
            "--repo",
            "/srv/projects/greeter",
            "--json",
            "--intake",
            "a greeting page",
        ],
        ["retry", str(PID), "--keep-workers", "--start-worker"],
    ]


async def test_with_no_intake_none_is_passed() -> None:
    runner = Runner(new=CommandResult(0, CREATED, ""))
    await _lifecycle(runner).create("greeter", "")
    assert "--intake" not in runner.calls[0]


async def test_a_reply_without_a_project_id_starts_no_worker() -> None:
    runner = Runner(new=CommandResult(0, json.dumps({"name": "greeter"}), ""))
    await _lifecycle(runner).create("greeter", "")
    assert [call[0] for call in runner.calls] == ["new"]


async def test_with_no_projects_root_nothing_can_be_started_and_nothing_is_run() -> None:
    runner = Runner()
    undeclared = CliProjectLifecycle(projects_root=None, runner=runner, folders=Folders())
    with pytest.raises(LifecycleUnavailable, match=r"\[hub\] projects_root"):
        await undeclared.create("greeter", "")
    assert runner.calls == []


async def test_a_folder_that_exists_is_a_conflict_and_nothing_is_run() -> None:
    runner = Runner()
    with pytest.raises(LifecycleConflict, match="greeter already exists"):
        await _lifecycle(runner, Folders(FileExistsError())).create("greeter", "")
    assert runner.calls == []


async def test_a_folder_that_cannot_be_made_is_a_failure_in_the_hosts_words() -> None:
    with pytest.raises(LifecycleFailed, match="could not make the folder: disk full"):
        await _lifecycle(Runner(), Folders(OSError("disk full"))).create("greeter", "")


@pytest.mark.parametrize(
    ("stdout", "said"),
    [("project abc", "did not print JSON"), ("[1]", "did not print a JSON object")],
)
async def test_a_creation_reply_that_is_not_a_json_object_is_a_failure(
    stdout: str, said: str
) -> None:
    runner = Runner(new=CommandResult(0, stdout, ""))
    with pytest.raises(LifecycleFailed, match=said):
        await _lifecycle(runner).create("greeter", "")


async def test_a_failed_creation_reads_as_the_commands_own_refusal() -> None:
    runner = Runner(new=CommandResult(3, "", "checkout /x is held by live project p"))
    with pytest.raises(LifecycleConflict):
        await _lifecycle(runner).create("greeter", "")


async def test_start_and_pause_run_exactly_the_scoped_commands() -> None:
    runner = Runner(
        retry=CommandResult(0, "worker started (pid 7)\n", ""),
        recover=CommandResult(0, "stopped\n", ""),
    )
    lifecycle = _lifecycle(runner)
    assert await lifecycle.start_work(PID) == {"message": "worker started (pid 7)"}
    assert await lifecycle.pause_work(PID) == {"message": "stopped"}
    assert runner.calls == [
        ["retry", str(PID), "--keep-workers", "--start-worker"],
        ["recover", "--project", str(PID), "--stop-workers"],
    ]


async def test_a_pause_a_shared_worker_blocks_says_why_in_the_commands_words() -> None:
    said = "left running, because it serves more than this project:\n--include-shared"
    runner = Runner(recover=CommandResult(1, said, ""))
    with pytest.raises(LifecycleConflict, match="--include-shared"):
        await _lifecycle(runner).pause_work(PID)


async def test_an_unwind_is_recorded_under_the_caller_and_may_be_a_dry_run() -> None:
    document = {"project_id": str(PID), "dry_run": True}
    runner = Runner(abandon=CommandResult(0, json.dumps(document), ""))
    lifecycle = _lifecycle(runner)
    assert await lifecycle.abandon(PID, "not needed", by="device:phone", dry_run=True) == document
    await lifecycle.abandon(PID, "not needed", by="device:phone", dry_run=False)
    base = ["abandon", str(PID), "--reason", "not needed", "--by", "device:phone", "--json"]
    assert runner.calls == [[*base, "--dry-run"], base]


@pytest.mark.parametrize(
    ("result", "kind"),
    [
        (CommandResult(75, "", "the Sabbath rests this"), LifecycleUnavailable),
        (CommandResult(3, "held by live project", ""), LifecycleConflict),
        (CommandResult(1, "left running", ""), LifecycleConflict),
        (CommandResult(2, "", "bad option"), LifecycleInvalid),
        (CommandResult(127, "", "vibey could not be run"), LifecycleFailed),
        (CommandResult(9, "", ""), LifecycleFailed),
    ],
)
def test_each_exit_code_reads_as_its_kind_of_refusal(
    result: CommandResult, kind: type[Exception]
) -> None:
    assert type(refusal("x", result)) is kind


def test_a_refusal_is_in_the_commands_words_or_names_the_command_and_is_bounded() -> None:
    assert str(refusal("pause", CommandResult(9, "", ""))) == "vibey pause failed"
    assert len(str(refusal("x", CommandResult(2, "", "w" * 5000)))) == SHOWN_CHARS


def test_the_runner_runs_the_vibey_it_was_given_and_reports_what_it_printed() -> None:
    seen: dict[str, object] = {}

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.update(argv=argv, **kwargs)
        return subprocess.CompletedProcess(argv, 4, stdout="out", stderr="err")

    result = SubprocessVibeyRunner(executable="/x/vibey", run=run).run(["status", "--json"])

    assert result == CommandResult(4, "out", "err")
    assert seen["argv"] == ["/x/vibey", "status", "--json"]
    assert seen["timeout"] == COMMAND_SECONDS and seen["check"] is False


def test_a_command_that_takes_too_long_or_cannot_start_is_a_result_not_a_crash() -> None:
    def too_slow(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(argv, 1)

    def missing(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("no vibey")

    slow = SubprocessVibeyRunner(executable="v", run=too_slow).run(["new"])
    gone = SubprocessVibeyRunner(executable="v", run=missing).run(["new"])
    assert slow.code == 124 and "took longer" in slow.stderr
    assert gone.code == 127 and "no vibey" in gone.stderr


def test_the_default_executable_is_resolved_when_none_is_given() -> None:
    runner = SubprocessVibeyRunner(
        run=lambda argv, **_: subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
    )
    assert runner.run(["--version"]).code == 0


def test_a_project_folder_is_a_repository_with_one_commit(tmp_path: Path) -> None:
    ran: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        ran.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    target = tmp_path / "greeter"
    GitProjectFolders(run=run).make(target)

    assert target.is_dir()
    assert ran[0][:4] == ["git", "-C", str(target), "init"]
    assert "--allow-empty" in ran[1] and "chore: start greeter" in ran[1]


def test_an_existing_folder_is_never_adopted(tmp_path: Path) -> None:
    (tmp_path / "taken").mkdir()
    with pytest.raises(FileExistsError):
        GitProjectFolders(run=lambda argv, **_: subprocess.CompletedProcess(argv, 0)).make(
            tmp_path / "taken"
        )


def test_a_git_failure_is_reported_in_gits_words(tmp_path: Path) -> None:
    def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 128, stdout="", stderr="not a git thing")

    with pytest.raises(OSError, match="git init failed: not a git thing"):
        GitProjectFolders(run=run).make(tmp_path / "x")
