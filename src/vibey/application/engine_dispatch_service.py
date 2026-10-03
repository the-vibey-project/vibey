# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hybrid engine dispatch, as the worker runs it (ADR-0079).

The domain decides (`domain/engine_dispatch.py`); this asks the queue and the ledger for
what it decides on, and records what it decided. Three things it reads -- the slots in use,
how long this job has waited for one, today's paid overflows -- and three it writes, each
an append-only, trusted ledger event: `EngineSlotWaitStarted` the first time a job is held
for a local slot, `EngineOverflowSelected` when a paid engine takes one as overflow, and
`EngineDispatchMeasured` when `auto` measures.

`auto` (ADR-0074, applied to the engine pool): the latest recorded measurement decides
while it is current -- same local engines and slots, same thresholds, same algorithm and
vibey, younger than `auto_max_age_hours`. Otherwise a new one is taken from the project's
own recorded BUILD sessions and recorded before it is used. A measurement that cannot be
taken or recorded is no measurement, and the mode is `singleton`.

Capability gap (10.e). ADR-0074's machinery for `[bus] mode` --
`infrastructure/bus/dispatch.py`'s `BusDispatchBenchmark`, `BusDispatchSelection` and
`WeeklyBusDispatchRecomputer`, and qwenloop's in-process `HybridTurnMultiplexer` -- is not
reused here, for reasons that are gaps rather than taste: the benchmark measures a policy
by running synthetic load through it, and the engine pool's only synthetic load is paid
sessions, which no unattended default may buy (8.a, 8.b); its winner lives in one
machine's user cache with no workload or implementation check, where every worker of a
project must read the same answer and a changed slot count must invalidate it; and the
multiplexer's semaphore is per process, where slots are shared by every worker on the
queue. What is kept is ADR-0074's contract itself: per surface, measured where it runs,
durable, inspectable, invalidated by a change, `singleton` on any doubt.
"""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from vibey.domain.config import EngineDispatchConfig
from vibey.domain.engine import EngineId, EngineTier
from vibey.domain.engine_dispatch import (
    DISPATCH_MEASUREMENT_JUDGE,
    UTC_DAY,
    DispatchLoad,
    DispatchMeasurement,
    DispatchMode,
    EngineDispatchPolicy,
    ModeSource,
    OverflowGrounds,
    SlotHold,
)

if TYPE_CHECKING:
    from vibey.application.dto import JobRecord
    from vibey.application.interfaces.engine_dispatch import EngineDispatchStorePort
    from vibey.application.interfaces.observability import Logger
    from vibey.application.interfaces.system import Clock
    from vibey.domain.interfaces.engine_dispatch_interface import (
        DispatchMeasurementJudgeInterface,
        UtcDayInterface,
    )


class EngineDispatchService:
    """Declared by `interfaces/engine_dispatch.py::EngineDispatchServiceInterface`."""

    def __init__(
        self,
        *,
        store: EngineDispatchStorePort,
        config: EngineDispatchConfig,
        local_engines: tuple[EngineId, ...],
        clock: Clock,
        implementation: str,
        judge: DispatchMeasurementJudgeInterface = DISPATCH_MEASUREMENT_JUDGE,
        day: UtcDayInterface = UTC_DAY,
        logger: Logger | None = None,
    ) -> None:
        self._store = store
        self._config = config
        self._local_engines = local_engines
        self._clock = clock
        self._implementation = implementation
        self._judge = judge
        self._day = day
        self._logger = logger

    async def policy(self, project_id: UUID) -> EngineDispatchPolicy:
        mode = DispatchMode(self._config.mode)
        if mode is not DispatchMode.AUTO:
            return EngineDispatchPolicy.from_config(self._config, mode)
        return await self._measured(project_id)

    async def _measured(self, project_id: UUID) -> EngineDispatchPolicy:
        declared = EngineDispatchPolicy.from_config(self._config, DispatchMode.SINGLETON)
        local_slots = {
            engine: declared.slots_for(engine, EngineTier.LOCAL) for engine in self._local_engines
        }
        if not local_slots:
            return self._fallback("no local engine is enabled, so there is no slot to measure")
        fingerprint = self._judge.fingerprint(self._config, local_slots, self._implementation)
        now = self._clock.now()
        try:
            stored = await self._store.latest_measurement(project_id)
            measurement = self._judge.current(
                None if stored is None else DispatchMeasurement.from_payload(stored),
                now=now,
                fingerprint=fingerprint,
                max_age=timedelta(hours=self._config.auto_max_age_hours),
            )
            if measurement is None:
                sessions = await self._store.local_sessions(
                    project_id,
                    tuple(local_slots),
                    since=now - timedelta(hours=self._config.auto_window_hours),
                    until=now,
                )
                measurement = self._judge.measure(
                    sessions,
                    local_slots=local_slots,
                    config=self._config,
                    window_end=now,
                    fingerprint=fingerprint,
                )
                await self._store.record_measurement(
                    project_id, payload=measurement.payload(), at=now
                )
        except Exception as exc:  # noqa: BLE001 -- a failed measurement is no measurement
            if self._logger is not None:
                with suppress(Exception):
                    self._logger.warning(
                        "engine_dispatch.measurement_failed",
                        project_id=str(project_id),
                        error=str(exc),
                    )
            return self._fallback(f"the measurement failed: {exc}")
        return EngineDispatchPolicy.from_config(
            self._config,
            measurement.winner,
            source=ModeSource.MEASURED,
            reason=measurement.reason,
        )

    def _fallback(self, reason: str) -> EngineDispatchPolicy:
        return EngineDispatchPolicy.from_config(
            self._config, DispatchMode.SINGLETON, source=ModeSource.FALLBACK, reason=reason
        )

    async def load(self, job: JobRecord) -> DispatchLoad:
        now = self._clock.now()
        in_flight = await self._store.in_flight(excluding=job.id)
        started = await self._store.slot_wait_started(job.project_id, job.id, job.attempts)
        waited = 0.0 if started is None else max((now - started).total_seconds(), 0.0)
        today = await self._store.paid_overflow_count(job.project_id, since=self._day.start(now))
        return DispatchLoad(in_flight=in_flight, waited_seconds=waited, paid_overflow_today=today)

    async def hold(self, job: JobRecord, hold: SlotHold, policy: EngineDispatchPolicy) -> datetime:
        now = self._clock.now()
        await self._store.record_slot_wait(
            job,
            payload={
                **self._job_fields(job, policy),
                **hold.grounds.payload(),
                "retry_after_seconds": hold.retry_after_seconds,
            },
            at=now,
        )
        return now + timedelta(seconds=hold.retry_after_seconds)

    async def reserve_overflow(
        self,
        job: JobRecord,
        engine_id: EngineId,
        grounds: OverflowGrounds,
        policy: EngineDispatchPolicy,
    ) -> bool:
        now = self._clock.now()
        granted = await self._store.reserve_overflow(
            job,
            engine_id=engine_id,
            payload={
                **self._job_fields(job, policy),
                **grounds.payload(),
                "engine": engine_id.value,
                "utc_day": self._day.label(now),
            },
            cap=policy.paid_daily_cap,
            since=self._day.start(now),
            at=now,
        )
        if self._logger is not None:
            with suppress(Exception):
                self._logger.info(
                    "engine_dispatch.overflow" if granted else "engine_dispatch.overflow_refused",
                    project_id=str(job.project_id),
                    job_id=str(job.id),
                    engine_id=engine_id.value,
                )
        return granted

    @staticmethod
    def _job_fields(job: JobRecord, policy: EngineDispatchPolicy) -> dict[str, object]:
        return {
            "job_id": str(job.id),
            "job_kind": job.kind,
            "attempt": job.attempts,
            "mode": policy.mode.value,
            "mode_source": policy.source.value,
            "mode_reason": policy.reason,
        }


__all__ = ["EngineDispatchService"]
