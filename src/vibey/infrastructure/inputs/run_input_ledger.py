# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Records a run input on the append-only ledger: its digest, kind and size, never its content
(SP-LOOPS Phase 3; design Decision 6).

An input is a person's act outside any job, so the event has no job, no engine and no causing
run; it is a BUILD-phase event because BUILD runs are what inputs are given to. Translation goes
through `translate_event`, the same one every BUILD event goes through. Declared by
`interfaces/run_input_ledger_interface.py::PostgresRunInputLedgerInterface`.
"""

from __future__ import annotations

from uuid import UUID

from vibey.application.dto import EngineEvent
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import translate_event


class PostgresRunInputLedger:
    """Declared by `interfaces/run_input_ledger_interface.py::PostgresRunInputLedgerInterface`."""

    def __init__(
        self,
        ledger: PostgresLedgerRepository,
        *,
        correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
    ) -> None:
        self._ledger = ledger
        self._correlation = correlation

    async def record(self, *, project_id: UUID, cycle: int, event: EngineEvent) -> None:
        draft = translate_event(
            event,
            project_id=project_id,
            cycle=cycle,
            phase=Phase.BUILD,
            engine_id=None,
            job_id=None,
            correlation_id=self._correlation.for_project(project_id).value,
            provenance=Provenance.TRUSTED,
        )
        if draft is None:
            raise ValueError(f"the ledger has no event kind {event.kind!r}; nothing was recorded")
        await self._ledger.append(draft)
