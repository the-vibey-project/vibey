# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams over one BUILD run's capability snapshot (SP-LOOPS Phase 4, Task 8; R1, R9, R10).

`LoopCapabilitiesInterface` is what BUILD consumes: prepare a run's snapshot, release it when the
run ends, and sweep what a crashed worker left. The two below it are what the service consumes
and the infrastructure layer implements: the person's marketplace store (its lock, its roots and
its snapshot folder) and the remover of run folders. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.lock_entry import LockEntry

from vibey.application.dto import PreparedCapabilities, PruneReport


@runtime_checkable
class LoopCapabilitiesInterface(Protocol):
    def prepare(
        self, *, project_config: Path | None, folders: Sequence[Path]
    ) -> PreparedCapabilities:
        """Resolves one run's snapshot and writes its document. The bundle is the person's own
        `[loops]`, narrowed by `project_config`'s `disable` (the worktree's `vibey.toml`, the
        only project input; every other key it carries is dropped, logged and returned as a
        notice, never recorded). It resolves against the person's lock and roots only -- a
        locked tree, never the network -- writes `capabilities.json` naming `folders` (the run's
        input folder, when it has one) into the run's own 0700 folder, and returns the counts.
        Synchronous: BUILD calls it off the event loop. Raises `CapabilityResolutionError` (an
        unlocked or changed marketplace says which `vibey loops marketplace update` to run; a
        lock that cannot be read is one too), `ConfigError` for a `[loops]` table that cannot be
        read, or `SnapshotDocumentError` when the document cannot be written; on any of them no
        run folder is left behind."""
        ...

    def release(self, prepared: PreparedCapabilities) -> None:
        """Removes the run's folder, and only it, when its run has ended however it ended
        (R10). A folder that cannot be removed is logged by name and left for the sweep; this
        never raises for it."""
        ...

    def sweep(self) -> PruneReport:
        """Removes run folders untouched for longer than `max([loops] snapshot_max_age_days,
        the engine run deadline + 1 hour)`, so no running session's snapshot is ever taken
        (R10). Raises `ConfigError` for a person's `[loops]` that cannot be read."""
        ...


@runtime_checkable
class LoopMarketplacesInterface(Protocol):
    """The part of the person's marketplace store a run's snapshot is resolved from."""

    @property
    def snapshots(self) -> Path:
        """Where each run's folder is made: `<store>/snapshots/run-*/`."""
        ...

    def locked(self) -> tuple[LockEntry, ...]:
        """What the lock file holds (none when there is no lock yet). Raises `LockError` for a
        lock that cannot be read whole."""
        ...

    def roots(self, lock: Sequence[LockEntry], declared: Iterable[str] = ()) -> dict[str, Path]:
        """The folder each marketplace is read from, for the resolver."""
        ...


@runtime_checkable
class LoopSnapshotRemoverInterface(Protocol):
    def prune(self, snapshots: Path, *, older_than_seconds: float) -> PruneReport:
        """Removes each `run-*` folder directly in `snapshots` with no change at its top (the
        folder or any entry directly in it) for more than `older_than_seconds`. A `run-*` entry
        that is a symlink or not a folder, a `snapshots` that is itself a symlink, and a folder
        that cannot be listed are named in `refused` and never followed or removed; nothing else
        is touched. No folder is nothing to do. Raises `ValueError` for a
        negative age."""
        ...

    def remove(self, folder: Path, snapshots: Path) -> bool:
        """Removes `folder` when it is a `run-*` folder directly in `snapshots` (compared by where
        each really is), and says whether it did. A `folder` that is a symlink, a file, missing,
        outside `snapshots` or not named `run-*`, a `snapshots` that is itself a symlink, and a
        folder that cannot be removed are all refused with `False`: nothing is ever followed,
        and nothing else is touched."""
        ...
