# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hybrid engine dispatch (ADR-0079): the plan, the cap, the hold, and `auto`'s measurement.

The properties are the ones the ADR promises: `singleton` is today's selection exactly; a
paid engine is never offered while a local slot is free; overflow is never granted at or
over the cap, and never before the job has waited; a hold is planned only when overflow
could follow it.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.config import (
    DEFAULT_LOCAL_ENGINE_SLOTS,
    DEFAULT_PAID_ENGINE_SLOTS,
    EngineDispatchConfig,
)
from vibey.domain.engine import EngineId, EngineTier
from vibey.domain.engine_dispatch import (
    DISPATCH_MEASUREMENT_JUDGE,
    ENGINE_DISPATCHER,
    MEASUREMENT_ALGORITHM,
    UTC_DAY,
    DispatchedSelection,
    DispatchLoad,
    DispatchMeasurement,
    DispatchMeasurementJudge,
    DispatchMode,
    DispatchPlan,
    EngineDispatcher,
    EngineDispatchPolicy,
    LocalSession,
    ModeSource,
    OverflowGrounds,
    SlotHeld,
    SlotHold,
    SlotOccupancy,
    UtcDay,
)
from vibey.domain.interfaces.engine_dispatch_interface import (
    DispatchMeasurementJudgeInterface,
    EngineDispatcherInterface,
    EngineDispatchPolicyInterface,
    UtcDayInterface,
)
from vibey.domain.rotation import Candidate, preferred_tier, select

LOCAL = EngineId.GPTOSSLOOP
LOCAL_TOO = EngineId.QWENLOOP
PAID = EngineId.CLAUDELOOP
PAID_TOO = EngineId.CODEXLOOP
T0 = datetime(2026, 10, 3, 12, 0, tzinfo=UTC)


def _candidate(
    engine_id: EngineId, tier: EngineTier, *, order: int, health: float = 1.0
) -> Candidate:
    return Candidate(
        engine_id=engine_id,
        base_weight=10,
        current=0,
        order=order,
        health_factor=health,
        fidelity_factor=1.0,
        cost_factor=1.0,
        affinity_factor=1.0,
        tier=tier,
    )


def _policy(
    mode: DispatchMode = DispatchMode.HYBRID,
    *,
    threshold: int = 600,
    cap: int = 10,
    poll: int = 30,
    slots: dict[EngineId, int] | None = None,
) -> EngineDispatchPolicy:
    return EngineDispatchPolicy(
        mode=mode,
        overflow_after_seconds=threshold,
        paid_daily_cap=cap,
        slot_poll_seconds=poll,
        slots=slots or {},
    )


LOCAL_C = _candidate(LOCAL, EngineTier.LOCAL, order=0)
LOCAL_TOO_C = _candidate(LOCAL_TOO, EngineTier.LOCAL, order=1)
PAID_C = _candidate(PAID, EngineTier.PAID, order=2)
PAID_TOO_C = _candidate(PAID_TOO, EngineTier.PAID, order=3)


# --- the shared instances honour their declared seams (ADR-0016) -----------------


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(ENGINE_DISPATCHER, EngineDispatcherInterface)
    assert isinstance(DISPATCH_MEASUREMENT_JUDGE, DispatchMeasurementJudgeInterface)
    assert isinstance(UTC_DAY, UtcDayInterface)
    assert isinstance(_policy(), EngineDispatchPolicyInterface)
    assert isinstance(ENGINE_DISPATCHER, EngineDispatcher)
    assert isinstance(DISPATCH_MEASUREMENT_JUDGE, DispatchMeasurementJudge)
    assert isinstance(UTC_DAY, UtcDay)


# --- the policy ----------------------------------------------------------------------


def test_a_resolved_policy_is_never_auto() -> None:
    with pytest.raises(ValueError, match="never auto"):
        _policy(DispatchMode.AUTO)


def test_slots_default_by_tier_and_a_declaration_wins() -> None:
    policy = _policy(slots={LOCAL: 3})
    assert policy.slots_for(LOCAL, EngineTier.LOCAL) == 3
    assert policy.slots_for(LOCAL_TOO, EngineTier.LOCAL) == DEFAULT_LOCAL_ENGINE_SLOTS == 1
    assert policy.slots_for(PAID, EngineTier.PAID) == DEFAULT_PAID_ENGINE_SLOTS


def test_from_config_carries_every_key_and_drops_unknown_engines() -> None:
    config = EngineDispatchConfig(
        mode="hybrid",
        overflow_after_seconds=120,
        paid_daily_cap=4,
        slot_poll_seconds=7,
        slots={"gptossloop": 2, "martian": 9},
    )
    policy = EngineDispatchPolicy.from_config(
        config, DispatchMode.HYBRID, source=ModeSource.MEASURED, reason="r"
    )
    assert policy == EngineDispatchPolicy(
        mode=DispatchMode.HYBRID,
        overflow_after_seconds=120,
        paid_daily_cap=4,
        slot_poll_seconds=7,
        slots={LOCAL: 2},
        source=ModeSource.MEASURED,
        reason="r",
    )


# --- the plan ---------------------------------------------------------------------------


def test_singleton_is_todays_tier_first_plan() -> None:
    candidates = [PAID_C, LOCAL_C]
    load = DispatchLoad(in_flight={LOCAL: 5}, waited_seconds=10_000)
    plan = ENGINE_DISPATCHER.plan(candidates, _policy(DispatchMode.SINGLETON), load)
    assert plan == DispatchPlan(preferred_tier(candidates))


def test_hybrid_offers_only_the_local_engines_with_a_free_slot() -> None:
    plan = ENGINE_DISPATCHER.plan(
        [LOCAL_C, LOCAL_TOO_C, PAID_C], _policy(), DispatchLoad(in_flight={LOCAL: 1})
    )
    assert plan == DispatchPlan((LOCAL_TOO_C,))


def test_hybrid_with_no_local_engine_that_can_win_is_todays_fallback() -> None:
    decayed = _candidate(LOCAL, EngineTier.LOCAL, order=0, health=0.0)
    plan = ENGINE_DISPATCHER.plan([decayed, PAID_C], _policy(), DispatchLoad())
    assert plan == DispatchPlan((PAID_C,))


def test_a_saturated_local_tier_holds_a_job_that_has_not_waited_long_enough() -> None:
    plan = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C],
        _policy(threshold=600, poll=30),
        DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=100, paid_overflow_today=3),
    )
    assert isinstance(plan, SlotHold)
    assert plan.retry_after_seconds == 30
    assert plan.grounds == OverflowGrounds(
        local=(SlotOccupancy(LOCAL, 1, 1),),
        waited_seconds=100,
        overflow_after_seconds=600,
        paid_daily_cap=10,
        paid_overflow_today=3,
    )
    assert plan.detail == (
        "held for a local slot (gptossloop 1/1); waited 100s of 600s before a paid engine "
        "may take it as overflow (7 of 10 left today)"
    )


def test_a_hold_never_outlasts_the_threshold_nor_rounds_to_zero() -> None:
    near = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C],
        _policy(threshold=600, poll=30),
        DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=590.5),
    )
    assert isinstance(near, SlotHold) and near.retry_after_seconds == 10
    edge = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C],
        _policy(threshold=600, poll=30),
        DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=599.9999),
    )
    assert isinstance(edge, SlotHold) and edge.retry_after_seconds == 1


def test_a_job_that_waited_overflows_to_the_paid_engines_with_a_free_slot() -> None:
    plan = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C, PAID_TOO_C],
        _policy(),
        DispatchLoad(in_flight={LOCAL: 1, PAID: 2}, waited_seconds=600, paid_overflow_today=9),
    )
    assert isinstance(plan, DispatchPlan)
    assert plan.candidates == (PAID_TOO_C,)
    assert plan.overflow is not None
    assert plan.overflow.cap_remaining == 1
    assert plan.overflow.payload() == {
        "reason": "every eligible local slot is occupied",
        "local_slots": [{"engine": "gptossloop", "in_flight": 1, "slots": 1}],
        "waited_seconds": 600.0,
        "overflow_after_seconds": 600,
        "paid_daily_cap": 10,
        "paid_overflow_today": 9,
        "cap_remaining": 1,
    }


def test_at_the_cap_the_job_waits_for_local_as_it_always_has() -> None:
    candidates = [LOCAL_C, PAID_C]
    plan = ENGINE_DISPATCHER.plan(
        candidates,
        _policy(cap=2),
        DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=10_000, paid_overflow_today=2),
    )
    assert plan == DispatchPlan(preferred_tier(candidates))


def test_a_zero_cap_means_no_overflow_at_all() -> None:
    plan = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C], _policy(cap=0), DispatchLoad(in_flight={LOCAL: 1}, waited_seconds=1e9)
    )
    assert plan == DispatchPlan((LOCAL_C,))


def test_with_every_paid_slot_taken_the_job_waits_for_local_and_is_not_held() -> None:
    plan = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C],
        _policy(slots={PAID: 1}),
        DispatchLoad(in_flight={LOCAL: 1, PAID: 1}),
    )
    assert plan == DispatchPlan((LOCAL_C,))


def test_with_no_paid_engine_in_the_pool_a_saturated_job_waits_for_local() -> None:
    plan = ENGINE_DISPATCHER.plan([LOCAL_C], _policy(), DispatchLoad(in_flight={LOCAL: 1}))
    assert plan == DispatchPlan((LOCAL_C,))


def test_a_zero_threshold_overflows_at_once() -> None:
    plan = ENGINE_DISPATCHER.plan(
        [LOCAL_C, PAID_C], _policy(threshold=0), DispatchLoad(in_flight={LOCAL: 1})
    )
    assert isinstance(plan, DispatchPlan) and plan.overflow is not None
    assert plan.candidates == (PAID_C,)


def test_slot_held_carries_its_hold_and_says_why() -> None:
    hold = SlotHold(
        retry_after_seconds=5,
        grounds=OverflowGrounds(
            local=(SlotOccupancy(LOCAL, 2, 1),),
            waited_seconds=0,
            overflow_after_seconds=60,
            paid_daily_cap=3,
            paid_overflow_today=5,
        ),
    )
    held = SlotHeld(hold)
    assert held.hold is hold
    assert str(held) == hold.detail
    assert hold.grounds.cap_remaining == 0


def test_a_dispatched_selection_is_plain_data() -> None:
    selection = select([LOCAL_C])
    chosen = DispatchedSelection(engine_id=LOCAL, selection=selection)
    assert chosen.overflow is None and chosen.selection.engine_id is LOCAL


# --- the properties --------------------------------------------------------------------

_ENGINES = (
    (LOCAL, EngineTier.LOCAL),
    (LOCAL_TOO, EngineTier.LOCAL),
    (EngineId.CLAUDELOOP_LOCAL, EngineTier.LOCAL),
    (PAID, EngineTier.PAID),
    (PAID_TOO, EngineTier.PAID),
)


@st.composite
def _situations(
    draw: st.DrawFn,
) -> tuple[list[Candidate], EngineDispatchPolicy, DispatchLoad]:
    present = draw(st.lists(st.sampled_from(_ENGINES), min_size=1, max_size=5, unique=True))
    candidates = [
        _candidate(
            engine,
            tier,
            order=i,
            health=draw(st.sampled_from([0.0, 0.25, 1.0])),
        )
        for i, (engine, tier) in enumerate(present)
    ]
    slots = {
        engine: draw(st.integers(min_value=1, max_value=3))
        for engine, _ in present
        if draw(st.booleans())
    }
    policy = _policy(
        draw(st.sampled_from([DispatchMode.SINGLETON, DispatchMode.HYBRID])),
        threshold=draw(st.integers(min_value=0, max_value=1200)),
        cap=draw(st.integers(min_value=0, max_value=5)),
        poll=draw(st.integers(min_value=1, max_value=60)),
        slots=slots,
    )
    load = DispatchLoad(
        in_flight={engine: draw(st.integers(min_value=0, max_value=4)) for engine, _ in present},
        waited_seconds=draw(st.floats(min_value=0, max_value=2000, allow_nan=False)),
        paid_overflow_today=draw(st.integers(min_value=0, max_value=6)),
    )
    return candidates, policy, load


@given(_situations())
def test_singleton_is_byte_for_byte_todays_selection(
    situation: tuple[list[Candidate], EngineDispatchPolicy, DispatchLoad],
) -> None:
    candidates, policy, load = situation
    singleton = EngineDispatchPolicy(
        mode=DispatchMode.SINGLETON,
        overflow_after_seconds=policy.overflow_after_seconds,
        paid_daily_cap=policy.paid_daily_cap,
        slot_poll_seconds=policy.slot_poll_seconds,
        slots=policy.slots,
    )
    plan = ENGINE_DISPATCHER.plan(candidates, singleton, load)
    assert plan == DispatchPlan(preferred_tier(candidates))


@given(_situations())
def test_paid_is_never_offered_while_a_local_slot_is_free(
    situation: tuple[list[Candidate], EngineDispatchPolicy, DispatchLoad],
) -> None:
    candidates, policy, load = situation
    if policy.mode is not DispatchMode.HYBRID:
        return
    free_local = [
        c
        for c in candidates
        if c.tier is EngineTier.LOCAL
        and c.effective_weight > 0
        and load.in_flight.get(c.engine_id, 0) < policy.slots_for(c.engine_id, c.tier)
    ]
    plan = ENGINE_DISPATCHER.plan(candidates, policy, load)
    if free_local:
        assert isinstance(plan, DispatchPlan)
        assert all(c.tier is EngineTier.LOCAL for c in plan.candidates)
        assert plan.overflow is None


@given(_situations())
def test_overflow_is_never_granted_at_or_over_the_cap_nor_before_the_wait(
    situation: tuple[list[Candidate], EngineDispatchPolicy, DispatchLoad],
) -> None:
    candidates, policy, load = situation
    plan = ENGINE_DISPATCHER.plan(candidates, policy, load)
    if isinstance(plan, DispatchPlan) and plan.overflow is not None:
        assert load.paid_overflow_today < policy.paid_daily_cap
        assert load.waited_seconds >= policy.overflow_after_seconds
        assert all(c.tier is EngineTier.PAID for c in plan.candidates)
        assert all(
            load.in_flight.get(c.engine_id, 0) < policy.slots_for(c.engine_id, c.tier)
            for c in plan.candidates
        )


@given(_situations())
def test_a_hold_is_only_planned_when_overflow_could_follow(
    situation: tuple[list[Candidate], EngineDispatchPolicy, DispatchLoad],
) -> None:
    candidates, policy, load = situation
    plan = ENGINE_DISPATCHER.plan(candidates, policy, load)
    if isinstance(plan, SlotHold):
        assert policy.mode is DispatchMode.HYBRID
        assert load.paid_overflow_today < policy.paid_daily_cap
        assert load.waited_seconds < policy.overflow_after_seconds
        assert 1 <= plan.retry_after_seconds <= policy.slot_poll_seconds
        assert any(
            c.tier is EngineTier.PAID
            and c.effective_weight > 0
            and load.in_flight.get(c.engine_id, 0) < policy.slots_for(c.engine_id, c.tier)
            for c in candidates
        )


# --- the UTC day ------------------------------------------------------------------------


def test_the_utc_day_starts_at_utc_midnight_whatever_the_zone() -> None:
    late_in_new_york = datetime(2026, 10, 3, 22, 30, tzinfo=timezone(timedelta(hours=-4)))
    assert UTC_DAY.start(late_in_new_york) == datetime(2026, 10, 4, tzinfo=UTC)
    assert UTC_DAY.label(late_in_new_york) == "2026-10-04"


def test_a_naive_instant_has_no_utc_day() -> None:
    with pytest.raises(ValueError, match="aware"):
        UTC_DAY.start(datetime(2026, 10, 3, 12, 0))  # noqa: DTZ001 -- the point of the test


# --- the measurement --------------------------------------------------------------------


def _session(engine: EngineId, start_min: float, end_min: float) -> LocalSession:
    return LocalSession(
        engine_id=engine,
        started_at=T0 + timedelta(minutes=start_min),
        ended_at=T0 + timedelta(minutes=end_min),
    )


def _config(**overrides: object) -> EngineDispatchConfig:
    base: dict[str, object] = {
        "overflow_after_seconds": 600,
        "auto_min_sessions": 3,
        "auto_min_contention": 0.25,
    }
    base.update(overrides)
    return EngineDispatchConfig(**base)  # type: ignore[arg-type]


def _measure(sessions: list[LocalSession], **overrides: object) -> DispatchMeasurement:
    return DISPATCH_MEASUREMENT_JUDGE.measure(
        sessions,
        local_slots={LOCAL: 1},
        config=_config(**overrides),
        window_end=T0 + timedelta(days=1),
        fingerprint="fp",
    )


def test_too_few_sessions_is_singleton() -> None:
    m = _measure([_session(LOCAL, 0, 60)])
    assert m.winner is DispatchMode.SINGLETON
    assert m.sessions == 1 and m.contended_sessions == 0 and m.contention == 0.0
    assert "fewer than 3" in m.reason


def test_uncontended_sessions_are_singleton() -> None:
    m = _measure([_session(LOCAL, 0, 10), _session(LOCAL, 20, 30), _session(LOCAL, 40, 50)])
    assert m.winner is DispatchMode.SINGLETON and m.contended_sessions == 0
    assert "seldom all occupied" in m.reason


def test_contended_but_short_waits_are_singleton() -> None:
    # Each queued session would have waited one minute: below a ten-minute threshold.
    m = _measure([_session(LOCAL, 0, 10), _session(LOCAL, 9, 20), _session(LOCAL, 19, 30)])
    assert m.contended_sessions == 2
    assert m.p50_contended_wait_seconds == 60.0
    assert m.winner is DispatchMode.SINGLETON and "hybrid would hold jobs" in m.reason


def test_long_contended_waits_are_hybrid() -> None:
    sessions = [_session(LOCAL, 0, 60), _session(LOCAL, 1, 61), _session(LOCAL, 2, 62)]
    m = _measure(sessions)
    # The second waits 59 minutes for the first; the third, with two open on one slot,
    # until both have ended -- 59 minutes too.
    assert m.contended_sessions == 2
    assert m.p50_contended_wait_seconds == 59 * 60
    assert m.winner is DispatchMode.HYBRID
    assert m.window_seconds == 168 * 3600 and m.measured_at == T0 + timedelta(days=1)


def test_a_free_slot_on_another_local_engine_means_no_wait() -> None:
    judge = DispatchMeasurementJudge()
    sessions = [_session(LOCAL, 0, 60), _session(LOCAL, 1, 61)]
    m = judge.measure(
        sessions,
        local_slots={LOCAL: 1, LOCAL_TOO: 1},
        config=_config(auto_min_sessions=1),
        window_end=T0,
        fingerprint="fp",
    )
    assert m.contended_sessions == 0


def test_two_slots_free_one_when_enough_sessions_end() -> None:
    judge = DispatchMeasurementJudge()
    sessions = [_session(LOCAL, 0, 30), _session(LOCAL, 0, 50), _session(LOCAL, 5, 60)]
    m = judge.measure(
        sessions,
        local_slots={LOCAL: 2},
        config=_config(auto_min_sessions=1),
        window_end=T0,
        fingerprint="fp",
    )
    # The third starts with two open on two slots; one frees at minute 30.
    assert m.contended_sessions == 1 and m.p50_contended_wait_seconds == 25 * 60


def test_sessions_of_unmeasured_engines_or_reversed_times_are_not_counted() -> None:
    m = _measure([_session(PAID, 0, 60), _session(LOCAL, 10, 5)])
    assert m.sessions == 0


def test_a_measurement_round_trips_through_its_payload() -> None:
    m = _measure([_session(LOCAL, 0, 60), _session(LOCAL, 1, 61), _session(LOCAL, 2, 62)])
    payload = m.payload()
    assert payload["algorithm"] == MEASUREMENT_ALGORITHM
    assert DispatchMeasurement.from_payload(payload) == m


@pytest.mark.parametrize(
    "change",
    [
        {"winner": "auto"},
        {"winner": "bogus"},
        {"measured_at": "not a date"},
        {"measured_at": "2026-10-03T12:00:00"},
        {"sessions": True},
        {"sessions": "3"},
        {"fingerprint": 7},
        {"algorithm": None},
    ],
)
def test_an_invalid_payload_is_no_measurement(change: dict[str, object]) -> None:
    payload = _measure([]).payload()
    payload.update(change)
    assert DispatchMeasurement.from_payload(payload) is None


def test_a_payload_missing_a_field_is_no_measurement() -> None:
    payload = _measure([]).payload()
    del payload["window_seconds"]
    assert DispatchMeasurement.from_payload(payload) is None


def test_a_payload_without_a_reason_reads_as_an_empty_one() -> None:
    payload = _measure([]).payload()
    del payload["reason"]
    measurement = DispatchMeasurement.from_payload(payload)
    assert measurement is not None and measurement.reason == ""


def test_the_fingerprint_changes_with_the_workload_and_the_implementation() -> None:
    judge = DISPATCH_MEASUREMENT_JUDGE
    base = judge.fingerprint(_config(), {LOCAL: 1}, "vibey-engine 1")
    assert base == judge.fingerprint(_config(), {LOCAL: 1}, "vibey-engine 1")
    assert base != judge.fingerprint(_config(), {LOCAL: 2}, "vibey-engine 1")
    assert base != judge.fingerprint(_config(), {LOCAL: 1, LOCAL_TOO: 1}, "vibey-engine 1")
    assert base != judge.fingerprint(
        _config(overflow_after_seconds=1), {LOCAL: 1}, "vibey-engine 1"
    )
    assert base != judge.fingerprint(_config(), {LOCAL: 1}, "vibey-engine 2")


def test_only_a_current_measurement_may_decide() -> None:
    judge = DISPATCH_MEASUREMENT_JUDGE
    m = _measure([])
    now = m.measured_at + timedelta(hours=1)
    day = timedelta(hours=24)
    assert judge.current(m, now=now, fingerprint="fp", max_age=day) is m
    assert judge.current(None, now=now, fingerprint="fp", max_age=day) is None
    assert judge.current(m, now=now, fingerprint="other", max_age=day) is None
    assert judge.current(m, now=now, fingerprint="fp", max_age=timedelta(minutes=30)) is None
    assert (
        judge.current(m, now=m.measured_at - timedelta(seconds=1), fingerprint="fp", max_age=day)
        is None
    )
    old = DispatchMeasurement(
        winner=m.winner,
        measured_at=m.measured_at,
        window_seconds=m.window_seconds,
        sessions=m.sessions,
        contended_sessions=m.contended_sessions,
        p50_contended_wait_seconds=m.p50_contended_wait_seconds,
        fingerprint="fp",
        reason=m.reason,
        algorithm="local-slot-contention/0",
    )
    assert judge.current(old, now=now, fingerprint="fp", max_age=day) is None
