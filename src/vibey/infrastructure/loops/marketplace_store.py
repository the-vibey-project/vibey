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
from vibey.domain.marketplace_source import MARKETPLACE_SOURCE_RULE
from vibey.infrastructure.loops.interfaces.marketplace_fetcher_interface import (
    MarketplaceFetcherInterface,
)
from vibey.infrastructure.loops.local_marketplace_copier import MAX_BYTES
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.records import MarketplaceUpdate

LOCK_FILE: Final = "lock.json"
MARKETPLACES: Final = "marketplaces"
SNAPSHOTS: Final = "snapshots"
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
        self.marketplaces.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.marketplaces, 0o700)
        staging = Path(tempfile.mkdtemp(prefix=_STAGING, dir=self.marketplaces))
        try:
            tree = staging / _TREE
            fetched = self._fetchers[source.kind].fetch(source, spec.ref, tree)
            digest = self._checked(spec.name, tree)
            root, made = self._placed(spec.name, tree, digest)
            entry = LockEntry(spec.name, spec.source, spec.ref, digest)
            try:
                self._locker.update(self.lock_path, put=[entry])
            except (LockError, OSError) as exc:
                if made:
                    shutil.rmtree(root, ignore_errors=True)
                raise MarketplaceFetchError(f"{spec.name} cannot be locked: {exc}") from exc
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        self._forget(spec.name, keep=root)
        return MarketplaceUpdate(entry, root, fetched)

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

    def _forget(self, name: str, *, keep: Path) -> None:
        """Removes every other copy of `name`: the lock no longer names them."""
        for folder in (self.marketplaces / name).iterdir():
            if folder != keep:
                shutil.rmtree(folder, ignore_errors=True)

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
