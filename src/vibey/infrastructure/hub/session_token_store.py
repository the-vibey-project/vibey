# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An engine session's hub token file: `<run folder>/web-token` (SP-LOOPS Phase 6, Task 2; R1).

The session's environment carries only the file's path (`VIBEY_WEB_TOKEN_FILE`), so the token is
on disk exactly once, in the run's own folder, and nowhere else at rest:

- the run folder must already exist and be a real folder (`lstat`, never a symlink), owned by
  this account and open to no other -- the 0700 folder Phase 4's resolver makes for each run;
  vibey never makes it here, so a token never lands in a folder of somebody else's choosing;
- the file is created `O_CREAT | O_EXCL | O_NOFOLLOW`, mode 0600 and set exactly so whatever the
  umask, so an existing file -- or a symlink planted where it goes -- refuses the grant instead
  of being overwritten or followed: one grant per run folder;
- a write that fails or comes up short removes the file before the error goes up;
- `read` opens without following a symlink and checks the open descriptor: a regular file, this
  account's, open to no other, and not empty;
- `remove` takes away a regular file only, never a symlink or what it points at.

Every refusal is a `SessionGrantRefused` naming the path, never the token.

Why not the family's file adapters: `LocalTokenStore._secret` (`local_token.py`) returns a file
that already exists rather than refusing it, and is fixed to the hub's own named secrets in its
state folder; `NoFollowFiles` (`infrastructure/inputs/`) replaces an existing file by rename and
speaks the run input store's error. Neither offers a create-exclusive-or-refuse write into a
folder the caller owns, which is the one rule here. Declared by
`interfaces/session_token_store_interface.py::SessionTokenStoreInterface`.
"""

from __future__ import annotations

import contextlib
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Final

from vibey.domain.errors import SessionGrantRefused

WEB_TOKEN_FILE: Final = "web-token"
"""The token file's name in its run's folder (R1)."""
FILE_MODE: Final = 0o600
OTHERS: Final = 0o077
"""Any permission bit for the group or other accounts: a token file or its folder has none."""


class SessionTokenStore:
    """Declared by `interfaces/session_token_store_interface.py::SessionTokenStoreInterface`."""

    def __init__(self, *, write: Callable[[int, bytes], int] = os.write) -> None:
        self._write = write

    def write(self, folder: Path, token: str) -> Path:
        self._checked_folder(folder)
        path = folder / WEB_TOKEN_FILE
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            descriptor = os.open(path, flags, FILE_MODE)
        except FileExistsError as exc:  # a file, or a symlink planted where it goes
            raise SessionGrantRefused(
                f"{path} already exists; a run folder holds one session token"
            ) from exc
        data = token.encode()
        try:
            os.fchmod(descriptor, FILE_MODE)  # exact, whatever the umask
            written = self._write(descriptor, data)
            if written != len(data):
                raise OSError(f"{path}: a short write ({written} of {len(data)} bytes)")
            os.fsync(descriptor)
        except BaseException:
            os.close(descriptor)
            with contextlib.suppress(OSError):
                os.unlink(path)
            raise
        os.close(descriptor)
        return path

    def read(self, path: Path) -> str:
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        except FileNotFoundError:
            raise
        except OSError as exc:  # ELOOP for a symlink under O_NOFOLLOW, EACCES, ...
            raise SessionGrantRefused(f"{path} cannot be read: {exc.strerror}") from exc
        try:
            facts = os.fstat(descriptor)
            if not stat.S_ISREG(facts.st_mode):
                raise SessionGrantRefused(f"{path} is not a regular file")
            self._owned(facts, path)
        except BaseException:
            os.close(descriptor)
            raise
        with os.fdopen(descriptor, "rb") as handle:
            token = handle.read().decode().strip()
        if not token:
            raise SessionGrantRefused(f"{path} holds no token")
        return token

    def remove(self, path: Path) -> bool:
        try:
            facts = os.lstat(path)
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if not stat.S_ISREG(facts.st_mode):  # a symlink (lstat sees the link) or a folder
            return False
        try:
            os.unlink(path)
        except FileNotFoundError:
            return True
        except OSError:
            return False
        return True

    def _checked_folder(self, folder: Path) -> None:
        try:
            facts = os.lstat(folder)
        except FileNotFoundError as exc:
            raise SessionGrantRefused(
                f"{folder} does not exist; a run folder is made first"
            ) from exc
        if not stat.S_ISDIR(facts.st_mode):
            raise SessionGrantRefused(f"{folder} is a symlink or not a folder")
        self._owned(facts, folder)

    @staticmethod
    def _owned(facts: os.stat_result, path: Path) -> None:
        if facts.st_uid != os.getuid():
            raise SessionGrantRefused(f"{path} belongs to another account")
        if facts.st_mode & OTHERS:
            raise SessionGrantRefused(f"{path} is open to other accounts")
