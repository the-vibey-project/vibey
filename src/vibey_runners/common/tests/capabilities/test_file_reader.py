# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The bounded reader: never more than the cap, never through a final symlink."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.not_regular_file_error import NotRegularFileError


def test_a_file_at_the_cap_is_read(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_text("abcd", encoding="utf-8")
    assert BoundedFileReader().read_text(path, 4) == "abcd"
    assert isinstance(BoundedFileReader(), FileReaderInterface)


def test_a_file_over_the_cap_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_text("abcde", encoding="utf-8")
    with pytest.raises(FileTooLargeError) as caught:
        BoundedFileReader().read_text(path, 4)
    assert caught.value.path == path
    assert caught.value.limit == 4
    assert "4 bytes" in str(caught.value)


def test_a_final_symlink_is_never_followed(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    with pytest.raises(OSError):
        BoundedFileReader().read_text(link, 100)


def test_bytes_that_are_not_utf8_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(UnicodeDecodeError):
        BoundedFileReader().read_text(path, 100)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this operating system")
def test_a_fifo_is_refused_without_blocking(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(NotRegularFileError):
        BoundedFileReader().read_text(fifo, 100)


def test_a_folder_is_refused_as_not_a_regular_file(tmp_path: Path) -> None:
    with pytest.raises(NotRegularFileError, match="not a regular file"):
        BoundedFileReader().read_text(tmp_path, 100)
