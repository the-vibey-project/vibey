# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pure half of `vibey budget`: which values are caps, what a request changes, who
it is recorded as, and the history read back from the ledger."""

import dataclasses
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.budget_caps import (
    BUDGET_CAP_HISTORY,
    CAP_CHANGE_PLANNER,
    BudgetCapHistory,
    CapChange,
    CapChangePlanner,
    CapField,
    CapHistoryEntry,
    CapRequest,
    CycleCaps,
)
from vibey.domain.errors import InvalidBudgetChange, VibeyError
from vibey.domain.interfaces.budget_caps_interface import (
    BudgetCapHistoryInterface,
    CapChangeInterface,
    CapChangePlannerInterface,
    CapHistoryEntryInterface,
    CapRequestInterface,
    CycleCapsInterface,
)
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    UnrecognizedProvenance,
    digest_event,
)
from vibey.domain.phase import Phase, UnrecognizedPhase

PROJECT = UUID("6f1c2a0e-0000-4000-8000-00000000b0d9")
T0 = datetime(2026, 9, 24, 19, 2, tzinfo=UTC)
DOLLARS = CapField.MAX_CYCLE_DOLLARS
TURNS = CapField.MAX_CYCLE_TURNS
PLANNER = CapChangePlanner()


def test_the_shared_instances_and_value_objects_satisfy_their_seams() -> None:
    assert isinstance(CAP_CHANGE_PLANNER, CapChangePlannerInterface)
    assert isinstance(BUDGET_CAP_HISTORY, BudgetCapHistoryInterface)
    assert isinstance(CycleCaps(), CycleCapsInterface)
    assert isinstance(CapChange(DOLLARS, None, 1.0), CapChangeInterface)
    assert isinstance(CapRequest(set_to={}), CapRequestInterface)
    assert isinstance(
        CapHistoryEntry(T0, "adam", "max_cycle_dollars", None, 1.0), CapHistoryEntryInterface
    )
    assert issubclass(InvalidBudgetChange, VibeyError)


def test_the_cap_fields_are_the_config_keys_the_brake_reads() -> None:
    assert [cap.value for cap in CapField] == ["max_cycle_dollars", "max_cycle_turns"]


def test_cycle_caps_names_each_cap_by_its_field() -> None:
    caps = CycleCaps(max_dollars=15.0, max_turns=40)
    assert caps.value_of(DOLLARS) == 15.0
    assert caps.value_of(TURNS) == 40
    assert CycleCaps().value_of(DOLLARS) is None


# -- what a cap is -----------------------------------------------------------------------


@pytest.mark.parametrize(("given_", "expected"), [(15, 15.0), (15.5, 15.5), (0.001, 0.001)])
def test_a_dollar_cap_is_any_finite_number_above_zero(given_: object, expected: float) -> None:
    cap = PLANNER.dollars(given_)
    assert cap == expected
    assert type(cap) is float


@pytest.mark.parametrize(
    "refused",
    [0, 0.0, -1, -0.01, math.nan, math.inf, -math.inf, True, False, "10", None, 10**400],
    ids=["0", "0.0", "-1", "-0.01", "nan", "inf", "-inf", "true", "false", "text", "none", "huge"],
)
def test_anything_else_is_not_a_dollar_cap(refused: object) -> None:
    with pytest.raises(InvalidBudgetChange, match="a dollar cap must be a number above zero"):
        PLANNER.dollars(refused)


@given(st.floats(min_value=0, exclude_min=True, allow_nan=False, allow_infinity=False))
def test_every_positive_finite_amount_is_kept_exactly(amount: float) -> None:
    assert PLANNER.dollars(amount) == amount


@given(st.floats(max_value=0, allow_nan=False))
def test_no_amount_at_or_below_zero_is_a_cap(amount: float) -> None:
    with pytest.raises(InvalidBudgetChange):
        PLANNER.dollars(amount)


@pytest.mark.parametrize("given_", [1, 40, 10**9])
def test_a_turn_cap_is_a_whole_number_above_zero(given_: int) -> None:
    assert PLANNER.turns(given_) == given_


@pytest.mark.parametrize(
    "refused",
    [0, -3, True, 2.5, 3.0, "5", None],
    ids=["0", "-3", "true", "2.5", "3.0", "text", "none"],
)
def test_anything_else_is_not_a_turn_cap(refused: object) -> None:
    with pytest.raises(InvalidBudgetChange, match="a turn cap must be a whole number above zero"):
        PLANNER.turns(refused)


# -- requests ----------------------------------------------------------------------------


def test_setting_checks_every_value_it_is_given() -> None:
    request = PLANNER.setting(max_dollars=15, max_turns=200)
    assert dict(request.set_to) == {DOLLARS: 15.0, TURNS: 200}
    assert request.clear == frozenset()
    assert PLANNER.setting(max_turns=5).set_to == {TURNS: 5}
    assert PLANNER.setting(max_dollars=2.5).set_to == {DOLLARS: 2.5}
    with pytest.raises(InvalidBudgetChange, match="a turn cap"):
        PLANNER.setting(max_dollars=15, max_turns=0)


def test_setting_nothing_is_refused() -> None:
    with pytest.raises(InvalidBudgetChange, match="nothing to set"):
        PLANNER.setting()


def test_clearing_names_the_caps_to_remove_and_refuses_none() -> None:
    assert PLANNER.clearing([DOLLARS]).clear == frozenset({DOLLARS})
    assert PLANNER.clearing([DOLLARS, TURNS, DOLLARS]).clear == frozenset(CapField)
    assert PLANNER.clearing([TURNS]).set_to == {}
    with pytest.raises(InvalidBudgetChange, match="nothing to clear"):
        PLANNER.clearing([])


def test_a_cap_is_never_both_set_and_cleared() -> None:
    with pytest.raises(InvalidBudgetChange, match="max_cycle_dollars cannot be both"):
        CapRequest(set_to={DOLLARS: 1.0}, clear=frozenset({DOLLARS}))


def test_a_request_keeps_its_own_copy_of_the_values() -> None:
    values: dict[CapField, float | int] = {DOLLARS: 1.0}
    request = CapRequest(set_to=values)
    values[TURNS] = 5

    assert TURNS not in request.set_to
    with pytest.raises(TypeError):
        request.set_to[TURNS] = 5  # type: ignore[index]


# -- plans -------------------------------------------------------------------------------


def test_a_plan_changes_only_the_caps_it_names_dollars_first() -> None:
    current = CycleCaps(max_dollars=15.0, max_turns=None)

    changes = PLANNER.plan(current, PLANNER.setting(max_turns=200, max_dollars=20))

    assert changes == (CapChange(DOLLARS, 15.0, 20.0), CapChange(TURNS, None, 200))


def test_setting_a_cap_to_the_value_it_has_changes_nothing() -> None:
    current = CycleCaps(max_dollars=15.0, max_turns=40)

    assert PLANNER.plan(current, PLANNER.setting(max_dollars=15, max_turns=40)) == ()
    assert PLANNER.plan(current, PLANNER.setting(max_dollars=15, max_turns=41)) == (
        CapChange(TURNS, 40, 41),
    )


def test_clearing_removes_a_cap_and_clearing_no_cap_changes_nothing() -> None:
    current = CycleCaps(max_dollars=15.0, max_turns=None)

    assert PLANNER.plan(current, PLANNER.clearing(CapField)) == (CapChange(DOLLARS, 15.0, None),)
    assert PLANNER.plan(CycleCaps(), PLANNER.clearing(CapField)) == ()


@given(
    st.one_of(st.none(), st.floats(0.01, 1e6)),
    st.one_of(st.none(), st.integers(1, 10**6)),
    st.one_of(st.none(), st.floats(0.01, 1e6)),
    st.one_of(st.none(), st.integers(1, 10**6)),
)
def test_a_replayed_plan_changes_nothing(
    dollars: float | None, turns: int | None, new_dollars: float | None, new_turns: int | None
) -> None:
    """Idempotent under replay: applying a plan, then planning the same request against
    the result, changes nothing."""
    if new_dollars is None and new_turns is None:
        return
    current = CycleCaps(max_dollars=dollars, max_turns=turns)
    request = PLANNER.setting(max_dollars=new_dollars, max_turns=new_turns)
    changes = PLANNER.plan(current, request)
    after = dataclasses.replace(
        current,
        **{
            ("max_dollars" if change.field is DOLLARS else "max_turns"): change.new
            for change in changes
        },
    )

    assert PLANNER.plan(after, request) == ()
    for change in changes:
        assert change.old != change.new


def test_a_change_becomes_the_event_payload_with_both_names_for_who_made_it() -> None:
    payload = CapChange(DOLLARS, None, 15.0).payload(by="vibey-vscode", account="adam")

    assert payload == {
        "field": "max_cycle_dollars",
        "old": None,
        "new": 15.0,
        "by": "vibey-vscode",
        "account": "adam",
    }


# -- who ---------------------------------------------------------------------------------


def test_the_actor_is_the_account_unless_the_caller_names_itself() -> None:
    assert PLANNER.actor(None, account="adam") == "adam"
    assert PLANNER.actor("  vibey-vscode ", account="adam") == "vibey-vscode"
    longest = "x" * CapChangePlanner.MAX_ACTOR_LENGTH
    assert PLANNER.actor(longest, account="adam") == longest


@pytest.mark.parametrize(
    ("label", "reason"),
    [
        ("", "cannot be empty"),
        ("   ", "cannot be empty"),
        ("x" * (CapChangePlanner.MAX_ACTOR_LENGTH + 1), "over 200 characters"),
        ("vibey\nChanged by root:", "control or formatting"),
        ("tool\x1b[2Jname", "control or formatting"),
        ("evil‮edoc", "control or formatting"),
        ("zero​width", "control or formatting"),
    ],
    ids=["empty", "blank", "too-long", "newline", "escape", "bidi-override", "zero-width"],
)
def test_a_label_that_cannot_be_recorded_as_one_visible_line_is_refused(
    label: str, reason: str
) -> None:
    with pytest.raises(InvalidBudgetChange, match=reason):
        PLANNER.actor(label, account="adam")


# -- history -----------------------------------------------------------------------------


def _event(
    seq: int,
    payload: dict[str, object],
    *,
    kind: EventKind | UnrecognizedEventKind = EventKind.BUDGET_CAP_CHANGED,
    provenance: Provenance | UnrecognizedProvenance = Provenance.TRUSTED,
    phase: Phase | UnrecognizedPhase = Phase.BUILD,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=PROJECT,
        cycle=1,
        phase=phase,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=PROJECT,
        provenance=provenance,
        produced_at=T0 + timedelta(minutes=seq),
        payload=payload,
        digest=digest_event(payload),
    )


def _change(field: str, old: object, new: object, by: object = "adam") -> dict[str, object]:
    return {"field": field, "old": old, "new": new, "by": by, "account": "adam"}


def test_the_history_is_every_trusted_change_oldest_first() -> None:
    events = [
        _event(3, _change("max_cycle_turns", None, 200, by="vibey-vscode")),
        _event(1, _change("max_cycle_dollars", None, 15.0)),
        _event(2, {"dollars": 1.0, "turns": 1}, kind=EventKind.BUDGET_SPENT),
    ]

    history = BudgetCapHistory().entries(events)

    assert history == (
        CapHistoryEntry(T0 + timedelta(minutes=1), "adam", "max_cycle_dollars", None, 15.0),
        CapHistoryEntry(T0 + timedelta(minutes=3), "vibey-vscode", "max_cycle_turns", None, 200),
    )


@pytest.mark.parametrize(
    "provenance",
    [Provenance.AGENT, Provenance.UNTRUSTED, UnrecognizedProvenance("sealed")],
    ids=["agent", "untrusted", "unrecognized"],
)
def test_a_change_vibey_did_not_write_as_trusted_is_not_history(
    provenance: Provenance | UnrecognizedProvenance,
) -> None:
    forged = _event(1, _change("max_cycle_dollars", 15.0, 1e9), provenance=provenance)

    assert BUDGET_CAP_HISTORY.entries([forged]) == ()


def test_a_kind_that_only_looks_like_a_change_is_not_history() -> None:
    lookalike = _event(
        1, _change("max_cycle_dollars", None, 1.0), kind=UnrecognizedEventKind("budgetcapchanged")
    )

    assert BUDGET_CAP_HISTORY.entries([lookalike]) == ()


def test_the_history_reads_the_record_as_it_was_written() -> None:
    """A newer vibey's cap, a phase this vibey does not know, a label that is not text:
    the record is still a change someone made, shown as stored rather than dropped."""
    events = [
        _event(1, _change("max_cycle_minutes", 30, 45), phase=UnrecognizedPhase("hyperdrive")),
        _event(2, {"old": None, "new": 1.0, "by": 7}),
    ]

    first, second = BUDGET_CAP_HISTORY.entries(events)

    assert (first.field, first.old, first.new, first.by) == ("max_cycle_minutes", 30, 45, "adam")
    assert (second.field, second.by) == ("", None)
