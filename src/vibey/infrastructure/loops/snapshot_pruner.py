# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Removes finished runs' snapshots past an age (SP-LOOPS Task 7; Task 6 review advisory).

Each run's verified copy (`CapabilityResolver`, `<store>/snapshots/run-*`) is made fresh and
nothing removed it after the run. A stale copy is disk, and it is also reachable by relative path
from a later run's plugin, so removing it is containment. `vibey loops snapshots prune` removes
the `run-*` folders directly in the person's snapshot folder that were last changed more than an
age ago (7 days unless the person says otherwise), with `shutil.rmtree`, which never follows a
symlink inside what it removes. A `run-*` entry that is a symlink or not a folder, and a snapshot
folder that is itself a symlink, are named and left alone. Wiring the removal to the end of each
run, and a sweep when a worker starts, belongs to the phase that wires runs (Phase 4). Declared by
`interfaces/snapshot_pruner_interface.py::SnapshotPrunerInterface`.
"""

from __future__ import annotations

import os
import shutil
import stat
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

from vibey.infrastructure.loops.records import PruneReport

RUN_PREFIX: Final = "run-"
"""What `CapabilityResolver` names each run's folder."""
DEFAULT_AGE_DAYS: Final = 7
LINK: Final = "is a symlink; it is never followed or removed"
NOT_A_FOLDER: Final = "is not a folder; it is left alone"


class SnapshotPruner:
    """Declared by `interfaces/snapshot_pruner_interface.py::SnapshotPrunerInterface`."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        remove: Callable[[Path], None] = shutil.rmtree,
    ) -> None:
        self._clock = clock
        self._remove = remove

    def prune(self, snapshots: Path, *, older_than_seconds: float) -> PruneReport:
        if older_than_seconds < 0:
            raise ValueError(f"the age must be at least 0 seconds, not {older_than_seconds}")
        try:
            if stat.S_ISLNK(os.lstat(snapshots).st_mode):
                return PruneReport((), ((snapshots, LINK),))
        except FileNotFoundError:
            return PruneReport((), ())
        cutoff = self._clock() - older_than_seconds
        removed: list[Path] = []
        refused: list[tuple[Path, str]] = []
        for name in sorted(os.listdir(snapshots)):
            if not name.startswith(RUN_PREFIX):
                continue
            path = snapshots / name
            status = os.lstat(path)
            if stat.S_ISLNK(status.st_mode):
                refused.append((path, LINK))
            elif not stat.S_ISDIR(status.st_mode):
                refused.append((path, NOT_A_FOLDER))
            elif status.st_mtime < cutoff:
                try:
                    self._remove(path)
                except OSError as exc:
                    refused.append((path, f"cannot be removed: {exc}"))
                else:
                    removed.append(path)
        return PruneReport(tuple(removed), tuple(refused))
