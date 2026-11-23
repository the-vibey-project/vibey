# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the person's run input store (SP-LOOPS Phase 3; design Decision 6; fix round 1:
R-A, the store is keyed by project id in the person's own state, never inside a checkout).

`infrastructure/inputs/hash_addressed_input_store.py` implements it; the run inputs service
consumes it. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.run_input import InputKind, InputListing, RunInput


@runtime_checkable
class InputStoreInterface(Protocol):
    def put(self, project_id: UUID, kind: InputKind, name: str, data: bytes) -> RunInput:
        """Stores `data` once under its digest in the project's folder and appends one index
        row (digest, kind, name, size, when). The same bytes added again write no second object,
        only a second row -- unless the object there no longer matches its digest, which is then
        replaced. Raises `InputStoreError` -- and writes no row -- when the store cannot be made
        or written; it checks no limit and no name (the service does)."""
        ...

    def get(self, project_id: UUID, digest: str, *, size: int) -> bytes:
        """The exact bytes stored under `digest`, which its index row says are `size` long.
        Raises `InputStoreError` for a digest that is not one, an object that is missing, not a
        regular file, of another size (refused from its size, before it is read), or whose bytes
        no longer match the digest."""
        ...

    def listed(self, project_id: UUID) -> InputListing:
        """Every index row, in the order added, and how many lines were skipped as unreadable
        (a torn line after a crash among them); a project with no store is an empty listing.
        Raises `InputStoreError` only when the store itself cannot be read."""
        ...
