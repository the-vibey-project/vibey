# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp`'s own `vibey connect` step: register `vibey mcp` with the clients installed here.

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

When every installed client is connected (no `WARN`), `<state_dir>/acp-connect-<version>.json`
records which ones. The next `vibey acp` of this version skips the step only while the clients
installed then are all in that record: a `WARN` is tried again, and so is a client installed
since. A marker that is missing, unreadable or malformed only means the step runs again, which
changes nothing that is already right.

Declared by `application/acp/interfaces/host_connector_interface.py`.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path

from vibey.application.acp.dto import DoctorResult
from vibey.domain.host_clients import HOST_CLIENT_CATALOG, HostClientError
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.host_installer import HOST_INSTALLER
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface


class HostConnector:
    """Declared by `application/acp/interfaces/host_connector_interface.py`."""

    def __init__(
        self,
        *,
        state_dir: Path,
        version: str,
        installer: HostInstallerInterface = HOST_INSTALLER,
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        home_dir: Callable[[], Path] = Path.home,
        platform: str = sys.platform,
    ) -> None:
        self._installer = installer
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
        if not isinstance(clients, list):
            return False
        return set(self._installed()) <= set(clients)

    def _installed(self) -> list[str]:
        """The user-scope clients whose config folder exists here now."""
        home = str(self._home_dir())
        return [
            spec.client_id
            for spec in self._catalog.all()
            if spec.scope == "user"
            and Path(
                spec.config_path(home_dir=home, project_dir="", platform=self._platform)
            ).parent.is_dir()
        ]

    def _connect(self) -> tuple[DoctorResult, ...]:
        home = Path(os.path.realpath(self._home_dir()))
        results: list[DoctorResult] = []
        connected: list[str] = []
        for spec in self._catalog.all():
            if spec.scope != "user":
                continue
            result = self._one(spec.client_id, home)
            results.append(result)
            if result.mark == "PASS":
                connected.append(spec.client_id)
        if any(result.mark == "WARN" for result in results):
            return tuple(results)  # not recorded: the next vibey acp tries again
        try:
            self._record(connected)
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

    def _one(self, client_id: str, home: Path) -> DoctorResult:
        try:
            plan = self._installer.build_plan([client_id])
            item = plan[0]
            target = Path(item.target_path)
            if not target.parent.is_dir():
                return DoctorResult(
                    "UNKNOWN", client_id, f"not installed here ({target.parent} does not exist)"
                )
            if not Path(os.path.realpath(target.parent)).is_relative_to(home):
                return DoctorResult(
                    "UNKNOWN", client_id, f"not written: {target} is not inside your home folder"
                )
            if item.action == "unchanged":
                return DoctorResult("PASS", client_id, f"already connected in {target}")
            self._installer.apply_plan(plan)
        except (HostClientError, OSError, UnicodeDecodeError) as exc:
            return DoctorResult("WARN", client_id, f"not connected: {exc}")
        backup = f" (the old file is in {item.backup_path})" if item.backup_path else ""
        return DoctorResult("PASS", client_id, f"{item.action}d {target}{backup}")

    def _record(self, connected: list[str]) -> None:
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        staged = self._marker.with_name(f"{self._marker.name}.tmp")
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"version": self._version, "clients": connected}, handle)
        os.replace(staged, self._marker)
