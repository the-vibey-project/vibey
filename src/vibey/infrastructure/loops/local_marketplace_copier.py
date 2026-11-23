# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Copies a marketplace the person keeps in a folder of their own, without git (SP-LOOPS Task 7).

A local source is an absolute folder path (`MarketplaceSourceRule`): git is never handed a local
path, so its `file` protocol stays refused. The folder is copied the way a run's snapshot is,
with the family's own pieces: `CapabilityLock.tree_records` lists it (never following a link,
refusing a FIFO, socket or device, leaving the root's `.git` out, at most `MAX_TREE_ENTRIES`
entries) and `SnapshotCopier` copies the folders and files (0700/0600 or 0700 for an executable,
new files only, at most `max_entries` entries and `max_bytes` bytes). A symlink is left out and
named. The copy is then listed again and must match the plan record by record, so a file changed
while it was copied is refused, not stored. Declared by
`interfaces/marketplace_fetcher_interface.py::MarketplaceFetcherInterface`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.interfaces.lock_interface import CapabilityLockInterface
from vibey_runners.common.capabilities.interfaces.snapshot_copier_interface import (
    SnapshotCopierInterface,
)
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.snapshot_copier import COPIED_KINDS, SnapshotCopier
from vibey_runners.common.capabilities.tree_record import TreeRecord

from vibey.domain.marketplace_source import MarketplaceSource
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.records import FetchResult

MAX_ENTRIES: Final = 100_000
"""The most folders and files one marketplace copy may hold."""
MAX_BYTES: Final = 256 * 1024 * 1024
"""The most bytes one marketplace copy may hold."""


class LocalMarketplaceCopier:
    """Declared by `interfaces/marketplace_fetcher_interface.py::MarketplaceFetcherInterface`."""

    def __init__(
        self,
        *,
        locker: CapabilityLockInterface | None = None,
        copier: SnapshotCopierInterface | None = None,
        max_entries: int = MAX_ENTRIES,
        max_bytes: int = MAX_BYTES,
    ) -> None:
        self._locker = locker or CapabilityLock()
        self._copier = copier or SnapshotCopier()
        self._max_entries = max_entries
        self._max_bytes = max_bytes

    def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
        if source.kind != "local":
            raise MarketplaceFetchError(f"{source.text} is not a local folder")
        if ref is not None:
            raise MarketplaceFetchError(f"{source.text}: a local folder has no ref to pin")
        root = Path(source.text)
        records = self._records(root)
        plan = [record for record in records if record.kind in COPIED_KINDS]
        left_out = tuple(record.path for record in records if record.kind not in COPIED_KINDS)
        try:
            self._copier.copy(
                root, plan, into, max_entries=self._max_entries, max_bytes=self._max_bytes
            )
        except CapabilityResolutionError as exc:
            raise MarketplaceFetchError(f"{root} cannot be copied: {exc}") from exc
        if self._records(into) != tuple(plan):
            raise MarketplaceFetchError(f"{root}: a file changed while it was copied; try again")
        return FetchResult(None, left_out)

    def _records(self, root: Path) -> tuple[TreeRecord, ...]:
        try:
            return self._locker.tree_records(root)
        except (LockError, OSError) as exc:
            raise MarketplaceFetchError(f"{root} cannot be read: {exc}") from exc
