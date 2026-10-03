# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hybrid engine dispatch in the application layer (ADR-0079): the service that reads the
queue and the ledger for the domain and records what it decided, the selector's dispatched
round, and the provider's hold, overflow and refused reservation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from tests.application.test_engine_selector import (
    FakeEngineHealthRepository,
    FakeRotationCursorRepository,
    _healthy_record,
)
from vibey.application.dto import JobRecord, PreflightResult
from vibey.application.engine_dispatch_service import EngineDispatchService
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.engine_selection import SelectingEngineProvider
from vibey.application.engine_selector import EngineSelector
from vibey.application.interfaces import (
    EngineDispatchServiceInterface,
    EngineDispatchStorePort,
)
from vibey.application.worker import CapacityDeferred
from vibey.domain.config import EngineDispatchConfig
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId, JobRequirement
from vibey.domain.engine_dispatch import (
    DISPATCH_MEASUREMENT_JUDGE,
    DispatchLoad,
    DispatchMeasurement,
    DispatchMode,
    EngineDispatchPolicy,
    LocalSession,
    ModeSource,
    OverflowGrounds,
    SlotHeld,
    SlotHold,
    SlotOccupancy,
)
from vibey.domain.job import JobState
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)
LOCAL = EngineId.GPTOSSLOOP
PAID = EngineId.CLAUDELOOP


class FixedClock:
    def __init__(self, now: datetime = NOW) -> None:
        self.at = now

    def now(self) -> datetime:
        return self.at


class FakeDispatchStore:
    """The dispatch store in memory, recording what it was asked and what it wrote."""

    def __init__(self) -> None:
        self.taken: dict[EngineId, int] = {}
        self.waits: dict[tuple[UUID, int], datetime] = {}
        self.wait_payloads: list[Mapping[str, object]] = []
        self.overflows: list[tuple[datetime, Mapping[str, object]]] = []
        self.measurements: list[Mapping[str, object]] = []
        self.sessions: tuple[LocalSession, ...] = ()
        self.session_queries: list[tuple[UUID, tuple[EngineId, ...], datetime, datetime]] = []
        self.refuse_reservation = False
        self.fail_with: Exception | None = None

    async def in_flight(self, *, excluding: UUID) -> Mapping[EngineId, int]:
        return dict(self.taken)

    async def slot_wait_started(
        self, project_id: UUID, job_id: UUID, attempt: int
    ) -> datetime | None:
        return self.waits.get((job_id, attempt))

    async def record_slot_wait(
        self, job: JobRecord, *, payload: Mapping[str, object], at: datetime
    ) -> datetime:
        self.wait_payloads.append(payload)
        return self.waits.setdefault((job.id, job.attempts), at)

    async def paid_overflow_count(self, project_id: UUID, *, since: datetime) -> int:
        return sum(1 for at, _ in self.overflows if at >= since)

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
        if (
            self.refuse_reservation
            or await self.paid_overflow_count(job.project_id, since=since) >= cap
        ):
            return False
        self.overflows.append((at, payload))
        return True

    async def latest_measurement(self, project_id: UUID) -> Mapping[str, object] | None:
        if self.fail_with is not None:
            raise self.fail_with
        return self.measurements[-1] if self.measurements else None

    async def local_sessions(
        self,
        project_id: UUID,
        engines: Sequence[EngineId],
        *,
        since: datetime,
        until: datetime,
    ) -> tuple[LocalSession, ...]:
        self.session_queries.append((project_id, tuple(engines), since, until))
        return self.sessions

    async def record_measurement(
        self, project_id: UUID, *, payload: Mapping[str, object], at: datetime
    ) -> None:
        self.measurements.append(payload)


class RecordingLogger:
    def __init__(self, *, explode: bool = False) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []
        self.explode = explode

    def bind(self, **kwargs: Any) -> RecordingLogger:
        return self

    def _log(self, event: str, **kwargs: Any) -> None:
        if self.explode:
            raise RuntimeError("the log sink is down")
        self.events.append((event, kwargs))

    debug = info = warning = error = _log


def _service(
    store: FakeDispatchStore,
    *,
    clock: FixedClock | None = None,
    local: tuple[EngineId, ...] = (LOCAL,),
    logger: RecordingLogger | None = None,
    **config: Any,
) -> EngineDispatchService:
    return EngineDispatchService(
        store=store,
        config=EngineDispatchConfig(**config),
        local_engines=local,
        clock=clock or FixedClock(),
        implementation="vibey-engine test",
        logger=logger,
    )


def _job(project_id: UUID | None = None, *, attempts: int = 1) -> JobRecord:
    return replace(make_job(project_id or uuid4(), attempts=attempts), lease_owner="w1")


def _session(minutes: float, length: float) -> LocalSession:
    start = NOW - timedelta(hours=2) + timedelta(minutes=minutes)
    return LocalSession(LOCAL, start, start + timedelta(minutes=length))


# --- the seams ----------------------------------------------------------------------


def test_the_fake_and_the_service_satisfy_their_seams() -> None:
    store = FakeDispatchStore()
    assert isinstance(store, EngineDispatchStorePort)
    assert isinstance(_service(store), EngineDispatchServiceInterface)


# --- the policy -----------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["singleton", "hybrid"])
async def test_a_declared_mode_is_used_as_declared_and_measures_nothing(mode: str) -> None:
    store = FakeDispatchStore()
    policy = await _service(store, mode=mode, paid_daily_cap=3).policy(uuid4())
    assert policy.mode is DispatchMode(mode)
    assert policy.source is ModeSource.DECLARED
    assert policy.paid_daily_cap == 3
    assert store.measurements == [] and store.session_queries == []


async def test_auto_with_no_local_engine_falls_back_to_singleton() -> None:
    store = FakeDispatchStore()
    policy = await _service(store, local=()).policy(uuid4())
    assert policy.mode is DispatchMode.SINGLETON
    assert policy.source is ModeSource.FALLBACK
    assert "no local engine" in policy.reason
    assert store.measurements == []


async def test_auto_measures_when_nothing_is_recorded_and_records_what_it_measured() -> None:
    store = FakeDispatchStore()
    store.sessions = (_session(0, 60), _session(1, 60), _session(2, 60))
    project_id = uuid4()
    policy = await _service(
        store, auto_min_sessions=3, overflow_after_seconds=600, auto_window_hours=12
    ).policy(project_id)
    assert policy.mode is DispatchMode.HYBRID
    assert policy.source is ModeSource.MEASURED
    assert store.session_queries == [(project_id, (LOCAL,), NOW - timedelta(hours=12), NOW)]
    assert len(store.measurements) == 1
    recorded = DispatchMeasurement.from_payload(store.measurements[0])
    assert recorded is not None and recorded.winner is DispatchMode.HYBRID
    assert recorded.measured_at == NOW


async def test_auto_uses_a_current_measurement_without_measuring_again() -> None:
    store = FakeDispatchStore()
    service = _service(store, auto_min_sessions=1)
    first = await service.policy(uuid4())
    assert first.mode is DispatchMode.SINGLETON and first.source is ModeSource.MEASURED
    store.sessions = (_session(0, 60), _session(1, 60))
    again = await service.policy(uuid4())
    assert again == first
    assert len(store.measurements) == 1 and len(store.session_queries) == 1


async def test_auto_measures_again_once_the_measurement_is_stale() -> None:
    store = FakeDispatchStore()
    clock = FixedClock()
    service = _service(store, clock=clock, auto_max_age_hours=1)
    await service.policy(uuid4())
    clock.at = NOW + timedelta(hours=2)
    await service.policy(uuid4())
    assert len(store.measurements) == 2


async def test_auto_measures_again_when_the_stored_one_is_unreadable() -> None:
    store = FakeDispatchStore()
    store.measurements.append({"winner": "auto"})
    await _service(store).policy(uuid4())
    assert len(store.measurements) == 2


async def test_auto_measures_again_when_the_workload_changed() -> None:
    store = FakeDispatchStore()
    await _service(store, slots={"gptossloop": 1}).policy(uuid4())
    await _service(store, slots={"gptossloop": 2}).policy(uuid4())
    assert len(store.measurements) == 2


@pytest.mark.parametrize("logger", [None, RecordingLogger(), RecordingLogger(explode=True)])
async def test_a_failed_measurement_is_no_measurement(logger: RecordingLogger | None) -> None:
    store = FakeDispatchStore()
    store.fail_with = RuntimeError("the ledger is unreachable")
    policy = await _service(store, logger=logger).policy(uuid4())
    assert policy.mode is DispatchMode.SINGLETON
    assert policy.source is ModeSource.FALLBACK
    assert "the ledger is unreachable" in policy.reason
    if logger is not None and not logger.explode:
        assert logger.events[0][0] == "engine_dispatch.measurement_failed"


# --- the load, the hold, the overflow -------------------------------------------------


async def test_the_load_reads_slots_the_wait_and_todays_overflows() -> None:
    store = FakeDispatchStore()
    store.taken = {LOCAL: 1}
    job = _job(attempts=2)
    store.waits[(job.id, 2)] = NOW - timedelta(seconds=90)
    store.overflows = [
        (NOW - timedelta(hours=1), {}),
        (NOW - timedelta(days=1), {}),
    ]
    load = await _service(store).load(job)
    assert load == DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=90.0, paid_overflow_today=1)


async def test_a_job_never_held_has_waited_nothing_and_a_clock_behind_never_goes_negative() -> None:
    store = FakeDispatchStore()
    job = _job()
    assert (await _service(store).load(job)).waited_seconds == 0.0
    store.waits[(job.id, job.attempts)] = NOW + timedelta(seconds=5)
    assert (await _service(store).load(job)).waited_seconds == 0.0


def _grounds(today: int = 0) -> OverflowGrounds:
    return OverflowGrounds(
        local=(SlotOccupancy(LOCAL, 1, 1),),
        waited_seconds=12.0,
        overflow_after_seconds=600,
        paid_daily_cap=10,
        paid_overflow_today=today,
    )


def _hybrid_policy(**overrides: Any) -> EngineDispatchPolicy:
    values: dict[str, Any] = {
        "mode": DispatchMode.HYBRID,
        "overflow_after_seconds": 600,
        "paid_daily_cap": 10,
        "slot_poll_seconds": 30,
        "source": ModeSource.MEASURED,
        "reason": "jobs waited",
    }
    values.update(overrides)
    return EngineDispatchPolicy(**values)


async def test_a_hold_is_recorded_with_its_evidence_and_says_when_to_look_again() -> None:
    store = FakeDispatchStore()
    job = _job()
    retry_at = await _service(store).hold(
        job, SlotHold(retry_after_seconds=30, grounds=_grounds()), _hybrid_policy()
    )
    assert retry_at == NOW + timedelta(seconds=30)
    assert store.waits[(job.id, job.attempts)] == NOW
    payload = store.wait_payloads[0]
    assert payload["job_id"] == str(job.id)
    assert payload["attempt"] == job.attempts
    assert payload["mode"] == "hybrid" and payload["mode_source"] == "measured"
    assert payload["retry_after_seconds"] == 30
    assert payload["local_slots"] == [{"engine": "gptossloop", "in_flight": 1, "slots": 1}]


@pytest.mark.parametrize("logger", [None, RecordingLogger(), RecordingLogger(explode=True)])
async def test_an_overflow_is_reserved_against_todays_cap(logger: RecordingLogger | None) -> None:
    store = FakeDispatchStore()
    job = _job()
    granted = await _service(store, logger=logger).reserve_overflow(
        job, PAID, _grounds(), _hybrid_policy()
    )
    assert granted is True
    at, payload = store.overflows[0]
    assert at == NOW
    assert payload["engine"] == "claudeloop"
    assert payload["utc_day"] == "2026-10-03"
    assert payload["reason"] == "every eligible local slot is occupied"
    if logger is not None and not logger.explode:
        assert logger.events[0][0] == "engine_dispatch.overflow"


async def test_a_reservation_past_the_cap_is_refused_and_said() -> None:
    store = FakeDispatchStore()
    logger = RecordingLogger()
    granted = await _service(store, logger=logger).reserve_overflow(
        _job(), PAID, _grounds(), _hybrid_policy(paid_daily_cap=0)
    )
    assert granted is False and store.overflows == []
    assert logger.events[0][0] == "engine_dispatch.overflow_refused"


# --- the selector's dispatched round -------------------------------------------------


async def _selector(
    *engines: EngineId,
) -> tuple[EngineSelector, FakeRotationCursorRepository, UUID]:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    for engine_id in engines:
        await repo.upsert(_healthy_record(project_id, engine_id))
    cursors = FakeRotationCursorRepository()
    selector = EngineSelector(
        health_service=EngineHealthService(repo),
        cursor_repository=cursors,
        descriptors=BY_ENGINE_ID,
    )
    return selector, cursors, project_id


async def test_a_dispatched_round_with_a_free_local_slot_picks_local() -> None:
    selector, _, project_id = await _selector(LOCAL, PAID)
    chosen = await selector.select_dispatched(
        project_id, JobRequirement(effort=Effort.LOW), policy=_hybrid_policy(), load=DispatchLoad()
    )
    assert chosen.engine_id is LOCAL and chosen.overflow is None


async def test_a_dispatched_hold_moves_no_cursor() -> None:
    selector, cursors, project_id = await _selector(LOCAL, PAID)
    with pytest.raises(SlotHeld) as held:
        await selector.select_dispatched(
            project_id,
            JobRequirement(effort=Effort.LOW),
            policy=_hybrid_policy(),
            load=DispatchLoad(in_flight={LOCAL: 1}),
        )
    assert held.value.hold.grounds.local[0].engine_id is LOCAL
    assert all(c.current == 0 for c in await cursors.list_for_project(project_id))


async def test_a_dispatched_overflow_picks_paid_and_says_why() -> None:
    selector, _, project_id = await _selector(LOCAL, PAID)
    chosen = await selector.select_dispatched(
        project_id,
        JobRequirement(effort=Effort.LOW),
        policy=_hybrid_policy(),
        load=DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=600),
    )
    assert chosen.engine_id is PAID
    assert chosen.overflow is not None and chosen.overflow.waited_seconds == 600


# --- the provider ---------------------------------------------------------------------


class _Adapter:
    def __init__(self, engine_id: EngineId) -> None:
        self.descriptor = BY_ENGINE_ID[engine_id]

    async def preflight(self) -> PreflightResult:
        return PreflightResult(installed=True, version="0.1.0", auth_ok=True)


class _Dispatch:
    """A dispatch service with a fixed policy over a fake store."""

    def __init__(self, policy: EngineDispatchPolicy, store: FakeDispatchStore) -> None:
        self._policy = policy
        self._inner = _service(store)

    async def policy(self, project_id: UUID) -> EngineDispatchPolicy:
        return self._policy

    async def load(self, job: JobRecord) -> DispatchLoad:
        return await self._inner.load(job)

    async def hold(self, job: JobRecord, hold: SlotHold, policy: EngineDispatchPolicy) -> datetime:
        return await self._inner.hold(job, hold, policy)

    async def reserve_overflow(
        self,
        job: JobRecord,
        engine_id: EngineId,
        grounds: OverflowGrounds,
        policy: EngineDispatchPolicy,
    ) -> bool:
        return await self._inner.reserve_overflow(job, engine_id, grounds, policy)


async def _provider(
    policy: EngineDispatchPolicy, store: FakeDispatchStore
) -> tuple[SelectingEngineProvider, dict[EngineId, _Adapter], JobRecord, FakeJobRepository]:
    selector, _, project_id = await _selector(LOCAL, PAID)
    adapters = {LOCAL: _Adapter(LOCAL), PAID: _Adapter(PAID)}
    job = replace(_job(project_id), state=JobState.LEASED)
    jobs = FakeJobRepository([job])
    provider = SelectingEngineProvider(
        selector=selector,
        health=selector._health_service,  # type: ignore[arg-type]
        adapters=adapters,
        jobs=jobs,
        clock=FixedClock(),
        owner="w1",
        local_engines=(LOCAL,),
        dispatch=_Dispatch(policy, store),
    )
    return provider, adapters, job, jobs


async def test_a_singleton_policy_is_todays_selection() -> None:
    store = FakeDispatchStore()
    store.taken = {LOCAL: 5}
    provider, adapters, job, _ = await _provider(_hybrid_policy(mode=DispatchMode.SINGLETON), store)
    assert await provider.select_for(job) is adapters[LOCAL]
    assert store.wait_payloads == [] and store.overflows == []


async def test_hybrid_with_a_free_local_slot_runs_local() -> None:
    store = FakeDispatchStore()
    provider, adapters, job, jobs = await _provider(_hybrid_policy(), store)
    assert await provider.select_for(job) is adapters[LOCAL]
    assert (await jobs.get(job.id)).assigned_engine == "gptossloop"  # type: ignore[union-attr]


async def test_hybrid_holds_a_job_for_a_local_slot_as_a_capacity_defer() -> None:
    store = FakeDispatchStore()
    store.taken = {LOCAL: 1}
    provider, _, job, jobs = await _provider(_hybrid_policy(slot_poll_seconds=45), store)
    with pytest.raises(CapacityDeferred) as deferred:
        await provider.select_for(job)
    assert deferred.value.retry_at == NOW + timedelta(seconds=45)
    assert "held for a local slot" in deferred.value.detail
    assert store.waits[(job.id, job.attempts)] == NOW
    assert (await jobs.get(job.id)).assigned_engine is None  # type: ignore[union-attr]


async def test_hybrid_overflows_a_job_that_waited_to_a_paid_engine() -> None:
    store = FakeDispatchStore()
    store.taken = {LOCAL: 1}
    provider, adapters, job, jobs = await _provider(_hybrid_policy(), store)
    store.waits[(job.id, job.attempts)] = NOW - timedelta(seconds=601)
    assert await provider.select_for(job) is adapters[PAID]
    assert len(store.overflows) == 1
    assert (await jobs.get(job.id)).assigned_engine == "claudeloop"  # type: ignore[union-attr]


async def test_a_refused_reservation_defers_and_assigns_nothing() -> None:
    store = FakeDispatchStore()
    store.taken = {LOCAL: 1}
    store.refuse_reservation = True
    provider, _, job, jobs = await _provider(_hybrid_policy(), store)
    store.waits[(job.id, job.attempts)] = NOW - timedelta(seconds=601)
    with pytest.raises(CapacityDeferred) as deferred:
        await provider.select_for(job)
    assert deferred.value.retry_at == NOW + timedelta(seconds=30)
    assert "reached first" in deferred.value.detail
    assert (await jobs.get(job.id)).assigned_engine is None  # type: ignore[union-attr]


def test_the_shared_judge_is_the_services_default() -> None:
    service = _service(FakeDispatchStore())
    assert service._judge is DISPATCH_MEASUREMENT_JUDGE
