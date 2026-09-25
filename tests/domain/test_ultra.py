# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ULTRA's pure half (ADR-0063): it is chosen and never climbed into, it never parks for
length, and it always stops -- on the operator's Stop or at a cap -- and nowhere else."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.budget import BudgetLedger
from vibey.domain.effort import (
    BUILD_LADDER,
    BUILD_LADDER_EXHAUSTED,
    PHASE_BASE_EFFORT,
    Effort,
    effort_for_attempt,
    triage_required_effort,
)
from vibey.domain.engine import EngineId
from vibey.domain.interfaces.ultra_interface import UltraPassInterface, UltraPolicyInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.review import Ambiguity, FindingRef, Severity
from vibey.domain.ultra import (
    NO_CAP_PHRASE,
    ULTRA_PAYLOAD_KEY,
    ULTRA_POLICY,
    UltraPass,
    UltraState,
    UltraVerdict,
)

PROJECT = UUID("00000000-0000-0000-0000-00000000aaaa")
T0 = datetime(2026, 9, 25, tzinfo=UTC)


def _event(
    seq: int,
    kind: EventKind,
    payload: dict[str, object] | None = None,
    *,
    provenance: Provenance = Provenance.TRUSTED,
    engine_id: EngineId | None = None,
    minutes: float = 0,
) -> LedgerEvent:
    body = payload or {}
    return LedgerEvent(
        event_id=uuid4(),
        project_id=PROJECT,
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=engine_id,
        job_id=None,
        causation_id=None,
        correlation_id=PROJECT,
        provenance=provenance,
        produced_at=T0 + timedelta(minutes=minutes),
        payload=body,
        digest=digest_event(body),
    )


def _budget(spent: float, cap: float | None, turns: int = 0, turn_cap: int | None = None):  # type: ignore[no-untyped-def]
    return BudgetLedger(turns_spent=turns, dollars_spent=spent, max_turns=turn_cap, max_dollars=cap)


def test_the_policy_and_a_pass_satisfy_their_interfaces() -> None:
    assert isinstance(ULTRA_POLICY, UltraPolicyInterface)
    assert isinstance(UltraPass("item"), UltraPassInterface)


def test_ultra_is_the_sixth_effort_after_max() -> None:
    assert list(Effort)[-1] is Effort.ULTRA
    assert Effort.ULTRA == 5 and Effort.ULTRA > Effort.MAX


@given(attempt=st.integers(min_value=1, max_value=BUILD_LADDER_EXHAUSTED))
def test_no_ladder_ever_climbs_into_ultra(attempt: int) -> None:
    for base in Effort:
        if base is Effort.ULTRA:
            continue
        assert effort_for_attempt(base, attempt) < Effort.ULTRA
    assert Effort.ULTRA not in BUILD_LADDER
    assert Effort.ULTRA not in PHASE_BASE_EFFORT.values()


@given(severities=st.lists(st.sampled_from(list(Severity)), max_size=6))
def test_triage_never_asks_for_ultra(severities: list[Severity]) -> None:
    findings = [
        FindingRef(finding_id=f"f{i}", severity=s, ambiguity=Ambiguity.CLEAR)
        for i, s in enumerate(severities)
    ]
    assert triage_required_effort(findings) < Effort.ULTRA


@given(
    ladder=st.sampled_from([e for e in Effort if e is not Effort.ULTRA]),
    attempts=st.integers(min_value=1, max_value=10_000),
)
def test_an_active_run_is_ultra_at_any_attempt_so_it_never_parks_for_length(
    ladder: Effort, attempts: int
) -> None:
    # The handler consults no ladder at ULTRA, so no attempt count can exhaust it.
    assert ULTRA_POLICY.effort(UltraState(active=True), ladder) is Effort.ULTRA
    assert ULTRA_POLICY.effort(UltraState(active=False), ladder) is ladder


@given(
    active=st.booleans(),
    no_cap=st.booleans(),
    spent=st.floats(min_value=0, max_value=1e6, allow_nan=False),
    cap=st.one_of(st.none(), st.floats(min_value=0.01, max_value=1e6, allow_nan=False)),
    turns=st.integers(min_value=0, max_value=10_000),
    turn_cap=st.one_of(st.none(), st.integers(min_value=1, max_value=10_000)),
)
def test_ultra_always_stops_on_stop_or_at_a_cap_and_nowhere_else(
    active: bool,
    no_cap: bool,
    spent: float,
    cap: float | None,
    turns: int,
    turn_cap: int | None,
) -> None:
    budget = _budget(spent, cap, turns, turn_cap)
    verdict = ULTRA_POLICY.decide(UltraState(active=active, no_cap_declared=no_cap), budget)
    if not active:
        assert verdict is UltraVerdict.OPERATOR_STOP
    elif budget.any_exhausted:
        assert verdict is UltraVerdict.BUDGET_BRAKE
    elif cap is None and not no_cap:
        assert verdict is UltraVerdict.NEEDS_CAP
    else:
        assert verdict is UltraVerdict.CONTINUE


@given(
    passes=st.integers(min_value=1, max_value=50),
    stop_after=st.integers(min_value=1, max_value=50),
    per_pass=st.floats(min_value=0.01, max_value=100, allow_nan=False),
    cap=st.one_of(st.none(), st.floats(min_value=0.01, max_value=500, allow_nan=False)),
)
def test_a_run_of_passes_ends_at_the_stop_or_the_cap_whichever_comes_first(
    passes: int, stop_after: int, per_pass: float, cap: float | None
) -> None:
    """Simulate the loop: each pass spends; Stop lands after `stop_after` passes. The
    run always ends, and ends for one of the two reasons."""
    no_cap = cap is None
    spent = 0.0
    number = 0
    ended = None
    for number in range(1, 10_000):  # pragma: no branch -- every run ends
        state = UltraState(active=number <= stop_after, no_cap_declared=no_cap)
        verdict = ULTRA_POLICY.decide(state, _budget(spent, cap))
        if verdict is not UltraVerdict.CONTINUE:
            ended = verdict
            break
        spent += per_pass
    assert ended in {UltraVerdict.OPERATOR_STOP, UltraVerdict.BUDGET_BRAKE}
    assert number <= stop_after + 1


def test_the_latest_trusted_control_decides_and_untrusted_ones_count_for_nothing() -> None:
    events = [
        _event(1, EventKind.ULTRA_STARTED),
        _event(2, EventKind.ULTRA_NO_CAP_CHANGED, {"enabled": True}),
        _event(3, EventKind.ULTRA_STOPPED, provenance=Provenance.AGENT),
        _event(4, EventKind.ULTRA_NO_CAP_CHANGED, {"enabled": False}, provenance=Provenance.AGENT),
        _event(5, EventKind.TURN_COMPLETED),
    ]
    assert ULTRA_POLICY.state(events) == UltraState(active=True, no_cap_declared=True)
    stopped = [*events, _event(6, EventKind.ULTRA_STOPPED)]
    assert ULTRA_POLICY.state(stopped).active is False
    withdrawn = [*events, _event(7, EventKind.ULTRA_NO_CAP_CHANGED, {"enabled": "yes"})]
    assert ULTRA_POLICY.state(withdrawn).no_cap_declared is False
    assert ULTRA_POLICY.state([]) == UltraState()


def test_each_pass_has_its_own_key_so_a_replay_is_answered_once() -> None:
    first = UltraPass("item-1")
    second = first.next()
    assert second == UltraPass("item-1", 2)
    assert first.job_key(PROJECT, 1) != second.job_key(PROJECT, 1)
    assert second.job_key(PROJECT, 1) == UltraPass("item-1", 2).job_key(PROJECT, 1)
    assert UltraPass("item-2", 2).job_key(PROJECT, 1) != second.job_key(PROJECT, 1)
    with pytest.raises(ValueError, match="numbered from 1"):
        UltraPass("item-1", 0)


@pytest.mark.parametrize(
    ("payload", "number"),
    [
        ({}, 1),
        ({ULTRA_PAYLOAD_KEY: 3}, 3),
        ({ULTRA_PAYLOAD_KEY: True}, 1),
        ({ULTRA_PAYLOAD_KEY: 0}, 1),
        ({ULTRA_PAYLOAD_KEY: "4"}, 1),
    ],
)
def test_a_payload_names_its_pass_or_is_the_first(payload: dict[str, object], number: int) -> None:
    assert ULTRA_POLICY.pass_of("item", payload) == UltraPass("item", number)


def test_the_phrase_is_matched_exactly_but_for_surrounding_space() -> None:
    assert ULTRA_POLICY.phrase_matches(NO_CAP_PHRASE)
    assert ULTRA_POLICY.phrase_matches(f"  {NO_CAP_PHRASE}\n")
    assert not ULTRA_POLICY.phrase_matches(NO_CAP_PHRASE.lower())
    assert not ULTRA_POLICY.phrase_matches("")


def test_the_rate_is_measured_spend_over_its_span_or_unknown() -> None:
    claude = EngineId.CLAUDELOOP
    events = [
        _event(1, EventKind.TURN_COMPLETED, {"cost_usd": 1.0}, engine_id=claude, minutes=0),
        _event(2, EventKind.TURN_COMPLETED, {"cost_usd": 2.0}, engine_id=claude, minutes=30),
        _event(3, EventKind.TURN_COMPLETED, {"cost_usd": 0.0}, engine_id=claude, minutes=90),
        _event(4, EventKind.TURN_COMPLETED, {"cost_usd": 5.0}, engine_id=EngineId.CODEXLOOP),
        _event(5, EventKind.ULTRA_STARTED),
    ]
    assert ULTRA_POLICY.rate_per_hour(events, "claudeloop") == pytest.approx(6.0)
    assert ULTRA_POLICY.rate_per_hour(events) == pytest.approx(16.0)
    assert ULTRA_POLICY.rate_per_hour(events[:1]) is None  # one instant is no span
    assert ULTRA_POLICY.rate_per_hour([]) is None
    assert ULTRA_POLICY.rate_per_hour(events, "gptossloop") is None
