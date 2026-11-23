# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the marketplace lock (SP-LOOPS Task 5)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.tree_record import TreeRecord


@runtime_checkable
class CapabilityLockInterface(Protocol):
    def digest_tree(self, root: Path, within: Sequence[PurePosixPath] | None = None) -> str:
        """`sha256:<hex>` over every path under `root` (sorted, relative; only the root's own
        `.git` excluded) with each file's content digest, each symlink's target text (never
        followed) and each folder's presence. Independent of listing order. With `within`, only
        those relative paths, what is below them and the folders above them, and never Python
        bytecode (`__pycache__`, `*.pyc`, `*.pyo`). Raises `LockError` for a tree that cannot be
        locked (a FIFO or device, too many entries, `root` not a folder, a `within` path that
        leaves it) and `OSError` when the file system refuses a look or a read -- the same on
        every Python."""
        ...

    def tree_records(
        self, root: Path, within: Sequence[PurePosixPath] | None = None
    ) -> tuple[TreeRecord, ...]:
        """The records `digest_tree(root, within)` hashes, sorted by path: one per folder, file
        and symlink it covers. Raises as `digest_tree` does."""
        ...

    def digest_records(self, records: Sequence[TreeRecord]) -> str:
        """`sha256:<hex>` over `records` in any order: `digest_tree(root)` is
        `digest_records(tree_records(root))`."""
        ...

    def write(self, path: Path, entries: Sequence[LockEntry]) -> None:
        """Replaces `path` atomically (a temporary file beside it, fsynced, renamed over it)
        with mode 0600. Raises `LockError`, writing nothing, for a malformed entry; on any
        failure the previous lock is left as it was and no temporary file remains."""
        ...

    def read(self, path: Path) -> tuple[LockEntry, ...]:
        """Every entry in `path`, or none when there is no lock yet. Raises `LockError` for a
        lock that is truncated, corrupted or hand-edited, oversized, a symlink, not a regular
        file or malformed, or in a folder that cannot be searched (never read as "no lock"), and
        never returns part of one."""
        ...
