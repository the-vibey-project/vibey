# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over a project's run inputs: add one, list them, and give one BUILD run its input
value (SP-LOOPS Phase 3; design Goal 4). Interfaces declare; they never consume."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import RunInputs
from vibey.domain.run_input import InputKind, InputListing, RunInput


@runtime_checkable
class RunInputsInterface(Protocol):
    async def add(self, project_id: UUID, kind: InputKind, name: str, data: bytes) -> RunInput:
        """Stores `data` as the project's next run input and records its digest, kind and size
        (never its content) on the ledger. Raises `RunInputRefused` -- having written nothing --
        for a kind or name vibey refuses, or for more than the `[inputs]` limits allow;
        `UnknownProject` for an id that names none; `InputStoreError` when the store cannot be
        written."""
        ...

    async def listed(self, project_id: UUID) -> InputListing:
        """The project's run inputs in the order added, with how many index lines were skipped
        as unreadable. Raises `UnknownProject` or `InputStoreError`."""
        ...

    async def materialize(
        self,
        project_id: UUID,
        run_id: UUID,
        worktree_path: Path,
        *,
        job_id: UUID | None = None,
        pinned: Sequence[str] | None = None,
    ) -> RunInputs:
        """Writes the project's inputs into `worktree_path / ".vibey/inputs/<run_id>/"` and
        returns the run's input value; with no inputs, writes nothing and returns an empty value.
        Idempotent for one `run_id`. One ledger event, under `job_id`, records the digests the
        run was actually given. Raises `UnknownProject` or `InputStoreError` (an object
        whose bytes no longer match its digest is never copied).

        With `pinned` (a handed-off run; SP-LOOPS Phase 3c), the run is given exactly those
        digests, in that order, each read from its latest index row: no limit but
        `max_prompt_bytes` is applied again (withholding now would drop what the outgoing engine
        had; what is not inlined stays in `paste.md`), and no input added since is given. A
        pinned digest with no row or no object raises `HandoffInputsMissing`. An empty pin gives
        nothing and writes nothing."""
        ...
