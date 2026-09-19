# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey#275: a kind this vibey does not know never crashes a domain reader, and
changes nothing any of them concludes -- except the range digest, which it joins
exactly as a newer vibey's reader would.

The event under test carries a payload shaped to fool a careless reader: ids a
closable kind would carry, the dollars and turns the budget sums, a verdict's
`complete` and `remaining_work`. A reader that matched on payload shape rather
than on a known kind would change its answer, and this property would catch it.
"""

import dataclasses
from datetime import UTC, datetime
from uuid import UUID, uuid4

from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.briefing import build_deterministic_brief
from vibey.domain.handoff import BudgetSnapshot, LedgerRef
from vibey.domain.ledger import (
    CLOSABLE,
    EVENT_KIND_PARSER,
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    digest_event,
    digest_range,
    open_items,
)
from vibey.domain.ledger_chain import LedgerChain
from vibey.domain.noloss import verify
from vibey.domain.phase import Phase
from vibey.domain.projections import (
    answer_why_question,
    build_cost_report,
    build_decision_log,
    build_deltas,
    build_open_items,
    build_work_ledger,
)

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000275")
NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
KNOWN_VALUES = frozenset(kind.value for kind in EventKind)

_raw_kinds = st.text().filter(lambda value: value not in KNOWN_VALUES)
_lookalike_payloads = st.dictionaries(
    keys=st.sampled_from(
        [
            "question_id",
            "decision_id",
            "assumption_id",
            "finding_id",
            "supersedes",
            "dollars",
            "turns",
            "cost_usd",
            "complete",
            "remaining_work",
            "text",
            "severity",
            "referenced_by_open_item",
        ]
    ),
    values=st.one_of(
        st.text(max_size=10),
        st.integers(-5, 5),
        st.floats(allow_nan=False, allow_infinity=False, width=32),
        st.booleans(),
        st.lists(st.text(max_size=5), max_size=3),
    ),
)


def _event(seq: int, kind: EventKind, payload: dict[str, object]) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=PROJECT,
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=uuid4(),
        correlation_id=PROJECT,
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload=payload,
        digest=digest_event(payload),
    )


def _baseline() -> list[LedgerEvent]:
    return [
        _event(1, EventKind.SESSION_SEEDED, {"seed_digest": "d1"}),
        _event(2, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "cap retries?"}),
        _event(3, EventKind.DECISION_RECORDED, {"decision_id": "d1", "title": "outbox"}),
        _event(4, EventKind.ASSUMPTION_STATED, {"assumption_id": "a1", "text": "idempotent"}),
        _event(5, EventKind.FINDING_RAISED, {"finding_id": "f1", "text": "flaky test"}),
        _event(6, EventKind.BUDGET_SPENT, {"dollars": 0.25, "turns": 3}),
        _event(7, EventKind.VERDICT_RENDERED, {"complete": False, "remaining_work": ["relay"]}),
    ]


def _ref_for(events: list[LedgerEvent]) -> LedgerRef:
    return LedgerRef(
        uri="handoff/ledger.jsonl",
        from_seq=min(e.seq for e in events),
        to_seq=max(e.seq for e in events),
        event_count=len(events),
        digest=digest_range(events),
    )


BUDGET = BudgetSnapshot(turns_spent=3, dollars_spent=0.25, max_turns=None, max_dollars=None)


@given(raw=_raw_kinds, payload=_lookalike_payloads, at=st.integers(0, 7))
def test_no_domain_reader_is_moved_by_an_unrecognized_kind(
    raw: str, payload: dict[str, object], at: int
) -> None:
    kind = EVENT_KIND_PARSER.parse(raw)
    assert isinstance(kind, UnrecognizedEventKind)
    assert kind.value == raw

    baseline = _baseline()
    stranger = dataclasses.replace(
        baseline[0], event_id=uuid4(), kind=kind, payload=payload, digest=digest_event(payload)
    )
    # Insert it anywhere in the range and renumber, so seq stays gapless.
    events = baseline[:at] + [stranger] + baseline[at:]
    events = [dataclasses.replace(e, seq=i) for i, e in enumerate(events, 1)]
    known_only = [e for e in events if isinstance(e.kind, EventKind)]

    # Projections: the same answer with the stranger as without it.
    for closable in CLOSABLE:
        assert open_items(events, closable) == open_items(known_only, closable)
    assert build_open_items(events) == build_open_items(known_only)
    assert build_decision_log(events) == build_decision_log(known_only)
    assert build_cost_report(events) == build_cost_report(known_only)
    assert build_work_ledger(events) == build_work_ledger(known_only)
    assert build_deltas(events) == build_deltas(known_only)
    assert answer_why_question(events, "why outbox?") == answer_why_question(
        known_only, "why outbox?"
    )

    # The brief ignores it; the gate passes over the whole range, stranger and all.
    brief = build_deterministic_brief(events)
    assert brief == build_deterministic_brief(known_only)
    result = verify(ledger=events, brief=brief, ref=_ref_for(events), budget=BUDGET)
    assert result.ok, result.violations

    # R6 folds it -- the stranger is in the range the next engine receives.
    assert digest_range(events) != digest_range(known_only)

    # The hash chain walks it like any other row.
    assert LedgerChain().verify(PROJECT, events).ok
