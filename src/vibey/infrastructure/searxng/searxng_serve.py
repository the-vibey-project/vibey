# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey searxng serve`: what the SearXNG unit runs (ADR-0102).

It reads the person's provision record and checks every value in it (`SearxngPlan.parse`), checks
the settings file is a regular file, checks the pinned image is already here -- it never pulls:
nothing downloads when the person logs in -- removes a container a killed run left behind (same
fixed name), then replaces itself (`execve`) with the runtime's one command line
(`SearxngPlan.run_argv`). The runtime gets an environment of `CONTAINER_VARIABLES` and a fixed
PATH, never this process's database URL, tokens or keys. The service manager owns the process
from then on: stopping the unit stops the runtime, which stops and removes the container (`--rm`).

A refusal is said on standard error (the unit's log) and returns an exit code: 78 (EX_CONFIG)
for nothing installed or a record vibey would not have written, 1 for a missing image or a
runtime that would not remove the old container.

Declared by `interfaces/searxng_serve_interface.py`.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from pathlib import PurePath
from typing import Final

from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import SearxngPlan
from vibey.infrastructure.acp.acp_command_runner import SAFE_PATH
from vibey.infrastructure.searxng.container_runtime import CONTAINER_VARIABLES
from vibey.infrastructure.searxng.interfaces.container_runtime_interface import (
    ContainerRuntimeInterface,
)
from vibey.infrastructure.searxng.interfaces.searxng_files_interface import SearxngFilesInterface

EXIT_CONFIG: Final = 78
INSTALL_COMMAND: Final = "vibey searxng install"

type Execve = Callable[[str, list[str], Mapping[str, str]], object]


class SearxngServe:
    """Declared by `SearxngServeInterface`. `execve`, `uid`, `gid` and `say` are seams."""

    def __init__(
        self,
        files: SearxngFilesInterface,
        runtime: ContainerRuntimeInterface,
        *,
        plan: SearxngPlanInterface | None = None,
        execve: Execve = os.execve,
        environ: Mapping[str, str] = os.environ,
        uid: Callable[[], int] = os.getuid,
        gid: Callable[[], int] = os.getgid,
        say: Callable[[str], object] | None = None,
    ) -> None:
        self._files = files
        self._runtime = runtime
        self._plan = plan or SearxngPlan()
        self._execve = execve
        self._environ = environ
        self._uid = uid
        self._gid = gid
        self._say = say or self._stderr

    def run(self) -> int:
        try:
            provision = self._files.read()
        except ValueError as exc:
            return self._refuse(EXIT_CONFIG, f"the provision record is not one vibey wrote: {exc}")
        if provision is None:
            return self._refuse(
                EXIT_CONFIG, f"vibey has installed no SearXNG here; `{INSTALL_COMMAND}` does"
            )
        if not self._files.settings_ready():
            return self._refuse(
                EXIT_CONFIG,
                f"{self._files.settings_path} is missing or not a file; `{INSTALL_COMMAND}` "
                "writes it again",
            )
        runtime = provision.runtime
        if not (os.path.isfile(runtime) and os.access(runtime, os.X_OK)):
            return self._refuse(
                EXIT_CONFIG,
                f"{runtime} is gone; install podman or docker again, then `{INSTALL_COMMAND}`",
            )
        if not self._runtime.image_present(runtime, provision.image):
            return self._refuse(
                1,
                f"the image {provision.image} is not here, and serve never downloads; "
                f"`{INSTALL_COMMAND}` does",
            )
        removed = self._runtime.remove_container(runtime)
        if not removed.ok:
            return self._refuse(1, f"the old container could not be removed: {removed.detail}")
        argv = self._plan.run_argv(
            provision,
            settings_path=str(self._files.settings_path),
            uid=self._uid(),
            gid=self._gid(),
        )
        kept = {key: self._environ[key] for key in CONTAINER_VARIABLES if key in self._environ}
        path = dict.fromkeys([str(PurePath(runtime).parent), *SAFE_PATH])
        self._execve(argv[0], list(argv), {**kept, "PATH": os.pathsep.join(path)})
        return 0  # reached only when `execve` is a stand-in

    def _refuse(self, code: int, why: str) -> int:
        self._say(f"vibey searxng serve: {why}")
        return code

    @staticmethod
    def _stderr(text: str) -> None:
        print(text, file=sys.stderr)
