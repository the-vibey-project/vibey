# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over where a run's capability document lives (SP-LOOPS Phase 4, Task 2; R1, R14)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)


@runtime_checkable
class SnapshotDocumentStoreInterface(Protocol):
    def write(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        """Writes `document` once, mode 0600, as `capabilities.json` in `folder` (the run's own
        0700 folder), never through a symlink and never over an existing file. Returns its
        path. Raises `SnapshotDocumentError` when it cannot be written."""
        ...

    def read(self, path: Path) -> SnapshotDocumentInterface:
        """The document at `path`, read strictly. Raises `SnapshotDocumentError` when its folder
        is not a folder this user owns with no group or other mode bit, when the document is not
        a regular 0600 file, when it is larger than 4 MiB (refused before it is read), when it
        cannot be read as UTF-8, or when its content is refused
        (`SnapshotDocumentInterface.from_json`)."""
        ...
