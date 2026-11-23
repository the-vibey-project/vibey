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
        """Removes each `run-*` folder directly in `snapshots` last changed more than
        `older_than_seconds` ago. A `run-*` entry that is a symlink or not a folder, and a
        `snapshots` that is itself a symlink, are named in `refused` and never followed or
        removed; nothing else is touched. No folder is nothing to do. Raises `ValueError` for a
        negative age."""
        ...
