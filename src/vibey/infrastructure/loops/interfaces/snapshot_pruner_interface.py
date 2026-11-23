# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over removing finished runs' snapshots (SP-LOOPS Task 7).

Implemented by `snapshot_pruner.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.infrastructure.loops.records import PruneReport


@runtime_checkable
class SnapshotPrunerInterface(Protocol):
    def prune(self, snapshots: Path, *, older_than_seconds: float) -> PruneReport:
        """Removes each `run-*` folder directly in `snapshots` with no change at its top (the
        folder or any entry directly in it) for more than `older_than_seconds`. A `run-*` entry
        that is a symlink or not a folder, a `snapshots` that is itself a symlink, and a folder
        that cannot be listed are named in `refused` and never followed or removed; nothing else
        is touched. No folder is nothing to do. Raises `ValueError` for a
        negative age."""
        ...
