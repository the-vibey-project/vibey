# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the host package runner.

The original specification lists a series of behavioural checks.  The tests
mirror those checks as closely as possible, exercising the public API of
``HostPackageRunner`` and the fake executor.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.fakes.host import FakeCommandExecutor
from vibey.domain.local_stack import PackageSource, PackageSpec
from vibey.infrastructure.host_packages import (
    HOMEBREW_REQUIRED,
    CommandResult,
    HostOs,
    HostPackageRunner,
    SubprocessCommandExecutor,
)
from vibey.infrastructure.interfaces.host_packages_interface import (
    CommandExecutorInterface,
    HostPackageRunnerInterface,
)

# Helper: create a runner with custom executor


def make_runner(
    *,
    platform: str,
    os_release: str,
    uid: int,
    user: str,
    executor: FakeCommandExecutor | SubprocessCommandExecutor,
) -> HostPackageRunner:
    return HostPackageRunner(
        executor,
        platform=platform,
        os_release=os_release,
        effective_uid=uid,
        user=user,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_detects_arch_and_its_derivatives_from_os_release(tmp_path: Path):
    release = tmp_path / "os-release"
    release.write_text("ID=endeavouros\nID_LIKE=arch\n")
    runner = HostPackageRunner(
        SubprocessCommandExecutor(),
        platform="linux",
        os_release=release.read_text(),
        effective_uid=1000,
        user="alice",
    )
    assert runner.host() == HostOs.ARCH


def test_detects_macos_and_rejects_other_hosts(tmp_path: Path):
    runner = HostPackageRunner(
        SubprocessCommandExecutor(),
        platform="darwin",
        os_release="",
        effective_uid=1000,
        user="alice",
    )
    assert runner.host() == HostOs.MACOS
    runner2 = HostPackageRunner(
        SubprocessCommandExecutor(),
        platform="linux",
        os_release="",
        effective_uid=1000,
        user="alice",
    )
    assert runner2.host() is None


def test_host_label_prefers_pretty_name(tmp_path: Path):
    release = tmp_path / "os-release"
    release.write_text("PRETTY_NAME=My Arch Linux\n")
    runner = HostPackageRunner(
        SubprocessCommandExecutor(),
        platform="linux",
        os_release=release.read_text(),
        effective_uid=1000,
        user="alice",
    )
    assert runner.host_label() == "My Arch Linux"
    # No pretty: fallback to generic
    runner2 = HostPackageRunner(
        SubprocessCommandExecutor(),
        platform="linux",
        os_release="ID=arch",
        effective_uid=1000,
        user="alice",
    )
    assert runner2.host_label() == "Arch Linux"


@pytest.mark.parametrize(
    "uid,executable_paths,expected",
    [
        # macOS root
        (0, (), "run `vibey install` as your own user: Homebrew refuses to run as root"),
        # macOS no brew
        (1000, (), HOMEBREW_REQUIRED),
        # arch no pacman
        (
            1000,
            ("sudo",),
            "pacman is not on PATH; this does not look like a working Arch Linux install",
        ),
        # arch no sudo
        (
            1000,
            ("pacman",),
            "vibey install needs sudo on Arch Linux: pacman and systemctl run as root",
        ),
        # unknown host
        (
            1000,
            ("pacman", "sudo"),
            "Arch Linux is not a default OS for `vibey install` (Arch Linux, macOS)",
        ),
    ],
)
def test_precondition_names_what_is_missing(uid, executable_paths, expected):
    executor = FakeCommandExecutor(on_path=executable_paths)
    unknown = expected.startswith("Arch Linux is not")
    platform = (
        "plan9"
        if unknown
        else (
            "darwin" if expected == HOMEBREW_REQUIRED or expected.startswith("run `") else "linux"
        )
    )
    release = (
        "PRETTY_NAME=Arch Linux\n"
        if unknown
        else ("" if platform == "darwin" else "PRETTY_NAME=Arch Linux\nID=arch\n")
    )
    runner = HostPackageRunner(
        executor,
        platform=platform,
        os_release=release,
        effective_uid=uid,
        user="alice",
    )
    assert runner.precondition() == expected


def test_privileged_uses_sudo_only_when_not_root(tmp_path: Path):
    executor = FakeCommandExecutor(on_path=("sudo",))
    runner = HostPackageRunner(
        SubprocessCommandExecutor(),
        platform="linux",
        os_release="",
        effective_uid=1000,
        user="alice",
    )
    runner._executor = executor
    assert runner.privileged(("pacman", "-S", "foo")) == ("sudo", "pacman", "-S", "foo")
    runner._effective_uid = 0
    assert runner.privileged(("pacman",)) == ("pacman",)
    # no sudo
    executor = FakeCommandExecutor(on_path=())
    runner._executor = executor
    runner._effective_uid = 1000
    assert runner.privileged(("pacman",)) is None


def test_is_installed_accepts_a_binary_on_path_or_a_package_query(tmp_path: Path):
    executor = FakeCommandExecutor(on_path=("postgres",))
    runner = HostPackageRunner(
        SubprocessCommandExecutor(), platform="linux", os_release="", effective_uid=0, user="alice"
    )
    runner._executor = executor
    spec = PackageSpec(PackageSource.PACMAN, ("postgres",), ())
    assert runner.is_installed(spec)
    # No binaries, but pacman reports installed
    executor = FakeCommandExecutor(
        on_path=("pacman",), responses={("pacman", "-Q", "postgres"): CommandResult(0)}
    )
    runner._executor = executor
    assert runner.is_installed(spec)


def test_ensure_is_idempotent_for_an_installed_package(tmp_path: Path):
    executor = FakeCommandExecutor(
        on_path=("pacman",), responses={("pacman", "-Q", "foo"): CommandResult(0)}
    )
    runner = HostPackageRunner(
        SubprocessCommandExecutor(), platform="linux", os_release="", effective_uid=0, user="alice"
    )
    runner._executor = executor
    spec = PackageSpec(PackageSource.PACMAN, ("foo",), ())
    outcome = runner.ensure(spec)
    assert outcome.ok and not outcome.changed
    # only one query executed
    assert executor.calls == [("pacman", "-Q", "foo")]


def test_for_this_host_reads_sudo_user_and_missing_os_release(tmp_path: Path) -> None:
    runner = HostPackageRunner.for_this_host(
        FakeCommandExecutor(on_path=()),
        os_release_path=tmp_path / "missing",
        environ={"SUDO_USER": "alice"},
    )
    assert runner.user == "alice"


@pytest.mark.parametrize(
    "error,code",
    [
        (FileNotFoundError("missing"), 127),
        (subprocess.TimeoutExpired(("x",), 0.1), 124),
        (OSError("bad"), 1),
    ],
)
def test_subprocess_executor_maps_execution_errors(
    monkeypatch, error: BaseException, code: int
) -> None:
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "run", fail)
    result = SubprocessCommandExecutor().run(("missing",))
    assert result.returncode == code
    assert result.stderr


def test_subprocess_executor_returns_process_result(monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 3, "out", "err"),
    )
    assert SubprocessCommandExecutor().run(("x",)) == CommandResult(3, "out", "err")


def test_is_installed_handles_none_and_brew_sources() -> None:
    executor = FakeCommandExecutor(
        on_path=("brew",),
        responses={
            ("brew", "list", "--formula", "--versions", "foo"): CommandResult(0),
            ("brew", "list", "--cask", "--versions", "bar"): CommandResult(0),
        },
    )
    runner = make_runner(
        platform="darwin", os_release="", uid=1000, user="alice", executor=executor
    )
    assert runner.is_installed(PackageSpec(PackageSource.NONE))
    assert runner.is_installed(PackageSpec(PackageSource.BREW_FORMULA, ("foo",)))
    assert runner.is_installed(PackageSpec(PackageSource.BREW_CASK, ("bar",)))


@pytest.mark.parametrize(
    "source,paths,uid,expected",
    [
        (
            PackageSource.PACMAN,
            ("sudo",),
            1000,
            ("sudo", "pacman", "-S", "--needed", "--noconfirm", "foo"),
        ),
        (PackageSource.PACMAN, (), 0, ("pacman", "-S", "--needed", "--noconfirm", "foo")),
        (PackageSource.AUR, ("paru",), 1000, ("paru", "-S", "--needed", "--noconfirm", "foo")),
        (PackageSource.AUR, ("yay",), 1000, ("yay", "-S", "--needed", "--noconfirm", "foo")),
        (PackageSource.BREW_FORMULA, ("brew",), 1000, ("brew", "install", "foo")),
        (PackageSource.BREW_CASK, ("brew",), 1000, ("brew", "install", "--cask", "foo")),
    ],
)
def test_ensure_installs_each_package_source(source, paths, uid, expected) -> None:
    query_prefix = (
        ("pacman", "-Q")
        if source in (PackageSource.PACMAN, PackageSource.AUR)
        else ("brew", "list")
    )
    executor = FakeCommandExecutor(
        on_path=paths,
        responses={query_prefix: CommandResult(1)},
        default=CommandResult(0),
    )
    platform = "linux" if source in (PackageSource.PACMAN, PackageSource.AUR) else "darwin"
    runner = make_runner(
        platform=platform, os_release="ID=arch", uid=uid, user="alice", executor=executor
    )
    outcome = runner.ensure(PackageSpec(source, ("foo",)))
    assert outcome.ok and outcome.changed
    assert executor.calls[-1] == expected


def test_ensure_handles_none_missing_privilege_and_aur_helper() -> None:
    none = make_runner(
        platform="linux",
        os_release="ID=arch",
        uid=0,
        user="alice",
        executor=FakeCommandExecutor(on_path=(), default=CommandResult(1)),
    )
    assert none.ensure(PackageSpec(PackageSource.NONE)).detail == "nothing to install"
    no_sudo = make_runner(
        platform="linux",
        os_release="ID=arch",
        uid=1000,
        user="alice",
        executor=FakeCommandExecutor(on_path=(), default=CommandResult(1)),
    )
    assert not no_sudo.ensure(PackageSpec(PackageSource.PACMAN, ("foo",))).ok
    no_helper = make_runner(
        platform="linux",
        os_release="ID=arch",
        uid=1000,
        user="alice",
        executor=FakeCommandExecutor(on_path=(), default=CommandResult(1)),
    )
    assert "AUR helper" in no_helper.ensure(PackageSpec(PackageSource.AUR, ("foo",))).detail
    root_aur = make_runner(
        platform="linux",
        os_release="ID=arch",
        uid=0,
        user="alice",
        executor=FakeCommandExecutor(on_path=(), default=CommandResult(1)),
    )
    assert (
        "refuse to run as root" in root_aur.ensure(PackageSpec(PackageSource.AUR, ("foo",))).detail
    )


def test_ensure_reports_brew_preconditions_and_failed_commands() -> None:
    root = make_runner(
        platform="darwin",
        os_release="",
        uid=0,
        user="alice",
        executor=FakeCommandExecutor(on_path=(), default=CommandResult(1)),
    )
    assert (
        "refuses to run as root"
        in root.ensure(PackageSpec(PackageSource.BREW_FORMULA, ("foo",))).detail
    )
    missing = make_runner(
        platform="darwin",
        os_release="",
        uid=1000,
        user="alice",
        executor=FakeCommandExecutor(on_path=(), default=CommandResult(1)),
    )
    assert (
        missing.ensure(PackageSpec(PackageSource.BREW_FORMULA, ("foo",))).detail
        == HOMEBREW_REQUIRED
    )
    failed = FakeCommandExecutor(
        on_path=("brew",), default=CommandResult(1, stderr="first\nlast\n")
    )
    runner = make_runner(platform="darwin", os_release="", uid=1000, user="alice", executor=failed)
    result = runner.ensure(PackageSpec(PackageSource.BREW_FORMULA, ("foo",)))
    assert result.detail.endswith("last") and result.changed


def test_executor_which_and_healthy_preconditions() -> None:
    executor = FakeCommandExecutor(on_path=("brew", "pacman", "sudo"))
    assert SubprocessCommandExecutor().which("python3")
    mac = make_runner(platform="darwin", os_release="", uid=1000, user="alice", executor=executor)
    arch = make_runner(
        platform="linux", os_release="ID=arch", uid=1000, user="alice", executor=executor
    )
    assert mac.host_label() == "macOS"
    assert mac.precondition() is None
    assert arch.precondition() is None


def test_runner_and_executor_satisfy_interfaces() -> None:
    executor = FakeCommandExecutor(on_path=())
    runner = make_runner(
        platform="linux", os_release="ID=arch", uid=0, user="alice", executor=executor
    )
    assert isinstance(executor, CommandExecutorInterface)
    assert isinstance(runner, HostPackageRunnerInterface)
