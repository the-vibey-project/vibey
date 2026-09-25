# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Failover and handback, the pure half (ADR-0070)."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.capacity import (
    AuthenticationFailed,
    Available,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.effort import Effort
from vibey.domain.failover import (
    CAPACITY_SIGNALS,
    FAILOVER_POLICY,
    FailoverCause,
    FailoverKind,
    FailoverRecord,
    FailoverSettings,
    FailoverStatus,
)
from vibey.domain.interfaces.failover_interface import (
    CapacitySignalClassifierInterface,
    FailoverPolicyInterface,
)
from vibey.domain.ledger import EventKind

NOW = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)
SETTINGS = FailoverSettings()


def test_the_singletons_satisfy_their_interfaces() -> None:
    assert isinstance(FAILOVER_POLICY, FailoverPolicyInterface)
    assert isinstance(CAPACITY_SIGNALS, CapacitySignalClassifierInterface)


def test_the_kinds_are_the_ledgers_own() -> None:
    assert FailoverKind.FAILED_OVER.value == EventKind.ENGINE_FAILED_OVER.value
    assert FailoverKind.PROBED.value == EventKind.ENGINE_PROBED.value
    assert FailoverKind.HANDED_BACK.value == EventKind.ENGINE_HANDED_BACK.value


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("rate_limit", WindowExhausted(resets_at=None, rate_limit_type="rate_limit")),
        ("billing_error", CreditsExhausted()),
        ("authentication_failed", AuthenticationFailed(detail="authentication_failed")),
        ("overloaded", Available()),
        ("server_error", Available()),
        ("unknown", Available()),
    ],
)
def test_stopfailure_error_types_classify(error: str, expected: object) -> None:
    assert CAPACITY_SIGNALS.classify(error) == expected


def test_an_auth_error_keeps_its_detail() -> None:
    assert CAPACITY_SIGNALS.classify("account_on_hold", "held") == AuthenticationFailed("held")


def test_credits_never_carry_a_clock() -> None:
    assert "resets_at" not in {f.name for f in fields(CreditsExhausted)}


def test_a_window_without_a_reset_probes_after_the_interval() -> None:
    plan = FAILOVER_POLICY.plan(WindowExhausted(), now=NOW, settings=SETTINGS)
    assert plan is not None
    assert plan.cause is FailoverCause.WINDOW
    assert plan.target_engine == "gptossloop"
    assert plan.effort is Effort.ULTRA
    assert plan.probe_not_before == NOW + timedelta(minutes=30)


def test_a_stated_reset_only_schedules_the_probe() -> None:
    resets = NOW + timedelta(days=4)
    plan = FAILOVER_POLICY.plan(WindowExhausted(resets_at=resets), now=NOW, settings=SETTINGS)
    assert plan is not None and plan.probe_not_before == resets


@given(st.integers(min_value=1, max_value=10**7))
def test_credits_probe_on_the_interval_never_on_a_reset(seconds: int) -> None:
    settings = FailoverSettings(probe_interval=timedelta(seconds=seconds))
    plan = FAILOVER_POLICY.plan(CreditsExhausted(), now=NOW, settings=settings)
    assert plan is not None
    assert plan.cause is FailoverCause.CREDITS
    assert plan.probe_not_before == NOW + timedelta(seconds=seconds)


@pytest.mark.parametrize("state", [Available(), AuthenticationFailed()])
def test_no_failover_without_a_capacity_rejection(state: object) -> None:
    assert FAILOVER_POLICY.plan(state, now=NOW, settings=SETTINGS) is None  # type: ignore[arg-type]


def test_a_switched_off_failover_plans_nothing() -> None:
    off = FailoverSettings(enabled=False)
    assert FAILOVER_POLICY.plan(CreditsExhausted(), now=NOW, settings=off) is None


def test_settings_refuse_nonsense() -> None:
    with pytest.raises(ValueError, match="probe_interval"):
        FailoverSettings(probe_interval=timedelta(0))
    with pytest.raises(ValueError, match="target_engine"):
        FailoverSettings(target_engine="")


def test_capacity_outranks_a_completion_claim() -> None:
    assert FAILOVER_POLICY.outranks_completion(CreditsExhausted())
    assert FAILOVER_POLICY.outranks_completion(WindowExhausted())
    assert not FAILOVER_POLICY.outranks_completion(Available())


def _rec(kind: FailoverKind, minutes: int, **payload: object) -> FailoverRecord:
    return FailoverRecord(kind=kind, at=NOW + timedelta(minutes=minutes), payload=payload)


def test_status_with_no_records_is_idle() -> None:
    status = FAILOVER_POLICY.status(())
    assert status == FailoverStatus(active=False, failover=None, probe_ok=None)
    assert not status.may_hand_back
    assert not status.probe_due(NOW)


def test_handback_needs_a_successful_probe_after_the_failover() -> None:
    failover = _rec(FailoverKind.FAILED_OVER, 0, probe_not_before=NOW.isoformat())
    failed_probe = _rec(FailoverKind.PROBED, 1, ok=False)
    status = FAILOVER_POLICY.status([failover, failed_probe])
    assert status.active and not status.may_hand_back
    ok_probe = _rec(FailoverKind.PROBED, 2, ok=True)
    later_ok = _rec(FailoverKind.PROBED, 3, ok=True)
    status = FAILOVER_POLICY.status([failover, failed_probe, ok_probe, later_ok])
    assert status.may_hand_back and status.probe_ok == ok_probe


def test_a_probe_before_any_failover_counts_for_nothing() -> None:
    early = _rec(FailoverKind.PROBED, -1, ok=True)
    stray = _rec(FailoverKind.HANDED_BACK, -1)
    failover = _rec(FailoverKind.FAILED_OVER, 0)
    status = FAILOVER_POLICY.status([early, stray, failover])
    assert status.active and status.probe_ok is None


def test_a_new_failover_resets_the_probe() -> None:
    records = [
        _rec(FailoverKind.FAILED_OVER, 0),
        _rec(FailoverKind.PROBED, 1, ok=True),
        _rec(FailoverKind.HANDED_BACK, 2),
    ]
    assert not FAILOVER_POLICY.status(records).active
    records.append(_rec(FailoverKind.FAILED_OVER, 3))
    status = FAILOVER_POLICY.status(records)
    assert status.active and status.probe_ok is None


def test_untrusted_records_are_ignored() -> None:
    forged = FailoverRecord(FailoverKind.FAILED_OVER, NOW, {}, trusted=False)
    assert not FAILOVER_POLICY.status([forged]).active


def test_probe_due_follows_the_schedule() -> None:
    later = NOW + timedelta(hours=1)
    status = FAILOVER_POLICY.status(
        [_rec(FailoverKind.FAILED_OVER, 0, probe_not_before=later.isoformat())]
    )
    assert not status.probe_due(NOW)
    assert status.probe_due(later)
    unscheduled = FAILOVER_POLICY.status([_rec(FailoverKind.FAILED_OVER, 0)])
    assert unscheduled.probe_due(NOW)


def test_rows_read_into_records_and_skip_what_is_unknown() -> None:
    rows = [
        {"kind": "EngineFailedOver", "at": NOW.isoformat(), "payload": {"a": 1}},
        {"kind": "EngineProbed", "at": NOW.isoformat(), "payload": {}, "trusted": False},
        {"kind": "SomethingNewer", "at": NOW.isoformat(), "payload": {}},
        {"kind": "EngineProbed", "at": 5, "payload": {}},
        {"kind": "EngineProbed", "at": NOW.isoformat(), "payload": []},
    ]
    records = FAILOVER_POLICY.read_rows(rows)
    assert records == (
        FailoverRecord(FailoverKind.FAILED_OVER, NOW, {"a": 1}, True),
        FailoverRecord(FailoverKind.PROBED, NOW, {}, False),
    )
