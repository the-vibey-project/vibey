# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The engine sessions' hub principals, where the worker records them and the hub finds them
(SP-LOOPS Phase 6, Task 2).

The worker mints a session's principal; the hub (`vibey serve`, another process) authenticates
the session's token. Both already share one place: the hub's owner-only state folder
(`[hub] state_dir`), where the worker finds a running hub (`serving.json`) and the hub reads its
paired devices afresh on every request (`devices.json`). The registry is a folder there,
`<state_dir>/sessions/`, 0700, with one file per session named by the SHA-256 digest of its
token -- `<64 hex>.json`, 0600 -- holding the principal (`name`, `run_id`, `expires_at`) and never
the token. One file per session, not one shared file, so concurrent workers never rewrite each
other's entries and need no lock; each is staged under a unique name and renamed into place, so
the hub never reads half an entry.

Read afresh on every lookup, so a revocation (`forget`) refuses the token's very next request, in
this process and any other hub on the host. A name that is not 64 lower-case hex characters is
never turned into a path. Nothing is followed through a symlink: the folder is checked with
`lstat`, an entry is opened `O_NOFOLLOW` and checked on its descriptor, and `forget` unlinks the
name itself. An entry or folder that is not this account's own and owner-only raises
`PermissionError`; a malformed entry raises `ValueError` naming it -- neither is the same fact as
no session. Expired entries are harmless here (the service refuses them) and are the start-up
sweep's to remove. Declared by `interfaces/session_registry_interface.py::SessionRegistryInterface`.
"""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
import stat
from pathlib import Path
from typing import Final
from uuid import UUID, uuid4

from vibey.domain.session_principal import SessionPrincipal

SESSIONS_FOLDER: Final = "sessions"
"""The registry's folder in the hub's state folder."""
ENTRY_SUFFIX: Final = ".json"
FOLDER_MODE: Final = 0o700
FILE_MODE: Final = 0o600
OTHERS: Final = 0o077
_DIGEST: Final = re.compile(r"[0-9a-f]{64}")


class SessionRegistry:
    """Declared by `interfaces/session_registry_interface.py::SessionRegistryInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._folder = state_dir / SESSIONS_FOLDER

    def record(self, digest: str, principal: SessionPrincipal) -> None:
        if not self._is_digest(digest):
            raise ValueError("a session entry is named by a SHA-256 digest in lower-case hex")
        self._folder.parent.mkdir(mode=FOLDER_MODE, parents=True, exist_ok=True)
        with contextlib.suppress(FileExistsError):
            os.mkdir(self._folder, FOLDER_MODE)
            os.chmod(self._folder, FOLDER_MODE)  # exact, whatever the umask narrowed
        self._checked_folder()
        data = json.dumps(
            {
                "name": principal.name,
                "run_id": str(principal.run_id),
                "expires_at": principal.expires_at,
            }
        ).encode()
        staged = self._folder / f".{digest}.{uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open(staged, flags, FILE_MODE)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                os.fchmod(handle.fileno(), FILE_MODE)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, self._entry(digest))
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(staged)
            raise

    def find(self, digest: str) -> SessionPrincipal | None:
        if not self._is_digest(digest):
            return None
        try:
            self._checked_folder()
        except FileNotFoundError:
            return None
        path = self._entry(digest)
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        except FileNotFoundError:
            return None
        try:
            facts = os.fstat(descriptor)
            if not stat.S_ISREG(facts.st_mode):
                raise PermissionError(f"{path} is not a regular file; refusing to use it")
            self._owned(facts, path)
        except BaseException:
            os.close(descriptor)
            raise
        with os.fdopen(descriptor, "rb") as handle:
            raw = handle.read()
        return self._principal(raw, path)

    def forget(self, digest: str) -> bool:
        if not self._is_digest(digest):
            return False
        try:
            os.unlink(self._entry(digest))  # unlinks a symlink itself, never its target
        except FileNotFoundError:
            return False
        return True

    def _entry(self, digest: str) -> Path:
        return self._folder / f"{digest}{ENTRY_SUFFIX}"

    @staticmethod
    def _is_digest(digest: str) -> bool:
        return _DIGEST.fullmatch(digest) is not None

    def _checked_folder(self) -> None:
        facts = os.lstat(self._folder)
        if not stat.S_ISDIR(facts.st_mode):
            raise PermissionError(
                f"{self._folder} is a symlink or not a folder; refusing to use it"
            )
        self._owned(facts, self._folder)

    @staticmethod
    def _owned(facts: os.stat_result, path: Path) -> None:
        if facts.st_uid != os.getuid():
            raise PermissionError(f"{path} belongs to another account; refusing to use it")
        if facts.st_mode & OTHERS:
            raise PermissionError(f"{path} is open to other accounts; refusing to use it")

    @staticmethod
    def _principal(raw: bytes, path: Path) -> SessionPrincipal:
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise ValueError(f"{path} is not JSON") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a JSON object")
        name, run_id, expires_at = data.get("name"), data.get("run_id"), data.get("expires_at")
        if (
            not isinstance(name, str)
            or not isinstance(run_id, str)
            or not isinstance(expires_at, int | float)
            or isinstance(expires_at, bool)
            or not math.isfinite(expires_at)
        ):
            raise ValueError(f"{path} does not name a session, its run and its expiry")
        try:
            return SessionPrincipal(name=name, run_id=UUID(run_id), expires_at=float(expires_at))
        except ValueError as exc:
            raise ValueError(f"{path} holds a malformed session: {exc}") from exc
