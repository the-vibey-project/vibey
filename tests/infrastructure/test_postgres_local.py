# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit coverage for the opt-in local PostgreSQL installer."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vibey.infrastructure.interfaces import PostgresLocalServiceInterface
from vibey.infrastructure.postgres import (
    POSTGRES_MIN_MAJOR,
    POSTGRES_SUPPORTED_MAJORS,
    PostgresCommandResult,
    PostgresLocalService,
    PostgresStatus,
    PostgresVersion,
    parse_postgres_server_version,
    parse_postgres_version,
)


def _which(*names: str) -> dict[str, str]:
    return {name: f"/usr/bin/{name}" for name in names}


def test_version_parser_accepts_client_suffixes_and_rejects_noise() -> None:
    assert parse_postgres_version("psql (PostgreSQL) 14.24") == PostgresVersion(14, 24)
    assert parse_postgres_version("PostgreSQL 18.4 (Homebrew)") == PostgresVersion(18, 4)
    assert parse_postgres_version("not a postgres version") is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [("140024", PostgresVersion(14, 24)), (180004, PostgresVersion(18, 4))],
)
def test_server_version_parser_decodes_numeric_setting(
    value: str | int, expected: PostgresVersion
) -> None:
    assert parse_postgres_server_version(value) == expected


@pytest.mark.parametrize("value", ["not numeric", 99_999])
def test_server_version_parser_rejects_invalid_or_legacy_values(value: str | int) -> None:
    assert parse_postgres_server_version(value) is None


def test_support_matrix_is_the_current_supported_major_range() -> None:
    assert POSTGRES_MIN_MAJOR == 14
    assert POSTGRES_SUPPORTED_MAJORS == (14, 15, 16, 17, 18)
    assert PostgresVersion(14, 0).supported is True
    assert PostgresVersion(13, 99).supported is False
    assert PostgresVersion(19, 0).supported is True


def test_status_reports_missing_client_tools() -> None:
    service = PostgresLocalService(which=lambda _name: None)

    status = service.status()

    assert status == PostgresStatus(
        installed=False,
        running=False,
        supported=False,
        version=None,
        detail="PostgreSQL client tools are not installed; vibey requires PostgreSQL 14+",
    )
    assert status.ready is False


def test_status_finds_supported_version_in_stderr_and_ready_server() -> None:
    available = _which("pg_config", "pg_isready")
    calls: list[tuple[str, ...]] = []

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        calls.append(argv)
        if argv[-1] == "--version":
            return PostgresCommandResult(0, stderr="PostgreSQL 18.4 (Homebrew)")
        return PostgresCommandResult(0)

    service = PostgresLocalService(command_runner=run, which=available.get)

    status = service.status()

    assert status.ready is True
    assert status.version == PostgresVersion(18, 4)
    assert "accepting local connections" in status.detail
    assert calls[-1] == ("/usr/bin/pg_isready", "-h", "localhost", "-p", "5432")


def test_status_uses_psql_when_pg_config_is_missing() -> None:
    available = _which("psql", "pg_isready")

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if argv[-1] == "--version":
            return PostgresCommandResult(0, stdout="psql (PostgreSQL) 15.19")
        return PostgresCommandResult(1)

    status = PostgresLocalService(command_runner=run, which=available.get).status()

    assert status.installed is True
    assert status.supported is True
    assert status.running is False
    assert "not accepting" in status.detail


def test_status_reports_unsupported_server_without_readiness_probe() -> None:
    available = _which("pg_config", "pg_isready")
    calls: list[tuple[str, ...]] = []

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        calls.append(argv)
        return PostgresCommandResult(0, stdout="PostgreSQL 13.23")

    status = PostgresLocalService(command_runner=run, which=available.get).status()

    assert status.installed is True
    assert status.supported is False
    assert status.running is False
    assert "below" in status.detail
    assert len(calls) == 1


def test_status_reports_missing_pg_isready() -> None:
    available = _which("pg_config")
    status = PostgresLocalService(
        command_runner=lambda _argv: PostgresCommandResult(0, stdout="PostgreSQL 14.24"),
        which=available.get,
    ).status()

    assert status.supported is True
    assert status.running is False
    assert "pg_isready" in status.detail


def test_status_reports_unreadable_version() -> None:
    available = _which("pg_config", "pg_isready")
    status = PostgresLocalService(
        command_runner=lambda _argv: PostgresCommandResult(1, stderr="version failed"),
        which=available.get,
    ).status()

    assert status.installed is True
    assert status.supported is False
    assert "could not be determined" in status.detail


def test_brew_install_starts_service_and_verifies_it() -> None:
    available = _which("pg_config", "pg_isready", "brew")
    calls: list[tuple[str, ...]] = []
    version_calls = 0

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        nonlocal version_calls
        calls.append(argv)
        if argv[-1] == "--version":
            version_calls += 1
            return PostgresCommandResult(
                0, stdout=f"PostgreSQL {'13.23' if version_calls == 1 else '18.4'}"
            )
        if argv[0:2] == ("brew", "--prefix"):
            return PostgresCommandResult(0, stdout="/opt/homebrew/opt/postgresql@18\n")
        return PostgresCommandResult(0)

    result = PostgresLocalService(
        command_runner=run,
        which=available.get,
        effective_uid=lambda: 501,
    ).install()

    assert result.ok is True
    assert result.changed is True
    assert result.status.ready is True
    assert ("brew", "install", "postgresql@18") in result.commands
    assert ("brew", "services", "start", "postgresql@18") in result.commands


def test_brew_verification_prefers_the_versioned_formula_over_an_old_path_entry(
    tmp_path: Path,
) -> None:
    available = _which("pg_config", "pg_isready", "brew")
    prefix = tmp_path / "postgresql@18"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "bin" / "pg_config").touch()
    (prefix / "bin" / "pg_isready").touch()
    version_tools: list[str] = []

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if argv[-1] == "--version":
            version_tools.append(argv[0])
            return PostgresCommandResult(
                0, stdout=f"PostgreSQL {'13.23' if len(version_tools) == 1 else '18.4'}"
            )
        if argv[:2] == ("brew", "--prefix"):
            return PostgresCommandResult(0, stdout=f"{prefix}\n")
        if argv[0] in {"/usr/bin/pg_isready", str(prefix / "bin" / "pg_isready")}:
            return PostgresCommandResult(1 if len(version_tools) == 1 else 0)
        return PostgresCommandResult(0)

    result = PostgresLocalService(command_runner=run, which=available.get).install()

    assert result.ok is True
    assert version_tools == [
        str(prefix / "bin" / "pg_config"),
        str(prefix / "bin" / "pg_config"),
    ]


def test_status_discovers_an_unlinked_homebrew_formula(tmp_path: Path) -> None:
    prefix = tmp_path / "postgresql@18"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "bin" / "pg_config").touch()
    (prefix / "bin" / "pg_isready").touch()

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if argv[:2] == ("brew", "--prefix"):
            return PostgresCommandResult(0, stdout=f"{prefix}\n")
        if argv[-1] == "--version":
            return PostgresCommandResult(0, stdout="PostgreSQL 18.4")
        return PostgresCommandResult(0)

    status = PostgresLocalService(
        command_runner=run,
        which=lambda name: "/usr/bin/brew" if name == "brew" else None,
    ).status()

    assert status.ready is True
    assert status.version == PostgresVersion(18, 4)


def test_brew_does_not_reinstall_a_supported_stopped_server() -> None:
    available = _which("pg_config", "pg_isready", "brew")
    calls: list[tuple[str, ...]] = []
    ready_calls = 0

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        nonlocal ready_calls
        calls.append(argv)
        if argv[-1] == "--version":
            return PostgresCommandResult(0, stdout="PostgreSQL 18.4")
        if argv[0].endswith("/pg_isready"):
            ready_calls += 1
            return PostgresCommandResult(1 if ready_calls == 1 else 0)
        return PostgresCommandResult(0, stdout="/opt/homebrew/opt/postgresql@18\n")

    result = PostgresLocalService(command_runner=run, which=available.get).install()

    assert result.ok is True
    assert result.changed is True
    assert ("brew", "install", "postgresql@18") not in result.commands
    assert calls.count(("brew", "--prefix", "postgresql@18")) == 1


def test_brew_install_failure_is_reported() -> None:
    available = _which("pg_config", "pg_isready", "brew")

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if argv[:2] == ("brew", "install"):
            return PostgresCommandResult(1, stderr="formula unavailable")
        return PostgresCommandResult(0, stdout="PostgreSQL 13.23")

    result = PostgresLocalService(command_runner=run, which=available.get).install()

    assert result.ok is False
    assert result.changed is True
    assert "could not install" in result.detail


def test_brew_prefix_failure_still_attempts_service_and_verifies() -> None:
    available = _which("pg_config", "pg_isready", "brew")
    ready_calls = 0
    prefix_calls = 0

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        nonlocal prefix_calls, ready_calls
        if argv[-1] == "--version":
            return PostgresCommandResult(0, stdout="PostgreSQL 18.4")
        if argv[0] == "/usr/bin/pg_isready":
            ready_calls += 1
            return PostgresCommandResult(1 if ready_calls == 1 else 0)
        if argv[:2] == ("brew", "--prefix"):
            prefix_calls += 1
            return PostgresCommandResult(
                1 if prefix_calls == 1 else 0,
                stdout="/opt/homebrew/opt/postgresql@18\n",
            )
        return PostgresCommandResult(0)

    result = PostgresLocalService(command_runner=run, which=available.get).install()

    assert result.ok is True
    assert result.status.ready is True


def test_brew_prefix_falls_back_to_path_when_formula_binary_is_missing(tmp_path: Path) -> None:
    service = PostgresLocalService(which=lambda name: f"/usr/bin/{name}")
    service._brew_prefix = tmp_path / "not-installed"

    assert service._find("pg_config") == "/usr/bin/pg_config"


def test_brew_service_start_failure_is_reported() -> None:
    available = _which("pg_config", "pg_isready", "brew")

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if argv[-1] == "--version":
            return PostgresCommandResult(0, stdout="PostgreSQL 13.23")
        if argv[:3] == ("brew", "services", "start"):
            return PostgresCommandResult(1, stderr="service failed")
        return PostgresCommandResult(0)

    result = PostgresLocalService(command_runner=run, which=available.get).install()

    assert result.ok is False
    assert "could not start" in result.detail


def test_install_returns_without_commands_when_server_is_ready() -> None:
    available = _which("pg_config", "pg_isready")
    service = PostgresLocalService(
        command_runner=lambda argv: PostgresCommandResult(
            0,
            stdout="PostgreSQL 18.4" if argv[-1] == "--version" else "",
        ),
        which=available.get,
    )

    result = service.install()

    assert result.ok is True
    assert result.changed is False
    assert result.commands == ()
    assert "no installation was needed" in result.detail


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("win32", "Windows is not a supported"), ("freebsd", "could not find")],
)
def test_install_without_supported_package_manager_is_actionable(
    platform: str, expected: str
) -> None:
    result = PostgresLocalService(which=lambda _name: None, platform=platform).install()

    assert result.ok is False
    assert expected in result.detail


def test_apt_install_as_root_updates_installs_and_starts() -> None:
    available = _which("pg_config", "pg_isready", "apt-get", "systemctl")
    version_calls = 0

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        nonlocal version_calls
        if argv[-1] == "--version":
            version_calls += 1
            return PostgresCommandResult(
                0, stdout=f"PostgreSQL {'13.23' if version_calls == 1 else '14.24'}"
            )
        return PostgresCommandResult(0)

    result = PostgresLocalService(
        command_runner=run, which=available.get, effective_uid=lambda: 0
    ).install()

    assert result.ok is True
    assert ("apt-get", "update") in result.commands
    assert ("apt-get", "install", "-y", "postgresql") in result.commands
    assert ("systemctl", "enable", "--now", "postgresql") in result.commands


def test_apt_install_uses_sudo_for_non_root() -> None:
    available = _which("apt-get", "sudo", "service")
    calls: list[tuple[str, ...]] = []

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        calls.append(argv)
        return PostgresCommandResult(0)

    result = PostgresLocalService(
        command_runner=run, which=available.get, effective_uid=lambda: 1000
    ).install()

    assert result.ok is False  # no client binaries appeared for verification
    assert calls[:3] == [
        ("sudo", "apt-get", "update"),
        ("sudo", "apt-get", "install", "-y", "postgresql"),
        ("sudo", "service", "postgresql", "start"),
    ]


@pytest.mark.parametrize(
    "failed_command",
    ["update", "install", "service"],
)
def test_apt_failures_are_reported(failed_command: str) -> None:
    available = _which("apt-get", "systemctl")

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if failed_command == "update" and argv == ("apt-get", "update"):
            return PostgresCommandResult(1)
        if failed_command == "install" and argv[:2] == ("apt-get", "install"):
            return PostgresCommandResult(1)
        if failed_command == "service" and argv[0] == "systemctl":
            return PostgresCommandResult(1)
        return PostgresCommandResult(0)

    result = PostgresLocalService(
        command_runner=run, which=available.get, effective_uid=lambda: 0
    ).install()

    assert result.ok is False
    assert result.changed is True


def test_apt_requires_sudo_when_not_root() -> None:
    available = _which("apt-get")
    result = PostgresLocalService(which=available.get, effective_uid=lambda: 1000).install()

    assert result.ok is False
    assert "root or sudo" in result.detail
    assert result.commands == ()


def test_apt_reports_missing_service_manager() -> None:
    available = _which("apt-get")
    result = PostgresLocalService(
        command_runner=lambda _argv: PostgresCommandResult(0),
        which=available.get,
        effective_uid=lambda: 0,
    ).install()

    assert result.ok is False
    assert "service manager" in result.detail


def test_dnf_initializes_and_starts_the_server() -> None:
    available = _which("pg_config", "pg_isready", "dnf", "postgresql-setup", "systemctl")
    installed = False
    version_calls = 0

    def which(name: str) -> str | None:
        if name in {"pg_config", "pg_isready"} and not installed:
            return None
        return available.get(name)

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        nonlocal installed, version_calls
        if argv[:2] == ("dnf", "install"):
            installed = True
        if argv[-1] == "--version":
            version_calls += 1
            return PostgresCommandResult(
                0, stdout=f"PostgreSQL {'13.23' if not installed else '18.4'}"
            )
        return PostgresCommandResult(0)

    result = PostgresLocalService(
        command_runner=run, which=which, effective_uid=lambda: 0
    ).install()

    assert result.ok is True
    assert ("dnf", "install", "-y", "postgresql-server") in result.commands
    assert ("/usr/bin/postgresql-setup", "--initdb", "--unit", "postgresql") in result.commands


def test_dnf_without_setup_uses_service_manager() -> None:
    available = _which("dnf", "systemctl")
    result = PostgresLocalService(
        command_runner=lambda _argv: PostgresCommandResult(0),
        which=available.get,
        effective_uid=lambda: 0,
    ).install()

    assert result.ok is False
    assert "verification failed" in result.detail


def test_dnf_requires_sudo_when_not_root() -> None:
    available = _which("dnf")
    result = PostgresLocalService(which=available.get, effective_uid=lambda: 1000).install()

    assert result.ok is False
    assert "root or sudo" in result.detail
    assert result.commands == ()


def test_dnf_reports_initdb_privilege_failure() -> None:
    available = _which("dnf", "postgresql-setup")
    sudo_checks = 0

    def which(name: str) -> str | None:
        nonlocal sudo_checks
        if name == "sudo":
            sudo_checks += 1
            return "/usr/bin/sudo" if sudo_checks == 1 else None
        return available.get(name)

    result = PostgresLocalService(
        command_runner=lambda _argv: PostgresCommandResult(0),
        which=which,
        effective_uid=lambda: 1000,
    ).install()

    assert result.ok is False
    assert "initdb needs root or sudo" in result.detail


@pytest.mark.parametrize(
    "failed_command",
    ["install", "initdb", "service"],
)
def test_dnf_failures_are_reported(failed_command: str) -> None:
    available = _which("dnf", "postgresql-setup", "systemctl")

    def run(argv: tuple[str, ...]) -> PostgresCommandResult:
        if failed_command == "install" and argv[:2] == ("dnf", "install"):
            return PostgresCommandResult(1)
        if failed_command == "initdb" and argv[0].endswith("postgresql-setup"):
            return PostgresCommandResult(1)
        if failed_command == "service" and argv[0] == "systemctl":
            return PostgresCommandResult(1)
        return PostgresCommandResult(0)

    result = PostgresLocalService(
        command_runner=run, which=available.get, effective_uid=lambda: 0
    ).install()

    assert result.ok is False
    assert result.changed is True


def test_dnf_reports_missing_service_manager() -> None:
    available = _which("dnf")
    result = PostgresLocalService(
        command_runner=lambda _argv: PostgresCommandResult(0),
        which=available.get,
        effective_uid=lambda: 0,
    ).install()

    assert result.ok is False
    assert "service manager" in result.detail


def test_brew_prefix_can_supply_unlinked_binaries(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "pg_config").touch()
    (bin_dir / "pg_isready").touch()
    service = PostgresLocalService(
        command_runner=lambda argv: PostgresCommandResult(
            0,
            stdout="PostgreSQL 18.4" if argv[-1] == "--version" else "",
        ),
        which=lambda _name: None,
    )
    service._brew_prefix = tmp_path

    status = service.status()

    assert status.ready is True


def test_interface_matches_service() -> None:
    assert isinstance(PostgresLocalService(which=lambda _name: None), PostgresLocalServiceInterface)


def test_subprocess_runner_handles_success_oserror_and_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from vibey.infrastructure import postgres as module

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=("echo",), returncode=0, stdout="ok", stderr=""
        ),
    )
    assert module._run_command(("echo",)).stdout == "ok"

    def raise_oserror(*_args: object, **_kwargs: object) -> object:
        raise OSError("missing")

    monkeypatch.setattr(subprocess, "run", raise_oserror)
    assert module._run_command(("missing",)).returncode == 1

    def raise_timeout(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="slow", timeout=1)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    assert module._run_command(("slow",)).returncode == 1
