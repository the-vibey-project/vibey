# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the marketplace lock (SP-LOOPS Task 5)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.lock_entry import LockEntry


@runtime_checkable
class CapabilityLockInterface(Protocol):
    def digest_tree(self, root: Path) -> str:
        """`sha256:<hex>` over every path under `root` (sorted, relative; only the root's own
        `.git` excluded) with each file's content digest, each symlink's target text (never
        followed) and each folder's presence. Independent of listing order. Raises `LockError` for a
        tree that cannot be locked (a FIFO or device, too many entries, `root` not a folder) and
        `OSError` when the file system refuses a read."""
        ...

    def write(self, path: Path, entries: Sequence[LockEntry]) -> None:
        """Replaces `path` atomically (a temporary file beside it, fsynced, renamed over it)
        with mode 0600. Raises `LockError`, writing nothing, for a malformed entry; on any
        failure the previous lock is left as it was and no temporary file remains."""
        ...

    def read(self, path: Path) -> tuple[LockEntry, ...]:
        """Every entry in `path`, or none when there is no lock yet. Raises `LockError` for a
        lock that is truncated, corrupted or hand-edited, oversized, a symlink, not a regular
        file or malformed, and never
        returns part of one."""
        ...
