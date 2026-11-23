# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Copying locked marketplace content into a run's own folder: bytes, never a hard link, never a
symlink, inside caps, private to the person (SP-LOOPS Task 6)."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

import pytest

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.interfaces.snapshot_copier_interface import (
    SnapshotCopierInterface,
)
from vibey_runners.common.capabilities.snapshot_copier import SnapshotCopier
from vibey_runners.common.capabilities.tree_record import TreeRecord

BIG = 1 << 30


def _file(path: Path, content: bytes, mode: int = 0o644) -> TreeRecord:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(mode)
    return TreeRecord("", "X" if mode & stat.S_IXUSR else "F", hashlib.sha256(content).hexdigest())


def _source(tmp_path: Path) -> tuple[Path, list[TreeRecord]]:
    source = tmp_path / "market"
    plain = _file(source / "plugins/p/README.md", b"read me")
    tool = _file(source / "plugins/p/bin/tool", b"#!/bin/sh\n", 0o755)
    plan = [
        TreeRecord("plugins", "D", ""),
        TreeRecord("plugins/p", "D", ""),
        TreeRecord("plugins/p/README.md", plain.kind, plain.payload),
        TreeRecord("plugins/p/bin", "D", ""),
        TreeRecord("plugins/p/bin/tool", tool.kind, tool.payload),
    ]
    return source, plan


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_folders_and_files_are_copied_private_to_the_person(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    target = tmp_path / "snapshot" / "acme"
    (tmp_path / "snapshot").mkdir()
    copied = SnapshotCopier().copy(source, plan, target, max_entries=10, max_bytes=BIG)
    assert copied == len(b"read me") + len(b"#!/bin/sh\n")
    assert (target / "plugins/p/README.md").read_bytes() == b"read me"
    assert (target / "plugins/p/bin/tool").read_bytes() == b"#!/bin/sh\n"
    assert _mode(target) == 0o700
    assert _mode(target / "plugins") == 0o700
    assert _mode(target / "plugins/p/bin") == 0o700
    assert _mode(target / "plugins/p/README.md") == 0o600
    assert _mode(target / "plugins/p/bin/tool") == 0o700  # the owner's execute bit is kept
    assert isinstance(SnapshotCopier(), SnapshotCopierInterface)


def test_a_copy_is_never_a_hard_link_even_of_a_hard_linked_source(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    os.link(source / "plugins/p/README.md", tmp_path / "elsewhere")  # uv installs hard links
    target = tmp_path / "copy"
    SnapshotCopier().copy(source, plan, target, max_entries=10, max_bytes=BIG)
    original = os.stat(source / "plugins/p/README.md")
    copy = os.stat(target / "plugins/p/README.md")
    assert original.st_nlink == 2
    assert copy.st_nlink == 1
    assert (copy.st_dev, copy.st_ino) != (original.st_dev, original.st_ino)


def test_folders_a_plan_does_not_list_are_made_on_the_way(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    files_only = [record for record in reversed(plan) if record.kind != "D"]
    target = tmp_path / "copy"
    SnapshotCopier().copy(source, files_only, target, max_entries=10, max_bytes=BIG)
    assert (target / "plugins/p/bin/tool").is_file()
    assert _mode(target / "plugins/p") == 0o700


def test_an_existing_target_is_refused(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    target = tmp_path / "copy"
    target.mkdir()
    with pytest.raises(CapabilityResolutionError, match="already exists"):
        SnapshotCopier().copy(source, plan, target, max_entries=10, max_bytes=BIG)


@pytest.mark.parametrize("kind", ["L", "?"])
def test_a_record_that_is_not_a_folder_or_file_is_refused(tmp_path: Path, kind: str) -> None:
    source, _ = _source(tmp_path)
    target = tmp_path / "copy"
    plan = [TreeRecord("plugins/p/README.md", kind, "")]
    with pytest.raises(CapabilityResolutionError, match="never copies"):
        SnapshotCopier().copy(source, plan, target, max_entries=10, max_bytes=BIG)
    assert not target.exists()


@pytest.mark.parametrize("path", ["", ".", "/etc/passwd", "../outside", "plugins/../../x"])
def test_a_record_path_that_leaves_the_tree_is_refused(tmp_path: Path, path: str) -> None:
    source, _ = _source(tmp_path)
    target = tmp_path / "copy"
    with pytest.raises(CapabilityResolutionError, match="not a path inside"):
        SnapshotCopier().copy(
            source, [TreeRecord(path, "F", "")], target, max_entries=10, max_bytes=BIG
        )
    assert not target.exists()


def test_a_plan_past_the_entry_cap_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    target = tmp_path / "copy"
    with pytest.raises(CapabilityResolutionError, match="more than 4 entries"):
        SnapshotCopier().copy(source, plan, target, max_entries=4, max_bytes=BIG)
    assert not target.exists()


def test_content_past_the_byte_cap_is_refused(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    with pytest.raises(CapabilityResolutionError, match="more than 8 bytes"):
        SnapshotCopier().copy(source, plan, tmp_path / "copy", max_entries=10, max_bytes=8)


def test_a_file_swapped_for_a_symlink_is_not_followed(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    (tmp_path / "secret").write_bytes(b"secret")
    (source / "plugins/p/README.md").unlink()
    (source / "plugins/p/README.md").symlink_to(tmp_path / "secret")
    target = tmp_path / "copy"
    with pytest.raises(CapabilityResolutionError, match="cannot copy plugins/p/README.md"):
        SnapshotCopier().copy(source, plan, target, max_entries=10, max_bytes=BIG)
    assert not (target / "plugins/p/README.md").exists()


def test_a_fifo_in_place_of_a_file_is_never_waited_on(tmp_path: Path) -> None:
    source, plan = _source(tmp_path)
    (source / "plugins/p/README.md").unlink()
    os.mkfifo(source / "plugins/p/README.md")
    with pytest.raises(CapabilityResolutionError, match="not a regular file"):
        SnapshotCopier().copy(source, plan, tmp_path / "copy", max_entries=10, max_bytes=BIG)
