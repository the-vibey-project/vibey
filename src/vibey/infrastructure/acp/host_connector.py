# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp`'s own `vibey connect` step: register vibey with the clients installed here.

Each client gets the entry it speaks: `vibey mcp` for the MCP clients, `vibey acp` for Zed (an
external agent server). A Zed settings file with comments is never rewritten: it is a `WARN`
carrying the snippet to paste, unless it already carries the entry.

`vibey connect` asks before it writes; this step runs under the operator's standing grant
(`[acp] auto_bootstrap` and `auto_connect`), so it is held narrower than the command:

- **User scope only.** A project-scoped client (Claude Code's `.mcp.json`, VS Code's
  `.vscode/mcp.json`) is a file in the repository the editor opened; it is never written here.
- **Inside the home folder only, after symlinks.** A target whose folder's real path (every
  symlink resolved) is not under the home folder's real path is never written (`UNKNOWN`, with
  that reason); `HostInstaller` refuses one again as it writes, and refuses a config file that
  is itself a symbolic link (a `WARN`).
- **Installed clients only.** A client counts as installed when its config folder already
  exists; the step never creates one (`UNKNOWN`, not installed here).
- **The same merge `vibey connect` makes** (`HostInstaller`): sibling servers are kept, a
  changed file is backed up to `<file>.vibey.bak` with the original's permissions, the new file
  replaces the old one atomically and no wider than it was, and a file that already carries the
  entry is left as it is, so running again changes nothing.
- **One client at a time.** A client whose file cannot be read, parsed or written is a `WARN`
  for that client, and the others still go on.

When every installed client is settled (no `WARN` but a settled one),
`<state_dir>/acp-connect-<version>.json` records which ones. A client is settled when it is
connected, or when vibey will never write it as things stand: its config folder resolves outside
the home folder, or its config file is a symbolic link (a dotfile-managed config, a `WARN` with
what to do). Such a client is recorded with that state -- the folder's real path, or where the
link points -- so it is not tried at every launch, and is tried again the moment the state
changes (SP-ACP Task 11a). The next `vibey acp` of this version skips the step only while every
client installed is in that record as it stands now: any other `WARN` is tried again, and so is
a client installed since. A marker that is missing, unreadable or malformed only means the step
runs again, which changes nothing that is already right.

Declared by `application/acp/interfaces/host_connector_interface.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from vibey.application.acp.dto import DoctorResult
from vibey.domain.host_clients import (
    HOST_CLIENT_CATALOG,
    ClientHomes,
    HostClientError,
    HostClientSpec,
)
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface


class HostConnector:
    """Declared by `application/acp/interfaces/host_connector_interface.py`."""

    def __init__(
        self,
        *,
        state_dir: Path,
        version: str,
        installer: HostInstallerInterface,
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        home_dir: Callable[[], Path] = Path.home,
        platform: str = sys.platform,
        environ: Mapping[str, str] = os.environ,
    ) -> None:
        # `installer` has no default: the one wired in (`bootstrap.acp_machine`) writes the
        # running install's own launcher, and a PATH-resolving default would be a trap.
        self._installer = installer
        self._environ = environ
        self._platform = platform
        self._catalog = catalog
        self._home_dir = home_dir
        self._state_dir = state_dir
        self._version = version
        self._marker = state_dir / f"acp-connect-{version}.json"

    async def connect_detected(self) -> tuple[DoctorResult, ...]:
        return await asyncio.to_thread(self._connect)

    def already_connected(self) -> bool:
        try:
            recorded = json.loads(self._marker.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(recorded, dict) or recorded.get("version") != self._version:
            return False
        clients = recorded.get("clients")
        settled = recorded.get("settled", {})
        if not isinstance(clients, list) or not isinstance(settled, dict):
            return False
        home = Path(os.path.realpath(self._home_dir()))
        return all(
            spec.client_id in clients
            or (
                spec.client_id in settled
                and settled[spec.client_id] == self._unwritable(self._target(spec), home)
            )
            for spec in self._installed()
        )

    def _target(self, spec: HostClientSpec) -> Path:
        """Where `spec`'s user-scope config lives on this computer."""
        return Path(
            spec.config_path(
                home_dir=str(self._home_dir()),
                project_dir="",
                platform=self._platform,
                homes=self._homes(),
            )
        )

    def _homes(self) -> ClientHomes:
        """Where the person moved clients' config (`XDG_CONFIG_HOME`, `CODEX_HOME`,
        `CLAUDE_CONFIG_DIR`, a Flatpak Zed), from this process's environment."""
        return ClientHomes.from_environ(
            self._environ,
            home_dir=str(self._home_dir()),
            platform=self._platform,
            is_dir=os.path.isdir,
        )

    @staticmethod
    def _unwritable(target: Path, home: Path) -> str | None:
        """Why vibey will never write `target` as things stand, as a state that changes when
        the reason does: its folder's real path outside the home folder, or the link the file
        is. None when it may be written."""
        folder = Path(os.path.realpath(target.parent))
        if not folder.is_relative_to(home):
            return f"outside:{folder}"
        try:
            return f"link:{os.readlink(target)}" if target.is_symlink() else None
        except OSError:
            return None

    def _installed(self) -> list[HostClientSpec]:
        """The user-scope clients whose config folder exists here now."""
        return [
            spec
            for spec in self._catalog.all()
            if spec.scope == "user" and self._folder_exists(self._target(spec).parent)
        ]

    @staticmethod
    def _folder_exists(folder: Path) -> bool:
        """Whether the folder is there; one that cannot be looked into counts as absent."""
        try:
            return folder.is_dir()
        except OSError:
            return False

    def _connect(self) -> tuple[DoctorResult, ...]:
        home = Path(os.path.realpath(self._home_dir()))
        results: list[DoctorResult] = []
        connected: list[str] = []
        settled: dict[str, str] = {}
        unsettled = False
        for spec in self._catalog.all():
            if spec.scope != "user":
                continue
            result = self._one(spec, home)
            results.append(result)
            state = self._unwritable(self._target(spec), home)
            if result.mark == "PASS":
                connected.append(spec.client_id)
            elif state is not None:
                settled[spec.client_id] = state
            elif result.mark == "WARN":
                unsettled = True
        if unsettled:
            return tuple(results)  # not recorded: the next vibey acp tries again
        try:
            self._record(connected, settled)
        except OSError as exc:
            results.append(
                DoctorResult(
                    "WARN",
                    "connect-marker",
                    f"could not record the connection in {self._marker} ({exc}); the next "
                    "vibey acp connects again, which changes nothing that is already right",
                )
            )
        return tuple(results)

    def _one(self, spec: HostClientSpec, home: Path) -> DoctorResult:
        client_id = spec.client_id
        folder = Path(
            spec.config_path(
                home_dir=str(self._home_dir()),
                project_dir="",
                platform=self._platform,
                homes=self._homes(),
            )
        ).parent
        if not self._folder_exists(folder):
            return DoctorResult("UNKNOWN", client_id, f"not installed here ({folder} is not there)")
        try:
            plan = self._installer.build_plan([client_id])
            item = plan[0]
            target = Path(item.target_path)
            if not self._folder_exists(target.parent):
                return DoctorResult(
                    "UNKNOWN", client_id, f"not installed here ({target.parent} does not exist)"
                )
            if not Path(os.path.realpath(target.parent)).is_relative_to(home):
                return DoctorResult(
                    "UNKNOWN", client_id, f"not written: {target} is not inside your home folder"
                )
            if item.action == "unchanged":
                return DoctorResult("PASS", client_id, f"already connected in {target}")
            if target.is_symlink():
                return DoctorResult(
                    "WARN",
                    client_id,
                    f"not connected: {target} is a symbolic link (a dotfile-managed config?) and "
                    "vibey never writes through one; add vibey's entry by hand in the file it "
                    "points to",
                )
            self._installer.apply_plan(plan)
        except (HostClientError, OSError, ValueError, RecursionError) as exc:
            return DoctorResult("WARN", client_id, f"not connected: {exc}")
        backup = f" (the old file is in {item.backup_path})" if item.backup_path else ""
        return DoctorResult("PASS", client_id, f"{item.action}d {target}{backup}")

    def _record(self, connected: list[str], settled: dict[str, str]) -> None:
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        staged = self._marker.with_name(f"{self._marker.name}.tmp")
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"version": self._version, "clients": connected, "settled": settled}, handle)
        os.replace(staged, self._marker)
