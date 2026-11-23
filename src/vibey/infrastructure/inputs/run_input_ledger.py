# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Records a run input on the append-only ledger: its digest, kind and size, never its content
(SP-LOOPS Phase 3; design Decision 6).

An add is a person's act outside any job, so its event has no job; the event recording what a
BUILD run was given carries that run's job id (fix round 2, N6). Neither has an engine or a
causing run; both are BUILD-phase events because BUILD runs are what inputs are given to. Translation goes
through `translate_event`, the same one every BUILD event goes through. Declared by
`interfaces/run_input_ledger_interface.py::PostgresRunInputLedgerInterface`.
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

from vibey.application.dto import EngineEvent
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import translate_event

ADDED_TYPES: Final = ("vibey_run_input", "vibey_run_input_repaired")
"""The artifact types that record an input being stored: an add, and the repair of one."""


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

    async def record(
        self, *, project_id: UUID, cycle: int, event: EngineEvent, job_id: UUID | None = None
    ) -> None:
        draft = translate_event(
            event,
            project_id=project_id,
            cycle=cycle,
            phase=Phase.BUILD,
            engine_id=None,
            job_id=job_id,
            correlation_id=self._correlation.for_project(project_id).value,
            provenance=Provenance.TRUSTED,
        )
        if draft is None:
            raise ValueError(f"the ledger has no event kind {event.kind!r}; nothing was recorded")
        await self._ledger.append(draft)

    async def added(self, project_id: UUID) -> frozenset[str]:
        events = await self._ledger.artifacts_of_type(project_id, ADDED_TYPES)
        return frozenset(
            digest for event in events if isinstance(digest := event.payload.get("digest"), str)
        )
