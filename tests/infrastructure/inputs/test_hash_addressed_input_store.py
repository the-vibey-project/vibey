# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hash-addressed, append-only input store (SP-LOOPS Phase 3, Task 2; fix round 1: R-A, R-D,
R-F). The store's root stands in for the person's state folder in pytest's temporary folder: no
network, a fixed clock, no thread. Module-level test functions: the class-and-interface rule is
about production code (ADR-0016).
"""

from __future__ import annotations

import json
import stat
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from vibey.application.interfaces.input_store_interface import InputStoreInterface
from vibey.domain.errors import InputStoreError
from vibey.domain.run_input import RunInput, digest_of
from vibey.infrastructure.inputs.hash_addressed_input_store import (
    MAX_INDEX_LINE_BYTES,
    HashAddressedInputStore,
)
from vibey.infrastructure.inputs.interfaces.input_store_interface import (
    HashAddressedInputStoreInterface,
)

AT = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
PID = UUID("6f1c2a0e-0000-4000-8000-000000000001")


class _Clock:
    def now(self) -> datetime:
        return AT


def _store(root: Path, **kwargs: object) -> HashAddressedInputStore:
    return HashAddressedInputStore(root / "state" / "inputs", _Clock(), **kwargs)  # type: ignore[arg-type]


def _folder(root: Path, project_id: UUID = PID) -> Path:
    return root / "state" / "inputs" / str(project_id)


def _objects(root: Path) -> list[Path]:
    objects = _folder(root) / "objects"
    return sorted(p for p in objects.rglob("*") if p.is_file()) if objects.exists() else []


def _index_lines(root: Path) -> list[str]:
    index = _folder(root) / "index.jsonl"
    return index.read_text().splitlines() if index.exists() else []


def test_the_store_meets_both_interfaces(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert isinstance(store, InputStoreInterface)
    assert isinstance(store, HashAddressedInputStoreInterface)


def test_the_store_is_keyed_by_project_id_under_its_root(tmp_path: Path) -> None:
    store = _store(tmp_path)
    other = uuid4()
    store.put(PID, "paste", "paste", b"mine")
    store.put(other, "paste", "paste", b"theirs")
    assert (_folder(tmp_path) / "index.jsonl").is_file()
    assert (_folder(tmp_path, other) / "index.jsonl").is_file()
    assert [i.size for i in store.listed(PID).items] == [4]
    assert [i.size for i in store.listed(other).items] == [6]


def test_put_twice_with_the_same_bytes_makes_one_object_and_two_index_lines(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    first = store.put(PID, "file", "spec.md", b"same bytes")
    second = store.put(PID, "file", "copy.md", b"same bytes")
    assert first.digest == second.digest == digest_of(b"same bytes")
    assert _objects(tmp_path) == [_folder(tmp_path) / "objects" / first.digest[:2] / first.digest]
    lines = [json.loads(line) for line in _index_lines(tmp_path)]
    assert lines == [
        {"digest": first.digest, "kind": "file", "name": n, "size": 10, "at": AT.isoformat()}
        for n in ("spec.md", "copy.md")
    ]
    assert first == RunInput(digest=first.digest, kind="file", name="spec.md", size=10)


def test_get_returns_the_exact_bytes_nul_and_invalid_utf8_included(tmp_path: Path) -> None:
    store = _store(tmp_path)
    data = b"\x00\xff\xfe raw \x00"
    item = store.put(PID, "paste", "paste", data)
    assert store.get(PID, item.digest, size=item.size) == data


def test_the_folders_are_0700_and_the_files_0600(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = store.put(PID, "paste", "paste", b"hi")
    folder = _folder(tmp_path)
    for path in (folder, folder / "objects", folder / "objects" / item.digest[:2]):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700, path
    for path in (folder / "index.jsonl", folder / "objects" / item.digest[:2] / item.digest):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600, path


def test_a_symlinked_project_folder_is_refused_for_put_listed_and_get(tmp_path: Path) -> None:
    # Review finding 1: no folder of the store is ever followed out of it.
    store = _store(tmp_path)
    item = store.put(uuid4(), "paste", "paste", b"x")  # makes the root
    outside = tmp_path / "outside"
    outside.mkdir()
    _folder(tmp_path).symlink_to(outside)
    with pytest.raises(InputStoreError, match="symlink"):
        store.put(PID, "paste", "paste", b"x")
    with pytest.raises(InputStoreError, match="symlink"):
        store.listed(PID)
    with pytest.raises(InputStoreError, match="symlink"):
        store.get(PID, item.digest, size=item.size)
    assert list(outside.iterdir()) == []


def test_a_symlink_at_the_object_path_is_refused_and_nothing_is_written(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    data = b"the bytes"
    digest = digest_of(data)
    shard = _folder(tmp_path) / "objects" / digest[:2]
    shard.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_bytes(b"untouched")
    (shard / digest).symlink_to(elsewhere)
    with pytest.raises(InputStoreError, match="cannot be read"):
        store.put(PID, "file", "x.md", data)
    assert elsewhere.read_bytes() == b"untouched"
    assert _index_lines(tmp_path) == []


def test_a_root_that_cannot_be_made_is_refused_naming_it(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_bytes(b"a file, so nothing can be made under it")
    store = HashAddressedInputStore(blocked / "inputs", _Clock())
    with pytest.raises(InputStoreError, match="the input store cannot be made"):
        store.put(PID, "paste", "paste", b"x")


def test_an_index_line_longer_than_the_limit_is_refused_before_anything_is_written(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    with pytest.raises(InputStoreError, match="index line"):
        store.put(PID, "file", "n" * MAX_INDEX_LINE_BYTES, b"x")
    assert _objects(tmp_path) == []
    assert _index_lines(tmp_path) == []
    assert MAX_INDEX_LINE_BYTES == 4096


def test_the_line_limit_is_a_setting(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="index line"):
        _store(tmp_path, max_index_line_bytes=64).put(PID, "file", "spec.md", b"x")


def test_listed_gives_the_items_in_add_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.put(PID, "paste", "paste", b"one")
    second = store.put(PID, "file", "b.txt", b"two")
    listing = store.listed(PID)
    assert listing.items == (first, second)
    assert listing.skipped == 0


def test_listed_for_a_project_with_no_store_is_empty_and_makes_nothing(tmp_path: Path) -> None:
    listing = _store(tmp_path).listed(PID)
    assert (listing.items, listing.skipped) == ((), 0)
    assert not (tmp_path / "state").exists()
    _folder(tmp_path).mkdir(parents=True)  # a folder with no index yet
    assert _store(tmp_path).listed(PID).items == ()


def test_listed_skips_a_torn_last_line_with_a_count_and_never_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    kept = store.put(PID, "paste", "paste", b"kept")
    with (_folder(tmp_path) / "index.jsonl").open("ab") as handle:
        handle.write(b'{"digest": "ab')  # a crash mid-append: no newline
    listing = store.listed(PID)
    assert listing.items == (kept,)
    assert listing.skipped == 1


def test_an_add_after_a_torn_line_is_kept_and_only_the_torn_line_is_skipped(
    tmp_path: Path,
) -> None:
    # Review finding 3 (R-F): the next add was merged into the torn line and lost.
    store = _store(tmp_path)
    first = store.put(PID, "paste", "paste", b"first")
    with (_folder(tmp_path) / "index.jsonl").open("ab") as handle:
        handle.write(b'{"digest": "ab')
    second = store.put(PID, "paste", "paste", b"second")
    listing = store.listed(PID)
    assert listing.items == (first, second)
    assert listing.skipped == 1


@pytest.mark.parametrize(
    "line",
    [
        b"not json\n",
        b"\xff\xfe\n",
        b"[1, 2]\n",
        b'{"digest": "short", "kind": "file", "name": "a", "size": 1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "image", "name": "a", "size": 1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "file", "name": 3, "size": 1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "file", "name": "a", "size": -1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "file", "name": "a", "size": true}\n',
        b'{"digest": 7, "kind": "file", "name": "a", "size": 1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "file", "name": "../escape", "size": 1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "file", "name": "a/b", "size": 1}\n',
        b'{"digest": "' + b"a" * 64 + b'", "kind": "file", "name": "..", "size": 1}\n',
    ],
)
def test_listed_skips_a_line_it_cannot_read_as_a_row(tmp_path: Path, line: bytes) -> None:
    store = _store(tmp_path)
    kept = store.put(PID, "paste", "paste", b"kept")
    with (_folder(tmp_path) / "index.jsonl").open("ab") as handle:
        handle.write(line)
    listing = store.listed(PID)
    assert listing.items == (kept,)
    assert listing.skipped == 1


def test_get_of_a_digest_that_is_not_one_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="not a digest"):
        _store(tmp_path).get(PID, "../../etc/passwd", size=1)


def test_get_of_a_missing_object_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(InputStoreError, match="no stored input"):
        store.get(PID, digest_of(b"never stored"), size=12)
    item = store.put(PID, "paste", "paste", b"something")
    with pytest.raises(InputStoreError, match="no stored input"):
        store.get(PID, item.digest[:2] + "0" * 62, size=1)  # its shard exists, the object not


def test_get_of_an_object_whose_bytes_changed_is_refused(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = store.put(PID, "paste", "paste", b"original")
    path = _folder(tmp_path) / "objects" / item.digest[:2] / item.digest
    path.write_bytes(b"tampered")  # the same length, other bytes
    with pytest.raises(InputStoreError, match="does not match its digest"):
        store.get(PID, item.digest, size=item.size)


def test_get_refuses_an_object_larger_than_its_row_before_reading_it(tmp_path: Path) -> None:
    # Review finding 2: an object is never read past the size its row gives.
    store = _store(tmp_path)
    item = store.put(PID, "paste", "paste", b"small")
    path = _folder(tmp_path) / "objects" / item.digest[:2] / item.digest
    path.write_bytes(b"x" * 100_000)
    with pytest.raises(InputStoreError, match="at most 5"):
        store.get(PID, item.digest, size=item.size)


def test_get_refuses_an_object_shorter_than_its_row(tmp_path: Path) -> None:
    store = _store(tmp_path)
    item = store.put(PID, "paste", "paste", b"original")
    path = _folder(tmp_path) / "objects" / item.digest[:2] / item.digest
    path.write_bytes(b"short")
    with pytest.raises(InputStoreError, match="does not match its digest"):
        store.get(PID, item.digest, size=item.size)


def test_adding_the_bytes_again_repairs_a_changed_object(tmp_path: Path) -> None:
    # Review finding 5 (R-D): E0094's fix, "add that input again", now works.
    store = _store(tmp_path)
    item = store.put(PID, "paste", "paste", b"original")
    path = _folder(tmp_path) / "objects" / item.digest[:2] / item.digest
    path.write_bytes(b"corrupted bytes")
    store.put(PID, "paste", "paste", b"original")
    assert store.get(PID, item.digest, size=item.size) == b"original"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
