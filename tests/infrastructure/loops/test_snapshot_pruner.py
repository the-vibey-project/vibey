# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Removing finished runs' snapshots past an age (SP-LOOPS Task 7; Task 6 review advisory).

A stale `run-*` copy stays reachable by relative path from a later run's plugin, so removing it is
containment, not only disk space. Nothing outside the person's snapshot folder is touched, and a
symlink is never followed or removed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from vibey.infrastructure.loops.interfaces.snapshot_pruner_interface import (
    SnapshotPrunerInterface,
)
from vibey.infrastructure.loops.records import PruneReport
from vibey.infrastructure.loops.snapshot_pruner import SnapshotPruner

DAY = 86_400.0
NOW = 1_000 * DAY


def _run(snapshots: Path, name: str, age_days: float) -> Path:
    folder = snapshots / name
    (folder / "vibey" / "plugins" / "p").mkdir(parents=True)
    (folder / "vibey" / "plugins" / "p" / "SKILL.md").write_text("x", encoding="utf-8")
    stamp = NOW - age_days * DAY
    os.utime(folder / "vibey", (stamp, stamp))
    os.utime(folder, (stamp, stamp))
    return folder


def test_the_pruner_satisfies_its_interface() -> None:
    assert isinstance(SnapshotPruner(), SnapshotPrunerInterface)


def test_only_run_folders_past_the_age_are_removed(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    old = _run(snapshots, "run-old", 8)
    fresh = _run(snapshots, "run-fresh", 6)
    other = _run(snapshots, "keep-me", 30)
    report = SnapshotPruner(clock=lambda: NOW).prune(snapshots, older_than_seconds=7 * DAY)
    assert report == PruneReport((old,), ())
    assert not old.exists()
    assert fresh.is_dir() and other.is_dir()


def test_a_symlink_or_a_file_named_like_a_run_is_refused_never_followed(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious").write_text("keep", encoding="utf-8")
    (snapshots / "run-link").symlink_to(outside)
    (snapshots / "run-file").write_text("x", encoding="utf-8")
    report = SnapshotPruner(clock=lambda: NOW).prune(snapshots, older_than_seconds=0.0)
    assert report.removed == ()
    assert report.refused == (
        (snapshots / "run-file", "is not a folder; it is left alone"),
        (snapshots / "run-link", "is a symlink; it is never followed or removed"),
    )
    assert (outside / "precious").read_text(encoding="utf-8") == "keep"


def test_a_snapshot_folder_that_is_a_symlink_is_refused_whole(tmp_path: Path) -> None:
    real = tmp_path / "real"
    _run(real, "run-old", 30)
    link = tmp_path / "snapshots"
    link.symlink_to(real)
    report = SnapshotPruner(clock=lambda: NOW).prune(link, older_than_seconds=DAY)
    assert report == PruneReport((), ((link, "is a symlink; it is never followed or removed"),))
    assert (real / "run-old").is_dir()


def test_no_snapshot_folder_is_nothing_to_do(tmp_path: Path) -> None:
    assert SnapshotPruner().prune(tmp_path / "none", older_than_seconds=DAY) == PruneReport((), ())


def test_a_folder_that_cannot_be_removed_is_named(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    old = _run(snapshots, "run-old", 30)

    def refusing(path: Path) -> None:
        raise PermissionError(13, "Permission denied", str(path))

    report = SnapshotPruner(clock=lambda: NOW, remove=refusing).prune(
        snapshots, older_than_seconds=DAY
    )
    assert report == PruneReport(
        (), ((old, f"cannot be removed: [Errno 13] Permission denied: '{old}'"),)
    )


def test_a_negative_age_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 0"):
        SnapshotPruner().prune(tmp_path, older_than_seconds=-1.0)


def test_a_run_whose_top_still_changes_is_kept(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    run = _run(snapshots, "run-busy", 30)
    stamp = NOW - 1 * DAY
    os.utime(run / "vibey", (stamp, stamp))  # its marketplace folder changed a day ago
    report = SnapshotPruner(clock=lambda: NOW).prune(snapshots, older_than_seconds=7 * DAY)
    assert report == PruneReport((), ())
    assert run.is_dir()


def test_a_snapshot_path_that_is_a_file_is_reported_not_raised(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    snapshots.write_text("not a folder", encoding="utf-8")
    report = SnapshotPruner(clock=lambda: NOW).prune(snapshots, older_than_seconds=DAY)
    assert report.removed == ()
    ((path, reason),) = report.refused
    assert path == snapshots and reason.startswith("cannot be listed:")


def test_a_run_folder_that_cannot_be_listed_is_left_and_named(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    run = _run(snapshots, "run-locked", 30)
    run.chmod(0o000)
    try:
        if os.access(run, os.R_OK):  # root reads anything: the case cannot be made here
            pytest.skip("running as root")
        report = SnapshotPruner(clock=lambda: NOW).prune(snapshots, older_than_seconds=DAY)
    finally:
        run.chmod(0o700)
    ((path, reason),) = report.refused
    assert path == run and reason.startswith("cannot be listed:")
    assert run.is_dir()


def test_a_run_folder_that_vanishes_before_it_is_looked_at_is_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibey.infrastructure.loops.snapshot_pruner as module

    snapshots = tmp_path / "snapshots"
    gone = _run(snapshots, "run-gone", 30)
    kept = _run(snapshots, "run-old", 30)
    real_lstat = os.lstat

    def lstat(path: object, **options: object) -> os.stat_result:
        if not options and Path(str(path)) == gone:
            raise FileNotFoundError(2, "No such file or directory", str(path))
        return real_lstat(path, **options)  # type: ignore[arg-type]

    monkeypatch.setattr(module.os, "lstat", lstat)
    report = SnapshotPruner(clock=lambda: NOW).prune(snapshots, older_than_seconds=DAY)
    assert report == PruneReport((kept,), ())


# -- one run's folder, removed when its run ends (SP-LOOPS Phase 4, Task 8; R10) ---------------


def test_remove_removes_one_run_folder_directly_in_snapshots(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    run = _run(snapshots, "run-done", 0)
    other = _run(snapshots, "run-other", 0)
    assert SnapshotPruner().remove(run, snapshots) is True
    assert not run.exists()
    assert other.is_dir()


def test_remove_refuses_a_symlink_or_a_folder_outside_snapshots(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    outside = tmp_path / "outside"
    (outside / "run-x").mkdir(parents=True)
    (outside / "run-x" / "precious").write_text("keep", encoding="utf-8")
    link = snapshots / "run-link"
    link.symlink_to(outside / "run-x")
    nested = _run(snapshots / "run-parent", "run-nested", 0)
    not_a_run = _run(snapshots, "keep-me", 0)
    a_file = snapshots / "run-file"
    a_file.write_text("x", encoding="utf-8")
    pruner = SnapshotPruner()

    assert pruner.remove(link, snapshots) is False  # a symlink is never followed or removed
    assert pruner.remove(outside / "run-x", snapshots) is False  # not in the snapshot folder
    assert pruner.remove(nested, snapshots) is False  # not directly in it
    assert pruner.remove(not_a_run, snapshots) is False  # not a run's folder
    assert pruner.remove(a_file, snapshots) is False  # not a folder
    assert pruner.remove(snapshots / "run-gone", snapshots) is False  # nothing there

    assert (outside / "run-x" / "precious").read_text(encoding="utf-8") == "keep"
    assert link.is_symlink() and nested.is_dir() and not_a_run.is_dir() and a_file.is_file()


def test_remove_refuses_everything_in_a_snapshot_folder_that_is_a_symlink(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    run = _run(real, "run-x", 0)
    link = tmp_path / "snapshots"
    link.symlink_to(real)
    assert SnapshotPruner().remove(link / "run-x", link) is False
    assert run.is_dir()


def test_remove_reports_a_folder_it_cannot_remove(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    run = _run(snapshots, "run-x", 0)

    def refusing(path: Path) -> None:
        raise PermissionError(13, "Permission denied", str(path))

    assert SnapshotPruner(remove=refusing).remove(run, snapshots) is False
    assert run.is_dir()
