# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Removes finished runs' snapshots past an age (SP-LOOPS Task 7; Task 6 review advisory).

Each run's verified copy (`CapabilityResolver`, `<store>/snapshots/run-*`) is made fresh and
nothing removed it after the run. A stale copy is disk, and it is also reachable by relative path
from a later run's plugin, so removing it is containment. `vibey loops snapshots prune` removes
the `run-*` folders directly in the person's snapshot folder that have had no change at their top
-- the folder itself or any entry directly in it -- for longer than an age (7 days unless the person
says otherwise): N days of inactivity is the rule, so a run still changing its snapshot is kept, but
one that has sat untouched that long is removed even if it is still running. Removal is
`shutil.rmtree`, which never follows a symlink inside what it removes. A `run-*` entry that is a
symlink or not a folder, a snapshot folder that is itself a symlink, and a folder that cannot be
listed are named and left alone. Phase 4 (R10) wires both: `remove` takes one run's folder away
when its BUILD run ends, and a worker sweeps with `prune` as it starts. Declared by
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
        try:
            names = sorted(os.listdir(snapshots))
        except OSError as exc:  # a file where the folder should be, a folder not yours, ...
            return PruneReport((), ((snapshots, f"cannot be listed: {exc}"),))
        for name in names:
            if not name.startswith(RUN_PREFIX):
                continue
            path = snapshots / name
            try:
                status = os.lstat(path)
            except FileNotFoundError:
                continue  # removed meanwhile (another prune, a run's own cleanup)
            if stat.S_ISLNK(status.st_mode):
                refused.append((path, LINK))
            elif not stat.S_ISDIR(status.st_mode):
                refused.append((path, NOT_A_FOLDER))
            else:
                try:
                    newest = self._newest(path, status.st_mtime)
                except OSError as exc:
                    refused.append((path, f"cannot be listed: {exc}"))
                    continue
                if newest >= cutoff:
                    continue
                try:
                    self._remove(path)
                except OSError as exc:
                    refused.append((path, f"cannot be removed: {exc}"))
                else:
                    removed.append(path)
        return PruneReport(tuple(removed), tuple(refused))

    def remove(self, folder: Path, snapshots: Path) -> bool:
        if not folder.name.startswith(RUN_PREFIX):
            return False
        try:
            if stat.S_ISLNK(os.lstat(snapshots).st_mode):
                return False
            # Directly in the snapshot folder, compared by where each really is: the folder's
            # parent is resolved, never the folder itself, so a run folder that is a symlink is
            # seen as one below and left alone.
            if os.path.realpath(folder.parent) != os.path.realpath(snapshots):
                return False
            status = os.lstat(folder)
        except OSError:  # gone already, or a path that cannot be looked at
            return False
        if not stat.S_ISDIR(status.st_mode):  # a symlink (lstat sees the link) or a file
            return False
        try:
            self._remove(folder)
        except OSError:
            return False
        return True

    @staticmethod
    def _newest(run: Path, own: float) -> float:
        """The latest change at the top of a run folder: the folder itself and each entry
        directly in it (never following a link). A run is old after that long without one."""
        newest = own
        for entry in os.scandir(run):
            newest = max(newest, entry.stat(follow_symlinks=False).st_mtime)
        return newest
