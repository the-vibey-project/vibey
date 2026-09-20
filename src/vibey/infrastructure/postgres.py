# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Local PostgreSQL discovery and opt-in installation.

The conductor still accepts an explicit ``VIBEY_PG_URL`` for every database
operation.  This module only removes the separate prerequisite of having a
local server installed and started: ``doctor`` reports the local service, and
``doctor --install-postgres`` / ``install --postgres`` may install it.

The application uses SQL features available in PostgreSQL 14 and later.  The
upper bound is deliberately not a runtime restriction: a future major is
accepted once it exists.  ``POSTGRES_SUPPORTED_MAJORS`` is the finite set of
released majors that CI exercises today and the major selected by the local
installer is the current stable release.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed argv, never shell=True
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

POSTGRES_MIN_MAJOR: Final = 14
POSTGRES_LATEST_MAJOR: Final = 18
POSTGRES_SUPPORTED_MAJORS: Final[tuple[int, ...]] = tuple(
    range(POSTGRES_MIN_MAJOR, POSTGRES_LATEST_MAJOR + 1)
)
POSTGRES_INSTALL_MAJOR: Final = POSTGRES_LATEST_MAJOR
POSTGRES_LOCAL_PORT: Final = 5432

_VERSION_PATTERN = re.compile(r"\bPostgreSQL\)?\s+(\d+)(?:\.(\d+))?\b", re.IGNORECASE)
_COMMAND_TIMEOUT_SECONDS: Final = 120.0


@dataclass(frozen=True, slots=True, order=True)
class PostgresVersion:
    """A PostgreSQL server version reduced to the fields relevant to support."""

    major: int
    minor: int = 0

    @property
    def supported(self) -> bool:
        """Whether this major is at or above vibey's compatibility floor."""
        return self.major >= POSTGRES_MIN_MAJOR

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True, slots=True)
class PostgresStatus:
    """The locally discoverable PostgreSQL installation state."""

    installed: bool
    running: bool
    supported: bool
    version: PostgresVersion | None
    detail: str

    @property
    def ready(self) -> bool:
        """Whether a supported local server accepts connections."""
        return self.installed and self.supported and self.running


@dataclass(frozen=True, slots=True)
class PostgresCommandResult:
    """The small subprocess result shape needed by the install seam."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class PostgresInstallResult:
    """The result of an explicit local PostgreSQL installation attempt."""

    ok: bool
    changed: bool
    detail: str
    status: PostgresStatus
    commands: tuple[tuple[str, ...], ...] = ()


CommandRunner = Callable[[tuple[str, ...]], PostgresCommandResult]
Which = Callable[[str], str | None]


def parse_postgres_version(text: str) -> PostgresVersion | None:
    """Parse ``psql``/``pg_config`` output without depending on its suffix."""
    match = _VERSION_PATTERN.search(text)
    if match is None:
        return None
    return PostgresVersion(int(match.group(1)), int(match.group(2) or 0))


def parse_postgres_server_version(value: str | int) -> PostgresVersion | None:
    """Parse PostgreSQL's numeric ``server_version_num`` setting."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 100000:
        return None
    return PostgresVersion(number // 10000, number % 10000)


def _run_command(argv: tuple[str, ...]) -> PostgresCommandResult:
    """Run one fixed-argv package or service command."""
    try:
        completed = subprocess.run(  # nosec B603 B607 - fixed argv, never shell=True
            argv,
            capture_output=True,
            check=False,
            text=True,
            timeout=_COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return PostgresCommandResult(returncode=1, stderr=str(exc))
    return PostgresCommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


class PostgresLocalService:
    """Discover and explicitly install a local PostgreSQL service.

    The package-manager commands are intentionally small, fixed argv lists.
    No command runs from ``status``; installation only runs after the caller
    selected an install command or doctor flag.  Native Homebrew and the two
    common Linux package managers are covered because vibey itself supports
    macOS/Linux; an unsupported host receives an actionable diagnostic.
    """

    def __init__(
        self,
        *,
        command_runner: CommandRunner = _run_command,
        which: Which = shutil.which,
        platform: str | None = None,
        effective_uid: Callable[[], int] | None = None,
    ) -> None:
        self._run = command_runner
        self._which = which
        self._platform = platform or sys.platform
        self._effective_uid: Callable[[], int] = (
            effective_uid if effective_uid is not None else getattr(os, "geteuid", lambda: 1)
        )
        self._brew_prefix: Path | None = None

    def status(self) -> PostgresStatus:
        """Inspect client binaries, version support, and local readiness."""
        self._discover_brew_prefix()
        version_tool = self._find_first("pg_config", "psql")
        ready_tool = self._find("pg_isready")
        if version_tool is None:
            return PostgresStatus(
                installed=False,
                running=False,
                supported=False,
                version=None,
                detail=(
                    "PostgreSQL client tools are not installed; "
                    f"vibey requires PostgreSQL {POSTGRES_MIN_MAJOR}+"
                ),
            )

        version_result = self._run((version_tool, "--version"))
        version = parse_postgres_version(version_result.stdout)
        if version is None and version_result.returncode == 0:
            version = parse_postgres_version(version_result.stderr)
        if version is None:
            detail = "PostgreSQL is installed but its version could not be determined"
            return PostgresStatus(
                installed=True,
                running=False,
                supported=False,
                version=None,
                detail=detail,
            )

        if not version.supported:
            return PostgresStatus(
                installed=True,
                running=False,
                supported=False,
                version=version,
                detail=(
                    f"PostgreSQL {version} is below vibey's {POSTGRES_MIN_MAJOR}+ support floor"
                ),
            )

        if ready_tool is None:
            return PostgresStatus(
                installed=True,
                running=False,
                supported=True,
                version=version,
                detail="PostgreSQL is installed but pg_isready is not on PATH",
            )

        readiness = self._run((ready_tool, "-h", "localhost", "-p", str(POSTGRES_LOCAL_PORT)))
        if readiness.returncode == 0:
            detail = f"PostgreSQL {version} is accepting local connections"
            running = True
        else:
            detail = f"PostgreSQL {version} is installed but not accepting local connections"
            running = False
        return PostgresStatus(
            installed=True,
            running=running,
            supported=True,
            version=version,
            detail=detail,
        )

    def install(self) -> PostgresInstallResult:
        """Install and start the current stable supported PostgreSQL major."""
        before = self.status()
        if before.ready:
            return PostgresInstallResult(
                ok=True,
                changed=False,
                detail=f"{before.detail}; no installation was needed",
                status=before,
            )

        package_manager = self._package_manager()
        if package_manager is None:
            detail = self._unsupported_platform_detail()
            return PostgresInstallResult(
                ok=False,
                changed=False,
                detail=detail,
                status=before,
            )

        commands: list[tuple[str, ...]] = []
        if package_manager == "brew":
            ok, detail = self._install_brew(before, commands)
        elif package_manager == "apt-get":
            ok, detail = self._install_apt(before, commands)
        else:
            ok, detail = self._install_dnf(before, commands)

        if not ok:
            return PostgresInstallResult(
                ok=False,
                changed=bool(commands),
                detail=detail,
                status=self.status(),
                commands=tuple(commands),
            )

        after = self.status()
        if not after.ready:
            return PostgresInstallResult(
                ok=False,
                changed=bool(commands),
                detail=f"{detail}; verification failed: {after.detail}",
                status=after,
                commands=tuple(commands),
            )
        return PostgresInstallResult(
            ok=True,
            changed=bool(commands),
            detail=f"{detail}; {after.detail}",
            status=after,
            commands=tuple(commands),
        )

    def _find(self, name: str) -> str | None:
        if self._brew_prefix is not None:
            candidate = self._brew_prefix / "bin" / name
            if candidate.exists():
                return str(candidate)
        return self._which(name)

    def _discover_brew_prefix(self) -> None:
        """Find an installed versioned Homebrew formula even when it is unlinked."""
        if self._brew_prefix is not None or self._which("brew") is None:
            return
        formula = f"postgresql@{POSTGRES_INSTALL_MAJOR}"
        result = self._run(("brew", "--prefix", formula))
        if result.returncode == 0 and result.stdout.strip():
            self._brew_prefix = Path(result.stdout.strip())

    def _find_first(self, *names: str) -> str | None:
        for name in names:
            found = self._find(name)
            if found is not None:
                return found
        return None

    def _package_manager(self) -> str | None:
        for candidate in ("brew", "apt-get", "dnf"):
            if self._which(candidate) is not None:
                return candidate
        return None

    def _install_brew(
        self, before: PostgresStatus, commands: list[tuple[str, ...]]
    ) -> tuple[bool, str]:
        formula = f"postgresql@{POSTGRES_INSTALL_MAJOR}"
        if (not before.installed or not before.supported) and not self._run_step(
            ("brew", "install", formula), commands
        ):
            return False, "Homebrew could not install PostgreSQL"
        if self._brew_prefix is None:
            prefix = self._run_step_result(("brew", "--prefix", formula), commands)
            if prefix.returncode == 0 and prefix.stdout.strip():
                self._brew_prefix = Path(prefix.stdout.strip())
        if not self._run_step(("brew", "services", "start", formula), commands):
            return False, "Homebrew installed PostgreSQL but could not start its service"
        return True, f"Homebrew installed/started PostgreSQL {POSTGRES_INSTALL_MAJOR}"

    def _install_apt(
        self, before: PostgresStatus, commands: list[tuple[str, ...]]
    ) -> tuple[bool, str]:
        del before
        update = self._privileged(("apt-get", "update"))
        install = self._privileged(("apt-get", "install", "-y", "postgresql"))
        if update is None or install is None:
            return False, "apt-get needs root or sudo to install PostgreSQL"
        if not self._run_step(update, commands):
            return False, "apt-get could not refresh package metadata"
        if not self._run_step(install, commands):
            return False, "apt-get could not install PostgreSQL"
        start = self._service_start("postgresql")
        if start is None:
            return False, "PostgreSQL was installed but no service manager was found"
        if not self._run_step(start, commands):
            return False, "PostgreSQL was installed but its service could not start"
        return True, "apt-get installed/started PostgreSQL"

    def _install_dnf(
        self, before: PostgresStatus, commands: list[tuple[str, ...]]
    ) -> tuple[bool, str]:
        install = self._privileged(("dnf", "install", "-y", "postgresql-server"))
        if install is None:
            return False, "dnf needs root or sudo to install PostgreSQL"
        if not self._run_step(install, commands):
            return False, "dnf could not install PostgreSQL"
        initdb = self._which("postgresql-setup")
        if not before.installed and initdb is not None:
            init_command = self._privileged((initdb, "--initdb", "--unit", "postgresql"))
            if init_command is None:
                return False, "PostgreSQL was installed but initdb needs root or sudo"
            if not self._run_step(init_command, commands):
                return False, "PostgreSQL was installed but its data directory could not initialize"
        start = self._service_start("postgresql")
        if start is None:
            return False, "PostgreSQL was installed but no service manager was found"
        if not self._run_step(start, commands):
            return False, "PostgreSQL was installed but its service could not start"
        return True, "dnf installed/started PostgreSQL"

    def _service_start(self, service: str) -> tuple[str, ...] | None:
        if self._which("systemctl") is not None:
            return self._privileged(("systemctl", "enable", "--now", service))
        if self._which("service") is not None:
            return self._privileged(("service", service, "start"))
        return None

    def _privileged(self, argv: tuple[str, ...]) -> tuple[str, ...] | None:
        if self._effective_uid() == 0:
            return argv
        if self._which("sudo") is None:
            return None
        return ("sudo", *argv)

    def _run_step_result(
        self, argv: tuple[str, ...], commands: list[tuple[str, ...]]
    ) -> PostgresCommandResult:
        commands.append(argv)
        return self._run(argv)

    def _run_step(self, argv: tuple[str, ...], commands: list[tuple[str, ...]]) -> bool:
        return self._run_step_result(argv, commands).returncode == 0

    def _unsupported_platform_detail(self) -> str:
        host = self._platform
        if host.startswith("win"):
            return "Windows is not a supported vibey host; install PostgreSQL on macOS/Linux"
        return (
            f"could not find Homebrew, apt-get, or dnf on {host}; "
            f"install PostgreSQL {POSTGRES_MIN_MAJOR}+ and re-run `vibey doctor`"
        )


__all__ = [
    "POSTGRES_INSTALL_MAJOR",
    "POSTGRES_LATEST_MAJOR",
    "POSTGRES_LOCAL_PORT",
    "POSTGRES_MIN_MAJOR",
    "POSTGRES_SUPPORTED_MAJORS",
    "PostgresCommandResult",
    "PostgresInstallResult",
    "PostgresLocalService",
    "PostgresStatus",
    "PostgresVersion",
    "parse_postgres_server_version",
    "parse_postgres_version",
]
