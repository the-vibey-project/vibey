# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Copies locked marketplace content into a run's own folder (SP-LOOPS Task 6).

The copy is what a run loads, so it is made to be nothing but bytes the person owns: every folder
is created 0700 and every file 0600 (0700 when its owner may execute it, the one mode bit the
lock's digest sees), each file is written through a new descriptor (`O_CREAT | O_EXCL`), so a copy
is never a hard link to its source and never lands on anything already there, and a source file is
opened through the bounded reader (`O_NOFOLLOW`, non-blocking, regular files only). Only folders and
files are copied: a symlink is never followed or recreated. The plan is checked whole before the
target is made -- every path relative and inside the tree, at most `max_entries` entries -- and the
bytes are counted as they are written, so an oversized file costs at most the cap. Whether the copy
holds what was locked is not decided here: `CapabilityResolver` compares it record by record with
the records that matched the lock. Declared by
`interfaces/snapshot_copier_interface.py::SnapshotCopierInterface`.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Final

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.tree_record import TreeRecord

FOLDER: Final = "D"
COPIED_KINDS: Final = frozenset({FOLDER, "F", "X"})
_PRIVATE: Final = 0o600
_PRIVATE_EXECUTABLE: Final = 0o700
_CHUNK: Final = 1024 * 1024
_NEW_FILE: Final = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC


class SnapshotCopier:
    """Declared by `interfaces/snapshot_copier_interface.py::SnapshotCopierInterface`."""

    def __init__(self, reader: FileReaderInterface | None = None) -> None:
        self._reader = reader or BoundedFileReader()

    def copy(
        self,
        source: Path,
        plan: Sequence[TreeRecord],
        target: Path,
        *,
        max_entries: int,
        max_bytes: int,
    ) -> int:
        for record in plan:
            self._check(record)
        if len(plan) > max_entries:
            raise CapabilityResolutionError(
                f"copying {source} would put more than {max_entries} entries in the snapshot"
            )
        try:
            os.mkdir(target, _PRIVATE_EXECUTABLE)
        except FileExistsError as exc:
            raise CapabilityResolutionError(f"the snapshot folder {target} already exists") from exc
        os.chmod(target, _PRIVATE_EXECUTABLE)
        copied = 0
        for record in sorted(plan, key=lambda record: record.path):
            relative = PurePosixPath(record.path)
            try:
                if record.kind == FOLDER:
                    self._folders(target, relative)
                    continue
                self._folders(target, relative.parent)
                copied = self._file(source, record, target, copied, max_bytes)
            except OSError as exc:
                raise CapabilityResolutionError(
                    f"cannot copy {record.path} into the snapshot: {exc}"
                ) from exc
        return copied

    @staticmethod
    def _check(record: TreeRecord) -> None:
        relative = PurePosixPath(record.path)
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise CapabilityResolutionError(f"{record.path!r} is not a path inside the marketplace")
        if record.kind not in COPIED_KINDS:
            what = "a symlink" if record.kind == "L" else f"an entry of kind {record.kind!r}"
            raise CapabilityResolutionError(f"{record.path}: a snapshot never copies {what}")

    @staticmethod
    def _folders(target: Path, relative: PurePosixPath) -> None:
        """Makes each folder of `relative` under `target` that is not there yet, 0700."""
        folder = target
        for part in relative.parts:
            folder = folder / part
            try:
                os.mkdir(folder, _PRIVATE_EXECUTABLE)
            except FileExistsError:
                continue
            os.chmod(folder, _PRIVATE_EXECUTABLE)

    def _file(
        self, source: Path, record: TreeRecord, target: Path, copied: int, max_bytes: int
    ) -> int:
        mode = _PRIVATE_EXECUTABLE if record.kind == "X" else _PRIVATE
        # The source is opened first: a source that is not a regular file creates no copy.
        with (
            os.fdopen(self._reader.open_regular(source / record.path), "rb") as handle,
            os.fdopen(os.open(target / record.path, _NEW_FILE, _PRIVATE), "wb") as copy,
        ):
            os.fchmod(copy.fileno(), mode)
            while chunk := handle.read(min(_CHUNK, max_bytes - copied + 1)):
                copied += len(chunk)
                if copied > max_bytes:
                    raise CapabilityResolutionError(
                        f"copying {source} would put more than {max_bytes} bytes in the snapshot"
                    )
                copy.write(chunk)
        return copied
