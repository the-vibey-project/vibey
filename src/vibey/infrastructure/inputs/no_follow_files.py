# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Folders made and files written, read and appended without ever following a symlink: the one
hardened file adapter for run inputs (SP-LOOPS Phase 3, fix round 1: R-E, R-F, R-J).

The input store (in the person's own state folder) and a run's inputs folder (in its worktree,
which may be a cloned repository's) both go through it, so the rule lives in one place:

- every folder below a trusted root is checked with `lstat` and refused when it is a symlink or
  not a folder; one it makes is 0700;
- every file is written to a temporary name opened `O_EXCL | O_NOFOLLOW` (0600), synced, then
  renamed into place, and a symlink or other non-regular file where it goes is refused;
- every file is read `O_NOFOLLOW`, refused unless regular, and refused from its size before a
  byte is read when it is over the caller's bound;
- an append is one `O_APPEND` write, with a newline first when the file ends in a torn line;
- a platform with no `O_NOFOLLOW` is refused, never served by a fallback.

Every refusal is an `InputStoreError` naming the path. Declared by
`interfaces/no_follow_files_interface.py::NoFollowFilesInterface`.
"""

from __future__ import annotations

import contextlib
import os
import stat
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final
from uuid import uuid4

from vibey.domain.errors import InputStoreError
from vibey.domain.run_input import RUN_INPUT_RULE

FOLDER_MODE: Final = 0o700
FILE_MODE: Final = 0o600
_NOFOLLOW: Final[int | None] = getattr(os, "O_NOFOLLOW", None)
"""None where the platform has no `O_NOFOLLOW`: every read and write then refuses."""


class NoFollowFiles:
    """Declared by `interfaces/no_follow_files_interface.py::NoFollowFilesInterface`."""

    def __init__(
        self,
        *,
        nofollow: int | None = _NOFOLLOW,
        write: Callable[[int, bytes], int] = os.write,
    ) -> None:
        self._nofollow = nofollow
        self._write = write

    # -- folders -------------------------------------------------------------------------------

    def made(self, root: Path, parts: Sequence[str]) -> Path:
        if not root.is_dir():
            raise InputStoreError(f"{root}: the folder cannot be made under it: not a folder")
        path = root
        for part in parts:
            path = path / part
            try:
                with contextlib.suppress(FileExistsError):
                    os.mkdir(path, FOLDER_MODE)
                    os.chmod(path, FOLDER_MODE)  # exact, whatever the umask narrowed
                mode = os.lstat(path).st_mode
            except OSError as exc:
                raise InputStoreError(f"{path}: the folder cannot be made: {exc}") from exc
            self._a_folder(path, mode)
        return path

    def found(self, root: Path, parts: Sequence[str]) -> Path | None:
        path = root
        for part in parts:
            path = path / part
            try:
                mode = os.lstat(path).st_mode
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise InputStoreError(f"{path}: cannot be read: {exc}") from exc
            self._a_folder(path, mode)
        return path

    @staticmethod
    def _a_folder(path: Path, mode: int) -> None:
        if not stat.S_ISDIR(mode):
            raise InputStoreError(
                f"{path}: is a symlink or not a folder; nothing is written or read through one"
            )

    # -- files ---------------------------------------------------------------------------------

    def write(self, folder: Path, name: str, data: bytes) -> Path:
        nofollow = self._flag()
        target = folder / name
        if RUN_INPUT_RULE.valid_name(name) is not None or target.parent != folder:
            raise InputStoreError(f"{ascii(name)[:80]} does not name a file in {folder}")
        temporary = folder / f".vibey-{uuid4().hex}.tmp"
        try:
            try:
                mode: int | None = os.lstat(target).st_mode
            except FileNotFoundError:
                mode = None
            if mode is not None and not stat.S_ISREG(mode):
                raise InputStoreError(
                    f"{target}: is a symlink or not a regular file; nothing is written through one"
                )
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | nofollow
            descriptor = os.open(temporary, flags, FILE_MODE)
            try:
                view = memoryview(data)
                while view:
                    view = view[self._write(descriptor, bytes(view)) :]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(temporary, target)
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise InputStoreError(f"{target}: cannot be written: {exc}") from exc
        return target

    def read(self, path: Path, *, max_bytes: int | None = None) -> bytes | None:
        flags = os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | self._flag()
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            return None
        except OSError as exc:  # ELOOP for a symlink under O_NOFOLLOW, EACCES, ...
            raise InputStoreError(f"{path}: cannot be read: {exc}") from exc
        facts = os.fstat(descriptor)
        refusal = None
        if not stat.S_ISREG(facts.st_mode):
            refusal = f"{path}: cannot be read: not a regular file"
        elif max_bytes is not None and facts.st_size > max_bytes:
            refusal = f"{path}: is {facts.st_size} bytes; at most {max_bytes} are read"
        if refusal is not None:
            os.close(descriptor)
            raise InputStoreError(refusal)
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read() if max_bytes is None else handle.read(max_bytes + 1)

    def append(self, path: Path, line: bytes, *, max_bytes: int) -> None:
        # Read and write: the last byte is read to see whether the file ends in a torn line.
        flags = os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC | self._flag()
        try:
            descriptor = os.open(path, flags, FILE_MODE)
        except OSError as exc:
            raise InputStoreError(f"{path}: cannot be written: {exc}") from exc
        try:
            facts = os.fstat(descriptor)
            if not stat.S_ISREG(facts.st_mode):
                raise InputStoreError(f"{path}: cannot be written: not a regular file")
            if facts.st_size and os.pread(descriptor, 1, facts.st_size - 1) != b"\n":
                line = b"\n" + line  # end the torn line first, in the same write
            if len(line) > max_bytes:
                raise InputStoreError(
                    f"{path}: this line is {len(line)} bytes; at most {max_bytes} are appended "
                    "in one write"
                )
            written = self._write(descriptor, line)
            if written != len(line):
                raise InputStoreError(
                    f"{path}: a short write ({written} of {len(line)} bytes) left the line torn; "
                    "it is skipped when the file is read"
                )
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _flag(self) -> int:
        if self._nofollow is None:
            raise InputStoreError(
                "this platform cannot open a file without following a symlink (no O_NOFOLLOW), "
                "so vibey refuses to read or write run inputs"
            )
        return self._nofollow
