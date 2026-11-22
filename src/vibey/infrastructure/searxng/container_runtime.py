# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The container runtime vibey drives for its SearXNG: podman, else docker (ADR-0102).

- **Found once, never installed.** `find` asks the PATH this process started with for `podman`,
  then `docker`, once, and keeps an absolute path only (a relative PATH entry is never a
  runtime). With neither, vibey says how to install one and does nothing else.
- **Fixed argv only.** Every command is built by `SearxngPlan` (pull, inspect, remove), which
  refuses a runtime that is not podman or docker by absolute path and an image that is not
  SearXNG's by digest, before any command runs.
- **The ACP runner.** Each command runs through `AcpCommandRunner`: no shell, stdin closed, its
  own process group stopped as a whole past its bound, output captured, and an environment of
  `CONTAINER_VARIABLES` alone -- what a runtime finds its daemon or machine by, never a database
  URL, a token or a key. A pull is bounded by `[acp] install_timeout_seconds`, everything else by
  `bootstrap_timeout_seconds`.

What a runtime says is the machine's, not vibey's: a failure's detail is its last line, cleaned
of terminal control and cut, and the caller passes it through its own untrusted-text cleaner.

Declared by `interfaces/container_runtime_interface.py`.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePath
from typing import Final

from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import RUNTIMES, SearxngPlan
from vibey.infrastructure.acp.acp_command_runner import KEPT_VARIABLES
from vibey.infrastructure.acp.interfaces.acp_command_runner_interface import (
    AcpCommandRunnerInterface,
)
from vibey.infrastructure.postgres import PostgresCommandResult
from vibey.infrastructure.web.untrusted_text import UntrustedText

CONTAINER_VARIABLES: Final = (
    *KEPT_VARIABLES,
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
    "CONTAINER_HOST",
    "CONTAINER_CONNECTION",
)
"""The variables a runtime finds its daemon, rootless runtime folder or podman machine by: the
only ones of this process's environment it sees."""
ABSENT: Final = ("no such container", "no such image", "image not known")
"""What a runtime says when there was nothing to remove: removed already, not a failure."""
_DETAIL_LIMIT: Final = 300


@dataclass(frozen=True, slots=True)
class RuntimeOutcome:
    """How one runtime command ended. A value type."""

    ok: bool
    detail: str = ""
    still_running: bool = False


class ContainerRuntime:
    """Declared by `ContainerRuntimeInterface`. `which` and `path` are the lookup's seams."""

    def __init__(
        self,
        *,
        runner: AcpCommandRunnerInterface,
        pull_runner: AcpCommandRunnerInterface,
        plan: SearxngPlanInterface | None = None,
        which: Callable[..., str | None] = shutil.which,
        path: str | None = None,
    ) -> None:
        self._runner = runner
        self._pull_runner = pull_runner
        self._plan = plan or SearxngPlan()
        self._which = which
        self._path = path if path is not None else os.environ.get("PATH", os.defpath)
        self._found: tuple[str | None] | None = None

    def find(self) -> str | None:
        if self._found is None:
            self._found = (self._lookup(),)
        return self._found[0]

    def _lookup(self) -> str | None:
        for name in RUNTIMES:
            found = self._which(name, path=self._path)
            if found and PurePath(found).is_absolute():
                return str(found)
        return None

    def image_present(self, runtime: str, image: str) -> bool:
        return self._runner(self._plan.image_argv(runtime, image)).returncode == 0

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        argv = self._plan.pull_argv(runtime, image)
        return self._outcome(argv, self._pull_runner(argv), self._pull_runner)

    def remove_container(self, runtime: str) -> RuntimeOutcome:
        argv = self._plan.remove_argv(runtime)
        return self._outcome(argv, self._runner(argv), self._runner, absent_ok=True)

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        argv = self._plan.remove_image_argv(runtime, image)
        return self._outcome(argv, self._runner(argv), self._runner, absent_ok=True)

    @staticmethod
    def _outcome(
        argv: tuple[str, ...],
        result: PostgresCommandResult,
        runner: AcpCommandRunnerInterface,
        *,
        absent_ok: bool = False,
    ) -> RuntimeOutcome:
        if result.returncode == 0:
            return RuntimeOutcome(ok=True)
        said = result.stderr.lower()
        if absent_ok and any(phrase in said for phrase in ABSENT):
            return RuntimeOutcome(ok=True, detail="nothing to remove")
        lines = [
            line
            for line in (UntrustedText.clean(raw).strip() for raw in result.stderr.splitlines())
            if line
        ]
        name = PurePath(argv[0]).name
        detail = lines[-1][:_DETAIL_LIMIT] if lines else f"{name} exited {result.returncode}"
        return RuntimeOutcome(ok=False, detail=detail, still_running=runner.still_running(result))
