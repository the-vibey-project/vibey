# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The append-only event ledger, per phase, plus the handoff brief producer."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.design import (
    DesignEvent,
)
from vibey.application.dto import (
    EngineEvent,
)
from vibey.domain.engine import EngineId
from vibey.domain.handoff import (
    GateMode,
    HandoffBrief,
    HandoffEnvelope,
    Violation,
)
from vibey.domain.interfaces.ledger_query_interface import (
    LedgerQueryInterface,
    LedgerSearchResultInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent


@runtime_checkable
class BriefProducer(Protocol):
    """A brief producer is a job, not a method call (handoff-protocol.md
    §6.5): the outgoing engine, the incoming engine, any healthy engine, or
    vibey's own deterministic template can all fill this role."""

    async def produce(
        self, *, attempt: int, mode: GateMode, violations: tuple[Violation, ...]
    ) -> HandoffBrief: ...


@runtime_checkable
class BuildLedger(Protocol):
    async def record(
        self,
        *,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        engine_id: EngineId | None,
        correlation_id: UUID,
        causation_id: UUID | None = None,
        event: EngineEvent,
    ) -> None:
        """Append one engine event.

        ``correlation_id`` is the delivery's, derived from the project, and is
        the same for every event of the delivery. ``causation_id`` is what
        *caused* this event -- the engine run id for a tailed run -- and is
        what keeps individual runs distinguishable now that ``correlation_id``
        no longer varies. Events vibey writes on its own account (a finding it
        raised, a context packet it compiled) have no causing run and leave it
        ``None``.
        """
        ...


@runtime_checkable
class DesignLedger(Protocol):
    async def append(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID | None,
        engine_id: EngineId | None,
        event: DesignEvent,
    ) -> None: ...

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]: ...


@runtime_checkable
class PhaseLedger(Protocol):
    """The append-only ledger seam every interactive phase shares.

    Nine handlers each declared their own structurally identical copy of
    this (ReviewLedger, DeployDesignLedger, ...). It is one seam."""

    async def all_for_project(self, project_id: UUID) -> Sequence[LedgerEvent]: ...

    async def append_event(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
    ) -> None: ...


@runtime_checkable
class LedgerReader(Protocol):
    """Read access to the durable project ledger -- the wind-down
    orchestrator's source for the events the no-loss gate verifies."""

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]: ...


@runtime_checkable
class LedgerSearch(Protocol):
    """Searches one project's ledger (sub-doctrine 7.a, the searchable ledger).

    Every criterion is applied by the store, limit included -- a search never
    loads the whole project ledger to filter it afterwards, which is what
    `LedgerReader.all_for_project` is for and what a search must not become.
    """

    async def search(
        self, project_id: UUID, query: LedgerQueryInterface
    ) -> LedgerSearchResultInterface:
        """The most recent `query.limit` matches, oldest first, and whether
        older matches were left out."""
        ...


@runtime_checkable
class HandoffStore(Protocol):
    """Persists verified handoff envelopes (data-model.md §3.7)."""

    async def record(self, envelope: HandoffEnvelope) -> UUID: ...
