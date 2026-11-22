# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpCommandRunner` and `AcpPostgresInstaller`: the PostgreSQL install `vibey acp` may run.

The commands are `PostgresLocalService`'s fixed argv. Run from inside an editor's agent, they
never see the protocol's stdin, never wait at a password prompt (`sudo -n`), never run without a
bound, and never print: their output is captured. Module-level test functions rather than a
class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from vibey.application.acp.interfaces.postgres_installer_interface import (
    PostgresInstallerInterface,
)
from vibey.infrastructure.acp.acp_command_runner import (
    STILL_RUNNING,
    TIMED_OUT,
    AcpCommandRunner,
)
from vibey.infrastructure.acp.acp_postgres_installer import AcpPostgresInstaller
from vibey.infrastructure.acp.interfaces.acp_command_runner_interface import (
    AcpCommandRunnerInterface,
)
from vibey.infrastructure.postgres import PostgresCommandResult, PostgresLocalService


class FakeProcess:
    """A `Popen` that answers `communicate` from a script; records how it was started."""

    def __init__(self, argv: Any, **kwargs: Any) -> None:
        self.argv = tuple(argv)
        self.kwargs = kwargs
        self.pid = 4242
        self.returncode = 0
        self.timeouts: list[float | None] = []
        self.hangs = 0
        """How many `communicate` calls with a timeout overrun before one answers."""

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        self.timeouts.append(timeout)
        if timeout is not None and self.hangs:
            self.hangs -= 1
            raise subprocess.TimeoutExpired(self.argv, timeout)
        return "out", "err"


class Started:
    def __init__(self, *, hangs: int = 0, error: OSError | None = None) -> None:
        self.processes: list[FakeProcess] = []
        self.hangs = hangs
        self.error = error

    def __call__(self, argv: Any, **kwargs: Any) -> FakeProcess:
        if self.error is not None:
            raise self.error
        process = FakeProcess(argv, **kwargs)
        process.hangs = self.hangs
        self.processes.append(process)
        return process


TOOLS = {"sudo": "/usr/bin/sudo", "apt-get": "/usr/bin/apt-get", "brew": "/opt/homebrew/bin/brew"}


def _which(name: str, path: str | None = None) -> str | None:
    return TOOLS.get(name)


def _runner(started: Started, **kwargs: Any) -> AcpCommandRunner:
    environ = {"PATH": "/evil/bin:/usr/bin", "HOME": "/home/me", "VIBEY_PG_URL": "postgresql://x"}
    return AcpCommandRunner(
        timeout_seconds=kwargs.pop("timeout_seconds", 30),
        environ=environ,
        which=_which,
        popen=started,
        **kwargs,
    )


def test_sudo_becomes_non_interactive_and_stdin_is_closed() -> None:
    started = Started()

    result = _runner(started)(("sudo", "apt-get", "update"))

    seen = started.processes[0]
    assert seen.argv == ("/usr/bin/sudo", "-n", "/usr/bin/apt-get", "update")
    assert seen.kwargs["stdin"] is subprocess.DEVNULL
    assert seen.kwargs["stdout"] is subprocess.PIPE and seen.kwargs["stderr"] is subprocess.PIPE
    assert seen.kwargs["text"] is True and seen.kwargs.get("shell", False) is False
    assert seen.kwargs["start_new_session"] is True  # a process group of its own
    assert seen.timeouts == [30]
    assert result == PostgresCommandResult(returncode=0, stdout="out", stderr="err")


def test_the_commands_see_a_minimal_environment() -> None:
    started = Started()

    _runner(started)(("brew", "install", "postgresql@18"))

    env = started.processes[0].kwargs["env"]
    assert env["HOME"] == "/home/me"
    assert "VIBEY_PG_URL" not in env
    assert "/evil/bin" not in env["PATH"]
    assert env["PATH"].split(":")[:2] == ["/opt/homebrew/bin", "/usr/local/bin"]


@pytest.mark.parametrize(
    ("argv", "sent"),
    [
        (
            ("sudo", "-n", "dnf", "install", "-y", "x"),
            ("/usr/bin/sudo", "-n", "dnf", "install", "-y", "x"),
        ),
        (
            ("brew", "install", "postgresql@18"),
            ("/opt/homebrew/bin/brew", "install", "postgresql@18"),
        ),
        (("/usr/bin/apt-get", "-n", "x"), ("/usr/bin/apt-get", "-n", "x")),
        (("sudo", "systemctl", "-n", "x"), ("/usr/bin/sudo", "-n", "systemctl", "-n", "x")),
        (("sudo",), ("/usr/bin/sudo", "-n")),
    ],
)
def test_only_a_sudo_without_its_own_n_is_changed(
    argv: tuple[str, ...], sent: tuple[str, ...]
) -> None:
    started = Started()

    _runner(started)(argv)

    assert started.processes[0].argv == sent


def test_a_command_that_cannot_start_is_a_failure_not_an_exception() -> None:
    absent = _runner(Started(error=FileNotFoundError("brew")))(("brew", "--prefix"))

    assert absent.returncode == 1 and "brew" in absent.stderr


def test_an_overrun_stops_the_whole_group_with_sigterm_first() -> None:
    signals: list[tuple[int, int]] = []
    started = Started(hangs=1)

    result = _runner(
        started, timeout_seconds=7, kill_group=lambda pid, sig: signals.append((pid, sig))
    )(("brew", "install", "postgresql@18"))

    assert signals == [(4242, signal.SIGTERM)]
    assert result.returncode == TIMED_OUT and "within 7 s and was stopped" in result.stderr


def test_a_group_that_ignores_sigterm_gets_sigkill() -> None:
    signals: list[int] = []
    started = Started(hangs=2)

    result = _runner(started, kill_group=lambda pid, sig: signals.append(sig))(("brew",))

    assert signals == [signal.SIGTERM, signal.SIGKILL]
    assert result.returncode == TIMED_OUT


def test_a_group_already_gone_is_reaped_not_signalled_again() -> None:
    def gone(pid: int, sig: int) -> None:
        raise ProcessLookupError

    result = _runner(Started(hangs=1), kill_group=gone)(("brew",))

    assert result.returncode == TIMED_OUT


@pytest.mark.parametrize("hangs", [3, 1], ids=["never-ends", "may-not-be-signalled"])
def test_a_group_that_cannot_be_confirmed_stopped_is_still_running_not_failed(
    hangs: int,
) -> None:
    signals: list[int] = []
    started = Started(hangs=hangs)

    def refuse_when_asked(pid: int, sig: int) -> None:
        signals.append(sig)
        if hangs == 1:
            raise PermissionError("sudo runs as root")

    result = _runner(started, kill_group=refuse_when_asked)(("sudo", "apt-get", "update"))

    assert result.returncode == STILL_RUNNING
    assert AcpCommandRunner.still_running(result)
    assert "may still be running" in result.stderr
    process = started.processes[0]
    for _ in range(200):  # the drain thread reads it to the end, with no timeout
        if process.timeouts[-1] is None:
            break
        time.sleep(0.01)
    assert process.timeouts[-1] is None


# -- real processes ------------------------------------------------------------------------

_TREE = """
import os, subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30); open(sys.argv[1], 'w')", sys.argv[1]])
open(sys.argv[2], "w").write(str(child.pid))
time.sleep(30)
"""


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_a_real_overrun_stops_the_grandchild_too(tmp_path: Path) -> None:
    marker, pid_file = tmp_path / "ran", tmp_path / "pid"
    tree = (sys.executable, "-c", _TREE, str(marker), str(pid_file))

    result = AcpCommandRunner(timeout_seconds=1.5, stop_grace_seconds=5)(tree)

    assert result.returncode == TIMED_OUT
    grandchild = int(pid_file.read_text())
    for _ in range(200):
        if not _alive(grandchild):
            break
        time.sleep(0.02)
    assert not _alive(grandchild)
    assert not marker.exists()


def test_a_real_group_that_may_not_be_signalled_is_left_running_without_a_wait() -> None:
    processes: list[subprocess.Popen[str]] = []

    def popen(argv: Any, **kwargs: Any) -> subprocess.Popen[str]:
        processes.append(subprocess.Popen(argv, **kwargs))  # noqa: S603
        return processes[-1]

    def refuse(pid: int, sig: int) -> None:
        raise PermissionError("sudo runs as root")

    sleeper = (sys.executable, "-c", "import time; time.sleep(30)")
    started_at = time.monotonic()
    try:
        result = AcpCommandRunner(timeout_seconds=0.5, popen=popen, kill_group=refuse)(sleeper)
        assert time.monotonic() - started_at < 10
        assert result.returncode == STILL_RUNNING
        assert processes[0].poll() is None  # not killed, not waited for, its pipes still open
    finally:
        os.killpg(processes[0].pid, signal.SIGKILL)


def test_a_real_child_reads_end_of_file_not_the_protocol_stream() -> None:
    reads_stdin = (sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))")

    result = AcpCommandRunner(timeout_seconds=30)(reads_stdin)

    assert result.returncode == 0 and result.stdout.strip() == "''"


@pytest.mark.parametrize(
    ("argv", "result", "refused"),
    [
        (
            ("sudo", "-n", "apt-get", "update"),
            PostgresCommandResult(1, "", "sudo: a password is required\n"),
            True,
        ),
        (
            ("sudo", "-n", "dnf"),
            PostgresCommandResult(1, "", "sudo: a terminal is required to read the password"),
            True,
        ),
        (
            ("sudo", "-n", "apt-get", "update"),
            PostgresCommandResult(100, "", "E: could not get lock"),
            False,
        ),
        (
            ("sudo", "-n", "apt-get", "update"),
            PostgresCommandResult(0, "", "a password is required"),
            False,
        ),
        (("apt-get", "update"), PostgresCommandResult(1, "", "a password is required"), False),
        (
            ("/usr/bin/sudo", "-n", "dnf"),
            PostgresCommandResult(1, "", "sudo: a password is required"),
            True,
        ),
        ((), PostgresCommandResult(1, "", "a password is required"), False),
    ],
)
def test_a_sudo_refused_for_want_of_a_password_is_recognised(
    argv: tuple[str, ...], result: PostgresCommandResult, refused: bool
) -> None:
    assert AcpCommandRunner.password_refused(argv, result) is refused


# -- the installer the bootstrap holds ------------------------------------------------------


class _Runner:
    """Answers each argv from a script; records what ran."""

    def __init__(self, answers: dict[tuple[str, ...], PostgresCommandResult]) -> None:
        self.answers = answers
        self.ran: list[tuple[str, ...]] = []

    def __call__(self, argv: tuple[str, ...]) -> PostgresCommandResult:
        self.ran.append(argv)
        return self.answers.get(argv, PostgresCommandResult(1, "", "no"))

    @staticmethod
    def password_refused(argv: tuple[str, ...], result: PostgresCommandResult) -> bool:
        return AcpCommandRunner.password_refused(argv, result)

    @staticmethod
    def still_running(result: PostgresCommandResult) -> bool:
        return AcpCommandRunner.still_running(result)


def _linux(runner: _Runner, probe: _Runner | None = None, **more: str) -> AcpPostgresInstaller:
    tools = {
        "apt-get": "/usr/bin/apt-get",
        "sudo": "/usr/bin/sudo",
        "systemctl": "/bin/systemctl",
        **more,
    }
    return AcpPostgresInstaller(
        runner,
        probe_runner=probe,
        service=lambda run: PostgresLocalService(
            command_runner=run, which=tools.get, platform="linux", effective_uid=lambda: 1000
        ),
    )


def test_the_installer_reports_readiness_and_the_package_manager() -> None:
    installer = _linux(_Runner({}))

    readiness = installer.status()

    assert readiness.ready is False
    assert readiness.package_manager == "apt-get"
    assert "not installed" in readiness.detail


def test_an_install_refused_by_sudo_says_it_needs_a_password() -> None:
    refused = PostgresCommandResult(1, "", "sudo: a password is required")
    runner = _Runner({("sudo", "apt-get", "update"): refused})

    outcome = _linux(runner).install()

    assert outcome.ok is False and outcome.needs_password is True
    assert outcome.detail == "apt-get could not refresh package metadata"
    assert runner.ran[-1] == ("sudo", "apt-get", "update")


def test_an_install_that_fails_otherwise_does_not_blame_sudo() -> None:
    outcome = _linux(_Runner({})).install()

    assert outcome.ok is False and outcome.needs_password is False


def test_a_successful_install_is_ok() -> None:
    ok = PostgresCommandResult(0, "", "")
    runner = _Runner(
        {
            ("sudo", "apt-get", "update"): ok,
            ("sudo", "apt-get", "install", "-y", "postgresql"): ok,
            ("sudo", "systemctl", "enable", "--now", "postgresql"): ok,
        }
    )

    outcome = _linux(runner).install()

    # Verification still finds no client tools (the fake `which` never learns of them), so the
    # install is reported as not ready -- but nothing in it blamed sudo.
    assert outcome.needs_password is False
    assert "apt-get installed/started PostgreSQL" in outcome.detail


def test_the_default_installer_uses_the_acp_runner() -> None:
    installer = AcpPostgresInstaller(AcpCommandRunner(timeout_seconds=5))

    assert isinstance(installer, PostgresInstallerInterface)
    assert isinstance(AcpCommandRunner(timeout_seconds=5), AcpCommandRunnerInterface)


def test_an_install_command_that_may_still_run_is_reported_so() -> None:
    running = PostgresCommandResult(STILL_RUNNING, "", "apt-get may still be running")
    outcome = _linux(_Runner({("sudo", "apt-get", "update"): running})).install()

    assert outcome.ok is False and outcome.still_running is True
    assert outcome.needs_password is False


def test_status_runs_through_the_short_probe_runner_and_install_through_the_long_one() -> None:
    install, probe = _Runner({}), _Runner({})
    installer = _linux(install, probe, pg_config="/usr/bin/pg_config")

    installer.status()
    assert probe.ran == [("/usr/bin/pg_config", "--version")] and install.ran == []
    installer.install()

    assert ("sudo", "apt-get", "update") in install.ran


def test_a_name_is_resolved_once() -> None:
    asked: list[str] = []

    def which(name: str, path: str | None = None) -> str | None:
        asked.append(name)
        return TOOLS.get(name)

    runner = AcpCommandRunner(timeout_seconds=5, which=which, popen=Started())
    runner(("brew", "--prefix"))
    runner(("brew", "services", "start", "postgresql@18"))

    assert asked == ["brew"]
