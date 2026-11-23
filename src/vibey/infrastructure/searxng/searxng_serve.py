# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey searxng serve`: what the SearXNG unit runs (ADR-0102).

Before anything runs it checks, and refuses (said on standard error, the unit's log) when:

- the person stopped it for good (`vibey acp unload`, `vibey searxng uninstall`);
- the unit that runs it was loaded under another label (`--label`) than the person's
  `[supervisor] label_prefix` now gives: it is left from an earlier prefix, and running beside
  the current unit the two would remove each other's container;
- there is no record, or one vibey would not have written (every value, the image equal to the
  pinned one), or one whose label is not this SearXNG's (`label`, from the person's own config);
- `settings.yml` is not a regular file the person owns, closed to everyone else;
- the record was written for an earlier pinned image (it says how to update);
- the recorded runtime fails `ContainerRuntime.vet` (trusted folder and file checks; it need not
  be the runtime a fresh look would choose now);
- docker's current context is not this computer's own daemon (or cannot be read): a later
  `docker context use <remote>` never starts SearXNG on another machine at login, and the run is
  pinned (`DOCKER_HOST`) to the local endpoint it was checked against;
- the pinned image is not here -- it never pulls: nothing downloads when the person logs in;
- a container of its name is there that vibey did not start for this user (no owner label).

Then it removes its own container a killed run left behind and replaces itself (`execve`) with
the runtime's one command line (`SearxngPlan.run_argv`), with an environment of
`CONTAINER_VARIABLES` and a fixed PATH: never this process's database URL, tokens, keys or
`DOCKER_HOST`; for docker, `DOCKER_HOST` is the local endpoint just checked, as is every docker
call before the exec (`-H`). The service manager owns the process from then on: stopping the unit stops the
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
import shlex
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
        unit: str | None = None,
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
        self._unit = unit
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
        if self._unit is not None and self._unit != self._label():
            quoted = shlex.quote(self._unit)  # from the unit file: pasted as a command
            return self._refuse(
                EXIT_CONFIG,
                f"this unit is {self._unit}, but your [supervisor] label_prefix now makes "
                f"vibey's SearXNG unit {self._label()}: it is left from an earlier prefix, so "
                f"it runs nothing; unload it (`launchctl bootout gui/$(id -u)/{quoted}` on "
                f"macOS, `systemctl --user disable --now {quoted}` on Linux) and remove its "
                "file",
            )
        try:
            installed = self._files.read_installed()
        except ValueError:
            installed = None  # refused below, with the strict reading's own reason
        if installed is not None and not self._plan.pinned(installed.image):
            return self._refuse(
                EXIT_CONFIG,
                f"it was installed from an earlier pinned image "
                f"({self._plan.digest_of(installed.image)}), and this vibey runs only the one it "
                f"pins now; `{INSTALL_COMMAND}` (or the editor's update offer) updates it",
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
        refusal = self._runtime.vet(runtime)
        if refusal is not None:
            return self._refuse(EXIT_CONFIG, f"{refusal}; nothing was run")
        where = self._runtime.endpoint(runtime)
        if not self._runtime.is_local(where):
            said = "could not be read" if where is None else f"points at {where}"
            return self._refuse(
                EXIT_CONFIG,
                f"{PurePath(runtime).name}'s current context {said}, not this computer's own "
                "daemon, so nothing was run; switch back to a local context (`docker context "
                "use default`)",
            )
        if not self._runtime.image_present(runtime, provision.image, host=where or ""):
            return self._refuse(
                EXIT_CONFIG,
                f"the image {provision.image} is not here, and serve never downloads; "
                f"`{INSTALL_COMMAND}` does",
            )
        removed = self._runtime.remove_container(runtime, self._uid(), host=where or "")
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
        if where:
            kept["DOCKER_HOST"] = where  # pinned to the local endpoint just checked
        path = dict.fromkeys([str(PurePath(runtime).parent), *SAFE_PATH])
        self._execve(argv[0], list(argv), {**kept, "PATH": os.pathsep.join(path)})
        return 0  # reached only when `execve` is a stand-in

    def _refuse(self, code: int, why: str) -> int:
        self._say(f"vibey searxng serve: {why}")
        return code

    @staticmethod
    def _stderr(text: str) -> None:
        print(text, file=sys.stderr)
