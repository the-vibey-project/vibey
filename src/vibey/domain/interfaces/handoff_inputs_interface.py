# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over which inputs a handed-off run must be given (SP-LOOPS Phase 3c, Task 7).

Implemented by `domain/handoff_inputs.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.domain.ledger import LedgerEvent


@runtime_checkable
class HandoffInputsInterface(Protocol):
    def pinned(self, events: Sequence[LedgerEvent], job_id: UUID) -> tuple[str, ...] | None:
        """The digests the run of `job_id` was given: those of the latest event, by `seq`, that
        is an `ArtifactProduced` of type `vibey_run_inputs_given` under that job. None when the
        job's run was given nothing (no such event). Raises `ValueError` when that event's
        `digests` is not a list of lowercase 64-hex digests: a pin is never guessed."""
        ...
