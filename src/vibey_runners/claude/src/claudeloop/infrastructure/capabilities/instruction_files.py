# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The repository's `CLAUDE.md` and `AGENTS.md` as instruction text (SP-LOOPS Phase 4, Task 6;
R8).

A capability snapshot switches Claude Code's own settings off (`setting_sources = []`, R5), and
with them its own reading of the repository's `CLAUDE.md`. So claudeloop reads the files the
snapshot names (`[loops] instruction_files`) itself, from the run's `cwd` only and never from a
folder below it, and the session's system prompt carries them after the voice contract and the
autonomy fragment, so the repository's rules never outrank either. They are never put in the
plan: a wind-down seed must reach the engine byte for byte.

A file is either inlined whole or named with the reason it was not; it is never truncated
(ADR-0075). A file over `[loops] instruction_max_bytes` is named with its size and the agent is
told to read it. A symlink is refused, never followed, as are a file that is not regular, bytes
that are not UTF-8 and a file that cannot be opened. A missing file is skipped and counted
nowhere. At most `max_bytes + 1` bytes of any file are read. Declared by
`interfaces/instruction_file_reader_interface.py::InstructionFileReaderInterface`.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)

HEADING: Final = "## Repository instructions ({name})"
"""The heading each inlined file sits under, so the agent can tell which file a rule came from."""

OVER_CAP: Final = (
    "{name} ({size} bytes) is longer than the [loops] instruction_max_bytes of {max_bytes}; "
    "read it from the repository before you start."
)
SYMLINK: Final = "{name} is a symbolic link, which is never followed; it was not read."
NOT_REGULAR: Final = "{name} is not a regular file; it was not read."
NOT_UTF8: Final = "{name} is not UTF-8 text; it was not read."
UNOPENABLE: Final = "{name} could not be opened; it was not read."


@dataclass(frozen=True, slots=True)
class InstructionText:
    """Declared by `interfaces/instruction_file_reader_interface.py::InstructionTextInterface`."""

    text: str
    inlined: tuple[str, ...]
    named: tuple[str, ...]


class InstructionFileReader:
    """Declared by `interfaces/instruction_file_reader_interface.py`."""

    def __init__(self, reader: FileReaderInterface | None = None) -> None:
        # The default is built here, not in the signature: ruff's B008 refuses a call there.
        self._reader = reader if reader is not None else BoundedFileReader()

    def read(self, cwd: Path, names: Sequence[str], max_bytes: int) -> InstructionText:
        parts: list[str] = []
        inlined: list[str] = []
        named: list[str] = []
        for name in names:
            entry = self._entry(cwd / name, name, max_bytes)
            if entry is None:
                continue
            text, whole = entry
            parts.append(text)
            (inlined if whole else named).append(name)
        return InstructionText("\n\n".join(parts), tuple(inlined), tuple(named))

    def _entry(self, path: Path, name: str, max_bytes: int) -> tuple[str, bool] | None:
        """The file's block and `True`, a line naming it and `False`, or `None` when it is
        missing."""
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return None
        except OSError:
            return UNOPENABLE.format(name=name), False
        if stat.S_ISLNK(mode):
            return SYMLINK.format(name=name), False
        if not stat.S_ISREG(mode):
            return NOT_REGULAR.format(name=name), False
        try:
            # Opened without following a final symlink and refused unless regular, so a file
            # swapped in after the check above is never read through.
            descriptor = self._reader.open_regular(path)
        except OSError:
            return UNOPENABLE.format(name=name), False
        with os.fdopen(descriptor, "rb") as handle:
            data = handle.read(max_bytes + 1)
            size = os.fstat(handle.fileno()).st_size
        if len(data) > max_bytes:
            return OVER_CAP.format(name=name, size=size, max_bytes=max_bytes), False
        try:
            body = data.decode("utf-8")
        except UnicodeDecodeError:
            return NOT_UTF8.format(name=name), False
        return f"{HEADING.format(name=name)}\n\n{body}", True
