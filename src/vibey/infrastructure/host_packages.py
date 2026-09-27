# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger)).
"""Host package installation for the declared local stack."""

from __future__ import annotations

import getpass
import os
import shutil
import subprocess  # nosec B404
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from vibey.domain.local_stack import HostOs, PackageSource, PackageSpec


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class StepOutcome:
    ok: bool
    changed: bool
    detail: str
    commands: tuple[tuple[str, ...], ...] = ()


HOMEBREW_REQUIRED: Final = "Homebrew is required on macOS and is not on PATH: install it with the signed .pkg from https://github.com/Homebrew/brew/releases/latest (vibey never pipes a remote script into a shell), then re-run `vibey install`"


class SubprocessCommandExecutor:
    def run(self, argv: tuple[str, ...], *, timeout: float = 600.0) -> CommandResult:
        try:
            result = subprocess.run(
                argv, capture_output=True, text=True, check=False, timeout=timeout
            )  # nosec B603
        except FileNotFoundError as exc:
            return CommandResult(127, stderr=str(exc))
        except subprocess.TimeoutExpired as exc:
            return CommandResult(124, stderr=str(exc))
        except OSError as exc:
            return CommandResult(1, stderr=str(exc))
        return CommandResult(result.returncode, result.stdout, result.stderr)

    def which(self, name: str) -> str | None:
        return shutil.which(name)


class HostPackageRunner:
    def __init__(
        self,
        executor: Any,
        *,
        platform: str,
        os_release: str,
        effective_uid: int,
        user: str,
    ) -> None:
        self._executor, self._platform, self._os_release = executor, platform, os_release
        self._effective_uid, self._user = effective_uid, user

    @classmethod
    def for_this_host(
        cls,
        executor: Any,
        *,
        os_release_path: Path = Path("/etc/os-release"),
        environ: Mapping[str, str] | None = None,
    ) -> HostPackageRunner:
        try:
            release = os_release_path.read_text(encoding="utf-8")
        except OSError:
            release = ""
        env = os.environ if environ is None else environ
        return cls(
            executor,
            platform=sys.platform,
            os_release=release,
            effective_uid=os.geteuid(),
            user=env.get("SUDO_USER", getpass.getuser()),
        )

    def _value(self, key: str) -> str:
        for line in self._os_release.splitlines():
            name, sep, value = line.partition("=")
            if sep and name == key:
                return value.strip().strip('"').strip("'")
        return ""

    def host(self) -> HostOs | None:
        if self._platform == "darwin":
            return HostOs.MACOS
        if self._platform.startswith("linux") and (
            self._value("ID") == "arch" or "arch" in self._value("ID_LIKE").split()
        ):
            return HostOs.ARCH
        return None

    def host_label(self) -> str:
        if self.host() == HostOs.MACOS:
            return "macOS"
        return self._value("PRETTY_NAME") or (
            "Arch Linux" if self.host() == HostOs.ARCH else self._platform
        )

    @property
    def user(self) -> str:
        return self._user

    def precondition(self) -> str | None:
        host = self.host()
        if host == HostOs.MACOS:
            if self._effective_uid == 0:
                return "run `vibey install` as your own user: Homebrew refuses to run as root"
            if self._executor.which("brew") is None:
                return HOMEBREW_REQUIRED
        elif host == HostOs.ARCH:
            if self._executor.which("pacman") is None:
                return "pacman is not on PATH; this does not look like a working Arch Linux install"
            if self._effective_uid != 0 and self._executor.which("sudo") is None:
                return "vibey install needs sudo on Arch Linux: pacman and systemctl run as root"
        else:
            return (
                f"{self.host_label()} is not a default OS for `vibey install` (Arch Linux, macOS)"
            )
        return None

    def privileged(self, argv: tuple[str, ...]) -> tuple[str, ...] | None:
        if self._effective_uid == 0:
            return argv
        return ("sudo", *argv) if self._executor.which("sudo") else None

    def is_installed(self, spec: PackageSpec) -> bool:
        if (
            any(self._executor.which(binary) for binary in spec.binaries)
            or spec.source == PackageSource.NONE
        ):
            return True
        if spec.source in (PackageSource.PACMAN, PackageSource.AUR):
            return all(
                self._executor.run(("pacman", "-Q", name), timeout=30.0).returncode == 0
                for name in spec.names
            )
        flag = "--cask" if spec.source == PackageSource.BREW_CASK else "--formula"
        return all(
            self._executor.run(("brew", "list", flag, "--versions", name), timeout=30.0).returncode
            == 0
            for name in spec.names
        )

    def ensure(self, spec: PackageSpec) -> StepOutcome:
        names = " ".join(spec.names)
        if spec.source == PackageSource.NONE:
            return StepOutcome(True, False, "nothing to install")
        if self.is_installed(spec):
            return StepOutcome(True, False, f"{names} already installed")
        if spec.source == PackageSource.PACMAN:
            argv = self.privileged(("pacman", "-S", "--needed", "--noconfirm", *spec.names))
            if argv is None:
                return StepOutcome(False, False, f"pacman needs root or sudo to install {names}")
            tool = "pacman"
        elif spec.source == PackageSource.AUR:
            if self._effective_uid == 0:
                return StepOutcome(
                    False,
                    False,
                    "AUR helpers refuse to run as root; run `vibey install` as your own user",
                )
            tool = next((name for name in ("paru", "yay") if self._executor.which(name)), "")
            if not tool:
                return StepOutcome(
                    False,
                    False,
                    f"installing {names} needs an AUR helper (paru or yay); install one, or build https://aur.archlinux.org/packages/{spec.names[0]} with makepkg",
                )
            argv = (tool, "-S", "--needed", "--noconfirm", *spec.names)
        else:
            if self._effective_uid == 0:
                return StepOutcome(
                    False,
                    False,
                    "run `vibey install` as your own user: Homebrew refuses to run as root",
                )
            if self._executor.which("brew") is None:
                return StepOutcome(False, False, HOMEBREW_REQUIRED)
            tool = "brew"
            argv = (
                ("brew", "install", "--cask", *spec.names)
                if spec.source == PackageSource.BREW_CASK
                else ("brew", "install", *spec.names)
            )
        result = self._executor.run(argv, timeout=1800.0)
        if result.returncode == 0:
            return StepOutcome(True, True, f"installed {names} with {tool}", (argv,))
        detail = next(
            (line for line in reversed(result.stderr.splitlines()) if line.strip()),
            f"exit {result.returncode}",
        )
        return StepOutcome(False, True, f"{tool} could not install {names}: {detail}", (argv,))


__all__ = [
    "CommandResult",
    "StepOutcome",
    "HOMEBREW_REQUIRED",
    "SubprocessCommandExecutor",
    "HostPackageRunner",
]
