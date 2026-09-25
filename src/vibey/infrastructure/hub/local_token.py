# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The host's own key to the hub, and the file that says where a running hub listens.

**The local token.** A process on the host -- the CLI, the VS Code extension, the desktop
app -- reaches the hub with `Authorization: Bearer <token>`, where the token is the
content of `<state_dir>/token`. The file is created on first run with 32 random bytes,
mode 0600 in a 0700 directory, so only the account that runs vibey can read it: holding
it proves the caller is that account, which is exactly who may already run every
`vibey` command. It grants the host principal every scope, and nothing that
`NEVER_FROM_THE_HUB` names, since no route offers those at all. A device on the network
never sees it; devices pair instead (ADR-0067).

**The runtime file.** `<state_dir>/serving.json` records the address and port a running
hub is bound to and its process id, so `vibey doctor` can say whether a running hub's
exposure is declared. It is removed when the hub stops cleanly; a stale one (no such
process) is reported as stale, never as a running hub.
"""

import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Final

TOKEN_FILE: Final = "token"
RUNTIME_FILE: Final = "serving.json"
TOKEN_BYTES: Final = 32


@dataclass(frozen=True, slots=True)
class ServingRecord:
    """Where a hub said it was listening, and which process said so."""

    host: str
    port: int
    pid: int


class LocalTokenStore:
    """Reads, or creates, the host's hub token and the runtime record.

    Declared by `interfaces/local_token_interface.py::LocalTokenStoreInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._dir = state_dir

    def token(self) -> str:
        """The token, created (0600) on first call. An existing file that is readable by
        anyone but its owner is refused rather than trusted."""
        path = self._dir / TOKEN_FILE
        self._ensure_dir()
        if not path.exists():
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as handle:
                handle.write(secrets.token_urlsafe(TOKEN_BYTES))
        if path.stat().st_mode & 0o077:
            raise PermissionError(f"{path} is readable by other accounts; refusing to use it")
        return path.read_text().strip()

    def record_serving(self, record: ServingRecord) -> None:
        """Writes the runtime record, replacing any earlier one."""
        self._ensure_dir()
        target = self._dir / RUNTIME_FILE
        staged = target.with_suffix(".tmp")
        staged.write_text(json.dumps({"host": record.host, "port": record.port, "pid": record.pid}))
        staged.chmod(0o600)
        staged.replace(target)

    def clear_serving(self) -> None:
        """Removes the runtime record; nothing when there is none."""
        (self._dir / RUNTIME_FILE).unlink(missing_ok=True)

    def serving(self) -> ServingRecord | None:
        """The runtime record, or `None` when there is none. A malformed record raises
        `ValueError`: it is not the same fact as no record."""
        path = self._dir / RUNTIME_FILE
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            return None
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a JSON object")
        host, port, pid = data.get("host"), data.get("port"), data.get("pid")
        if not isinstance(host, str) or not isinstance(port, int) or not isinstance(pid, int):
            raise ValueError(f"{path} does not name a host, port and pid")
        return ServingRecord(host=host, port=port, pid=pid)

    def _ensure_dir(self) -> None:
        self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)
