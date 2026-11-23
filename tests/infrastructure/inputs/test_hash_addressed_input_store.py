# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hash-addressed, append-only input store (SP-LOOPS Phase 3, Task 2).

Every test works in pytest's own temporary folder: no network, no clock but a fixed one, no
thread. Module-level test functions: the class-and-interface rule is about production code
(ADR-0016).
"""

from __future__ import annotations

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

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


class _Clock:
    def now(self) -> datetime:
        return AT


def _store(**kwargs: object) -> HashAddressedInputStore:
    return HashAddressedInputStore(_Clock(), **kwargs)  # type: ignore[arg-type]


def _objects(folder: Path) -> list[Path]:
    root = folder / "inputs" / "objects"
    return sorted(p for p in root.rglob("*") if p.is_file()) if root.exists() else []


def _index_lines(folder: Path) -> list[str]:
    index = folder / "inputs" / "index.jsonl"
    return index.read_text().splitlines() if index.exists() else []


def test_the_store_meets_both_interfaces() -> None:
    store = _store()
    assert isinstance(store, InputStoreInterface)
    assert isinstance(store, HashAddressedInputStoreInterface)


def test_put_twice_with_the_same_bytes_makes_one_object_and_two_index_lines(
    tmp_path: Path,
) -> None:
    store = _store()
    first = store.put(tmp_path, "file", "spec.md", b"same bytes")
    second = store.put(tmp_path, "file", "copy.md", b"same bytes")
    assert first.digest == second.digest == digest_of(b"same bytes")
    objects = _objects(tmp_path)
    assert objects == [tmp_path / "inputs" / "objects" / first.digest[:2] / first.digest]
    lines = [json.loads(line) for line in _index_lines(tmp_path)]
    assert lines == [
        {
            "digest": first.digest,
            "kind": "file",
            "name": "spec.md",
            "size": 10,
            "at": AT.isoformat(),
        },
        {
            "digest": first.digest,
            "kind": "file",
            "name": "copy.md",
            "size": 10,
            "at": AT.isoformat(),
        },
    ]
    assert first == RunInput(digest=first.digest, kind="file", name="spec.md", size=10)


def test_get_returns_the_exact_bytes_nul_and_invalid_utf8_included(tmp_path: Path) -> None:
    store = _store()
    data = b"\x00\xff\xfe raw \x00"
    item = store.put(tmp_path, "paste", "paste", data)
    assert store.get(tmp_path, item.digest) == data


def test_the_folders_are_0700_and_the_files_0600(tmp_path: Path) -> None:
    store = _store()
    item = store.put(tmp_path, "paste", "paste", b"hi")
    inputs = tmp_path / "inputs"
    for folder in (inputs, inputs / "objects", inputs / "objects" / item.digest[:2]):
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700, folder
    for file in (inputs / "index.jsonl", inputs / "objects" / item.digest[:2] / item.digest):
        assert stat.S_IMODE(file.stat().st_mode) == 0o600, file


def test_a_symlink_at_the_object_path_is_refused_and_nothing_is_written(
    tmp_path: Path,
) -> None:
    store = _store()
    data = b"the bytes"
    digest = digest_of(data)
    shard = tmp_path / "inputs" / "objects" / digest[:2]
    shard.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_bytes(b"untouched")
    (shard / digest).symlink_to(elsewhere)
    with pytest.raises(InputStoreError, match="not a regular file"):
        store.put(tmp_path, "file", "x.md", data)
    assert elsewhere.read_bytes() == b"untouched"
    assert _index_lines(tmp_path) == []


def test_a_symlinked_inputs_folder_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / "inputs").symlink_to(target)
    with pytest.raises(InputStoreError, match="not a folder"):
        _store().put(tmp_path, "paste", "paste", b"x")
    assert list(target.iterdir()) == []


def test_an_index_line_longer_than_the_limit_is_refused_before_anything_is_written(
    tmp_path: Path,
) -> None:
    store = _store()
    with pytest.raises(InputStoreError, match="index line"):
        store.put(tmp_path, "file", "n" * MAX_INDEX_LINE_BYTES, b"x")
    assert _objects(tmp_path) == []
    assert _index_lines(tmp_path) == []
    assert MAX_INDEX_LINE_BYTES == 4096


def test_the_line_limit_is_a_setting(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="index line"):
        _store(max_index_line_bytes=64).put(tmp_path, "file", "spec.md", b"x")


def test_listed_gives_the_items_in_add_order(tmp_path: Path) -> None:
    store = _store()
    first = store.put(tmp_path, "paste", "paste", b"one")
    second = store.put(tmp_path, "file", "b.txt", b"two")
    listing = store.listed(tmp_path)
    assert listing.items == (first, second)
    assert listing.skipped == 0


def test_listed_with_no_index_is_empty(tmp_path: Path) -> None:
    listing = _store().listed(tmp_path)
    assert listing.items == ()
    assert listing.skipped == 0


def test_listed_skips_a_torn_last_line_with_a_count_and_never_raises(tmp_path: Path) -> None:
    store = _store()
    kept = store.put(tmp_path, "paste", "paste", b"kept")
    with (tmp_path / "inputs" / "index.jsonl").open("ab") as handle:
        handle.write(b'{"digest": "ab')  # a crash mid-append: no newline
    listing = store.listed(tmp_path)
    assert listing.items == (kept,)
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
    ],
)
def test_listed_skips_a_line_it_cannot_read_as_a_row(tmp_path: Path, line: bytes) -> None:
    store = _store()
    kept = store.put(tmp_path, "paste", "paste", b"kept")
    with (tmp_path / "inputs" / "index.jsonl").open("ab") as handle:
        handle.write(line)
    listing = store.listed(tmp_path)
    assert listing.items == (kept,)
    assert listing.skipped == 1


def test_get_of_a_digest_that_is_not_one_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="not a digest"):
        _store().get(tmp_path, "../../etc/passwd")


def test_get_of_a_missing_object_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="no stored input"):
        _store().get(tmp_path, digest_of(b"never stored"))


def test_get_of_an_object_whose_bytes_changed_is_refused(tmp_path: Path) -> None:
    store = _store()
    item = store.put(tmp_path, "paste", "paste", b"original")
    path = tmp_path / "inputs" / "objects" / item.digest[:2] / item.digest
    path.chmod(0o600)
    path.write_bytes(b"tampered")
    with pytest.raises(InputStoreError, match="does not match its digest"):
        store.get(tmp_path, item.digest)


def test_get_of_a_symlinked_object_is_refused(tmp_path: Path) -> None:
    store = _store()
    data = b"bytes"
    digest = digest_of(data)
    shard = tmp_path / "inputs" / "objects" / digest[:2]
    shard.mkdir(parents=True)
    other = tmp_path / "other"
    other.write_bytes(data)
    (shard / digest).symlink_to(other)
    with pytest.raises(InputStoreError, match="cannot be read"):
        store.get(tmp_path, digest)


def test_a_file_where_a_folder_belongs_is_refused(tmp_path: Path) -> None:
    (tmp_path / "inputs").write_bytes(b"not a folder")
    with pytest.raises(InputStoreError, match="not a folder"):
        _store().put(tmp_path, "paste", "paste", b"x")


def test_a_folder_that_cannot_be_made_is_refused_naming_it(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_bytes(b"a file, so nothing can be made under it")
    with pytest.raises(InputStoreError, match="cannot be made"):
        _store().put(blocked / "deeper", "paste", "paste", b"x")


def test_an_index_that_is_not_a_regular_file_is_refused(tmp_path: Path) -> None:
    store = _store()
    store.put(tmp_path, "paste", "paste", b"x")
    index = tmp_path / "inputs" / "index.jsonl"
    index.unlink()
    index.mkdir()
    with pytest.raises(InputStoreError, match="cannot be read"):
        store.listed(tmp_path)
    with pytest.raises(InputStoreError, match="cannot be written"):
        store.put(tmp_path, "paste", "paste", b"y")


def test_a_short_index_write_is_refused_rather_than_left_half_said(tmp_path: Path) -> None:
    store = _store(write=lambda fd, data: os.write(fd, data[:3]))
    with pytest.raises(InputStoreError, match="short write"):
        store.put(tmp_path, "paste", "paste", b"x")


def test_an_object_write_that_fails_leaves_no_temporary_file(tmp_path: Path) -> None:
    def failing(fd: int, data: bytes) -> int:
        raise OSError(28, "No space left on device")

    store = _store(write=failing)
    with pytest.raises(InputStoreError, match="cannot be written"):
        store.put(tmp_path, "paste", "paste", b"x")
    assert _objects(tmp_path) == []
    assert _index_lines(tmp_path) == []
