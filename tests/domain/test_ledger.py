# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import dataclasses
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.interfaces import EventKindParserInterface, UnrecognizedEventKindInterface
from vibey.domain.ledger import (
    CLOSABLE,
    CLOSES,
    EVENT_KIND_PARSER,
    EventKind,
    EventKindParser,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    canonical_bytes,
    digest_event,
    digest_range,
    open_items,
)
from vibey.domain.phase import Phase

PROJECT_ID = uuid4()
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _event(
    seq: int,
    kind: EventKind,
    payload: dict[str, object],
    *,
    correlation_id: UUID | None = None,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=PROJECT_ID,
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=correlation_id or uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=NOW,
        payload=payload,
        digest=digest_event(payload),
    )


def test_canonical_bytes_is_order_independent_over_keys() -> None:
    a = canonical_bytes({"b": 1, "a": 2})
    b = canonical_bytes({"a": 2, "b": 1})
    assert a == b


def test_digest_event_is_deterministic() -> None:
    payload = {"question_id": "q1", "text": "why?"}
    assert digest_event(payload) == digest_event(payload)


def test_digest_event_changes_with_payload() -> None:
    assert digest_event({"a": 1}) != digest_event({"a": 2})


def test_digest_range_is_order_insensitive_to_input_ordering_but_seq_sensitive() -> None:
    e1 = _event(1, EventKind.TURN_REQUESTED, {"prompt_digest": "a"})
    e2 = _event(2, EventKind.TURN_COMPLETED, {"output_digest": "b"})

    assert digest_range([e1, e2]) == digest_range([e2, e1])


def test_digest_range_differs_when_a_seq_changes() -> None:
    e1 = _event(1, EventKind.TURN_REQUESTED, {"prompt_digest": "a"})
    e2 = _event(2, EventKind.TURN_REQUESTED, {"prompt_digest": "a"})
    assert digest_range([e1]) != digest_range([e2])


def test_open_items_rejects_non_closable_kind() -> None:
    with pytest.raises(ValueError, match="not a closable"):
        open_items([], EventKind.TURN_REQUESTED)


def test_open_items_question_open_until_answered() -> None:
    asked = _event(
        1, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "?", "blocking": True}
    )
    assert open_items([asked], EventKind.QUESTION_ASKED) == ("q1",)

    answered = _event(2, EventKind.ANSWER_GIVEN, {"question_id": "q1", "text": "yes"})
    assert open_items([asked, answered], EventKind.QUESTION_ASKED) == ()


def test_open_items_finding_open_until_resolved() -> None:
    raised = _event(
        1, EventKind.FINDING_RAISED, {"finding_id": "f1", "severity": "high", "text": "x"}
    )
    assert open_items([raised], EventKind.FINDING_RAISED) == ("f1",)

    resolved = _event(2, EventKind.FINDING_RESOLVED, {"finding_id": "f1", "resolution": "fixed"})
    assert open_items([raised, resolved], EventKind.FINDING_RAISED) == ()


def test_open_items_decision_closed_by_supersession() -> None:
    d1 = _event(1, EventKind.DECISION_RECORDED, {"decision_id": "d1", "title": "x", "choice": "a"})
    d2 = _event(
        2,
        EventKind.DECISION_RECORDED,
        {"decision_id": "d2", "title": "y", "choice": "b", "supersedes": "d1"},
    )

    assert open_items([d1, d2], EventKind.DECISION_RECORDED) == ("d2",)


def test_open_items_assumption_stays_open_without_a_closing_kind() -> None:
    a1 = _event(
        1, EventKind.ASSUMPTION_STATED, {"assumption_id": "a1", "text": "x", "confidence": "high"}
    )
    assert open_items([a1], EventKind.ASSUMPTION_STATED) == ("a1",)


def test_open_items_preserves_open_order_by_seq() -> None:
    q1 = _event(1, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "?", "blocking": False})
    q2 = _event(2, EventKind.QUESTION_ASKED, {"question_id": "q2", "text": "?", "blocking": False})
    assert open_items([q2, q1], EventKind.QUESTION_ASKED) == ("q1", "q2")


def test_closable_and_closes_tables_are_consistent() -> None:
    for closed_kind in CLOSES.values():
        assert closed_kind in CLOSABLE


_event_kind_strategy = st.sampled_from(list(EventKind))


@given(seq=st.integers(1, 10_000), payload_value=st.text(max_size=20))
def test_digest_event_never_raises(seq: int, payload_value: str) -> None:
    digest_event({"seq": seq, "v": payload_value})


# -- forward-compatible readers (vibey#275) ----------------------------------

_KNOWN_VALUES = frozenset(kind.value for kind in EventKind)


@pytest.mark.parametrize("kind", list(EventKind))
def test_every_known_kind_parses_to_its_member(kind: EventKind) -> None:
    assert EventKindParser().parse(kind.value) is kind


def test_a_kind_this_vibey_does_not_know_parses_to_its_exact_text() -> None:
    parsed = EVENT_KIND_PARSER.parse("FutureKindX")
    assert parsed == UnrecognizedEventKind("FutureKindX")
    assert parsed.value == "FutureKindX"
    assert str(parsed) == "FutureKindX"


def test_a_case_variant_of_a_known_kind_is_not_that_kind() -> None:
    """The column holds a member's value verbatim, so matching is exact: a
    reader never reinterprets a row as a kind it was not written as."""
    parsed = EVENT_KIND_PARSER.parse("turncompleted")
    assert isinstance(parsed, UnrecognizedEventKind)
    assert parsed is not EventKind.TURN_COMPLETED


@pytest.mark.parametrize("kind", list(EventKind))
def test_an_unrecognized_kind_can_never_name_a_known_one(kind: EventKind) -> None:
    with pytest.raises(ValueError, match="is a known event kind"):
        UnrecognizedEventKind(kind.value)


def test_an_unrecognized_kind_is_a_value() -> None:
    a, b = UnrecognizedEventKind("FutureKindX"), UnrecognizedEventKind("FutureKindX")
    assert a == b
    assert {a, b} == {a}
    assert a != UnrecognizedEventKind("FutureKindY")
    for kind in EventKind:
        assert a != kind
        assert kind != a


def test_the_parser_and_the_value_satisfy_their_declared_seams() -> None:
    assert isinstance(EVENT_KIND_PARSER, EventKindParserInterface)
    assert isinstance(UnrecognizedEventKind("FutureKindX"), UnrecognizedEventKindInterface)


def test_digest_range_does_not_fold_the_kind() -> None:
    """R6 is unchanged: the same rows fold to the same digest whether the
    reader knows the kind (a newer vibey) or does not (this one)."""
    payloads = [{"seed_digest": "d1"}, {"transcript_ref": "t1"}, {"dollars": 0.5}]
    as_newer_reads = [_event(i, EventKind.TURN_COMPLETED, p) for i, p in enumerate(payloads, 1)]
    as_older_reads = [
        dataclasses.replace(e, kind=UnrecognizedEventKind("TranscriptRecordedV2"))
        if e.seq == 2
        else e
        for e in as_newer_reads
    ]
    assert digest_range(as_older_reads) == digest_range(as_newer_reads)


@given(
    raw=st.text().filter(lambda value: value not in _KNOWN_VALUES),
    payload_value=st.text(max_size=20),
)
def test_an_unrecognized_kind_never_changes_digest_range(raw: str, payload_value: str) -> None:
    known = [
        _event(1, EventKind.SESSION_SEEDED, {"seed_digest": "d1"}),
        _event(2, EventKind.TURN_COMPLETED, {"v": payload_value}),
    ]
    unknown = [known[0], dataclasses.replace(known[1], kind=EVENT_KIND_PARSER.parse(raw))]
    assert isinstance(unknown[1].kind, UnrecognizedEventKind)
    assert digest_range(unknown) == digest_range(known)


def test_open_items_ignores_an_unrecognized_kind_carrying_an_id_field() -> None:
    """Even a payload shaped like a closing event closes nothing: only a
    kind this vibey knows can open or close an item."""
    q1 = _event(1, EventKind.QUESTION_ASKED, {"question_id": "q1", "text": "?", "blocking": False})
    lookalike = _event(
        2, EventKind.ANSWER_GIVEN, {"question_id": "q1", "text": "answered by a newer kind"}
    )
    lookalike = dataclasses.replace(lookalike, kind=UnrecognizedEventKind("QuestionWithdrawn"))
    assert open_items([q1, lookalike], EventKind.QUESTION_ASKED) == ("q1",)
