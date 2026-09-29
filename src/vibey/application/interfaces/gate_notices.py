# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices' seams: where a notice is recorded, the service that sends and records one,
and the sweep that reminds about gates still waiting.

Mirrors `vibey/application/gate_notices.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import GateReminderReport, HumanGateRecord
from vibey.domain.gate_notice import GateNotice


@runtime_checkable
class GateNoticeStore(Protocol):
    """The ledger side of gate notices. Each record is one transaction with its event."""

    async def record(self, notice: GateNotice) -> bool:
        """Append the notice's `GateNotified` or `GateNoticeUndeliverable` event under its
        project's current cycle and phase -- unless one for the same gate and notice number
        is on record already, whoever wrote it. True when this call recorded it."""
        ...

    async def recorded(self, project_id: UUID) -> Mapping[UUID, frozenset[int]]:
        """Every notice number on record for each of the project's gates, delivered or not.
        A gate with none is absent."""
        ...


@runtime_checkable
class GateNoticeServiceInterface(Protocol):
    """Sends one notice about one gate and records what became of it."""

    async def deliver(
        self,
        gate: HumanGateRecord,
        *,
        notice: int,
        config: Mapping[str, object] | None,
        waited_seconds: float = 0.0,
    ) -> GateNotice:
        """Never raises: a sink or store that fails is said at warning, and the notice
        comes back undeliverable. `config` is the project's stored configuration."""
        ...


@runtime_checkable
class GateReminderInterface(Protocol):
    """Reminds about gates still waiting, on each project's declared schedule."""

    async def run(
        self, project_id: UUID | None = None, *, dry_run: bool = False
    ) -> GateReminderReport:
        """One sweep over one project's open gates, or every project's. Each gate gets at
        most one notice: its raise notice when none is on record, else the reminder now
        due. A dry run judges and sends and records nothing."""
        ...

    async def run_if_due(self, project_id: UUID) -> GateReminderReport | None:
        """A sweep of `project_id`, at most once per `[notifications] sweep_interval_seconds`
        per process; None when it was not due."""
        ...
