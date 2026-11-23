# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The operating-system calls the hub commands make (#1186)."""

import os
import signal
import sys
from pathlib import Path

import pytest

from vibey.infrastructure.hub.interfaces.processes_interface import HubProcessesInterface
from vibey.infrastructure.hub.processes import HUB_PROCESSES, HubProcesses


def test_the_processes_meet_their_declared_seam() -> None:
    assert isinstance(HUB_PROCESSES, HubProcessesInterface)


def test_a_process_that_exists_is_alive_and_one_that_does_not_is_not() -> None:
    assert HubProcesses().alive(os.getpid()) is True
    assert HubProcesses().alive(2**22 + 12345) is False


def test_a_process_of_another_account_is_alive_but_not_ours_to_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(pid: int, sig: int) -> None:
        raise PermissionError

    monkeypatch.setattr(os, "kill", refuse)
    assert HubProcesses().alive(1) is True


def test_terminate_sends_sigterm_and_never_anything_stronger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple[int, int]] = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: sent.append((pid, sig)))
    assert HubProcesses().terminate(4242) is True
    assert sent == [(4242, signal.SIGTERM)]


def test_terminate_says_false_for_a_process_that_is_already_gone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def gone(pid: int, sig: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(os, "kill", gone)
    assert HubProcesses().terminate(4242) is False


def test_spawn_runs_the_program_detached_in_its_folder_with_its_output_in_the_log(
    tmp_path: Path,
) -> None:
    """The hub runs in the person's configuration folder, made owner-only (Task 11a M-2)."""
    log = tmp_path / "state" / "hub.log"
    folder = tmp_path / "config" / "vibey"
    pid = HubProcesses().spawn(
        [sys.executable, "-c", "import os; print('hub says hi in', os.getcwd())"], log, cwd=folder
    )
    assert pid > 0
    os.waitpid(pid, 0)  # it has ended, so its output is all there: no polling
    assert f"hub says hi in {os.path.realpath(folder)}" in log.read_text()
    assert (tmp_path / "state").stat().st_mode & 0o077 == 0
    assert folder.stat().st_mode & 0o777 == 0o700
