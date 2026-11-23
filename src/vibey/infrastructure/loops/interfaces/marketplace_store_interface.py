# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the marketplace store in the person's configuration folder (SP-LOOPS Task 7).

Implemented by `marketplace_store.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec

from vibey.infrastructure.loops.records import MarketplaceUpdate


@runtime_checkable
class MarketplaceStoreInterface(Protocol):
    @property
    def lock_path(self) -> Path:
        """The person's lock file: `<store>/lock.json`."""
        ...

    @property
    def marketplaces(self) -> Path:
        """Where fetched marketplaces live: `<store>/marketplaces/<name>/<digest hex>/`."""
        ...

    @property
    def snapshots(self) -> Path:
        """Where each run's verified copy is made: `<store>/snapshots/run-*/`."""
        ...

    def shipped_root(self) -> Path:
        """The marketplace that ships in the installed wheel."""
        ...

    def locked(self) -> tuple[LockEntry, ...]:
        """What the lock file holds (none when there is no lock yet). Raises `LockError` for a
        lock that cannot be read whole."""
        ...

    def update(self, spec: MarketplaceSpec) -> MarketplaceUpdate:
        """Fetches `spec` (the only call that may reach the network) into a 0700 staging folder,
        checks it -- at most `max_bytes`, a tree the lock can hash, a manifest that reads --
        moves it to `marketplaces/<name>/<digest hex>`, writes its lock entry (marketplace,
        source, ref, digest) and only then removes the copies the lock no longer names. Raises
        `MarketplaceSourceError` for a source or ref vibey will not fetch (before any fetch) and
        `MarketplaceFetchError` for anything else; a failure leaves the old copy and the old
        lock as they were."""
        ...

    def roots(self, lock: Sequence[LockEntry], declared: Iterable[str] = ()) -> dict[str, Path]:
        """The folder each marketplace is read from, for `CapabilityResolver.resolve`: a locked
        person-added one's copy named by its locked digest, the shipped one's folder, and for a
        `declared` one with no lock entry its folder in the store (never read: the resolver
        refuses an unlocked marketplace first, naming `marketplace update`)."""
        ...
