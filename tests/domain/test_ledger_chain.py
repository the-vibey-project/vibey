# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The derived hash chain: every field of every event is inside it, and every
disagreement is reported rather than the first one returned as False."""

import dataclasses
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.engine import EngineId
from vibey.domain.interfaces import (
    ChainFindingInterface,
    ChainLinkInterface,
    ChainVerificationInterface,
    LedgerChainInterface,
)
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    digest_event,
)
from vibey.domain.ledger_chain import (
    CHAIN_SCHEME,
    LEDGER_CHAIN,
    ChainFindingKind,
    LedgerChain,
)
from vibey.domain.phase import Phase

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000001")
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _event(seq: int, *, project_id: UUID = PROJECT, **overrides: object) -> LedgerEvent:
    payload = overrides.pop("payload", {"n": seq})
    fields: dict[str, object] = {
        "event_id": uuid4(),
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "seq": seq,
        "kind": EventKind.TURN_COMPLETED,
        "engine_id": EngineId.CLAUDELOOP,
        "job_id": None,
        "causation_id": None,
        "correlation_id": uuid4(),
        "provenance": Provenance.AGENT,
        "produced_at": T0 + timedelta(seconds=seq),
        "payload": payload,
        "digest": digest_event(payload),  # type: ignore[arg-type]
    }
    fields.update(overrides)
    return LedgerEvent(**fields)  # type: ignore[arg-type]


def _ledger(count: int) -> tuple[LedgerEvent, ...]:
    return tuple(_event(seq) for seq in range(1, count + 1))


def _kinds(result: ChainVerificationInterface) -> list[ChainFindingKind]:
    return [finding.kind for finding in result.findings]


# -- genesis and links ------------------------------------------------------


def test_genesis_is_deterministic_and_belongs_to_one_project() -> None:
    chain = LedgerChain()
    assert chain.genesis(PROJECT) == chain.genesis(PROJECT)
    assert chain.genesis(PROJECT) != chain.genesis(uuid4())


def test_the_scheme_separates_chains() -> None:
    assert LedgerChain().scheme == CHAIN_SCHEME
    other = LedgerChain(scheme="someone-else/v1")
    assert other.scheme == "someone-else/v1"
    assert other.genesis(PROJECT) != LedgerChain().genesis(PROJECT)
    event = _event(1)
    assert other.link("x", event) != LedgerChain().link("x", event)


def test_a_link_commits_to_the_link_before_it() -> None:
    event = _event(1)
    assert LedgerChain().link("a", event) != LedgerChain().link("b", event)


def test_the_same_instant_in_another_zone_is_the_same_link() -> None:
    event = _event(1)
    elsewhere = dataclasses.replace(
        event, produced_at=event.produced_at.astimezone(timezone(timedelta(hours=-7)))
    )
    assert LedgerChain().link("p", event) == LedgerChain().link("p", elsewhere)


def test_a_naive_instant_cannot_be_linked() -> None:
    naive = dataclasses.replace(_event(1), produced_at=datetime(2026, 9, 18, 12, 0))
    with pytest.raises(ValueError, match="naive produced_at"):
        LedgerChain().link("p", naive)


# -- verification -----------------------------------------------------------


def test_an_intact_ledger_verifies_and_its_head_is_the_last_link() -> None:
    events = _ledger(4)
    result = LedgerChain().verify(PROJECT, events)

    assert result.ok
    assert result.project_id == PROJECT
    assert result.start == LedgerChain().genesis(PROJECT)
    assert [link.seq for link in result.links] == [1, 2, 3, 4]
    assert [link.event_id for link in result.links] == [e.event_id for e in events]
    assert result.head == result.links[-1].link

    expected = LedgerChain().genesis(PROJECT)
    for event in events:
        expected = LedgerChain().link(expected, event)
    assert result.head == expected


def test_the_walk_is_in_seq_order_whatever_order_it_is_given() -> None:
    events = _ledger(3)
    forwards = LedgerChain().verify(PROJECT, events)
    backwards = LedgerChain().verify(PROJECT, tuple(reversed(events)))
    assert backwards.ok
    assert backwards.head == forwards.head


def test_no_events_is_no_findings_and_a_head_at_the_start() -> None:
    result = LedgerChain().verify(PROJECT, ())
    assert result.ok
    assert result.links == ()
    assert result.head == result.start == LedgerChain().genesis(PROJECT)


def test_an_anchor_the_walk_never_reaches_is_reported_not_passed() -> None:
    result = LedgerChain().verify(PROJECT, _ledger(2), anchors={9: "0" * 64})
    assert _kinds(result) == [ChainFindingKind.ANCHOR_UNREACHED]
    assert result.findings[0].seq == 9


def test_an_anchor_that_disagrees_is_reported() -> None:
    events = _ledger(3)
    head = LedgerChain().verify(PROJECT, events).head
    result = LedgerChain().verify(PROJECT, events, anchors={2: head, 3: head})
    assert _kinds(result) == [ChainFindingKind.ANCHOR_MISMATCH]
    assert result.findings[0].seq == 2


def test_a_window_without_a_starting_link_is_reported() -> None:
    result = LedgerChain().verify(PROJECT, _ledger(5)[2:])
    assert _kinds(result) == [ChainFindingKind.UNANCHORED_WINDOW]
    assert result.findings[0].seq == 3


def test_a_window_from_its_trusted_starting_link_matches_the_full_walk() -> None:
    """The fold vibey#114's chunks rest on: a chunk verifies alone, from the
    link before it to the link at its end, and agrees with the whole ledger."""
    events = _ledger(6)
    full = LedgerChain().verify(PROJECT, events)
    before = full.links[2].link  # the link at seq 3
    chunk = LedgerChain().verify(PROJECT, events[3:], prev_link=before, anchors={6: full.head})
    assert chunk.ok
    assert chunk.start == before
    assert chunk.head == full.head
    assert chunk.links == full.links[3:]


def test_a_starting_link_before_seq_one_must_be_genesis() -> None:
    events = _ledger(2)
    genesis = LedgerChain().genesis(PROJECT)
    assert LedgerChain().verify(PROJECT, events, prev_link=genesis).ok

    wrong = LedgerChain().verify(PROJECT, events, prev_link="f" * 64)
    assert _kinds(wrong) == [ChainFindingKind.ANCHOR_MISMATCH]
    assert wrong.findings[0].seq == 0


def test_a_repeated_seq_is_reported() -> None:
    first, second = _ledger(2)
    again = dataclasses.replace(second, event_id=uuid4())
    result = LedgerChain().verify(PROJECT, (first, second, again))
    assert _kinds(result) == [ChainFindingKind.SEQ_DUPLICATE]
    assert str(again.event_id) in result.findings[0].detail


def test_a_gap_says_how_many_events_are_missing() -> None:
    events = _ledger(5)
    result = LedgerChain().verify(PROJECT, (events[0], events[4]))
    assert _kinds(result) == [ChainFindingKind.SEQ_GAP]
    assert result.findings[0].seq == 5
    assert "3 event(s) missing" in result.findings[0].detail


def test_an_event_from_another_project_is_reported() -> None:
    stranger = uuid4()
    events = (_event(1), _event(2, project_id=stranger))
    result = LedgerChain().verify(PROJECT, events)
    assert _kinds(result) == [ChainFindingKind.FOREIGN_PROJECT]
    assert str(stranger) in result.findings[0].detail


def test_a_payload_that_no_longer_produces_its_digest_is_reported() -> None:
    event = _event(1, payload={"verdict": "pass"})
    tampered = dataclasses.replace(event, payload={"verdict": "fail"})
    result = LedgerChain().verify(PROJECT, (tampered,))
    assert _kinds(result) == [ChainFindingKind.DIGEST_MISMATCH]
    assert digest_event({"verdict": "fail"}) in result.findings[0].detail


def test_every_finding_is_reported_not_just_the_first() -> None:
    events = _ledger(4)
    tampered = dataclasses.replace(events[1], payload={"n": "changed"})
    stranger = dataclasses.replace(events[3], project_id=uuid4())
    result = LedgerChain().verify(PROJECT, (events[0], tampered, stranger), anchors={3: "0" * 64})
    assert _kinds(result) == [
        ChainFindingKind.DIGEST_MISMATCH,
        ChainFindingKind.FOREIGN_PROJECT,
        ChainFindingKind.SEQ_GAP,
        ChainFindingKind.ANCHOR_UNREACHED,
    ]


def test_the_classes_satisfy_their_declared_seams() -> None:
    result = LEDGER_CHAIN.verify(PROJECT, _ledger(2), anchors={7: "0" * 64})
    assert isinstance(LEDGER_CHAIN, LedgerChainInterface)
    assert isinstance(result, ChainVerificationInterface)
    assert isinstance(result.links[0], ChainLinkInterface)
    assert isinstance(result.findings[0], ChainFindingInterface)


# -- properties -------------------------------------------------------------

_ENGINES: list[EngineId | None] = [None, *EngineId]
_PAYLOAD_VALUES = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=8))


@st.composite
def ledgers(draw: st.DrawFn) -> tuple[UUID, tuple[LedgerEvent, ...]]:
    project_id = draw(st.uuids())
    events = []
    for seq in range(1, draw(st.integers(min_value=1, max_value=6)) + 1):
        payload = draw(st.dictionaries(st.text(max_size=5), _PAYLOAD_VALUES, max_size=3))
        events.append(
            LedgerEvent(
                event_id=draw(st.uuids()),
                project_id=project_id,
                cycle=draw(st.integers(min_value=1, max_value=9)),
                phase=draw(st.sampled_from(list(Phase))),
                seq=seq,
                kind=draw(st.sampled_from(list(EventKind))),
                engine_id=draw(st.sampled_from(_ENGINES)),
                job_id=draw(st.none() | st.uuids()),
                causation_id=draw(st.none() | st.uuids()),
                correlation_id=draw(st.uuids()),
                provenance=draw(st.sampled_from(list(Provenance))),
                produced_at=T0 + timedelta(microseconds=draw(st.integers(0, 10**12))),
                payload=payload,
                digest=digest_event(payload),
            )
        )
    return project_id, tuple(events)


def _other(data: st.DataObject, values: Sequence[object], current: object) -> object:
    return data.draw(st.sampled_from([v for v in values if v != current]))


def _tamper(event: LedgerEvent, field: str, data: st.DataObject) -> LedgerEvent:
    """`event` with `field` set to a value it does not have. Every field of
    `LedgerEvent` must be handled: a field added later fails here until someone
    decides whether the chain covers it."""
    current = getattr(event, field)
    new: object
    if field in {"event_id", "project_id", "correlation_id"}:
        new = data.draw(st.uuids().filter(lambda value: value != current))
    elif field in {"job_id", "causation_id"}:
        new = data.draw((st.none() | st.uuids()).filter(lambda value: value != current))
    elif field in {"seq", "cycle"}:
        new = current + data.draw(st.integers(min_value=1, max_value=5))
    elif field == "phase":
        new = _other(data, list(Phase), current)
    elif field == "kind":
        new = _other(data, list(EventKind), current)
    elif field == "engine_id":
        new = _other(data, list(_ENGINES), current)
    elif field == "provenance":
        new = _other(data, list(Provenance), current)
    elif field == "produced_at":
        new = current + timedelta(microseconds=data.draw(st.integers(1, 10**9)))
    elif field == "payload":
        # Keys are drawn at most five characters long, so this one is new.
        new = {**current, "tampered": True}
    elif field == "digest":
        new = "0" * 64 if current != "0" * 64 else "1" * 64
    else:
        raise AssertionError(f"LedgerEvent.{field} is not covered by the tamper test")
    return dataclasses.replace(event, **{field: new})


@given(ledger=ledgers())
def test_an_untouched_ledger_always_verifies_against_its_own_head(
    ledger: tuple[UUID, tuple[LedgerEvent, ...]],
) -> None:
    project_id, events = ledger
    head = LedgerChain().verify(project_id, events).head
    assert LedgerChain().verify(project_id, events, anchors={len(events): head}).ok


@given(ledger=ledgers(), data=st.data())
def test_changing_any_field_of_any_event_breaks_the_chain(
    ledger: tuple[UUID, tuple[LedgerEvent, ...]], data: st.DataObject
) -> None:
    project_id, events = ledger
    head = LedgerChain().verify(project_id, events).head
    index = data.draw(st.integers(min_value=0, max_value=len(events) - 1))
    field = data.draw(st.sampled_from([f.name for f in dataclasses.fields(LedgerEvent)]))

    tampered = list(events)
    tampered[index] = _tamper(events[index], field, data)
    result = LedgerChain().verify(project_id, tampered, anchors={len(events): head})

    assert not result.ok, f"changing {field} of seq {index + 1} went unnoticed"


@given(ledger=ledgers(), data=st.data())
def test_any_split_verifies_as_two_chunks_that_agree_with_the_whole(
    ledger: tuple[UUID, tuple[LedgerEvent, ...]], data: st.DataObject
) -> None:
    project_id, events = ledger
    full = LedgerChain().verify(project_id, events)
    cut = data.draw(st.integers(min_value=1, max_value=len(events)))

    older = LedgerChain().verify(project_id, events[:cut])
    newer = LedgerChain().verify(project_id, events[cut:], prev_link=older.head)

    assert older.ok
    assert newer.ok
    assert newer.head == full.head


# -- a mixed-version fleet (vibey#275) ---------------------------------------


class _NewerEventKind(StrEnum):
    """Stands in for a newer vibey's `EventKind`, which has a member this one lacks."""

    TRANSCRIPT_RECORDED = "TranscriptRecordedV2"


def test_an_older_vibey_computes_the_same_links_over_a_newer_kind() -> None:
    """The chain folds `kind.value`, and an unrecognized kind's value is the
    stored text verbatim -- so tamper evidence agrees across a rolling upgrade."""
    ledger = _ledger(3)
    as_newer_reads = [
        dataclasses.replace(e, kind=_NewerEventKind.TRANSCRIPT_RECORDED) if e.seq == 2 else e
        for e in ledger
    ]
    as_older_reads = [
        dataclasses.replace(e, kind=UnrecognizedEventKind("TranscriptRecordedV2"))
        if e.seq == 2
        else e
        for e in ledger
    ]
    newer = LedgerChain().verify(PROJECT, as_newer_reads)
    older = LedgerChain().verify(PROJECT, as_older_reads)
    assert older.ok
    assert older.head == newer.head
    assert [link.link for link in older.links] == [link.link for link in newer.links]
