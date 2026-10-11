# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starting a detached `vibey worker`, and where its log goes."""

import subprocess
from pathlib import Path
from uuid import UUID

import pytest

from vibey.infrastructure import worker_launcher
from vibey.infrastructure.worker_launcher import WorkerLauncher, default_executable, default_log

PROJECT = UUID("6b45e169-4653-4a8d-941c-7440249dc8ef")


class FakeProcess:
    pid = 4242


class FakePopen:
    def __init__(self) -> None:
        self.argv: list[str] = []
        self.kwargs: dict[str, object] = {}

    def __call__(self, argv: list[str], **kwargs: object) -> FakeProcess:
        self.argv, self.kwargs = argv, kwargs
        return FakeProcess()


def test_it_starts_the_command_detached_with_its_output_in_the_log(tmp_path: Path) -> None:
    popen = FakePopen()
    log = tmp_path / "deep" / "worker.log"

    pid = WorkerLauncher(executable="/venv/bin/vibey", popen=popen).start(  # type: ignore[arg-type]
        ["worker", "--project", "p"], log=log
    )

    assert pid == 4242
    assert popen.argv == ["/venv/bin/vibey", "worker", "--project", "p"]
    assert popen.kwargs["start_new_session"] is True  # closing the terminal must not stop it
    assert popen.kwargs["stdin"] is subprocess.DEVNULL
    assert popen.kwargs["stderr"] is subprocess.STDOUT
    assert log.exists()  # the directory was made and the file opened for appending


def test_the_log_is_appended_to_not_replaced(tmp_path: Path) -> None:
    log = tmp_path / "worker.log"
    log.write_bytes(b"earlier run\n")
    popen = FakePopen()

    WorkerLauncher(executable="vibey", popen=popen).start(["worker"], log=log)  # type: ignore[arg-type]

    assert popen.kwargs["stdout"].mode == "ab"  # type: ignore[attr-defined]
    assert log.read_bytes() == b"earlier run\n"


def test_the_default_log_is_per_project_under_the_state_dir() -> None:
    assert default_log(PROJECT, environ={"XDG_STATE_HOME": "/state"}) == Path(
        "/state/vibey/worker-6b45e169.log"
    )


def test_the_default_log_falls_back_to_the_home_state_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: Path("/home/me"))
    assert default_log(PROJECT, environ={}) == Path(
        "/home/me/.local/state/vibey/worker-6b45e169.log"
    )


def test_the_default_log_reads_the_real_environment_when_none_is_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", "/xdg")
    assert default_log(PROJECT) == Path("/xdg/vibey/worker-6b45e169.log")


def test_the_executable_is_the_one_on_path_else_the_one_that_was_started(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(worker_launcher.shutil, "which", lambda name: "/venv/bin/vibey")
    assert default_executable() == "/venv/bin/vibey"
    monkeypatch.setattr(worker_launcher.shutil, "which", lambda name: None)
    monkeypatch.setattr(worker_launcher.sys, "argv", ["/started/vibey"])
    assert default_executable() == "/started/vibey"
