# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam a run input's ledger record goes through (SP-LOOPS Phase 3; design Decision 6).

An input is added by a person, outside any job, so it has no job and no engine: unlike
`BuildLedger.record`, this seam takes neither. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import EngineEvent


@runtime_checkable
class RunInputLedgerInterface(Protocol):
    async def record(self, *, project_id: UUID, cycle: int, event: EngineEvent) -> None:
        """Append one BUILD-phase event vibey writes on its own account -- no job, no engine,
        no causing run -- under the delivery's correlation id. The caller builds the payload;
        it carries digests, kinds and sizes, never an input's content."""
        ...
