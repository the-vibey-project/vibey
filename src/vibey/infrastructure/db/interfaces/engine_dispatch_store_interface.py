# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/db/engine_dispatch_store.py` (ADR-0016, ADR-0079).
Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime
    from uuid import UUID

    from vibey.application.dto import JobRecord
    from vibey.domain.engine import EngineId
    from vibey.domain.engine_dispatch import LocalSession


@runtime_checkable
class PostgresEngineDispatchStoreInterface(Protocol):
    async def in_flight(self, *, excluding: UUID) -> Mapping[EngineId, int]: ...

    async def slot_wait_started(
        self, project_id: UUID, job_id: UUID, attempt: int
    ) -> datetime | None: ...

    async def record_slot_wait(
        self, job: JobRecord, *, payload: Mapping[str, object], at: datetime
    ) -> datetime: ...

    async def paid_overflow_count(self, project_id: UUID, *, since: datetime) -> int: ...

    async def reserve_overflow(
        self,
        job: JobRecord,
        *,
        engine_id: EngineId,
        payload: Mapping[str, object],
        cap: int,
        since: datetime,
        at: datetime,
    ) -> bool: ...

    async def latest_measurement(self, project_id: UUID) -> Mapping[str, object] | None: ...

    async def local_sessions(
        self,
        project_id: UUID,
        engines: Sequence[EngineId],
        *,
        since: datetime,
        until: datetime,
    ) -> tuple[LocalSession, ...]: ...

    async def record_measurement(
        self, project_id: UUID, *, payload: Mapping[str, object], at: datetime
    ) -> None: ...
