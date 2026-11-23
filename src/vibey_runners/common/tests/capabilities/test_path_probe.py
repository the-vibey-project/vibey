# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One answer to "what is at this path" on every Python: only a path that is not there is
"absent"; a path the file system will not let us look at raises (SP-LOOPS Task 6 review,
must-fix 1)."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest
from fakes import symlink_loop

from vibey_runners.common.capabilities.interfaces.path_probe_interface import PathProbeInterface
from vibey_runners.common.capabilities.path_probe import DIR, FILE, OTHER, PathProbe


def _raising(code: int) -> object:
    def stat(path: Path) -> os.stat_result:
        raise OSError(code, os.strerror(code), str(path))

    return stat


def test_files_folders_and_other_entries_are_told_apart(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("x")
    os.mkfifo(tmp_path / "fifo")
    probe = PathProbe()
    assert probe.kind(tmp_path) == DIR
    assert probe.kind(tmp_path / "file") == FILE
    assert probe.kind(tmp_path / "fifo") == OTHER
    assert probe.kind(tmp_path / "missing") is None
    assert probe.is_dir(tmp_path) and not probe.is_dir(tmp_path / "file")
    assert probe.is_file(tmp_path / "file") and not probe.is_file(tmp_path)
    assert isinstance(probe, PathProbeInterface)


def test_a_symlink_is_followed_unless_asked_not_to(tmp_path: Path) -> None:
    (tmp_path / "file").write_text("x")
    (tmp_path / "link").symlink_to("file")
    (tmp_path / "dangling").symlink_to("nowhere")
    probe = PathProbe()
    assert probe.kind(tmp_path / "link") == FILE
    assert probe.kind(tmp_path / "link", follow=False) == OTHER
    assert probe.kind(tmp_path / "dangling") is None
    assert probe.kind(tmp_path / "dangling", follow=False) == OTHER


@pytest.mark.parametrize("code", [errno.ENOENT, errno.ENOTDIR, errno.EBADF, errno.ELOOP])
def test_only_the_not_there_errors_read_as_absent(tmp_path: Path, code: int) -> None:
    probe = PathProbe(stat=_raising(code), lstat=_raising(code))  # type: ignore[arg-type]
    assert probe.kind(tmp_path) is None
    assert probe.kind(tmp_path, follow=False) is None
    assert not probe.is_dir(tmp_path) and not probe.is_file(tmp_path)


@pytest.mark.parametrize("code", [errno.EACCES, errno.EPERM, errno.EIO, errno.ENAMETOOLONG])
def test_any_other_error_is_raised(tmp_path: Path, code: int) -> None:
    probe = PathProbe(stat=_raising(code), lstat=_raising(code))  # type: ignore[arg-type]
    for check in (probe.kind, probe.is_dir, probe.is_file):
        with pytest.raises(OSError) as error:
            check(tmp_path)
        assert error.value.errno == code


def test_real_never_raises_for_a_symlink_loop_and_the_probe_reads_it_as_absent(
    tmp_path: Path,
) -> None:
    """`Path.resolve()` raised `RuntimeError` for a loop on 3.12 and returns a path on 3.13+;
    `real` returns a path on every Python, and `kind` says nothing usable is there."""
    loop = symlink_loop(tmp_path / "loop")
    probe = PathProbe()
    real = probe.real(loop / "inside")
    assert isinstance(real, Path) and real.is_absolute()
    assert probe.kind(real) is None and probe.kind(loop) is None


def test_real_is_resolve_for_an_ordinary_path(tmp_path: Path) -> None:
    (tmp_path / "dir").mkdir()
    (tmp_path / "link").symlink_to("dir")
    probe = PathProbe()
    assert probe.real(tmp_path / "link" / "x") == (tmp_path / "dir" / "x").resolve()
    assert probe.real(tmp_path / "dir" / ".." / "dir") == (tmp_path / "dir").resolve()
