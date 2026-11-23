# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over a project's run input store (SP-LOOPS Phase 3; design Decision 6).

`infrastructure/inputs/hash_addressed_input_store.py` implements it; the run inputs service
consumes it. Interfaces declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.domain.run_input import InputKind, InputListing, RunInput


@runtime_checkable
class InputStoreInterface(Protocol):
    def put(self, project_folder: Path, kind: InputKind, name: str, data: bytes) -> RunInput:
        """Stores `data` once under its digest in `project_folder / "inputs"` and appends one
        index row (digest, kind, name, size, when). The same bytes added again write no second
        object, only a second row. Raises `InputStoreError` -- and writes no row -- when the
        store cannot be made or written; it checks no limit and no name (the service does)."""
        ...

    def get(self, project_folder: Path, digest: str) -> bytes:
        """The exact bytes stored under `digest`. Raises `InputStoreError` for a digest that is
        not one, an object that is missing, not a regular file, or whose bytes no longer match
        the digest."""
        ...

    def listed(self, project_folder: Path) -> InputListing:
        """Every index row, in the order added, and how many lines were skipped as unreadable
        (a torn last line after a crash among them); an index that does not exist is an empty
        listing. Raises `InputStoreError` only when the index itself cannot be read."""
        ...
