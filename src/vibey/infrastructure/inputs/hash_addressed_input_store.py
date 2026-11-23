# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A project's run inputs on disk, stored once by digest, added to by appending (SP-LOOPS Phase
3, Task 2; design Decision 6). Nothing enters Postgres: inputs are files.

**Layout.** Under `project_folder / "inputs"` (0700): `objects/<digest[:2]>/<digest>` holds each
input's bytes once (0600), and `index.jsonl` (0600) one JSON line per add -- digest, kind, name,
size and when, never the content.

**Writing.** The index line is built and measured first: a line longer than
`max_index_line_bytes` is refused before anything is written, which keeps every append one
`O_APPEND` write and so whole. An object is written to a temporary name opened with `O_EXCL`,
synced, then renamed into place; when the object already exists no second copy is written. Only
then is the line appended, in one write, and synced: the append is the commit, so a crash leaves
at most an object no row names, never a row with no object. No lock and no thread.

**Refusals.** A symlink or other non-regular file where the store keeps its own folder, object
or index is refused, never followed (`O_NOFOLLOW`). Every failure is an `InputStoreError` naming
the path. Declared by `interfaces/input_store_interface.py::HashAddressedInputStoreInterface`.
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Final
from uuid import uuid4

from vibey.application.interfaces.system import Clock
from vibey.domain.errors import InputStoreError
from vibey.domain.run_input import (
    INPUT_KINDS,
    RUN_INPUT_RULE,
    InputKind,
    InputListing,
    RunInput,
)

MAX_INDEX_LINE_BYTES: Final = 4096
"""The longest index line appended: one `O_APPEND` write of a regular file this size is whole on
every filesystem vibey supports, so two adds at once can never interleave their lines."""
FOLDER_MODE: Final = 0o700
FILE_MODE: Final = 0o600
_WRITE_FLAGS: Final = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
_APPEND_FLAGS: Final = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS: Final = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC


class HashAddressedInputStore:
    """Declared by `interfaces/input_store_interface.py::HashAddressedInputStoreInterface`."""

    def __init__(
        self,
        clock: Clock,
        *,
        max_index_line_bytes: int = MAX_INDEX_LINE_BYTES,
        write: Callable[[int, bytes], int] = os.write,
    ) -> None:
        self._clock = clock
        self._max_line = max_index_line_bytes
        self._write = write

    def put(self, project_folder: Path, kind: InputKind, name: str, data: bytes) -> RunInput:
        item = RunInput(digest=RUN_INPUT_RULE.digest_of(data), kind=kind, name=name, size=len(data))
        line = self._line(item)
        root = self._folder(project_folder / "inputs", parents=True)
        shard = self._folder(self._folder(root / "objects") / item.digest[:2])
        self._object(shard / item.digest, data)
        self._append(root / "index.jsonl", line)
        return item

    def get(self, project_folder: Path, digest: str) -> bytes:
        if not RUN_INPUT_RULE.is_digest(digest):
            raise InputStoreError(f"{digest!r} is not a digest")
        path = project_folder / "inputs" / "objects" / digest[:2] / digest
        data = self._read(path)
        if data is None:
            raise InputStoreError(f"{path}: no stored input has this digest")
        if RUN_INPUT_RULE.digest_of(data) != digest:
            raise InputStoreError(f"{path}: the stored object does not match its digest")
        return data

    def listed(self, project_folder: Path) -> InputListing:
        data = self._read(project_folder / "inputs" / "index.jsonl")
        if data is None:
            return InputListing(items=(), skipped=0)
        *lines, tail = data.split(b"\n")
        items: list[RunInput] = []
        skipped = 1 if tail else 0  # a last line with no newline is one torn by a crash
        for line in lines:
            item = self._row(line)
            if item is None:
                skipped += 1
            else:
                items.append(item)
        return InputListing(items=tuple(items), skipped=skipped)

    # -- writing -------------------------------------------------------------------------------

    def _line(self, item: RunInput) -> bytes:
        row = {
            "digest": item.digest,
            "kind": item.kind,
            "name": item.name,
            "size": item.size,
            "at": self._clock.now().isoformat(),
        }
        line = (json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
        if len(line) > self._max_line:
            raise InputStoreError(
                f"the index line for this input is {len(line)} bytes; at most {self._max_line} "
                "are appended in one write"
            )
        return line

    @staticmethod
    def _folder(path: Path, *, parents: bool = False) -> Path:
        """`path` as a 0700 folder of the store's own: made when absent, refused when anything
        but a folder (a symlink to one included) is there."""
        try:
            if parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            with contextlib.suppress(FileExistsError):
                os.mkdir(path, FOLDER_MODE)
                os.chmod(path, FOLDER_MODE)  # the mode a umask could have narrowed is exact
            mode = os.lstat(path).st_mode
        except OSError as exc:
            raise InputStoreError(f"{path}: the input folder cannot be made: {exc}") from exc
        if not stat.S_ISDIR(mode):
            raise InputStoreError(f"{path}: is not a folder (a symlink is never followed)")
        return path

    def _object(self, path: Path, data: bytes) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        try:
            if self._stored(path):
                return  # the same bytes are already stored: one object, however many rows
            descriptor = os.open(temporary, _WRITE_FLAGS, FILE_MODE)
            try:
                view = memoryview(data)
                while view:
                    view = view[self._write(descriptor, bytes(view)) :]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.replace(temporary, path)
        except OSError as exc:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise InputStoreError(f"{path}: cannot be written: {exc}") from exc

    @staticmethod
    def _stored(path: Path) -> bool:
        """Whether an object is already at `path`. Raises `InputStoreError` for anything there
        but a regular file, and `OSError` when it cannot be looked at."""
        try:
            mode = os.lstat(path).st_mode
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(mode):
            raise InputStoreError(f"{path}: is not a regular file (a symlink is never followed)")
        return True

    def _append(self, path: Path, line: bytes) -> None:
        try:
            descriptor = os.open(path, _APPEND_FLAGS, FILE_MODE)
        except OSError as exc:
            raise InputStoreError(f"{path}: cannot be written: {exc}") from exc
        try:
            written = self._write(descriptor, line)
            if written != len(line):
                raise InputStoreError(
                    f"{path}: a short write ({written} of {len(line)} bytes) left the index "
                    "line torn; it is skipped when the index is read"
                )
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    # -- reading -------------------------------------------------------------------------------

    @staticmethod
    def _read(path: Path) -> bytes | None:
        """The whole regular file at `path`, or None when nothing is there."""
        try:
            descriptor = os.open(path, _READ_FLAGS)
        except FileNotFoundError:
            return None
        except OSError as exc:  # a symlink (ELOOP under O_NOFOLLOW), a folder with no access
            raise InputStoreError(f"{path}: cannot be read: {exc}") from exc
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise InputStoreError(f"{path}: cannot be read: not a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()

    @staticmethod
    def _row(line: bytes) -> RunInput | None:
        """One index line as a run input, or None when it is not one this store writes."""
        try:
            row = json.loads(line)
        except ValueError:  # not JSON, or not UTF-8
            return None
        if not isinstance(row, dict):
            return None
        digest, kind, name, size = (row.get(key) for key in ("digest", "kind", "name", "size"))
        if not (isinstance(digest, str) and RUN_INPUT_RULE.is_digest(digest)):
            return None
        if kind not in INPUT_KINDS or not isinstance(name, str):
            return None
        if RUN_INPUT_RULE.valid_name(name) is not None:
            return None  # the index is a file a person can edit: a name is checked as it is read
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return None
        return RunInput(digest=digest, kind=kind, name=name, size=size)
