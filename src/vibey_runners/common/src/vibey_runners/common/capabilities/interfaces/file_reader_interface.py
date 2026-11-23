# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam the manifest reader and the skill index read files through (SP-LOOPS Task 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileReaderInterface(Protocol):
    def read_text(self, path: Path, limit: int) -> str:
        """The UTF-8 text of `path`, never more than `limit` bytes of it. Raises
        `FileTooLargeError` past the limit, `UnicodeDecodeError` for bytes that are not UTF-8,
        and `OSError` when the file cannot be opened -- including when `path` itself is a
        symlink, which is never followed. A FIFO, folder or device raises
        `NotRegularFileError` (an `OSError`) without blocking."""
        ...

    def open_regular(self, path: Path) -> int:
        """A read-only descriptor for `path`, opened without following a final symlink and
        without blocking, or `NotRegularFileError` when it is not a regular file. The caller
        closes it."""
        ...
