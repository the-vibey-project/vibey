# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hybrid engine dispatch seams (ADR-0079).

`EngineDispatchStorePort` is what the queue and the ledger are asked: the slots in use,
how long a job has been held, today's paid overflows, and the recorded measurements --
and the atomic reservation that keeps the daily cap exact across workers. It is
implemented by `infrastructure/db/engine_dispatch_store.py`. `EngineDispatchServiceInterface`
is `application/engine_dispatch_service.py::EngineDispatchService`, which turns those
answers into the domain's inputs and records what dispatch decided.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import JobRecord
from vibey.domain.engine import EngineId
from vibey.domain.engine_dispatch import (
    DispatchLoad,
    EngineDispatchPolicy,
    LocalSession,
    OverflowGrounds,
    SlotHold,
)


@runtime_checkable
class EngineDispatchStorePort(Protocol):
    async def in_flight(self, *, excluding: UUID) -> Mapping[EngineId, int]:
        """Unexpired leased jobs per assigned engine, across every project -- an engine's
        slots are its backend's, not a project's. `excluding` is the job being selected."""
        ...

    async def slot_wait_started(
        self, project_id: UUID, job_id: UUID, attempt: int
    ) -> datetime | None:
        """When this job, on this attempt, was first held for a local slot; None if never."""
        ...

    async def record_slot_wait(
        self, job: JobRecord, *, payload: Mapping[str, object], at: datetime
    ) -> datetime:
        """Append `EngineSlotWaitStarted` once per job and attempt; return the wait's start
        (the earlier one when it was already recorded)."""
        ...

    async def paid_overflow_count(self, project_id: UUID, *, since: datetime) -> int:
        """`EngineOverflowSelected` events the project recorded at or after `since`."""
        ...

    async def reserve_overflow(
        self,
        job: JobRecord,
        *,
        engine_id: EngineId,
        payload: Mapping[str, object],
        cap: int,
        since: datetime,
        at: datetime,
    ) -> bool:
        """Under the project row's lock, count today's overflows again and append one
        more only while the count is below `cap`. False when the cap was reached first."""
        ...

    async def latest_measurement(self, project_id: UUID) -> Mapping[str, object] | None:
        """The payload of the project's latest `EngineDispatchMeasured`, or None."""
        ...

    async def local_sessions(
        self,
        project_id: UUID,
        engines: Sequence[EngineId],
        *,
        since: datetime,
        until: datetime,
    ) -> tuple[LocalSession, ...]:
        """Each BUILD job's first and last recorded event on each of `engines`."""
        ...

    async def record_measurement(
        self, project_id: UUID, *, payload: Mapping[str, object], at: datetime
    ) -> None: ...


@runtime_checkable
class EngineDispatchServiceInterface(Protocol):
    async def policy(self, project_id: UUID) -> EngineDispatchPolicy:
        """The resolved policy: declared, or measured for `auto` (singleton on any
        missing, invalid or failed measurement)."""
        ...

    async def load(self, job: JobRecord) -> DispatchLoad: ...

    async def hold(self, job: JobRecord, hold: SlotHold, policy: EngineDispatchPolicy) -> datetime:
        """Record the hold and return when the job may be looked at again."""
        ...

    async def reserve_overflow(
        self,
        job: JobRecord,
        engine_id: EngineId,
        grounds: OverflowGrounds,
        policy: EngineDispatchPolicy,
    ) -> bool: ...
