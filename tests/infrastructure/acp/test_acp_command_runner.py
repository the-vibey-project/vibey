# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpCommandRunner` and `AcpPostgresInstaller`: the PostgreSQL install `vibey acp` may run.

The commands are `PostgresLocalService`'s fixed argv. Run from inside an editor's agent, they
never see the protocol's stdin, never wait at a password prompt (`sudo -n`), never run without a
bound, and never print: their output is captured. Module-level test functions rather than a
class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from vibey.application.acp.interfaces.postgres_installer_interface import (
    PostgresInstallerInterface,
)
from vibey.infrastructure.acp.acp_command_runner import AcpCommandRunner
from vibey.infrastructure.acp.acp_postgres_installer import AcpPostgresInstaller
from vibey.infrastructure.acp.interfaces.acp_command_runner_interface import (
    AcpCommandRunnerInterface,
)
from vibey.infrastructure.postgres import PostgresCommandResult, PostgresLocalService


@dataclass
class Seen:
    argv: tuple[str, ...] = ()
    stdin: Any = None
    kwargs: dict[str, Any] | None = None


def _recording(seen: Seen, *, returncode: int = 0, stderr: str = "") -> Callable[..., Any]:
    def run(argv: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.argv = tuple(argv)
        seen.stdin = kwargs.get("stdin")
        seen.kwargs = kwargs
        return subprocess.CompletedProcess(argv, returncode, stdout="out", stderr=stderr)

    return run


def test_sudo_becomes_non_interactive_and_stdin_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = Seen()
    monkeypatch.setattr(subprocess, "run", _recording(seen))

    result = AcpCommandRunner(timeout_seconds=30)(("sudo", "apt-get", "update"))

    assert seen.argv == ("sudo", "-n", "apt-get", "update") and seen.stdin is subprocess.DEVNULL
    assert seen.kwargs is not None
    assert seen.kwargs["capture_output"] is True and seen.kwargs["text"] is True
    assert seen.kwargs["timeout"] == 30 and seen.kwargs.get("shell", False) is False
    assert result == PostgresCommandResult(returncode=0, stdout="out", stderr="")


@pytest.mark.parametrize(
    ("argv", "sent"),
    [
        (("sudo", "-n", "dnf", "install", "-y", "x"), ("sudo", "-n", "dnf", "install", "-y", "x")),
        (("brew", "install", "postgresql@18"), ("brew", "install", "postgresql@18")),
        (("apt-get", "-n", "x"), ("apt-get", "-n", "x")),
        (("sudo", "systemctl", "-n", "x"), ("sudo", "-n", "systemctl", "-n", "x")),
    ],
)
def test_only_a_sudo_without_its_own_n_is_changed(
    monkeypatch: pytest.MonkeyPatch, argv: tuple[str, ...], sent: tuple[str, ...]
) -> None:
    seen = Seen()
    monkeypatch.setattr(subprocess, "run", _recording(seen))

    AcpCommandRunner(timeout_seconds=5)(argv)

    assert seen.argv == sent and seen.stdin is subprocess.DEVNULL


def test_a_command_that_overruns_or_cannot_start_is_a_failure_not_a_hang(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def overrun(argv: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    def missing(argv: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError("brew")

    runner = AcpCommandRunner(timeout_seconds=7)
    monkeypatch.setattr(subprocess, "run", overrun)
    timed_out = runner(("brew", "install", "postgresql@18"))
    monkeypatch.setattr(subprocess, "run", missing)
    absent = runner(("brew", "--prefix"))

    assert timed_out.returncode != 0 and "7" in timed_out.stderr
    assert absent.returncode != 0 and "brew" in absent.stderr


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


def _linux(runner: _Runner) -> AcpPostgresInstaller:
    tools = {"apt-get": "/usr/bin/apt-get", "sudo": "/usr/bin/sudo", "systemctl": "/bin/systemctl"}
    return AcpPostgresInstaller(
        runner,
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
