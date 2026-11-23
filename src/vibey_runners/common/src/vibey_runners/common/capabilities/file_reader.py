# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a marketplace file with a byte cap, and never through a final symlink.

Callers resolve a path and check that it stays inside its marketplace before reading it; opening
with `O_NOFOLLOW` then refuses a symlink swapped in at the last component between that check and
this read. At most `limit + 1` bytes are ever read, so an oversized file costs one cap of memory,
not its size. Declared by `interfaces/file_reader_interface.py::FileReaderInterface`.
"""

from __future__ import annotations

import os
from pathlib import Path

from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError


class BoundedFileReader:
    """Declared by `interfaces/file_reader_interface.py::FileReaderInterface`."""

    def read_text(self, path: Path, limit: int) -> str:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(descriptor, "rb") as handle:
            data = handle.read(limit + 1)
        if len(data) > limit:
            raise FileTooLargeError(path, limit)
        return data.decode("utf-8")
