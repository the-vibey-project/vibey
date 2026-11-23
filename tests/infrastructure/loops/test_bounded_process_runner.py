# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Running one command with bounded output and a whole-group kill (SP-LOOPS Task 7 review 5).

The timeout path is driven by a fake process (no timers, no sleeps); the real path runs `sh` and
`printf`, which finish at once, never git."""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

import pytest

from vibey.infrastructure.loops.bounded_process_runner import BoundedProcessRunner
from vibey.infrastructure.loops.interfaces.bounded_process_runner_interface import (
    BoundedProcessRunnerInterface,
)

ENV = {"PATH": os.defpath}


def test_the_runner_satisfies_its_interface() -> None:
    assert isinstance(BoundedProcessRunner(), BoundedProcessRunnerInterface)


def test_a_command_runs_in_its_own_group_with_no_stdin(tmp_path: Path) -> None:
    result = BoundedProcessRunner().run(
        ["sh", "-c", 'printf "%s %s" "$(pwd -P)" "$(cat)"; printf err >&2; exit 3'],
        ENV,
        tmp_path,
        10.0,
    )
    assert result.returncode == 3
    assert result.stdout == f"{os.path.realpath(tmp_path)} "
    assert result.stderr == "err"


def test_output_is_read_back_capped_stdout_from_the_start_stderr_from_the_end(
    tmp_path: Path,
) -> None:
    script = 'printf "%0200d" 0; printf "start"; i=0; while [ $i -lt 50 ]; do printf "%050d" $i >&2; i=$((i+1)); done; printf "the end" >&2'
    result = BoundedProcessRunner(output_bytes=20).run(["sh", "-c", script], ENV, tmp_path, 10.0)
    assert result.stdout == "0" * 20
    assert len(result.stderr) == 20 and result.stderr.endswith("the end")


class FakeProcess:
    pid = 4242

    def __init__(self, times_out: bool, interrupt: bool = False) -> None:
        self.waits: list[float | None] = []
        self._times_out = times_out
        self._interrupt = interrupt

    def wait(self, timeout: float | None = None) -> int:
        self.waits.append(timeout)
        if self._interrupt and len(self.waits) == 1:
            raise KeyboardInterrupt
        if self._times_out and len(self.waits) == 1:
            raise subprocess.TimeoutExpired(["git"], timeout or 0.0)
        return 0


def test_a_timeout_kills_the_whole_group_and_reaps_it(tmp_path: Path) -> None:
    process = FakeProcess(times_out=True)
    killed: list[tuple[int, int]] = []
    seen: dict[str, object] = {}

    def popen(argv: list[str], **options: object) -> FakeProcess:
        seen.update(options)
        return process

    runner = BoundedProcessRunner(popen=popen, killpg=lambda g, s: killed.append((g, s)))
    with pytest.raises(subprocess.TimeoutExpired):
        runner.run(["git", "fetch"], ENV, tmp_path, 1.5)
    assert killed == [(4242, signal.SIGKILL)]
    assert process.waits == [1.5, None]
    assert seen["start_new_session"] is True and seen["stdin"] == subprocess.DEVNULL


def test_a_ctrl_c_while_git_runs_kills_its_group_and_is_raised_again(tmp_path: Path) -> None:
    """git runs in a session of its own, so the terminal's SIGINT never reaches it: the runner
    kills the group itself on any exception from the wait (review 2, N1)."""
    process = FakeProcess(times_out=False, interrupt=True)
    killed: list[tuple[int, int]] = []
    runner = BoundedProcessRunner(
        popen=lambda argv, **o: process, killpg=lambda g, s: killed.append((g, s))
    )
    with pytest.raises(KeyboardInterrupt):
        runner.run(["git", "fetch"], ENV, tmp_path, 300.0)
    assert killed == [(4242, signal.SIGKILL)]
    assert process.waits == [300.0, None]


@pytest.mark.parametrize(
    "error",
    [ProcessLookupError(3, "No such process"), PermissionError(1, "Operation not permitted")],
)
def test_a_finished_command_has_its_group_swept_and_a_gone_group_is_fine(
    tmp_path: Path, error: OSError
) -> None:
    """ESRCH, or EPERM as macOS answers for a group of unreaped zombies: nothing to kill."""

    def gone(group: int, sig: int) -> None:
        raise error

    runner = BoundedProcessRunner(popen=lambda argv, **o: FakeProcess(False), killpg=gone)
    assert runner.run(["git", "init"], ENV, tmp_path, 5.0).returncode == 0


def test_a_missing_command_is_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        BoundedProcessRunner().run(["/nonexistent/vibey-no-such-git"], ENV, tmp_path, 5.0)
