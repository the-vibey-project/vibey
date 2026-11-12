# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger record codec, as round-trip properties: what `to_fields` writes,
`from_fields` reads back as the same event, including events whose vocabulary values a
newer vibey wrote, and across the JSON text a ledger file actually holds."""

import json

from hypothesis import given
from hypothesis import strategies as st

from tests.ledger_strategies import ledger_events
from vibey.domain.ledger import LedgerEvent
from vibey.domain.ledger_record import RECORD_FIELDS, LedgerRecordCodec

CODEC = LedgerRecordCodec()


def assert_same_event(read: LedgerEvent, written: LedgerEvent) -> None:
    """Equal field for field, and the instant keeps its zone: equal datetimes of
    different offsets compare equal, and a file that rewrote the zone is not the file
    that was written."""
    assert read == written
    assert read.produced_at.utcoffset() == written.produced_at.utcoffset()
    assert read.produced_at.isoformat() == written.produced_at.isoformat()
    assert type(read.phase) is type(written.phase)
    assert type(read.kind) is type(written.kind)
    assert type(read.provenance) is type(written.provenance)
    assert type(read.engine_id) is type(written.engine_id)


@given(event=ledger_events(unknown_values=True))
def test_from_fields_reads_back_what_to_fields_wrote(event: LedgerEvent) -> None:
    fields = CODEC.to_fields(event)
    assert fields.keys() == RECORD_FIELDS
    assert_same_event(CODEC.from_fields(fields), event)


@given(event=ledger_events(unknown_values=True))
def test_the_round_trip_survives_the_json_text_of_a_ledger_file(event: LedgerEvent) -> None:
    line = json.dumps(CODEC.to_fields(event))
    assert_same_event(CODEC.from_fields(json.loads(line)), event)


@given(event=ledger_events(unknown_values=True))
def test_writing_what_was_read_writes_the_same_record(event: LedgerEvent) -> None:
    fields = CODEC.to_fields(event)
    assert CODEC.to_fields(CODEC.from_fields(fields)) == fields


@given(events=st.lists(ledger_events(), min_size=2, max_size=4, unique_by=lambda e: e.event_id))
def test_distinct_events_write_distinct_records(events: list[LedgerEvent]) -> None:
    records = [json.dumps(CODEC.to_fields(event), sort_keys=True) for event in events]
    assert len(set(records)) == len(events)
