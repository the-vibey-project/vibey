# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adamsteinberger)).
"""Local Ollama discovery and installation."""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - fixed argv, never shell=True
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from vibey.domain.local_stack import DEFAULT_LOCAL_MODEL, PackageSpec
from vibey.infrastructure.host_packages import HostPackageRunner
from vibey.infrastructure.interfaces.ollama_interface import OllamaLocalServiceInterface

OLLAMA_HOST: Final = "http://127.0.0.1:11434"
OLLAMA_VERSION_PATH: Final = "/api/version"
OLLAMA_TAGS_PATH: Final = "/api/tags"


@dataclass(frozen=True, slots=True)
class OllamaStatus:
    installed: bool
    running: bool
    model_present: bool
    detail: str

    @property
    def ready(self) -> bool:
        return self.installed and self.running and self.model_present


@dataclass(frozen=True, slots=True)
class OllamaInstallResult:
    ok: bool
    changed: bool
    detail: str
    status: OllamaStatus


@dataclass(frozen=True, slots=True)
class OllamaCommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class OllamaLocalService(OllamaLocalServiceInterface):
    """Install, start and probe Ollama through injectable process/HTTP seams."""

    def __init__(
        self,
        *,
        runner: HostPackageRunner | None = None,
        command_runner: Callable[[tuple[str, ...]], OllamaCommandResult] | None = None,
        opener: Callable[..., Any] | None = None,
        platform: str | None = None,
    ) -> None:
        self._runner = runner or HostPackageRunner.for_this_host(_DefaultExecutor())
        self._run = command_runner or _run_command
        self._open = opener or urllib.request.urlopen
        self._platform = platform or sys.platform

    def status(self, model: str | None = None) -> OllamaStatus:
        chosen = model or DEFAULT_LOCAL_MODEL
        installed = self._runner.is_installed(self._package_spec())
        if not installed:
            return OllamaStatus(False, False, False, "Ollama is not installed")
        if not self._is_running():
            return OllamaStatus(True, False, False, "Ollama is installed but stopped")
        present = self._model_present(chosen)
        detail = (
            f"Ollama is running and model {chosen} is present"
            if present
            else f"Ollama is running but model {chosen} is not present"
        )
        return OllamaStatus(True, True, present, detail)

    def install(
        self, *, model: str = DEFAULT_LOCAL_MODEL, confirm: bool = True, pull: bool = True
    ) -> OllamaInstallResult:
        del confirm  # confirmation belongs to the CLI boundary
        before = self.status(model)
        if before.ready or (before.running and not pull):
            return OllamaInstallResult(
                True, False, f"{before.detail}; no installation was needed", before
            )
        recipe = self._package_spec()
        package = self._runner.ensure(recipe)
        changed = package.changed
        if not package.ok:
            return OllamaInstallResult(False, changed, package.detail, self.status(model))
        start = self._start()
        changed = changed or start.returncode == 0
        if start.returncode != 0:
            return OllamaInstallResult(
                False, changed, "Ollama was installed but could not start", self.status(model)
            )
        if not self._is_running():
            return OllamaInstallResult(
                False, changed, "Ollama did not answer its version endpoint", self.status(model)
            )
        if not pull or self._model_present(model):
            after = self.status(model)
            return OllamaInstallResult(True, changed, after.detail, after)
        pull_result = self._run(("ollama", "pull", model))
        changed = True
        after = self.status(model)
        if pull_result.returncode != 0:
            return OllamaInstallResult(
                False, changed, pull_result.stderr or "Ollama model pull failed", after
            )
        return OllamaInstallResult(True, changed, f"pulled {model}; {after.detail}", after)

    def _package_spec(self) -> PackageSpec:
        from vibey.domain.local_stack import PackageSource

        return PackageSpec(
            PackageSource.BREW_FORMULA if self._platform == "darwin" else PackageSource.PACMAN,
            ("ollama",),
            ("ollama",),
        )

    def _start(self) -> OllamaCommandResult:
        if self._platform == "darwin":
            return self._run(("brew", "services", "start", "ollama"))
        command = self._runner.privileged(("systemctl", "enable", "--now", "ollama"))
        if command is None:
            return OllamaCommandResult(1, stderr="systemctl needs root or sudo")
        return self._run(command)

    def _is_running(self) -> bool:
        try:
            with self._open(OLLAMA_HOST + OLLAMA_VERSION_PATH, timeout=3) as response:
                return getattr(response, "status", 200) == 200
        except (OSError, urllib.error.URLError, TimeoutError):
            return False

    def _model_present(self, model: str) -> bool:
        try:
            with self._open(OLLAMA_HOST + OLLAMA_TAGS_PATH, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError, TimeoutError):
            return False
        return any(item.get("name") == model for item in payload.get("models", []))


class _DefaultExecutor:
    def run(self, argv: tuple[str, ...], *, timeout: float = 600.0) -> OllamaCommandResult:
        return _run_command(argv, timeout=timeout)

    def which(self, name: str) -> str | None:
        return shutil.which(name)


def _run_command(argv: tuple[str, ...], *, timeout: float = 600.0) -> OllamaCommandResult:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return OllamaCommandResult(1, stderr=str(exc))
    return OllamaCommandResult(result.returncode, result.stdout, result.stderr)


__all__ = [
    "OLLAMA_HOST",
    "OLLAMA_TAGS_PATH",
    "OLLAMA_VERSION_PATH",
    "OllamaCommandResult",
    "OllamaInstallResult",
    "OllamaLocalService",
    "OllamaStatus",
]
