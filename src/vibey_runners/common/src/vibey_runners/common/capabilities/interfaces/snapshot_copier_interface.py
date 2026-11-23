# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over copying locked marketplace content into a run's own folder (SP-LOOPS Task 6)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.tree_record import TreeRecord


@runtime_checkable
class SnapshotCopierInterface(Protocol):
    def copy(
        self,
        source: Path,
        plan: Sequence[TreeRecord],
        target: Path,
        *,
        max_entries: int,
        max_bytes: int,
    ) -> int:
        """Creates `target` (0700; it must not exist) and copies into it each folder and file
        `plan` names, at the same relative path under `source`: folders 0700, files 0600 or 0700
        by the record's kind, bytes only (never a hard link or a symlink). Returns the bytes
        copied. Raises `CapabilityResolutionError` for a plan entry that is not a relative path
        inside the tree or not a folder or file, for more than `max_entries` entries or
        `max_bytes` bytes, and for any file the system will not let it read or write."""
        ...
