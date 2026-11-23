# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The marketplaces a person added, fetched and locked on their word (SP-LOOPS Task 7; design
Decision 1; Review Focus 3).

Everything lives in one folder of the person's own, `<configuration folder>/loops` (never the
folder vibey runs in): `lock.json` (`CapabilityLock`), `marketplaces/<name>/<digest hex>/` (one
fetched tree per marketplace, named by what it hashed to) and `snapshots/run-*/` (each run's
verified copy, made by `CapabilityResolver`).

**An update commits at the lock.** `update` fetches into a fresh 0700 staging folder inside
`marketplaces/` (a git source through `GitMarketplaceFetcher`, an absolute folder through
`LocalMarketplaceCopier`, chosen by `MarketplaceSourceRule`, which refuses anything else before
any fetch), then checks what arrived: at most `max_bytes`, a tree `CapabilityLock` can hash (no
FIFO or device, at most its entry cap) and a manifest `MarketplaceManifest` reads. Only then is the
tree renamed into `marketplaces/<name>/<digest hex>` and the lock entry -- marketplace, source, ref,
digest -- written (`CapabilityLock.update`, under its file lock). A copy the lock does not name
yet is never read by a run, so a failure at any step leaves the old copy and the old lock as they
were; the staging folder is always removed, and so is the new copy when the lock cannot be
written. Once the lock names the new copy the older ones are removed.

The size cap is checked after the fetch, so a hostile remote can still fill the disk for as long
as git's deadline allows; the fetch is shallow and of one ref. Declared by
`interfaces/marketplace_store_interface.py::MarketplaceStoreInterface`.
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.defaults import DEFAULT_MARKETPLACE_NAME
from vibey_runners.common.capabilities.interfaces.lock_interface import CapabilityLockInterface
from vibey_runners.common.capabilities.interfaces.manifest_interface import (
    MarketplaceManifestInterface,
)
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.manifest import MarketplaceManifest
from vibey_runners.common.capabilities.manifest_error import ManifestError
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec

from vibey.domain.interfaces.marketplace_source_interface import MarketplaceSourceRuleInterface
from vibey.domain.marketplace_source import MARKETPLACE_SOURCE_RULE, MarketplaceSource
from vibey.infrastructure.loops.git_marketplace_fetcher import TIMEOUT_SECONDS
from vibey.infrastructure.loops.interfaces.marketplace_fetcher_interface import (
    MarketplaceFetcherInterface,
)
from vibey.infrastructure.loops.local_marketplace_copier import MAX_BYTES
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.records import MarketplaceUpdate

LOCK_FILE: Final = "lock.json"
MARKETPLACES: Final = "marketplaces"
SNAPSHOTS: Final = "snapshots"
STALE_STAGING_SECONDS: Final = 2 * TIMEOUT_SECONDS
"""A staging folder this old outlived any fetch: a killed update left it, and the next removes it."""
_STAGING: Final = ".staging-"
_TREE: Final = "tree"


class MarketplaceStore:
    """Declared by `interfaces/marketplace_store_interface.py::MarketplaceStoreInterface`."""

    def __init__(
        self,
        folder: Path,
        *,
        fetchers: Mapping[str, MarketplaceFetcherInterface],
        shipped_root: Callable[[], Path],
        locker: CapabilityLockInterface | None = None,
        manifest: MarketplaceManifestInterface | None = None,
        rule: MarketplaceSourceRuleInterface = MARKETPLACE_SOURCE_RULE,
        max_bytes: int = MAX_BYTES,
        clock: Callable[[], float] = time.time,
        stale_seconds: float = STALE_STAGING_SECONDS,
    ) -> None:
        if not folder.is_absolute():
            raise ValueError(f"the loops store must be an absolute folder, not {folder}")
        self._folder = folder
        self._fetchers = fetchers
        self._shipped_root = shipped_root
        self._locker = locker or CapabilityLock()
        self._manifest = manifest or MarketplaceManifest()
        self._rule = rule
        self._max_bytes = max_bytes
        self._clock = clock
        self._stale = stale_seconds

    @property
    def lock_path(self) -> Path:
        return self._folder / LOCK_FILE

    @property
    def marketplaces(self) -> Path:
        return self._folder / MARKETPLACES

    @property
    def snapshots(self) -> Path:
        return self._folder / SNAPSHOTS

    def shipped_root(self) -> Path:
        return self._shipped_root()

    def locked(self) -> tuple[LockEntry, ...]:
        return self._locker.read(self.lock_path)

    def update(self, spec: MarketplaceSpec) -> MarketplaceUpdate:
        source = self._rule.classify(spec.source)
        if spec.ref is not None:
            self._rule.check_ref(spec.ref)
        try:
            return self._update(spec, source)
        except OSError as exc:  # the store's own folders: a full disk, a folder not yours, ...
            raise MarketplaceFetchError(f"{spec.name} cannot be updated: {exc}") from exc

    def _update(self, spec: MarketplaceSpec, source: MarketplaceSource) -> MarketplaceUpdate:
        self.marketplaces.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.marketplaces, 0o700)
        self._sweep()
        staging = Path(tempfile.mkdtemp(prefix=_STAGING, dir=self.marketplaces))
        try:
            fetched = self._fetchers[source.kind].fetch(source, spec.ref, staging / _TREE)
            digest = self._checked(spec.name, staging / _TREE)
            entry = LockEntry(spec.name, spec.source, spec.ref, digest)
            try:
                with self._locker.exclusive(self.lock_path):
                    root = self._committed(spec.name, staging / _TREE, entry)
            except LockError as exc:  # another update held the lock past the bounded wait
                raise MarketplaceFetchError(f"{spec.name} cannot be locked: {exc}") from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return MarketplaceUpdate(entry, root, fetched)

    def _committed(self, name: str, tree: Path, entry: LockEntry) -> Path:
        """Under the lock's own file lock: the copy placed, its entry written, and only then
        every copy the lock no longer names removed. Neither of two overlapping updates can
        remove the copy the lock names when the other finishes."""
        root, made = self._placed(name, tree, entry.digest)
        try:
            self._locker.update(self.lock_path, put=[entry])
        except (LockError, OSError) as exc:
            if made:
                shutil.rmtree(root, ignore_errors=True)
            raise MarketplaceFetchError(f"{name} cannot be locked: {exc}") from exc
        self._forget(name)
        return root

    def roots(self, lock: Sequence[LockEntry], declared: Iterable[str] = ()) -> dict[str, Path]:
        roots = {name: self.marketplaces / name for name in declared}
        roots[DEFAULT_MARKETPLACE_NAME] = self._shipped_root()
        for entry in lock:
            if entry.marketplace != DEFAULT_MARKETPLACE_NAME:
                roots[entry.marketplace] = self._version(entry.marketplace, entry.digest)
        return roots

    # -- the steps of an update ----------------------------------------------------------------

    def _checked(self, name: str, tree: Path) -> str:
        """The tree's digest, once it is small enough, hashable and a marketplace."""
        size = self._size(tree)
        if size > self._max_bytes:
            raise MarketplaceFetchError(
                f"{name} holds more than {self._max_bytes} bytes ({size}); it is not stored"
            )
        try:
            digest = self._locker.digest_tree(tree)
        except (LockError, OSError) as exc:
            raise MarketplaceFetchError(f"{name} cannot be locked: {exc}") from exc
        try:
            self._manifest.read(tree)
        except (ManifestError, ValueError, RuntimeError) as exc:
            raise MarketplaceFetchError(f"{name} is not a marketplace: {exc}") from exc
        return digest

    def _placed(self, name: str, tree: Path, digest: str) -> tuple[Path, bool]:
        """`tree` moved to its version folder, and whether this update made that folder. A
        folder already there with the same digest is kept; one whose content no longer hashes
        to its name is replaced."""
        root = self._version(name, digest)
        root.parent.mkdir(mode=0o700, exist_ok=True)
        if root.exists():
            try:
                if self._locker.digest_tree(root) == digest:
                    return root, False
            except (LockError, OSError):
                pass  # a copy that cannot even be hashed is replaced like a changed one
            shutil.rmtree(root)
        os.rename(tree, root)
        return root, True

    def _forget(self, name: str) -> None:
        """Removes every copy of `name` the lock, read again now, does not name. A lock that
        cannot be read removes nothing."""
        try:
            named = {
                entry.digest.removeprefix("sha256:")
                for entry in self._locker.read(self.lock_path)
                if entry.marketplace == name
            }
        except LockError:
            return
        for folder in (self.marketplaces / name).iterdir():
            if folder.name not in named:
                shutil.rmtree(folder, ignore_errors=True)

    def _sweep(self) -> None:
        """Removes `.staging-*` folders an update left behind when it was killed: those older
        than `stale_seconds`, which is past any fetch's deadline. A symlink or file is left."""
        cutoff = self._clock() - self._stale
        for entry in os.scandir(self.marketplaces):
            if not entry.name.startswith(_STAGING):
                continue
            status = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(status.st_mode) and status.st_mtime < cutoff:
                shutil.rmtree(entry.path, ignore_errors=True)

    def _version(self, name: str, digest: str) -> Path:
        return self.marketplaces / name / digest.removeprefix("sha256:")

    @staticmethod
    def _size(tree: Path) -> int:
        """Bytes of the regular files under `tree`, never following a link."""
        total = 0
        for folder, _, files in os.walk(tree):
            for file in files:
                status = os.lstat(Path(folder) / file)
                if stat.S_ISREG(status.st_mode):
                    total += status.st_size
        return total
