# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over `vibey inputs add | list` (SP-LOOPS Phase 3, Task 5). Interfaces declare; they
never consume."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class InputsCommandsInterface(Protocol):
    def add(
        self, project_id: UUID, *, paste: str | None, paste_stdin: bool, file: Path | None
    ) -> int:
        """Adds one run input to the project from exactly one of `paste` (the text as given),
        standard input, or `file` (a regular file, named by its base name, refused from its size
        before it is read). Returns the exit code: 0 added; 1 an unknown project; 2 a refused
        input or not exactly one source; 78 the person's `vibey.toml` or the store cannot be
        read or written."""
        ...

    def list(self, project_id: UUID, *, as_json: bool) -> int:
        """Prints the project's run inputs in the order added -- digest, kind, size and name,
        never content -- one escaped line each, or as JSON for a program. Returns 0, 1 for an
        unknown project, or 78 when the store cannot be read."""
        ...
