# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fakes for the capability tests: a reader that records what it was asked to read, and a folder
made readable but not searchable."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from vibey_runners.common.capabilities.file_reader import BoundedFileReader


class RecordingReader:
    """Reads through the real bounded reader and remembers every path, so a test can prove a
    file was never read. `fail` makes a read of that path raise the given error instead."""

    def __init__(self, fail: dict[Path, Exception] | None = None) -> None:
        self.paths: list[Path] = []
        self._fail = fail or {}
        self._real = BoundedFileReader()

    def read_text(self, path: Path, limit: int) -> str:
        self.paths.append(path)
        if path in self._fail:
            raise self._fail[path]
        return self._real.read_text(path, limit)

    def open_regular(self, path: Path) -> int:
        return self._real.open_regular(path)


@contextmanager
def unsearchable(folder: Path) -> Iterator[Path]:
    """`folder` at mode 0600 (its names can be listed, nothing in it can be looked at) for the
    block; skipped where that does not bind this process (the superuser, or a file system that
    does not enforce modes). The case Python 3.12 and 3.14's pathlib answer differently."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:  # pragma: no cover - root ignores modes
        pytest.skip("permissions do not bind the superuser")
    folder.chmod(0o600)
    try:
        try:
            os.stat(folder / "probe")
        except PermissionError:
            pass
        except FileNotFoundError:  # pragma: no cover - modes not enforced here
            pytest.skip("this file system does not enforce folder permissions")
        yield folder
    finally:
        folder.chmod(0o700)
