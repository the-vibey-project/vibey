# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import os

import pytest

from vibey.infrastructure.git.clean_env import (
    GIT_ENVIRONMENT_OVERLAY,
    NEUTRALISING_OPTIONS,
    CleanGitEnvSubprocessExecutor,
)
from vibey.infrastructure.git.interfaces import GitExecutorInterface


async def test_cancelled_error_terminates_and_reaps_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        returncode = None
        terminated = False
        waited = False

        async def communicate(self) -> tuple[bytes, bytes]:
            raise asyncio.CancelledError

        def terminate(self) -> None:
            FakeProcess.terminated = True

        async def wait(self) -> None:
            FakeProcess.waited = True

    async def fake_create(*args: object, **kwargs: object) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)

    with pytest.raises(asyncio.CancelledError):
        await CleanGitEnvSubprocessExecutor().execute(("git", "status"))

    assert FakeProcess.terminated
    assert FakeProcess.waited


def test_every_git_call_switches_off_hooks_and_the_fsmonitor_before_the_subcommand() -> None:
    executor = CleanGitEnvSubprocessExecutor()

    argv = executor.neutralised(("git", "-C", "/repo", "merge", "x"))

    assert argv[0] == "git"
    assert argv[1:5] == NEUTRALISING_OPTIONS
    assert (
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.fsmonitor=false",
    ) == NEUTRALISING_OPTIONS
    assert argv[5:] == ("-C", "/repo", "merge", "x")
    assert executor.neutralised(("/usr/bin/git", "status"))[0] == "/usr/bin/git"


@pytest.mark.parametrize("argv", [(), ("az", "account", "show"), ("sh", "-c", "git status")])
def test_the_git_executor_runs_git_only(argv: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="git only"):
        CleanGitEnvSubprocessExecutor().neutralised(argv)


def test_the_git_environment_is_the_system_basics_and_no_machine_wide_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
        "PGPASSWORD": "secret",
        "GH_TOKEN": "ghp_secret",
        "GIT_DIR": "/elsewhere/.git",
        "HOME": "/home/worker",
    }.items():
        monkeypatch.setenv(name, value)
    seen: dict[str, str] = {}

    class Recording:
        def build(self) -> dict[str, str]:
            return seen

    default = CleanGitEnvSubprocessExecutor()._environment.build()
    assert default["GIT_CONFIG_NOSYSTEM"] == "1"
    assert default["HOME"] == "/home/worker"
    assert not {n for n in default if n.startswith(("VIBEY_", "PG", "GIT_DIR"))}
    assert "GH_TOKEN" not in default
    assert GIT_ENVIRONMENT_OVERLAY == {"GIT_CONFIG_NOSYSTEM": "1"}
    assert CleanGitEnvSubprocessExecutor(Recording())._environment.build() is seen


def test_the_executor_declares_its_interface() -> None:
    assert isinstance(CleanGitEnvSubprocessExecutor(), GitExecutorInterface)
