# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey searxng serve`: what the SearXNG unit runs (ADR-0102).

Before anything runs it checks, and refuses (said on standard error, the unit's log) when:

- the person stopped it for good (`vibey acp unload`, `vibey searxng uninstall`);
- there is no record, or one vibey would not have written (every value, the image equal to the
  pinned one), or one whose label is not this SearXNG's (`label`, from the person's own config);
- `settings.yml` is not a regular file the person owns, closed to everyone else;
- the recorded runtime fails `ContainerRuntime.vet` (trusted folder, file checks, the one a fresh
  look finds);
- the pinned image is not here -- it never pulls: nothing downloads when the person logs in;
- a container of its name is there that vibey did not start for this user (no owner label).

Then it removes its own container a killed run left behind and replaces itself (`execve`) with
the runtime's one command line (`SearxngPlan.run_argv`), with an environment of
`CONTAINER_VARIABLES` and a fixed PATH: never this process's database URL, tokens, keys or a
`DOCKER_HOST`. The service manager owns the process from then on: stopping the unit stops the
runtime, which stops and removes the container (`--rm`).

Exit codes: 78 (EX_CONFIG) for every refusal that can only change when the person acts -- the
unit's throttle (launchd `ThrottleInterval`, systemd's start limit) spaces its restarts, and
`vibey doctor` and `vibey searxng status` say why -- and 1 for a runtime that would not remove
the old container (it may answer next time). Nothing raises: a value `run_argv` refuses (running
as root) is a 78 too.

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
from vibey.infrastructure.web.untrusted_text import UntrustedText

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
        label: Callable[[], str],
        plan: SearxngPlanInterface | None = None,
        execve: Execve = os.execve,
        environ: Mapping[str, str] = os.environ,
        uid: Callable[[], int] = os.getuid,
        gid: Callable[[], int] = os.getgid,
        say: Callable[[str], object] | None = None,
    ) -> None:
        self._files = files
        self._runtime = runtime
        self._label = label
        self._plan = plan or SearxngPlan()
        self._execve = execve
        self._environ = environ
        self._uid = uid
        self._gid = gid
        self._say = say or self._stderr

    def run(self) -> int:
        try:
            return self._run()
        except ValueError as exc:
            return self._refuse(EXIT_CONFIG, UntrustedText.clean(str(exc)))

    def _run(self) -> int:
        if self._files.disabled():
            return self._refuse(
                EXIT_CONFIG,
                f"it was stopped for good (vibey acp unload, or uninstall); `{INSTALL_COMMAND}` "
                "starts it again",
            )
        try:
            provision = self._files.read()
        except ValueError as exc:
            return self._refuse(EXIT_CONFIG, f"the provision record is not one vibey wrote: {exc}")
        if provision is None:
            return self._refuse(
                EXIT_CONFIG, f"vibey has installed no SearXNG here; `{INSTALL_COMMAND}` does"
            )
        if provision.label != self._label():
            return self._refuse(
                EXIT_CONFIG,
                f"the record names another unit's label; `{INSTALL_COMMAND}` writes it again",
            )
        if not self._files.settings_ready():
            return self._refuse(
                EXIT_CONFIG,
                f"{self._files.settings_path} is missing, not a file, or not yours alone; "
                f"`{INSTALL_COMMAND}` writes it again",
            )
        runtime = provision.runtime
        problem = self._runtime.vet(runtime)
        if problem:
            return self._refuse(EXIT_CONFIG, f"{problem}; nothing was run")
        if not self._runtime.image_present(runtime, provision.image):
            return self._refuse(
                EXIT_CONFIG,
                f"the image {provision.image} is not here, and serve never downloads; "
                f"`{INSTALL_COMMAND}` does",
            )
        removed = self._runtime.remove_container(runtime, self._uid())
        if not removed.ok:
            foreign = "vibey did not start" in removed.detail
            return self._refuse(
                EXIT_CONFIG if foreign else 1,
                f"the old container could not be removed: {removed.detail}",
            )
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
