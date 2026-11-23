# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The container runtime vibey drives for its SearXNG: podman, else docker (ADR-0102).

- **Found in trusted folders only, never installed.** `find` looks for `podman`, then `docker`,
  in `TRUSTED_RUNTIME_DIRS` for this platform, once -- never on the PATH, which an editor may have
  taken from a project. A candidate must be a regular executable file, writable by nobody but its
  owner (neither its group nor anyone else; SP-ACP Task 11a), owned by root or the person, and
  any link must lead into `TRUSTED_RUNTIME_ROOTS`. With neither, vibey says how to install one
  and does nothing else.
- **Every use vets it again.** `vet(runtime)` refuses a runtime (a recorded one, say) that fails
  those checks, and every command here vets the runtime it is handed before anything runs: a
  changed `provision.json` cannot make vibey run a binary outside the trusted folders. It does not
  require the runtime `find` would choose now: that only picks the runtime at install, so a second
  runtime installed later never stops the recorded one.
- **A container is removed only when it is vibey's.** Before `rm -f`, its labels are read: only a
  container carrying `vibey.searxng.owner=<this uid>` is removed. One of that name without it is
  left alone and said.
- **Fixed argv only.** Every command is built by `SearxngPlan` (pull, inspect, remove), which
  refuses a runtime that is not podman or docker by absolute path and an image that is not
  SearXNG's by digest, before any command runs.
- **The ACP runner.** Each command runs through `AcpCommandRunner`: no shell, stdin closed, its
  own process group stopped as a whole past its bound, output captured, and an environment of
  `CONTAINER_VARIABLES` alone, the same the unit runs with -- never a database URL, a token or a
  key, and never `DOCKER_HOST`, `DOCKER_CONTEXT`, `DOCKER_CONFIG`, `CONTAINER_HOST` or
  `CONTAINER_CONNECTION`, which a login unit does not have: install and the unit always talk to the
  runtime's own default, local daemon. A pull is bounded by `[acp] install_timeout_seconds`, everything else by
  `bootstrap_timeout_seconds`.

What a runtime says is the machine's, not vibey's: a failure's detail is its last line, cleaned
of terminal control and cut, and the caller passes it through its own untrusted-text cleaner.

Declared by `interfaces/container_runtime_interface.py`.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePath
from typing import Final

from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import (
    OWNER_LABEL,
    RUNTIMES,
    TRUSTED_RUNTIME_DIRS,
    TRUSTED_RUNTIME_ROOTS,
    SearxngPlan,
)
from vibey.infrastructure.acp.acp_command_runner import KEPT_VARIABLES
from vibey.infrastructure.acp.interfaces.acp_command_runner_interface import (
    AcpCommandRunnerInterface,
)
from vibey.infrastructure.postgres import PostgresCommandResult
from vibey.infrastructure.web.untrusted_text import UntrustedText

CONTAINER_VARIABLES: Final = (*KEPT_VARIABLES, "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS")
"""The only variables of this process's environment a runtime sees, at install and in the unit
alike: home, user, locale, the temporary folder, and the rootless runtime's folder and bus."""
DAEMON_VARIABLES: Final = (
    "DOCKER_HOST",
    "CONTAINER_HOST",
    "DOCKER_CONTEXT",
    "CONTAINER_CONNECTION",
    "DOCKER_CONFIG",
)
"""What would point a runtime at another daemon. Never passed on: a login unit has none of them."""
ABSENT: Final = ("no such container", "no such image", "image not known", "no such object")
"""What a runtime says when there was nothing to remove: removed already, not a failure."""
_DETAIL_LIMIT: Final = 300


@dataclass(frozen=True, slots=True)
class RuntimeOutcome:
    """How one runtime command ended. A value type."""

    ok: bool
    detail: str = ""
    still_running: bool = False


class ContainerRuntime:
    """Declared by `ContainerRuntimeInterface`. `platform`, `dirs`, `roots` and `uid` are seams."""

    def __init__(
        self,
        *,
        runner: AcpCommandRunnerInterface,
        pull_runner: AcpCommandRunnerInterface,
        plan: SearxngPlanInterface | None = None,
        platform: str = sys.platform,
        dirs: tuple[str, ...] | None = None,
        roots: tuple[str, ...] | None = None,
        uid: Callable[[], int] = os.getuid,
    ) -> None:
        system = "darwin" if platform == "darwin" else "linux"
        self._runner = runner
        self._pull_runner = pull_runner
        self._dirs = dirs if dirs is not None else TRUSTED_RUNTIME_DIRS[system]
        self._plan = plan or SearxngPlan(runtime_dirs=dirs)
        self._roots = roots if roots is not None else TRUSTED_RUNTIME_ROOTS[system]
        self._uid = uid
        self._found: tuple[str | None] | None = None

    def find(self) -> str | None:
        if self._found is None:
            self._found = (self._lookup(),)
        return self._found[0]

    def vet(self, runtime: str) -> str:
        # The trust checks alone. A runtime installed later ahead of the recorded one (podman
        # beside Docker Desktop, a Homebrew docker CLI) passes the same checks and must not stop
        # serve, uninstall or purge: `find` only chooses the runtime at install.
        problem = self._problem(runtime)
        return f"{runtime} {problem}" if problem else ""

    def _lookup(self) -> str | None:
        for name in RUNTIMES:
            for folder in self._dirs:
                candidate = f"{folder}/{name}"
                if os.path.lexists(candidate) and not self._problem(candidate):
                    return candidate
        return None

    def _problem(self, path: str) -> str:
        """Why `path` may not be run as a runtime, or ""."""
        folder, _, name = path.rpartition("/")
        if folder not in self._dirs or name not in RUNTIMES:
            return "is not podman or docker in one of vibey's trusted folders"
        real = os.path.realpath(path)
        if not any(real.startswith(root) for root in self._roots):
            return "leads outside vibey's trusted folders"
        try:
            found = os.stat(real)
        except OSError:
            return "is not there"
        if not stat.S_ISREG(found.st_mode) or not os.access(real, os.X_OK):
            return "is not an executable file"
        if found.st_mode & 0o022:
            # Writable by its group too is writable by someone other than its owner.
            return "is writable by anyone but its owner"
        if found.st_uid not in (0, self._uid()):
            return "belongs to someone else"
        return ""

    def _checked(self, runtime: str) -> str:
        problem = self.vet(runtime)
        if problem:
            raise ValueError(UntrustedText.clean(problem))
        return runtime

    def image_present(self, runtime: str, image: str) -> bool:
        argv = self._plan.image_argv(self._checked(runtime), image)
        return self._runner(argv).returncode == 0

    def pull(self, runtime: str, image: str) -> RuntimeOutcome:
        argv = self._plan.pull_argv(self._checked(runtime), image)
        return self._outcome(argv, self._pull_runner(argv), self._pull_runner)

    def remove_container(self, runtime: str, uid: int) -> RuntimeOutcome:
        probe = self._plan.labels_argv(self._checked(runtime), uid)
        found = self._runner(probe)
        if found.returncode != 0:
            return self._outcome(probe, found, self._runner, absent_ok=True)
        name = self._plan.container_name(uid)
        try:
            labels = json.loads(found.stdout or "null")
        except (ValueError, RecursionError):
            labels = None
        if not isinstance(labels, dict) or labels.get(OWNER_LABEL) != str(uid):
            return RuntimeOutcome(
                ok=False,
                detail=(
                    f"a container named {name} is there that vibey did not start for you (it "
                    f"has no {OWNER_LABEL}={uid} label); vibey leaves it, so remove or rename it "
                    "yourself"
                ),
            )
        argv = self._plan.remove_argv(runtime, uid)
        return self._outcome(argv, self._runner(argv), self._runner, absent_ok=True)

    def remove_image(self, runtime: str, image: str) -> RuntimeOutcome:
        argv = self._plan.remove_image_argv(self._checked(runtime), image)
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
