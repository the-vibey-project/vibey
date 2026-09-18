# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Phase timing: visits bounded by PhaseTransitioned in seq order, measured
by produced_at, charged by the budget brake's own spend rule."""

import asyncio
import random
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.application.budget_source import LedgerBudgetSource
from vibey.domain.interfaces import (
    LedgerSpendRuleInterface,
    PhaseSpendInterface,
    PhaseTimelineInterface,
    PhaseTimingProjectionInterface,
    PhaseTotalInterface,
    PhaseVisitInterface,
    UnattributedSpendInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.phase_timing import (
    LEDGER_SPEND_RULE,
    NO_SPEND,
    PHASE_TIMING,
    TURN_EVENT_CAVEAT,
    LedgerSpendRule,
    PhaseSpend,
    PhaseTimeline,
    PhaseTimingProjection,
    PhaseVisit,
)

PROJECT_ID = uuid4()
T0 = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)


def _event(
    seq: int,
    kind: EventKind,
    *,
    phase: Phase,
    cycle: int = 1,
    at: datetime = T0,
    payload: dict[str, object] | None = None,
    project_id: UUID = PROJECT_ID,
) -> LedgerEvent:
    body = payload if payload is not None else {}
    return LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=cycle,
        phase=phase,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=at,
        payload=body,
        digest=digest_event(body),
    )


def _moved(seq: int, to: Phase, *, cycle: int = 1, at: datetime = T0) -> LedgerEvent:
    """A PhaseTransitioned shaped the way PhaseTransitionedDraftBuilder writes
    it: filed under the phase and cycle moved INTO."""
    return _event(
        seq,
        EventKind.PHASE_TRANSITIONED,
        phase=to,
        cycle=cycle,
        at=at,
        payload={"from": "unused-by-the-projection", "to": to.value, "cycle": cycle, "guard": None},
    )


def _turn(
    seq: int, phase: Phase, cost: object, *, cycle: int = 1, at: datetime = T0
) -> LedgerEvent:
    return _event(
        seq, EventKind.TURN_COMPLETED, phase=phase, cycle=cycle, at=at, payload={"cost_usd": cost}
    )


def _mins(n: int) -> timedelta:
    return timedelta(minutes=n)


# -- boundaries ---------------------------------------------------------------


def test_an_empty_ledger_projects_an_empty_timeline_that_still_carries_the_caveat() -> None:
    timeline = PhaseTimingProjection().project([])

    assert timeline == PhaseTimeline(
        visits=(), totals=(), unattributed=(), turn_caveat=TURN_EVENT_CAVEAT
    )


def test_each_transition_closes_the_visit_before_it_and_opens_the_next() -> None:
    events = [
        _moved(1, Phase.DESIGN, at=T0),
        _turn(2, Phase.DESIGN, 0.5, at=T0 + _mins(3)),
        _moved(3, Phase.BUILD, at=T0 + _mins(10)),
        _turn(4, Phase.BUILD, 1.25, at=T0 + _mins(20)),
        _moved(5, Phase.REVIEW, at=T0 + _mins(40)),
    ]

    design, build, review = PhaseTimingProjection().project(events).visits

    assert (design.phase, design.entered_seq, design.left_seq) == (Phase.DESIGN, 1, 3)
    assert (design.entered_at, design.left_at, design.duration) == (T0, T0 + _mins(10), _mins(10))
    assert design.measured and design.entry_observed and not design.clock_skewed
    assert design.spend == PhaseSpend(dollars=0.5, turn_completed_events=1)

    assert (build.phase, build.entered_seq, build.left_seq, build.duration) == (
        Phase.BUILD,
        3,
        5,
        _mins(30),
    )
    assert build.spend == PhaseSpend(dollars=1.25, turn_completed_events=1)

    # The last visit has not been left: no left_at, no duration, not measured.
    # Nothing here reads a clock, so "open" is never timed against "now".
    assert (review.phase, review.left_seq, review.left_at, review.duration) == (
        Phase.REVIEW,
        None,
        None,
        None,
    )
    assert not review.measured
    assert review.spend == NO_SPEND


def test_order_is_seq_even_when_the_caller_hands_the_events_over_shuffled() -> None:
    events = [
        _moved(1, Phase.DESIGN, at=T0),
        _moved(2, Phase.BUILD, at=T0 + _mins(5)),
        _turn(3, Phase.BUILD, 2.0, at=T0 + _mins(6)),
        _moved(4, Phase.REVIEW, at=T0 + _mins(9)),
    ]
    projection = PhaseTimingProjection()

    assert projection.project(list(reversed(events))) == projection.project(events)


def test_a_range_that_starts_inside_a_phase_opens_a_visit_whose_entry_was_not_observed() -> None:
    events = [
        _turn(7, Phase.BUILD, 1.0, at=T0),
        _moved(8, Phase.REVIEW, at=T0 + _mins(15)),
    ]

    build, _review = PhaseTimingProjection().project(events).visits

    assert (build.phase, build.entered_seq, build.entered_at) == (Phase.BUILD, 7, T0)
    assert not build.entry_observed
    # A lower bound, still reported -- but never offered to an estimator.
    assert build.duration == _mins(15)
    assert not build.measured
    assert build.spend.dollars == 1.0


def test_a_backwards_clock_reports_zero_flags_the_skew_and_keeps_the_raw_times() -> None:
    """PhaseTransitioned carries database time and other kinds a handler's
    clock; either can be behind. seq still fixes the boundaries."""
    events = [
        _moved(1, Phase.DESIGN, at=T0 + _mins(30)),
        _moved(2, Phase.BUILD, at=T0),  # recorded earlier than the move before it
        _moved(3, Phase.REVIEW, at=T0 + _mins(50)),
    ]

    design, build, _review = PhaseTimingProjection().project(events).visits

    assert design.clock_skewed
    assert design.duration == timedelta(0)
    assert (design.entered_at, design.left_at) == (T0 + _mins(30), T0)
    assert not design.measured
    # The skew moves time to the neighbour rather than destroying it.
    assert build.duration == _mins(50)
    assert not build.clock_skewed and build.measured


def test_a_phase_visited_twice_in_one_cycle_is_two_visits_and_one_total() -> None:
    """DEPLOY_EXECUTE -> DEPLOY_EXECUTE is a legal retry edge; the cycle does not move."""
    events = [
        _moved(1, Phase.DEPLOY_EXECUTE, at=T0),
        _turn(2, Phase.DEPLOY_EXECUTE, 1.0, at=T0 + _mins(1)),
        _moved(3, Phase.DEPLOY_EXECUTE, at=T0 + _mins(4)),
        _turn(4, Phase.DEPLOY_EXECUTE, 3.0, at=T0 + _mins(5)),
        _moved(5, Phase.DEPLOY_REVIEW, at=T0 + _mins(10)),
    ]

    timeline = PhaseTimingProjection().project(events)
    first, second, _review = timeline.visits
    retry_total, review_total = timeline.totals

    assert (first.duration, first.spend.dollars) == (_mins(4), 1.0)
    assert (second.duration, second.spend.dollars) == (_mins(6), 3.0)
    assert (retry_total.cycle, retry_total.phase, retry_total.visits) == (
        1,
        Phase.DEPLOY_EXECUTE,
        2,
    )
    assert retry_total.duration == _mins(10)
    assert retry_total.measured
    assert retry_total.spend == PhaseSpend(dollars=4.0, turn_completed_events=2)
    # A total over an open visit has no duration yet, and is not measured.
    assert (review_total.visits, review_total.duration, review_total.measured) == (1, None, False)


def test_a_total_is_unmeasured_when_any_visit_under_it_is() -> None:
    events = [
        _moved(1, Phase.BUILD, cycle=1, at=T0 + _mins(9)),
        _moved(2, Phase.REVIEW, cycle=1, at=T0),  # skewed: BUILD is clamped to zero
        _moved(3, Phase.BUILD, cycle=1, at=T0 + _mins(20)),
        _moved(4, Phase.REVIEW, cycle=1, at=T0 + _mins(30)),
    ]

    build_total = PhaseTimingProjection().project(events).totals[0]

    assert (build_total.phase, build_total.visits) == (Phase.BUILD, 2)
    assert build_total.duration == _mins(10)
    assert not build_total.measured


# -- spend attribution --------------------------------------------------------


def test_spend_follows_its_own_phase_tag_not_its_position() -> None:
    """A BUILD job's turn that the tailer appends after the move to REVIEW is
    still BUILD's money."""
    events = [
        _moved(1, Phase.BUILD, at=T0),
        _moved(2, Phase.REVIEW, at=T0 + _mins(10)),
        _turn(3, Phase.BUILD, 0.75, at=T0 + _mins(11)),
    ]

    build, review = PhaseTimingProjection().project(events).visits

    assert build.spend == PhaseSpend(dollars=0.75, turn_completed_events=1)
    assert review.spend == NO_SPEND


def test_spend_goes_to_the_latest_visit_with_its_tag_opened_by_its_seq() -> None:
    events = [
        _moved(1, Phase.DESIGN, at=T0),
        _moved(2, Phase.BUILD, at=T0 + _mins(1)),
        _moved(3, Phase.DESIGN, at=T0 + _mins(2)),  # BUILD -> DESIGN, same cycle
        _turn(4, Phase.DESIGN, 5.0, at=T0 + _mins(3)),
    ]

    first_design, _build, second_design = PhaseTimingProjection().project(events).visits

    assert first_design.spend == NO_SPEND
    assert second_design.spend.dollars == 5.0


def test_spend_no_visit_can_own_is_reported_unattributed_not_dropped() -> None:
    events = [
        _moved(1, Phase.DESIGN, at=T0),
        # Claims REVIEW before REVIEW was ever entered.
        _turn(2, Phase.REVIEW, 1.0, at=T0 + _mins(1)),
        _moved(3, Phase.REVIEW, at=T0 + _mins(2)),
        # Claims a cycle the ledger never moved into.
        _event(
            4,
            EventKind.BUDGET_SPENT,
            phase=Phase.BUILD,
            cycle=2,
            payload={"dollars": 2.5, "turns": 3},
        ),
        _turn(5, Phase.REVIEW, 0.5, at=T0 + _mins(3)),
        _turn(6, Phase.REVIEW, 0.25, cycle=1, at=T0 + _mins(4)),
    ]

    timeline = PhaseTimingProjection().project(events)
    early_review, never_entered = timeline.unattributed

    assert (early_review.cycle, early_review.phase) == (1, Phase.REVIEW)
    assert early_review.spend == PhaseSpend(dollars=1.0, turn_completed_events=1)
    assert (never_entered.cycle, never_entered.phase) == (2, Phase.BUILD)
    assert never_entered.spend == PhaseSpend(dollars=2.5, budget_turns=3)
    assert timeline.visits[1].spend == PhaseSpend(dollars=0.75, turn_completed_events=2)


def test_non_spend_events_move_neither_boundaries_nor_money() -> None:
    events = [
        _moved(1, Phase.BUILD, at=T0),
        _event(2, EventKind.FINDING_RAISED, phase=Phase.BUILD, payload={"cost_usd": 99.0}),
        _event(3, EventKind.TOOL_INVOKED, phase=Phase.BUILD),
    ]

    (build,) = PhaseTimingProjection().project(events).visits

    assert build.spend == NO_SPEND
    assert build.left_seq is None


# -- the spend rule -----------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "payload", "expected"),
    [
        (EventKind.TURN_COMPLETED, {"cost_usd": 0.4}, PhaseSpend(0.4, 1, 0)),
        (EventKind.TURN_COMPLETED, {"cost_usd": 2}, PhaseSpend(2.0, 1, 0)),
        (EventKind.TURN_COMPLETED, {}, PhaseSpend(0.0, 1, 0)),
        (EventKind.TURN_COMPLETED, {"cost_usd": "n/a"}, PhaseSpend(0.0, 1, 0)),
        (EventKind.BUDGET_SPENT, {"dollars": 1.5, "turns": 4}, PhaseSpend(1.5, 0, 4)),
        (EventKind.BUDGET_SPENT, {"dollars": 3}, PhaseSpend(3.0, 0, 0)),
        # Capacity chatter maps to BudgetSpent with neither key: a zero, not an error.
        (EventKind.BUDGET_SPENT, {"headroom": 0.9}, PhaseSpend(0.0, 0, 0)),
        (EventKind.BUDGET_SPENT, {"dollars": "bad", "turns": 1.5}, PhaseSpend(0.0, 0, 0)),
        (EventKind.VERDICT_RENDERED, {"cost_usd": 9.0}, None),
    ],
)
def test_the_spend_rule_is_the_budget_brakes_rule(
    kind: EventKind, payload: dict[str, object], expected: PhaseSpend | None
) -> None:
    event = _event(1, kind, phase=Phase.BUILD, payload=payload)

    assert LedgerSpendRule().spend_of(event) == expected


def test_spends_add_without_mutating_either_side() -> None:
    left = PhaseSpend(dollars=1.0, turn_completed_events=2, budget_turns=3)
    right = PhaseSpend(dollars=0.5, turn_completed_events=1, budget_turns=0)

    assert left.plus(right) == PhaseSpend(dollars=1.5, turn_completed_events=3, budget_turns=3)
    assert left == PhaseSpend(dollars=1.0, turn_completed_events=2, budget_turns=3)
    assert NO_SPEND.plus(left) == left


# -- turns are not turns ------------------------------------------------------


def test_the_turn_count_is_named_for_what_it_counts_and_carries_its_caveat() -> None:
    """Every claudeloop turn lands as two TurnCompleted events (chatter.assistant
    and turn.completed), so the projection must not present the count as turns."""
    events = [
        _moved(1, Phase.BUILD, at=T0),
        _turn(2, Phase.BUILD, None),  # chatter.assistant: no cost
        _turn(3, Phase.BUILD, 0.1),  # turn.completed: the real cost
    ]

    timeline = PhaseTimingProjection().project(events)

    assert timeline.visits[0].spend.turn_completed_events == 2
    assert not hasattr(timeline.visits[0].spend, "turns")
    assert "not turns" in timeline.turn_caveat
    assert "loop_events.py" in timeline.turn_caveat


def test_the_caveat_and_the_spend_rule_are_constructor_arguments() -> None:
    class FlatRule:
        def spend_of(self, event: LedgerEvent) -> PhaseSpend | None:
            return PhaseSpend(dollars=1.0) if event.kind is EventKind.TOOL_INVOKED else None

    projection = PhaseTimingProjection(spend_rule=FlatRule(), turn_caveat="exact turns")
    events = [_moved(1, Phase.BUILD), _event(2, EventKind.TOOL_INVOKED, phase=Phase.BUILD)]

    timeline = projection.project(events)

    assert timeline.turn_caveat == "exact turns"
    assert timeline.visits[0].spend == PhaseSpend(dollars=1.0)


# -- guards -------------------------------------------------------------------


def test_events_from_two_projects_are_refused() -> None:
    events = [_moved(1, Phase.DESIGN), _moved(2, Phase.BUILD, at=T0, cycle=1)]
    events[1] = replace(events[1], project_id=uuid4())

    with pytest.raises(ValueError, match="span 2 projects"):
        PhaseTimingProjection().project(events)


def test_a_visit_is_left_at_a_seq_and_a_time_together() -> None:
    with pytest.raises(ValueError, match="together"):
        PhaseVisit(
            cycle=1,
            phase=Phase.BUILD,
            entered_seq=1,
            entered_at=T0,
            entry_observed=True,
            left_seq=2,
            left_at=None,
            spend=NO_SPEND,
        )


def test_every_published_object_satisfies_its_declared_seam() -> None:
    events = [_moved(1, Phase.BUILD), _turn(2, Phase.REVIEW, 1.0), _moved(3, Phase.REVIEW)]
    timeline = PHASE_TIMING.project(events)

    assert isinstance(PHASE_TIMING, PhaseTimingProjectionInterface)
    assert isinstance(LEDGER_SPEND_RULE, LedgerSpendRuleInterface)
    assert isinstance(timeline, PhaseTimelineInterface)
    assert all(isinstance(visit, PhaseVisitInterface) for visit in timeline.visits)
    assert all(isinstance(total, PhaseTotalInterface) for total in timeline.totals)
    assert isinstance(timeline.unattributed[0], UnattributedSpendInterface)
    assert isinstance(timeline.unattributed[0].spend, PhaseSpendInterface)


# -- properties ---------------------------------------------------------------

_SPEND_KINDS = (EventKind.TURN_COMPLETED, EventKind.BUDGET_SPENT)
_KINDS = (EventKind.PHASE_TRANSITIONED, *_SPEND_KINDS, EventKind.FINDING_RAISED)

# Dyadic amounts sum exactly in binary floating point, so the per-cycle
# parity check below can demand equality instead of a tolerance. Junk values
# are included on purpose: both rules must agree on what they ignore.
_AMOUNTS = st.one_of(
    st.integers(0, 4096).map(lambda k: k / 64),
    st.integers(0, 50),
    st.just("bad"),
    st.none(),
)


@st.composite
def _ledgers(draw: st.DrawFn, *, monotone_clock: bool) -> list[LedgerEvent]:
    """One project's ledger: gapless seq, cycles that only move forward, and
    spend tagged mostly with the current visit, sometimes with anything."""
    size = draw(st.integers(0, 30))
    cycle, phase = 1, Phase.INTAKE
    clock = T0
    events: list[LedgerEvent] = []
    for seq in range(1, size + 1):
        kind = draw(st.sampled_from(_KINDS))
        if monotone_clock:
            clock += timedelta(seconds=draw(st.integers(0, 7200)))
        else:
            clock = T0 + timedelta(seconds=draw(st.integers(-86_400, 86_400)))
        if kind is EventKind.PHASE_TRANSITIONED:
            cycle += draw(st.integers(0, 1))
            phase = draw(st.sampled_from(list(Phase)))
            events.append(_moved(seq, phase, cycle=cycle, at=clock))
            continue
        tag_cycle, tag_phase = cycle, phase
        if seq > 1 and draw(st.booleans()):
            tag_cycle = draw(st.integers(1, cycle + 1))
            tag_phase = draw(st.sampled_from(list(Phase)))
        payload: dict[str, object] = (
            {"cost_usd": draw(_AMOUNTS)}
            if kind is EventKind.TURN_COMPLETED
            else {
                "dollars": draw(_AMOUNTS),
                "turns": draw(st.one_of(st.integers(0, 5), st.just("x"))),
            }
        )
        events.append(
            _event(seq, kind, phase=tag_phase, cycle=tag_cycle, at=clock, payload=payload)
        )
    return events


def _boundaries(timeline: PhaseTimeline) -> list[tuple[object, ...]]:
    return [
        (v.cycle, v.phase, v.entered_seq, v.left_seq, v.entry_observed, v.spend)
        for v in timeline.visits
    ]


@given(_ledgers(monotone_clock=True))
def test_durations_of_a_closed_cycle_sum_to_its_wall_clock_span(
    events: list[LedgerEvent],
) -> None:
    timeline = PhaseTimingProjection().project(events)

    for cycle in {visit.cycle for visit in timeline.visits}:
        visits = [visit for visit in timeline.visits if visit.cycle == cycle]
        left_at = visits[-1].left_at
        durations = [visit.duration for visit in visits]
        if left_at is None or None in durations:
            continue
        total = sum((d for d in durations if d is not None), timedelta(0))
        assert total == left_at - visits[0].entered_at
        assert not any(visit.clock_skewed for visit in visits)


@given(_ledgers(monotone_clock=False))
def test_skew_is_clamped_flagged_and_never_loses_wall_clock_time(
    events: list[LedgerEvent],
) -> None:
    visits = PhaseTimingProjection().project(events).visits
    # Only the last visit is ever open: every transition leaves one and enters the next.
    assert all(visit.left_at is not None for visit in visits[:-1])
    closed = visits[:-1]

    total = timedelta(0)
    for visit in closed:
        assert visit.left_at is not None and visit.duration is not None
        assert visit.duration >= timedelta(0)
        assert visit.clock_skewed == (visit.left_at < visit.entered_at)
        assert visit.measured == (visit.entry_observed and not visit.clock_skewed)
        total += visit.duration
    if closed:
        # The chain is contiguous: each visit is left where the next is entered,
        # so the raw differences telescope to the span and the clamped ones exceed it.
        assert visits[-1].entered_at == closed[-1].left_at
        span = visits[-1].entered_at - closed[0].entered_at
        assert total >= span
        assert (total == span) == (not any(visit.clock_skewed for visit in closed))


@given(st.data())
def test_permuting_produced_at_never_moves_a_seq_ordered_boundary(data: st.DataObject) -> None:
    events = data.draw(_ledgers(monotone_clock=True))
    times = data.draw(st.permutations([event.produced_at for event in events]))
    reclocked = [replace(event, produced_at=at) for event, at in zip(events, times, strict=True)]
    projection = PhaseTimingProjection()

    assert _boundaries(projection.project(reclocked)) == _boundaries(projection.project(events))


@given(_ledgers(monotone_clock=False), st.randoms(use_true_random=False))
def test_the_order_the_events_arrive_in_changes_nothing(
    events: list[LedgerEvent], rng: random.Random
) -> None:
    shuffled = list(events)
    rng.shuffle(shuffled)
    projection = PhaseTimingProjection()

    assert projection.project(shuffled) == projection.project(events)


def _charged(timeline: PhaseTimeline, cycle: int) -> PhaseSpend:
    spend = NO_SPEND
    for visit in timeline.visits:
        if visit.cycle == cycle:
            spend = spend.plus(visit.spend)
    for row in timeline.unattributed:
        if row.cycle == cycle:
            spend = spend.plus(row.spend)
    return spend


class _Reader:
    def __init__(self, events: Sequence[LedgerEvent]) -> None:
        self._events = tuple(sorted(events, key=lambda event: event.seq))

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return self._events


@given(_ledgers(monotone_clock=False))
def test_every_dollar_the_budget_brake_sees_is_charged_somewhere(
    events: list[LedgerEvent],
) -> None:
    """The cross-layer pin the module docstring promises: until
    LedgerBudgetSource adopts LedgerSpendRule, the two must agree per cycle,
    and the visits plus the unattributed rows must hold all of it."""
    timeline = PhaseTimingProjection().project(events)
    brake = LedgerBudgetSource(_Reader(events))

    for cycle in {event.cycle for event in events}:
        budget = asyncio.run(brake.current(PROJECT_ID, cycle))
        charged = _charged(timeline, cycle)
        assert charged.dollars == budget.dollars_spent
        assert charged.turn_completed_events + charged.budget_turns == budget.turns_spent
