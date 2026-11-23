# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of the one no-follow file adapter, beside its class (ADR-0016; SP-LOOPS Phase 3,
fix round 1: R-E).

Mirrors `infrastructure/inputs/no_follow_files.py`. It is the run folder writer the run inputs
service consumes (`RunFolderWriterInterface`) and, with what it adds here, everything the input
store does on disk. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.interfaces.run_folder_writer_interface import RunFolderWriterInterface


@runtime_checkable
class NoFollowFilesInterface(RunFolderWriterInterface, Protocol):
    def found(self, root: Path, parts: Sequence[str]) -> Path | None:
        """`root / parts...` when every part exists as a folder, None when one is absent; a
        symlink or anything but a folder at a part is an `InputStoreError`. Makes nothing."""
        ...

    def read(self, path: Path, *, max_bytes: int | None = None) -> bytes | None:
        """The whole regular file at `path`, opened without following a symlink, or None when
        nothing is there. A symlink, anything but a regular file, a file over `max_bytes` (from
        its size, before a byte is read), or a platform with no `O_NOFOLLOW` is an
        `InputStoreError`."""
        ...

    def append(self, path: Path, line: bytes, *, max_bytes: int) -> None:
        """Appends `line` (ending in a newline) to the file at `path` (0600, made when absent)
        in one `O_APPEND` write, synced. When the file does not end in a newline -- a line torn
        by a crash -- a newline is written first, in the same write, so the new line is never
        merged into the torn one. A write longer than `max_bytes`, a short write, a symlink or
        anything but a regular file is an `InputStoreError`."""
        ...
