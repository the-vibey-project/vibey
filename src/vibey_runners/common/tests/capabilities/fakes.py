# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fakes for the capability tests: a reader that records what it was asked to read."""

from __future__ import annotations

from pathlib import Path

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
