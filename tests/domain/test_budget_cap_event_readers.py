# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every reader of the ledger knows `BudgetCapChanged` -- an event kind a reader did not
know would be a silent failure.

The event under test carries a payload shaped to fool a careless reader: the numbers a
cap change holds sit beside the keys the brake sums, a closable item's id, a verdict's
remaining work. Each reader is asked the same question with and without the event: a
reader that matched on payload shape rather than on its known kinds would answer
differently, and this module would fail.

- the publication policy classifies every kind exactly once, and withholds this one
  from the public shard and from the operator's billing shard;
- the projections, the deterministic brief and the no-loss gate ignore it, and the gate
  folds it into the range digest (R6) like every other event;
- the budget brake's spend rule and the phase timeline count nothing for it;
- the record codec, the kind parser and the `--kind` resolver read it as the member.
"""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from vibey.domain.briefing import build_deterministic_brief
from vibey.domain.handoff import BudgetSnapshot, LedgerRef
from vibey.domain.ledger import (
    CLOSABLE,
    EVENT_KIND_PARSER,
    EventKind,
    LedgerEvent,
    Provenance,
    digest_event,
    digest_range,
    open_items,
)
from vibey.domain.ledger_query import EVENT_KINDS
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.domain.noloss import verify
from vibey.domain.phase import Phase
from vibey.domain.phase_timing import LEDGER_SPEND_RULE, PHASE_TIMING
from vibey.domain.projections import (
    answer_why_question,
    build_cost_report,
    build_decision_log,
    build_deltas,
    build_open_items,
    build_work_ledger,
)
from vibey.domain.publication_policy import (
    BILLING_POLICY,
    DEFAULT_ALLOWLIST,
    DEFAULT_POLICY,
    ENGINE_CHATTER,
    WITHHELD_KINDS,
    WithheldReason,
)

PROJECT = UUID("6f1c2a0e-0000-4000-8000-00000000cab5")
T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)

# A cap change's own fields, and beside them every key a careless reader might sum or
# close on. Only the first five are what `vibey budget` writes.
LOOKALIKE: dict[str, object] = {
    "field": "max_cycle_dollars",
    "old": 5.0,
    "new": 25.0,
    "by": "adam",
    "account": "adam",
    "dollars": 25.0,
    "turns": 40,
    "cost_usd": 25.0,
    "question_id": "q9",
    "decision_id": "d9",
    "finding_id": "f9",
    "complete": True,
    "remaining_work": ["nothing"],
    "referenced_by_open_item": True,
    "artifact_id": "a9",
}


def _event(
    seq: int, kind: EventKind, payload: dict[str, object], phase: Phase = Phase.BUILD
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
        causation_id=uuid4(),
        correlation_id=PROJECT,
        provenance=Provenance.TRUSTED,
        produced_at=T0 + timedelta(minutes=seq),
        payload=payload,
        digest=digest_event(payload),
    )


def _baseline() -> list[LedgerEvent]:
    return [
        _event(
            1,
            EventKind.PHASE_TRANSITIONED,
            {"from": "design", "to": "build", "cycle": 1, "guard": None},
        ),
        _event(2, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "cap retries?"}),
        _event(3, EventKind.DECISION_RECORDED, {"decision_id": "d1", "title": "outbox"}),
        _event(4, EventKind.ASSUMPTION_STATED, {"assumption_id": "a1", "text": "idempotent"}),
        _event(5, EventKind.FINDING_RAISED, {"finding_id": "f1", "text": "flaky test"}),
        _event(6, EventKind.BUDGET_SPENT, {"dollars": 0.25, "turns": 3}),
        _event(7, EventKind.TURN_COMPLETED, {"cost_usd": 1.5}),
        _event(8, EventKind.VERDICT_RENDERED, {"complete": False, "remaining_work": ["relay"]}),
    ]


def _with_cap_change(at: int) -> tuple[list[LedgerEvent], list[LedgerEvent]]:
    """The baseline with a cap change inserted at `at`, renumbered so seq stays
    gapless, and the same range without it."""
    baseline = _baseline()
    change = _event(0, EventKind.BUDGET_CAP_CHANGED, dict(LOOKALIKE))
    events = baseline[:at] + [change] + baseline[at:]
    events = [dataclasses.replace(e, seq=i) for i, e in enumerate(events, 1)]
    without = [e for e in events if e.kind is not EventKind.BUDGET_CAP_CHANGED]
    return events, without


# -- the publication policy ---------------------------------------------------------------


def test_every_kind_is_published_withheld_as_chatter_or_withheld_on_purpose_exactly_once() -> None:
    allowed, chatter, withheld = set(DEFAULT_ALLOWLIST), set(ENGINE_CHATTER), set(WITHHELD_KINDS)

    assert allowed | chatter | withheld == set(EventKind), "a kind nobody classified"
    assert not allowed & chatter and not allowed & withheld and not chatter & withheld


def test_a_cap_change_is_withheld_whole_from_the_public_shard() -> None:
    """The operator's caps, and the account that set them, are money and a name: the
    public shard carries neither, as it carries no `BudgetSpent`."""
    event = _event(1, EventKind.BUDGET_CAP_CHANGED, dict(LOOKALIKE))

    decision = DEFAULT_POLICY.decide(event)
    outcome = DEFAULT_POLICY.apply([event])

    assert decision.record is None
    assert decision.withheld is WithheldReason.KIND_NOT_ALLOWLISTED
    assert outcome.records == ()
    assert outcome.withheld[WithheldReason.KIND_NOT_ALLOWLISTED] == 1
    assert EventKind.BUDGET_CAP_CHANGED in WITHHELD_KINDS


def test_a_cap_change_is_not_spend_so_the_billing_shard_withholds_it_too() -> None:
    event = _event(1, EventKind.BUDGET_CAP_CHANGED, dict(LOOKALIKE))

    assert BILLING_POLICY.decide(event).withheld is WithheldReason.KIND_NOT_ALLOWLISTED


# -- projections, the brief and the no-loss gate -------------------------------------------


@pytest.mark.parametrize("at", range(9))
def test_no_projection_is_moved_by_a_cap_change(at: int) -> None:
    events, without = _with_cap_change(at)

    for closable in CLOSABLE:
        assert open_items(events, closable) == open_items(without, closable)
    assert build_open_items(events) == build_open_items(without)
    assert build_decision_log(events) == build_decision_log(without)
    assert build_cost_report(events) == build_cost_report(without)
    assert build_work_ledger(events) == build_work_ledger(without)
    assert build_deltas(events) == build_deltas(without)
    assert answer_why_question(events, "why outbox?") == answer_why_question(without, "why outbox?")


@pytest.mark.parametrize("at", range(9))
def test_the_gate_passes_a_range_holding_a_cap_change_and_folds_it_into_the_digest(
    at: int,
) -> None:
    events, without = _with_cap_change(at)
    brief = build_deterministic_brief(events)
    ref = LedgerRef(
        uri="handoff/ledger.jsonl",
        from_seq=1,
        to_seq=len(events),
        event_count=len(events),
        digest=digest_range(events),
    )
    # R8 sums the BudgetSpent events and nothing else: the cap change's numbers are not
    # spend, whatever its payload says.
    budget = BudgetSnapshot(turns_spent=3, dollars_spent=0.25, max_turns=None, max_dollars=None)

    result = verify(ledger=events, brief=brief, ref=ref, budget=budget)

    assert result.ok, result.violations
    assert brief == build_deterministic_brief(without)
    assert digest_range(events) != digest_range(without)


# -- the brake and the phase timeline -----------------------------------------------------


def test_the_brake_counts_nothing_for_a_cap_change() -> None:
    event = _event(1, EventKind.BUDGET_CAP_CHANGED, dict(LOOKALIKE))

    assert LEDGER_SPEND_RULE.spend_of(event) is None
    assert LEDGER_SPEND_RULE.spend_of_payload(EventKind.BUDGET_CAP_CHANGED.value, LOOKALIKE) is None


@pytest.mark.parametrize("at", range(1, 9))
def test_the_phase_timeline_is_the_same_with_a_cap_change_in_it(at: int) -> None:
    """From the first transition on. A range whose first event is not a transition opens
    an unobserved visit at that event, whatever its kind -- a cap change included."""
    events, without = _with_cap_change(at)

    assert PHASE_TIMING.project(events) == PHASE_TIMING.project(without)


# -- reading it back ----------------------------------------------------------------------


def test_the_record_codec_the_kind_parser_and_the_kind_filter_read_it_as_the_member() -> None:
    event = _event(1, EventKind.BUDGET_CAP_CHANGED, dict(LOOKALIKE))

    assert LEDGER_RECORDS.from_fields(LEDGER_RECORDS.to_fields(event)) == event
    assert EVENT_KIND_PARSER.parse("BudgetCapChanged") is EventKind.BUDGET_CAP_CHANGED
    for label in (
        "BudgetCapChanged",
        "budgetcapchanged",
        "BUDGET_CAP_CHANGED",
        " budget_cap_changed ",
    ):
        assert EVENT_KINDS.resolve(label) is EventKind.BUDGET_CAP_CHANGED
