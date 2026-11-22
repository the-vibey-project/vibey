# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The units `vibey acp` keeps running, and the hub they serve, for the bootstrap (ADR-0101).

**Trust.** Everything here reaches a service unit, a command line or a file outside the
project, so none of it comes from the folder the editor opened: `[supervisor]` is read from the
user's own `vibey.toml` (`config_path`, in their configuration folder) only; the unit's `vibey`
is the running install's own launcher (`launcher`), never a setting or a PATH lookup; the unit's
PATH is a fixed one (the launcher's folder, then the system's, `UNIT_PATH`), never the editor's;
and the environment file, the log folder and the working folders must resolve inside one of
`roots` (the user's home), or nothing is written.

**Where they run.** The hub always runs in the user's configuration folder, so `vibey serve`
reads the very `vibey.toml` `vibey acp` read its `[hub]` from (the same state folder, port and
token). The worker runs in `[acp] service_workdir`, or that folder too.

**What vibey wrote.** Every unit written, or found as vibey renders it, has the SHA-256 of its
text recorded in `<state_dir>/acp-units.json`. A unit that differs from the rendering but matches
its record is vibey's own older rendering (an upgrade, a moved install) and is replaced; one
that matches no record is the operator's edit and is kept as it is (`kept-differing`). `remove`
deletes only a unit that still matches its record, for `vibey acp unload`.

**A worker that would only crash.** `waiting("worker")` says what the environment file still
lacks (a database to reach, `VIBEY_PG_URL`); the bootstrap neither writes nor loads the worker
until it has it, so a fresh machine never gets a worker that crash-loops at every login.

**A hub someone started.** `detached_hub_pid` asks the hub's own lock, `<state_dir>/serve.lock`
(liveness is the flock, never a pid that may be reused): held means a hub runs, and its holder's
pid is said when the file names one (0 when it does not).

Declared by `application/acp/interfaces/service_units_interface.py`.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import secrets
import stat
from dataclasses import replace
from pathlib import Path
from typing import Final

from vibey.application.acp.dto import UnitOutcome
from vibey.domain.interfaces.supervisor_interface import (
    EnvFileParserInterface,
    SupervisorPlannerInterface,
)
from vibey.domain.supervisor import LABEL, WORKER, EnvFileParser, RestartPolicy
from vibey.infrastructure.hub.serve_lock import LOCK_FILE
from vibey.infrastructure.interfaces.supervisor_installer_interface import (
    SupervisorInstallerInterface,
)
from vibey.infrastructure.interfaces.supervisor_interface import (
    SupervisorHostInterface,
    SupervisorSettingsLoaderInterface,
)
from vibey.infrastructure.mcp.hub_gateway import HubStarter, default_hub_starter
from vibey.infrastructure.supervisor_installer import ENV_TEMPLATE

RESTART_POLICIES: Final[tuple[RestartPolicy, ...]] = ("always", "on-failure")
UNIT_PATH: Final = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
"""The PATH a unit runs with, after the launcher's own folder: stable across editors and
upgrades. A tool elsewhere is found by setting PATH in the environment file."""
RECORD_FILE: Final = "acp-units.json"
DATABASE_KEY: Final = "VIBEY_PG_URL"


class AcpServiceUnits:
    """Declared by `ServiceUnitsInterface`. `start_hub` and `parser` are seams."""

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
        launcher: str | None,
        roots: tuple[Path, ...],
        start_hub: HubStarter = default_hub_starter,
        parser: EnvFileParserInterface | None = None,
    ) -> None:
        self._host = host
        self._installer = installer
        self._planner = planner
        self._settings = settings
        self._config = config_path
        self._workdir = workdir
        self._state_dir = state_dir
        self._launcher = launcher
        self._roots = tuple(Path(os.path.realpath(root)) for root in roots)
        self._start_hub = start_hub
        self._parser = parser or EnvFileParser()

    # -- writing -------------------------------------------------------------------------------

    def write(self, names: tuple[str, ...], restart: str) -> tuple[UnitOutcome, ...]:
        policy = next((p for p in RESTART_POLICIES if p == restart), None)
        if policy is None:
            raise ValueError(f"[acp] restart must be always or on-failure, not {restart!r}")
        launcher = self._launcher
        if launcher is None:
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
            vibey=launcher,
            python=launcher,
        )
        home = self._config.absolute().parent
        if self._workdir:
            work = Path(self._workdir).expanduser().absolute()
            if not work.is_dir():
                raise ValueError(f"[acp] service_workdir {work} is not a folder")
        else:
            work = home
        paths = self._installer.paths(settings, home)
        for key, value in (
            ("[supervisor] env_file", paths.env_file),
            ("[supervisor] log_dir", paths.log_dir),
            ("your configuration folder", str(home)),
            ("[acp] service_workdir", str(work)),
        ):
            self._contain(key, value)
        services = tuple(
            self._planner.acp_services(
                settings,
                replace(paths, repo=str(work if name == WORKER else home)),
                names=(name,),
                restart=policy,
            )[0]
            for name in names
        )
        Path(paths.log_dir).mkdir(mode=0o700, parents=True, exist_ok=True)
        self._installer.env_file(Path(paths.env_file), ENV_TEMPLATE)
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        record = self._record()
        outcomes = self._installer.write(
            services,
            settings,
            out=None,
            overwrite=False,
            path_env=f"{os.path.dirname(launcher)}:{UNIT_PATH}",
            ours=lambda label, text: record.get(label) == self._digest(text),
        )
        for outcome in outcomes:
            if outcome.action in ("created", "updated", "unchanged"):
                record[outcome.label] = self._digest(Path(outcome.path).read_text("utf-8"))
        self._keep(record)
        return outcomes

    def waiting(self, name: str) -> str:
        if name != WORKER:
            return ""
        settings = self._settings.load(self._config)
        env_file = Path(settings.env_file or str(self._host.default_env_file())).expanduser()
        try:
            declared = self._parser.parse(env_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError):
            declared = {}
        if declared.get(DATABASE_KEY, "").strip():
            return ""
        return (
            f"set {DATABASE_KEY} in {env_file} (the worker needs a database to reach); vibey "
            "loads the worker once it is set"
        )

    def _contain(self, key: str, value: str) -> None:
        """Refuse a path that resolves outside the user's own folders (links followed)."""
        real = Path(os.path.realpath(value))
        if not any(real == root or root in real.parents for root in self._roots):
            raise ValueError(
                f"{key} {value} resolves outside your own folders, so vibey writes no unit for it"
            )

    # -- what vibey wrote ------------------------------------------------------------------------

    def recorded(self) -> tuple[str, ...]:
        return tuple(sorted(self._record()))

    def remove(self, label: str) -> UnitOutcome:
        record = self._record()
        unit = self._host.unit_path(label) if LABEL.fullmatch(label) else Path()
        if not LABEL.fullmatch(label):
            return UnitOutcome(label, "", "failed", "not a label vibey loads")
        try:
            found = os.lstat(unit)
        except FileNotFoundError:
            record.pop(label, None)
            self._keep(record)
            return UnitOutcome(label, str(unit), "absent")
        if not stat.S_ISREG(found.st_mode):
            return UnitOutcome(label, str(unit), "failed", "it is not a regular file")
        try:
            fd = os.open(unit, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            if record.get(label) != digest:
                return UnitOutcome(
                    label,
                    str(unit),
                    "kept-differing",
                    "it is not what vibey wrote (you edited it, or vibey never wrote it)",
                )
            unit.unlink()
        except OSError as exc:
            return UnitOutcome(label, str(unit), "failed", exc.strerror or str(exc))
        record.pop(label, None)
        self._keep(record)
        return UnitOutcome(label, str(unit), "removed")

    def _record(self) -> dict[str, str]:
        try:
            fd = os.open(self._state_dir / RECORD_FILE, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as handle:
                data = json.loads(handle.read(1 << 20))
        except (OSError, ValueError):
            return {}
        units = data.get("units") if isinstance(data, dict) else None
        if not isinstance(units, dict):
            return {}
        return {k: v for k, v in units.items() if isinstance(k, str) and isinstance(v, str)}

    def _keep(self, record: dict[str, str]) -> None:
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        staged = self._state_dir / f".{RECORD_FILE}.{secrets.token_hex(8)}.tmp"
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"units": dict(sorted(record.items()))}, handle)
            os.replace(staged, self._state_dir / RECORD_FILE)
        finally:
            with contextlib.suppress(FileNotFoundError):
                staged.unlink()

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # -- the hub ---------------------------------------------------------------------------------

    def label(self, name: str) -> str:
        return f"{self._settings.load(self._config).label_prefix}.{name}"

    def detached_hub_pid(self) -> int | None:
        path = self._state_dir / LOCK_FILE
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return None  # no lock file: no hub has ever run here
        try:
            try:
                # Shared and non-blocking: it never writes, and fails only while a hub holds it.
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                text = os.read(fd, 32).decode("ascii", errors="replace").strip()
                return int(text) if text.isdigit() else 0
            fcntl.flock(fd, fcntl.LOCK_UN)
            return None
        finally:
            os.close(fd)

    def start_hub(self) -> bool:
        return self._start_hub()
