# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Adapter between DESIGN application events and the durable event ledger."""

from uuid import UUID

from vibey.application.design import DesignEvent
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.engine import EngineId
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft


class PostgresDesignLedger:
    def __init__(
        self,
        ledger: PostgresLedgerRepository,
        *,
        correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
    ) -> None:
        self._ledger = ledger
        self._correlation = correlation

    async def append(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID | None,
        engine_id: EngineId | None,
        event: DesignEvent,
    ) -> None:
        payload = dict(event.payload)
        await self._ledger.append(
            LedgerEventDraft(
                project_id=project_id,
                cycle=cycle,
                phase=Phase.DESIGN,
                kind=event.kind,
                engine_id=engine_id,
                job_id=job_id,
                causation_id=None,
                correlation_id=self._correlation.for_project(project_id).value,
                provenance=event.provenance,
                produced_at=event.produced_at,
                payload=payload,
                digest=digest_event(payload),
            )
        )

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]:
        """The DESIGN-phase events, as the design handlers read them.

        A kind this vibey does not know is left out (vibey#275): no design handler
        could act on it, and a `DesignEvent` is also what the design handlers
        append, so it carries only kinds vibey can write. The row itself stays in
        the ledger and in every full ledger handed on.
        """
        events = await self._ledger.all_for_project(project_id)
        return tuple(
            DesignEvent(
                kind=event.kind,
                provenance=event.provenance,
                produced_at=event.produced_at,
                payload=event.payload,
            )
            for event in events
            if event.phase is Phase.DESIGN and isinstance(event.kind, EventKind)
        )
