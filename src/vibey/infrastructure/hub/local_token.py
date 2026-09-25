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
    tls: bool = False
    """Whether the hub serves its own certificate (a declared LAN) rather than plain HTTP."""


class LocalTokenStore:
    """Reads, or creates, the host's hub token and the runtime record.

    Declared by `interfaces/local_token_interface.py::LocalTokenStoreInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._dir = state_dir

    def token(self) -> str:
        """The token, created (0600) on first call. The file is opened without following
        a symlink and checked on the open descriptor: owned by this account and readable
        by no other, or it is refused rather than trusted -- whoever could plant it would
        know the host's key (security review of #1155)."""
        self._ensure_dir()
        path = self._dir / TOKEN_FILE
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w") as handle:
                handle.write(secrets.token_urlsafe(TOKEN_BYTES))
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as handle:
            self._owned(os.fstat(handle.fileno()), path, 0o077)
            return handle.read().strip()

    def record_serving(self, record: ServingRecord) -> None:
        """Writes the runtime record, replacing any earlier one. The staged file is made
        exclusively, owner-only, never through a symlink."""
        self._ensure_dir()
        target = self._dir / RUNTIME_FILE
        staged = self._dir / f".{RUNTIME_FILE}.{os.getpid()}.tmp"
        staged.unlink(missing_ok=True)
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(
                json.dumps(
                    {"host": record.host, "port": record.port, "pid": record.pid, "tls": record.tls}
                )
            )
        staged.replace(target)

    def clear_serving(self, pid: int | None = None) -> None:
        """Removes the runtime record -- only when it names `pid`, if one is given, so a
        hub that failed to start never erases the record of one that is running."""
        if pid is not None:
            try:
                current = self.serving()
            except ValueError:
                return
            if current is None or current.pid != pid:
                return
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
        tls = data.get("tls", False)
        if not isinstance(tls, bool):
            raise ValueError(f"{path} says tls is {tls!r}, not true or false")
        return ServingRecord(host=host, port=port, pid=pid, tls=tls)

    def _ensure_dir(self) -> None:
        """The directory, made 0700; an existing one must be a real directory owned by
        this account that no other can write or read."""
        self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._owned(os.lstat(self._dir), self._dir, 0o077)

    @staticmethod
    def _owned(status: os.stat_result, path: Path, forbidden: int) -> None:
        if status.st_uid != os.getuid():
            raise PermissionError(f"{path} belongs to another account; refusing to use it")
        if status.st_mode & forbidden:
            raise PermissionError(f"{path} is open to other accounts; refusing to use it")
