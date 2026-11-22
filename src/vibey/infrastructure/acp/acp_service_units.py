# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The units `vibey acp` keeps running, and the hub they serve, for the bootstrap (ADR-0101).

**Trust (ADR-0101).** Everything here reaches a service unit, a command line or a file outside
the project, so none of it comes from the folder the editor opened: `[supervisor]` is read from
the user's own `vibey.toml` (`config_path`, in their configuration folder) only; the unit's
`vibey` is the running install's own launcher (`launcher`), never a setting or a PATH lookup; and
the environment file, the log folder and the working folder must resolve inside one of `roots`
(the user's home), or nothing is written.

`write` reads `[supervisor]` afresh, plans only the hub and the worker (`acp_services`; never the
delivery bridge or the state sync), resolves their paths with the same refusals as
`vibey supervisor install` (vibey found, nothing on volatile storage or in a linked worktree),
creates the environment file from its template when it is missing (mode 0600: the units point at
it and never carry a secret themselves) and writes each unit with `overwrite=False`, so a unit
the operator edited is kept as it is. The services run in `[acp] service_workdir`, or the folder
of `[supervisor] env_file` when that is empty.

`detached_hub_pid` reads the hub's own `serving.json` (`LocalTokenStore.serving`) and answers only
for a process that is alive: the bootstrap asks before loading the hub unit, so a hub someone
started with `vibey hub start` is neither duplicated nor stopped.

Declared by `application/acp/interfaces/service_units_interface.py`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Final

from vibey.application.acp.dto import UnitOutcome
from vibey.domain.interfaces.supervisor_interface import SupervisorPlannerInterface
from vibey.domain.supervisor import RestartPolicy
from vibey.infrastructure.hub.local_token import LocalTokenStore
from vibey.infrastructure.interfaces.supervisor_installer_interface import (
    SupervisorInstallerInterface,
)
from vibey.infrastructure.interfaces.supervisor_interface import (
    SupervisorHostInterface,
    SupervisorSettingsLoaderInterface,
)
from vibey.infrastructure.mcp.hub_gateway import HubStarter, _default_starter
from vibey.infrastructure.supervisor_installer import ENV_TEMPLATE

RESTART_POLICIES: Final[tuple[RestartPolicy, ...]] = ("always", "on-failure")


class AcpServiceUnits:
    """Declared by `ServiceUnitsInterface`. `start_hub` and `alive` are seams."""

    def __init__(
        self,
        host: SupervisorHostInterface,
        installer: SupervisorInstallerInterface,
        planner: SupervisorPlannerInterface,
        settings: SupervisorSettingsLoaderInterface,
        *,
        config_path: Path,
        workdir: str,
        state_dir: Path,
        path_env: str,
        launcher: str | None,
        roots: tuple[Path, ...],
        start_hub: HubStarter = _default_starter,
        alive: Callable[[int], bool] | None = None,
    ) -> None:
        self._host = host
        self._installer = installer
        self._planner = planner
        self._settings = settings
        self._config = config_path
        self._workdir = workdir
        self._state_dir = state_dir
        self._path_env = path_env
        self._launcher = launcher
        self._roots = tuple(Path(os.path.realpath(root)) for root in roots)
        self._start_hub = start_hub
        self._alive = alive or self.alive

    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        policy = next((p for p in RESTART_POLICIES if p == restart), None)
        if policy is None:
            raise ValueError(f"[acp] restart must be always or on-failure, not {restart!r}")
        if self._launcher is None:
            raise ValueError(
                "the running vibey has no `vibey` launcher beside its Python, so no unit can be "
                "pinned to it; install vibey-engine into an environment with its scripts"
            )
        # Only the hub and the worker: the delivery bridge and the state sync are never planned.
        # The launcher is the running install's: `[supervisor] vibey` and `python` never reach
        # a unit vibey loads on its own (no Python is planned for the hub or the worker; the
        # path rules check the launcher for both).
        settings = replace(
            self._settings.load(self._config),
            delivery=False,
            state_sync=False,
            vibey=self._launcher,
            python=self._launcher,
        )
        env_file = Path(settings.env_file or str(self._host.default_env_file())).expanduser()
        if self._workdir:
            repo = Path(self._workdir).expanduser().absolute()
            if not repo.is_dir():
                raise ValueError(f"[acp] service_workdir {repo} is not a folder")
        else:
            repo = env_file.absolute().parent
        paths = self._installer.paths(settings, repo)
        for key, value in (
            ("[supervisor] env_file", paths.env_file),
            ("[supervisor] log_dir", paths.log_dir),
            ("[acp] service_workdir", paths.repo),
        ):
            self._contain(key, value)
        services = self._planner.acp_services(settings, paths, names=names, restart=policy)
        Path(paths.log_dir).mkdir(mode=0o700, parents=True, exist_ok=True)
        self._installer.env_file(Path(paths.env_file), ENV_TEMPLATE)
        repo.mkdir(mode=0o700, parents=True, exist_ok=True)
        return self._installer.write(
            services, settings, out=None, overwrite=False, path_env=self._path_env
        )

    def _contain(self, key: str, value: str) -> None:
        """Refuse a path that resolves outside the user's own folders (links followed)."""
        real = Path(os.path.realpath(value))
        if not any(real == root or root in real.parents for root in self._roots):
            raise ValueError(
                f"{key} {value} resolves outside your own folders, so vibey writes no unit for it"
            )

    def label(self, name: str) -> str:
        return f"{self._settings.load(self._config).label_prefix}.{name}"

    def detached_hub_pid(self) -> int | None:
        try:
            record = LocalTokenStore(self._state_dir).serving()
        except (ValueError, OSError):
            return None
        if record is None or not self._alive(record.pid):
            return None
        return record.pid

    def start_hub(self) -> bool:
        return self._start_hub()

    @staticmethod
    def alive(pid: int) -> bool:
        """Whether a process with this id exists (signal 0 checks, sends nothing). A pid of 0
        or below names a process group, never one process: not alive."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # it exists; it is another user's
        return True
