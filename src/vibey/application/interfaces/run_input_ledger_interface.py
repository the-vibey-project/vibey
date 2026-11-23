# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam a run input's ledger record goes through (SP-LOOPS Phase 3; design Decision 6).

An input is added by a person, outside any job, so an add has no job and no engine: unlike
`BuildLedger.record`, this seam needs neither. The event recording what a run was given carries
its BUILD job's id (fix round 2, N6). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import EngineEvent


@runtime_checkable
class RunInputLedgerInterface(Protocol):
    async def record(
        self, *, project_id: UUID, cycle: int, event: EngineEvent, job_id: UUID | None = None
    ) -> None:
        """Append one BUILD-phase event vibey writes on its own account -- no engine, no
        causing run -- under the delivery's correlation id. `job_id` is the BUILD job a run's
        inputs were given in; an add, a person's act outside any job, has none. The caller
        builds the payload; it carries digests, kinds and sizes, never an input's content."""
        ...

    async def added(self, project_id: UUID) -> frozenset[str]:
        """The digests of every input the ledger records as added to the project: its
        `vibey_run_input` and `vibey_run_input_repaired` events. The ledger, not the store, is
        the authority on which inputs exist (ADR-0105): a store missing one of these is the
        wrong store or a damaged one, and a row in the store none of these names was never
        added through vibey."""
        ...
