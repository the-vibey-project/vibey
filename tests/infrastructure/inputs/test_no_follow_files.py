# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one no-follow file adapter the input store and the run folders share (SP-LOOPS Phase 3,
fix round 1: R-E, R-F, R-J). Every test works in pytest's own temporary folder."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from vibey.application.interfaces.run_folder_writer_interface import RunFolderWriterInterface
from vibey.domain.errors import InputStoreError
from vibey.infrastructure.inputs.interfaces.no_follow_files_interface import (
    NoFollowFilesInterface,
)
from vibey.infrastructure.inputs.no_follow_files import NoFollowFiles

FILES = NoFollowFiles()


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def test_the_adapter_meets_both_interfaces() -> None:
    assert isinstance(FILES, RunFolderWriterInterface)
    assert isinstance(FILES, NoFollowFilesInterface)


def test_made_folders_are_0700_and_written_files_0600(tmp_path: Path) -> None:
    folder = FILES.made(tmp_path, ("a", "b"))
    assert folder == tmp_path / "a" / "b"
    assert _mode(tmp_path / "a") == _mode(folder) == 0o700
    written = FILES.write(folder, "x.md", b"bytes")
    assert written == folder / "x.md"
    assert _mode(written) == 0o600
    assert written.read_bytes() == b"bytes"


def test_made_keeps_an_existing_folder_and_its_mode(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir(mode=0o755)
    (tmp_path / "a").chmod(0o755)
    assert FILES.made(tmp_path, ("a",)) == tmp_path / "a"
    assert _mode(tmp_path / "a") == 0o755


@pytest.mark.parametrize("depth", [1, 2])
def test_a_symlinked_folder_at_any_depth_is_refused(tmp_path: Path, depth: int) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    parts = ["a", "b"][:depth]
    planted = tmp_path.joinpath(*parts[:-1])
    planted.mkdir(parents=True, exist_ok=True)
    (planted / parts[-1]).symlink_to(outside)
    with pytest.raises(InputStoreError, match="symlink"):
        FILES.made(tmp_path, ("a", "b"))
    with pytest.raises(InputStoreError, match="symlink"):
        FILES.found(tmp_path, ("a", "b"))
    assert list(outside.iterdir()) == []


def test_a_root_that_is_not_a_folder_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="not a folder"):
        FILES.made(tmp_path / "missing", ("a",))


def test_a_folder_that_cannot_be_made_is_refused(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="cannot be made"):
        FILES.made(tmp_path, ("x" * 300,))  # longer than any file name a filesystem allows


def test_found_is_none_for_an_absent_part_and_makes_nothing(tmp_path: Path) -> None:
    assert FILES.found(tmp_path, ("a", "b")) is None
    assert not (tmp_path / "a").exists()
    (tmp_path / "a" / "b").mkdir(parents=True)
    assert FILES.found(tmp_path, ("a", "b")) == tmp_path / "a" / "b"


def test_found_refuses_a_file_where_a_folder_belongs(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"a file")
    with pytest.raises(InputStoreError, match="not a folder"):
        FILES.found(tmp_path, ("a", "b"))


def test_found_refuses_a_part_it_cannot_look_at(tmp_path: Path) -> None:
    with pytest.raises(InputStoreError, match="cannot be read"):
        FILES.found(tmp_path, ("x" * 300,))


def test_write_replaces_a_regular_file_and_refuses_a_symlink(tmp_path: Path) -> None:
    FILES.write(tmp_path, "x.md", b"one")
    FILES.write(tmp_path, "x.md", b"two")
    assert (tmp_path / "x.md").read_bytes() == b"two"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_bytes(b"untouched")
    (tmp_path / "link.md").symlink_to(elsewhere)
    with pytest.raises(InputStoreError, match="symlink"):
        FILES.write(tmp_path, "link.md", b"evil")
    assert elsewhere.read_bytes() == b"untouched"


@pytest.mark.parametrize("name", ["../escape", "a/b", "..", ""])
def test_write_refuses_a_name_that_is_not_one_segment(tmp_path: Path, name: str) -> None:
    with pytest.raises(InputStoreError, match="does not name a file"):
        FILES.write(tmp_path / "f", name, b"x")


def test_a_failed_write_leaves_no_temporary_file(tmp_path: Path) -> None:
    def failing(fd: int, data: bytes) -> int:
        raise OSError(28, "No space left on device")

    with pytest.raises(InputStoreError, match="cannot be written"):
        NoFollowFiles(write=failing).write(tmp_path, "x.md", b"bytes")
    assert list(tmp_path.iterdir()) == []


def test_a_partial_write_is_finished(tmp_path: Path) -> None:
    one_at_a_time = NoFollowFiles(write=lambda fd, data: os.write(fd, data[:1]))
    one_at_a_time.write(tmp_path, "x.md", b"bytes")
    assert (tmp_path / "x.md").read_bytes() == b"bytes"


def test_a_platform_without_o_nofollow_is_refused(tmp_path: Path) -> None:
    none = NoFollowFiles(nofollow=None)
    for act in (
        lambda: none.write(tmp_path, "x.md", b"x"),
        lambda: none.read(tmp_path / "x.md"),
        lambda: none.append(tmp_path / "x.md", b"x\n", max_bytes=10),
    ):
        with pytest.raises(InputStoreError, match="O_NOFOLLOW"):
            act()
    assert list(tmp_path.iterdir()) == []


def test_read_gives_the_bytes_none_when_absent_and_refuses_the_rest(tmp_path: Path) -> None:
    (tmp_path / "x").write_bytes(b"\x00\xff")
    assert FILES.read(tmp_path / "x") == b"\x00\xff"
    assert FILES.read(tmp_path / "missing") is None
    (tmp_path / "link").symlink_to(tmp_path / "x")
    with pytest.raises(InputStoreError, match="cannot be read"):
        FILES.read(tmp_path / "link")
    with pytest.raises(InputStoreError, match="not a regular file"):
        FILES.read(tmp_path)


def test_read_refuses_a_file_over_its_bound_from_its_size(tmp_path: Path) -> None:
    (tmp_path / "x").write_bytes(b"12345")
    assert FILES.read(tmp_path / "x", max_bytes=5) == b"12345"
    with pytest.raises(InputStoreError, match="is 5 bytes; at most 4"):
        FILES.read(tmp_path / "x", max_bytes=4)


def test_append_adds_one_line_0600(tmp_path: Path) -> None:
    index = tmp_path / "index.jsonl"
    FILES.append(index, b"one\n", max_bytes=100)
    FILES.append(index, b"two\n", max_bytes=100)
    assert index.read_bytes() == b"one\ntwo\n"
    assert _mode(index) == 0o600


def test_append_after_a_torn_line_ends_it_first(tmp_path: Path) -> None:
    index = tmp_path / "index.jsonl"
    index.write_bytes(b'one\n{"torn')
    FILES.append(index, b"two\n", max_bytes=100)
    assert index.read_bytes() == b'one\n{"torn\ntwo\n'


def test_append_counts_the_newline_it_adds_against_the_bound(tmp_path: Path) -> None:
    index = tmp_path / "index.jsonl"
    index.write_bytes(b"torn")
    with pytest.raises(InputStoreError, match="5 bytes; at most 4"):
        FILES.append(index, b"abc\n", max_bytes=4)
    assert index.read_bytes() == b"torn"


def test_a_short_append_is_refused_rather_than_left_half_said(tmp_path: Path) -> None:
    short = NoFollowFiles(write=lambda fd, data: os.write(fd, data[:2]))
    with pytest.raises(InputStoreError, match="short write"):
        short.append(tmp_path / "index.jsonl", b"line\n", max_bytes=100)


def test_append_refuses_a_symlink_and_a_folder(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.write_bytes(b"")
    (tmp_path / "link").symlink_to(target)
    with pytest.raises(InputStoreError, match="cannot be written"):
        FILES.append(tmp_path / "link", b"x\n", max_bytes=10)
    assert target.read_bytes() == b""
    (tmp_path / "folder").mkdir()
    with pytest.raises(InputStoreError, match="cannot be written"):
        FILES.append(tmp_path / "folder", b"x\n", max_bytes=10)
    with pytest.raises(InputStoreError, match="not a regular file"):
        FILES.append(Path(os.devnull), b"x\n", max_bytes=10)
