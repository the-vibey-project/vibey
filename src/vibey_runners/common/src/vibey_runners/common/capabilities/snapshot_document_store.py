# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a run's capability document lives: `capabilities.json` in the run's own 0700 folder
(SP-LOOPS Phase 4, Task 2; R1, R14; Review Focus 5).

**Written once.** The conductor writes the document with `O_CREAT | O_EXCL | O_NOFOLLOW`, so it
never replaces a file or writes through a symlink planted in its place, and sets mode 0600 on
the open file whatever the umask. **Rewritten whole, in one step** (SP-LOOPS Phase 6): a run's
own `vibey-web` connector is added once its web grant exists, after the document is written; the
new document is written the same way at `STAGED_NAME` and renamed over the old, so a reader sees
the old document or the new one, never a part of either, and a failure leaves the old one.

**Read only from a place nobody else could have changed.** The folder must be a real folder (not
a symlink) owned by this user, with no group or other mode bit; the document must be a regular
0600 file (not a symlink) no larger than `DOCUMENT_MAX_BYTES`, which is refused from its size
before a byte is read. It is then read through `BoundedFileReader` with the same cap (the second
guard, should it grow in between) and parsed strictly by `SnapshotDocument.from_json`. Every
refusal is a `SnapshotDocumentError`, which a runner turns into exit 78 (R9). Declared by
`interfaces/snapshot_document_store_interface.py::SnapshotDocumentStoreInterface`.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.snapshot_document import SnapshotDocument
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError

DOCUMENT_NAME: Final = "capabilities.json"
"""The document's name in the run's folder."""
DOCUMENT_MAX_BYTES: Final = 4 * 1024 * 1024
"""A parser guard, not a policy limit (R14): sized from the bundle's own caps -- at most 256
entries of at most 4096 characters, over the document's four lists -- with room to spare. The
conductor writes the document itself, so a real one is far smaller."""
STAGED_NAME: Final = f"{DOCUMENT_NAME}.next"
"""Where a rewrite writes the new document before it takes the old one's place."""
DOCUMENT_MODE: Final = 0o600
_PRIVATE: Final = 0o077
"""The group and other mode bits, none of which the run's folder may carry."""


class SnapshotDocumentStore:
    """Declared by `interfaces/snapshot_document_store_interface.py::SnapshotDocumentStoreInterface`."""

    def __init__(self, reader: FileReaderInterface | None = None, uid: int | None = None) -> None:
        self._reader = reader or BoundedFileReader()
        self._uid = os.getuid() if uid is None else uid

    def write(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        path = folder / DOCUMENT_NAME
        try:
            self._create(document, path)
        except OSError as exc:
            raise SnapshotDocumentError(
                f"the capability document cannot be written at {path}: {exc}"
            ) from exc
        return path

    def rewrite(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        path = folder / DOCUMENT_NAME
        staged = folder / STAGED_NAME
        try:
            self._create(document, staged)
        except OSError as exc:
            raise SnapshotDocumentError(
                f"the capability document cannot be rewritten at {path}: {exc}"
            ) from exc
        try:
            os.replace(staged, path)
        except OSError as exc:
            staged.unlink(missing_ok=True)
            raise SnapshotDocumentError(
                f"the capability document cannot be rewritten at {path}: {exc}"
            ) from exc
        return path

    @staticmethod
    def _create(document: SnapshotDocumentInterface, path: Path) -> None:
        """Writes `document` as a new 0600 file at `path`: never over a file, never through a
        link."""
        data = document.to_json().encode("ascii")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open(path, flags, DOCUMENT_MODE)
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), DOCUMENT_MODE)  # whatever the umask took away
            handle.write(data)

    def read(self, path: Path) -> SnapshotDocumentInterface:
        folder = path.parent
        try:
            held = os.lstat(folder)
            status = os.lstat(path)
        except OSError as exc:
            raise SnapshotDocumentError(
                f"the capability document cannot be read at {path}: {exc}"
            ) from exc
        self._check_folder(folder, held)
        self._check_document(path, status)
        try:
            text = self._reader.read_text(path, DOCUMENT_MAX_BYTES)
        except (OSError, ValueError) as exc:  # grew past the cap, not UTF-8, gone
            raise SnapshotDocumentError(
                f"the capability document cannot be read at {path}: {exc}"
            ) from exc
        return SnapshotDocument.from_json(text, folder)

    def _check_folder(self, folder: Path, held: os.stat_result) -> None:
        if not stat.S_ISDIR(held.st_mode):
            raise SnapshotDocumentError(
                f"the capability document's folder {folder} is not a folder (a symlink is refused)"
            )
        if held.st_uid != self._uid:
            raise SnapshotDocumentError(
                f"the capability document's folder {folder} is not owned by this user "
                f"(uid {self._uid})"
            )
        if held.st_mode & _PRIVATE:
            raise SnapshotDocumentError(
                f"the capability document's folder {folder} is open to its group or others "
                f"(mode {stat.S_IMODE(held.st_mode):o}); it must be 0700"
            )

    @staticmethod
    def _check_document(path: Path, status: os.stat_result) -> None:
        if not stat.S_ISREG(status.st_mode):
            raise SnapshotDocumentError(
                f"the capability document {path} is not a regular file (a symlink is refused)"
            )
        if stat.S_IMODE(status.st_mode) != DOCUMENT_MODE:
            raise SnapshotDocumentError(
                f"the capability document {path} is mode {stat.S_IMODE(status.st_mode):o}; it "
                "must be 0600"
            )
        if status.st_size > DOCUMENT_MAX_BYTES:
            raise SnapshotDocumentError(
                f"the capability document {path} is larger than {DOCUMENT_MAX_BYTES} bytes"
            )
