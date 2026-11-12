# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger's row mapper and `to_drafts`, as round-trip properties, with no database.

`EventRowMapper.to_event` reads an `event` row; a dict with the same columns stands in
for the row, as the existing forward-compatibility property does. `to_drafts` hands
persisted events back as drafts, and appending those drafts to the in-memory ledger (held
to PostgreSQL's behaviour by tests/contracts) must write the events down again.

Nothing here reaches PostgreSQL, so the payload floats are unrestricted. A property that
did would have to keep floats of magnitude 1e16 and up, and -0.0, out of its payloads,
because jsonb rewrites them on read-back (vibey#1883).
"""

import asyncio
import json
from dataclasses import replace
from datetime import UTC
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tests.fakes.ledger_repository import InMemoryLedgerRepository
from tests.ledger_strategies import ledger_events
from vibey.domain.engine import UnrecognizedEngineId
from vibey.domain.ledger import (
    LedgerEvent,
    UnrecognizedEventKind,
    UnrecognizedProvenance,
    digest_event,
)
from vibey.domain.phase import UnrecognizedPhase
from vibey.infrastructure.db.ledger_repository import EVENT_ROWS, to_drafts

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000001883")


def _row(event: LedgerEvent) -> dict[str, object]:
    """`event` as asyncpg hands its row over: columns by name, the payload as JSON text."""
    return {
        "event_id": event.event_id,
        "project_id": event.project_id,
        "cycle": event.cycle,
        "phase": event.phase.value,
        "seq": event.seq,
        "kind": event.kind.value,
        "engine_id": event.engine_id.value if event.engine_id is not None else None,
        "job_id": event.job_id,
        "causation_id": event.causation_id,
        "correlation_id": event.correlation_id,
        "provenance": event.provenance.value,
        "produced_at": event.produced_at,
        "payload": json.dumps(event.payload),
        "digest": event.digest,
    }


@st.composite
def _ledgers(draw: st.DrawFn, *, unknown_values: bool = False) -> tuple[LedgerEvent, ...]:
    """One project's events, seq 1..n with no gap, as an append-only ledger holds them."""
    count = draw(st.integers(1, 5))
    return tuple(
        draw(
            ledger_events(
                project_id=PROJECT,
                seq=seq,
                payloads=st.dictionaries(
                    st.text(max_size=4),
                    st.integers()
                    | st.text(max_size=6)
                    | st.floats(allow_nan=False, allow_infinity=False),
                    max_size=3,
                ),
                unknown_values=unknown_values,
            )
        )
        for seq in range(1, count + 1)
    )


def _append_all(events: tuple[LedgerEvent, ...]) -> tuple[LedgerEvent, ...]:
    async def run() -> tuple[LedgerEvent, ...]:
        ledger = InMemoryLedgerRepository(projects=[PROJECT])
        for draft in to_drafts(events):
            await ledger.append(draft)
        return await ledger.all_for_project(PROJECT)

    return asyncio.run(run())


@given(event=ledger_events(unknown_values=True))
def test_a_row_maps_to_the_event_it_was_written_from(event: LedgerEvent) -> None:
    mapped = EVENT_ROWS.to_event(_row(event))  # type: ignore[arg-type]
    assert mapped == event
    assert type(mapped.phase) is type(event.phase)
    assert type(mapped.kind) is type(event.kind)
    assert type(mapped.engine_id) is type(event.engine_id)
    assert type(mapped.provenance) is type(event.provenance)


@settings(max_examples=40)
@given(events=_ledgers())
def test_appending_the_drafts_of_a_ledger_writes_the_ledger_again(
    events: tuple[LedgerEvent, ...],
) -> None:
    """Everything but the event ids, which the ledger mints, and the instants, which come
    back in UTC, is what was written; the digests are recomputed, and agree."""
    again = _append_all(events)
    assert [replace(e, event_id=UUID(int=0)) for e in again] == [
        replace(
            e,
            event_id=UUID(int=0),
            produced_at=e.produced_at.astimezone(UTC),
            payload=json.loads(json.dumps(e.payload)),
        )
        for e in events
    ]
    assert all(e.digest == digest_event(e.payload) for e in again)


@settings(max_examples=40)
@given(events=_ledgers())
def test_a_draft_of_an_event_carries_no_state_the_event_lacks(
    events: tuple[LedgerEvent, ...],
) -> None:
    drafts = to_drafts(events)
    assert len(drafts) == len(events)
    for draft, event in zip(drafts, events, strict=True):
        assert draft.payload == event.payload
        assert draft.payload is not event.payload
        assert (draft.project_id, draft.cycle, draft.job_id, draft.digest) == (
            event.project_id,
            event.cycle,
            event.job_id,
            event.digest,
        )


def _is_unrecognized(event: LedgerEvent) -> bool:
    return (
        isinstance(event.kind, UnrecognizedEventKind)
        or isinstance(event.phase, UnrecognizedPhase)
        or isinstance(event.provenance, UnrecognizedProvenance)
        or isinstance(event.engine_id, UnrecognizedEngineId)
    )


@settings(max_examples=40)
@given(events=_ledgers(unknown_values=True))
def test_a_value_this_vibey_does_not_know_is_read_but_never_written_back(
    events: tuple[LedgerEvent, ...],
) -> None:
    if any(_is_unrecognized(event) for event in events):
        with pytest.raises(ValueError, match="does not know"):
            to_drafts(events)
    else:
        assert len(to_drafts(events)) == len(events)
