# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The marketplace store under the person's configuration folder (SP-LOOPS Task 7).

`update` fetches into a private staging folder, checks what arrived, moves it into place and only
then writes the lock; a failure at any step leaves the old copy and the old lock as they were.
"""

from __future__ import annotations

import json
import stat
from collections.abc import Collection, Sequence
from pathlib import Path

import pytest
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec

from vibey.domain.marketplace_source import MarketplaceSource, MarketplaceSourceError
from vibey.infrastructure.loops.interfaces.marketplace_store_interface import (
    MarketplaceStoreInterface,
)
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.marketplace_store import MarketplaceStore
from vibey.infrastructure.loops.records import FetchResult

ACME = MarketplaceSpec("acme", "https://example.test/acme.git", "v1")
COMMIT = "a" * 40


def _manifest(plugins: Sequence[str] = ("lint",)) -> str:
    return json.dumps(
        {
            "name": "acme",
            "plugins": [{"name": p, "source": f"./plugins/{p}", "description": p} for p in plugins],
        }
    )


class FakeFetcher:
    """Plays a fetch: writes `files` into the staging folder, or raises `error`."""

    def __init__(self, files: dict[str, str] | None = None, error: Exception | None = None) -> None:
        self.files = (
            files
            if files is not None
            else {
                ".claude-plugin/marketplace.json": _manifest(),
                "plugins/lint/README.md": "# lint\n",
            }
        )
        self.error = error
        self.calls: list[tuple[MarketplaceSource, str | None, Path]] = []

    def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
        self.calls.append((source, ref, into))
        into.mkdir(mode=0o700)
        for relative, text in self.files.items():
            (into / relative).parent.mkdir(parents=True, exist_ok=True)
            (into / relative).write_text(text, encoding="utf-8")
        if self.error is not None:
            raise self.error
        return FetchResult(COMMIT, ())


def _store(tmp_path: Path, fetcher: FakeFetcher, **options: object) -> MarketplaceStore:
    return MarketplaceStore(
        tmp_path / "loops",
        fetchers={"git": fetcher, "local": fetcher},
        shipped_root=lambda: tmp_path / "wheel" / "marketplace",
        **options,  # type: ignore[arg-type]
    )


def _children(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else []


def test_the_store_satisfies_its_interface(tmp_path: Path) -> None:
    assert isinstance(_store(tmp_path, FakeFetcher()), MarketplaceStoreInterface)


def test_its_folders_are_under_the_one_it_was_given(tmp_path: Path) -> None:
    store = _store(tmp_path, FakeFetcher())
    assert store.lock_path == tmp_path / "loops" / "lock.json"
    assert store.snapshots == tmp_path / "loops" / "snapshots"
    assert store.marketplaces == tmp_path / "loops" / "marketplaces"
    assert store.shipped_root() == tmp_path / "wheel" / "marketplace"


def test_the_store_folder_must_be_absolute(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="absolute"):
        MarketplaceStore(Path("loops"), fetchers={}, shipped_root=lambda: tmp_path)


def test_an_update_stores_the_verified_tree_and_then_locks_it(tmp_path: Path) -> None:
    fetcher = FakeFetcher()
    store = _store(tmp_path, fetcher)
    update = store.update(ACME)
    digest = CapabilityLock().digest_tree(update.root)
    assert update.entry == LockEntry("acme", ACME.source, "v1", digest)
    assert update.root == store.marketplaces / "acme" / digest.removeprefix("sha256:")
    assert update.fetched == FetchResult(COMMIT, ())
    assert CapabilityLock().read(store.lock_path) == (update.entry,)
    assert (update.root / "plugins/lint/README.md").read_text(encoding="utf-8") == "# lint\n"
    assert _children(store.marketplaces) == ["acme"]  # no staging folder is left
    assert stat.S_IMODE(store.marketplaces.stat().st_mode) == 0o700
    (source, ref, into) = fetcher.calls[0]
    assert (source.kind, source.protocol, ref) == ("git", "https", "v1")
    assert into.parent.parent == store.marketplaces and into.name == "tree"
    assert store.locked() == (update.entry,)
    assert store.roots(store.locked()) == {
        "acme": update.root,
        "vibey": tmp_path / "wheel" / "marketplace",
    }


def test_a_local_folder_source_goes_to_the_local_fetcher(tmp_path: Path) -> None:
    git, local = FakeFetcher(), FakeFetcher()
    store = MarketplaceStore(
        tmp_path / "loops", fetchers={"git": git, "local": local}, shipped_root=lambda: tmp_path
    )
    store.update(MarketplaceSpec("mine", "/srv/marketplace", None))
    assert (git.calls, [c[0].kind for c in local.calls]) == ([], ["local"])


@pytest.mark.parametrize(
    "spec",
    [
        MarketplaceSpec("acme", "ext::sh -c x", None),
        MarketplaceSpec("acme", "file:///srv/x", None),
        MarketplaceSpec("acme", "https://example.test/x.git", "--upload-pack=x"),
    ],
)
def test_a_source_or_ref_vibey_will_not_fetch_is_refused_before_any_fetch(
    tmp_path: Path, spec: MarketplaceSpec
) -> None:
    fetcher = FakeFetcher()
    with pytest.raises(MarketplaceSourceError):
        _store(tmp_path, fetcher).update(spec)
    assert fetcher.calls == []


def _locked_once(tmp_path: Path) -> tuple[MarketplaceStore, bytes, Path]:
    store = _store(tmp_path, FakeFetcher())
    first = store.update(ACME)
    return store, store.lock_path.read_bytes(), first.root


@pytest.mark.parametrize(
    ("fetcher", "reason"),
    [
        (FakeFetcher(error=MarketplaceFetchError("git fetch failed")), "git fetch failed"),
        (FakeFetcher(files={"README.md": "no manifest"}), "is not a marketplace"),
        (
            FakeFetcher(files={".claude-plugin/marketplace.json": "{not json"}),
            "is not a marketplace",
        ),
        (FakeFetcher(files={"big.bin": "x" * 64}), "more than 32 bytes"),
    ],
)
def test_a_failed_update_leaves_the_old_copy_and_the_old_lock(
    tmp_path: Path, fetcher: FakeFetcher, reason: str
) -> None:
    store, lock_before, old_root = _locked_once(tmp_path)
    failing = _store(tmp_path, fetcher, max_bytes=32)
    with pytest.raises(MarketplaceFetchError, match=reason):
        failing.update(ACME)
    assert store.lock_path.read_bytes() == lock_before
    assert (old_root / "plugins/lint/README.md").is_file()
    assert _children(store.marketplaces) == ["acme"]
    assert _children(store.marketplaces / "acme") == [old_root.name]


def test_a_new_tree_replaces_the_old_copy_once_it_is_locked(tmp_path: Path) -> None:
    store, _, old_root = _locked_once(tmp_path)
    newer = FakeFetcher(
        files={".claude-plugin/marketplace.json": _manifest(("lint", "fmt")), "plugins/x": "y"}
    )
    update = _store(tmp_path, newer).update(ACME)
    assert update.root != old_root
    assert _children(store.marketplaces / "acme") == [update.root.name]
    assert CapabilityLock().read(store.lock_path) == (update.entry,)


def test_the_same_tree_again_keeps_its_folder(tmp_path: Path) -> None:
    store, lock_before, old_root = _locked_once(tmp_path)
    assert store.update(ACME).root == old_root
    assert store.lock_path.read_bytes() == lock_before


def test_a_damaged_copy_of_the_same_tree_is_replaced(tmp_path: Path) -> None:
    store, _, old_root = _locked_once(tmp_path)
    (old_root / "plugins/lint/README.md").write_text("tampered\n", encoding="utf-8")
    update = store.update(ACME)
    assert update.root == old_root
    assert (old_root / "plugins/lint/README.md").read_text(encoding="utf-8") == "# lint\n"


def test_a_lock_that_cannot_be_written_removes_the_new_copy_and_keeps_the_old(
    tmp_path: Path,
) -> None:
    store, lock_before, old_root = _locked_once(tmp_path)

    class Refusing(CapabilityLock):
        def update(
            self, path: Path, put: Sequence[LockEntry] = (), drop: Collection[str] = ()
        ) -> tuple[LockEntry, ...]:
            raise PermissionError(13, "Permission denied", str(path))

    newer = FakeFetcher(files={".claude-plugin/marketplace.json": _manifest(()), "n": "n"})
    with pytest.raises(MarketplaceFetchError, match="cannot be locked: .*Permission denied"):
        _store(tmp_path, newer, locker=Refusing()).update(ACME)
    assert store.lock_path.read_bytes() == lock_before
    assert _children(store.marketplaces / "acme") == [old_root.name]


def test_a_tree_that_cannot_be_listed_is_refused(tmp_path: Path) -> None:
    import os

    fetcher = FakeFetcher(
        files={".claude-plugin/marketplace.json": _manifest(()), "plugins/.keep": ""}
    )

    class WithFifo(FakeFetcher):
        def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
            result = fetcher.fetch(source, ref, into)
            os.mkfifo(into / "pipe")
            return result

    store = _store(tmp_path, WithFifo())
    with pytest.raises(MarketplaceFetchError, match="cannot be locked: .*not a file, folder"):
        store.update(ACME)
    assert not store.lock_path.exists()
    assert _children(store.marketplaces) == []


def test_roots_name_only_locked_person_added_marketplaces_and_the_shipped_one(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, FakeFetcher())
    digest = "sha256:" + "b" * 64
    entries = (
        LockEntry("vibey", "vibey-engine 1.0.0", None, "sha256:" + "c" * 64),
        LockEntry("acme", ACME.source, "v1", digest),
    )
    assert store.roots(entries, declared=["acme", "beta"]) == {
        "vibey": tmp_path / "wheel" / "marketplace",
        "acme": store.marketplaces / "acme" / ("b" * 64),
        "beta": store.marketplaces / "beta",
    }


def test_a_lock_failure_keeps_a_copy_the_update_did_not_make(tmp_path: Path) -> None:
    store, lock_before, old_root = _locked_once(tmp_path)

    class Refusing(CapabilityLock):
        def update(
            self, path: Path, put: Sequence[LockEntry] = (), drop: Collection[str] = ()
        ) -> tuple[LockEntry, ...]:
            raise LockError(f"{path}: checksum does not match its entries")

    with pytest.raises(MarketplaceFetchError, match="cannot be locked: .*checksum"):
        _store(tmp_path, FakeFetcher(), locker=Refusing()).update(ACME)
    assert (old_root / "plugins/lint/README.md").is_file()
    assert store.lock_path.read_bytes() == lock_before


def test_a_copy_of_the_same_name_that_cannot_be_hashed_is_replaced(tmp_path: Path) -> None:
    import os

    store, _, old_root = _locked_once(tmp_path)
    os.mkfifo(old_root / "pipe")
    assert store.update(ACME).root == old_root
    assert not (old_root / "pipe").exists()
