# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger record: one JSON object per event, written one way, read back strictly."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from vibey.domain.engine import EngineId, UnrecognizedEngineId
from vibey.domain.interfaces import LedgerRecordCodecInterface
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    UnrecognizedProvenance,
    digest_event,
)
from vibey.domain.ledger_record import (
    LEDGER_RECORDS,
    RECORD_FIELDS,
    InvalidLedgerRecord,
    LedgerRecordCodec,
)
from vibey.domain.phase import Phase, UnrecognizedPhase

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000002")


def _event(**overrides: object) -> LedgerEvent:
    payload = overrides.pop("payload", {"text": "hello", "n": [1, 2]})
    fields: dict[str, object] = {
        "event_id": uuid4(),
        "project_id": PROJECT,
        "cycle": 2,
        "phase": Phase.REVIEW,
        "seq": 7,
        "kind": EventKind.FINDING_RAISED,
        "engine_id": EngineId.CODEXLOOP,
        "job_id": uuid4(),
        "causation_id": uuid4(),
        "correlation_id": uuid4(),
        "provenance": Provenance.AGENT,
        "produced_at": datetime(2026, 9, 18, 12, 0, tzinfo=timezone(timedelta(hours=2))),
        "payload": payload,
        "digest": digest_event(payload),  # type: ignore[arg-type]
    }
    fields.update(overrides)
    return LedgerEvent(**fields)  # type: ignore[arg-type]


def test_the_default_codec_satisfies_its_interface() -> None:
    assert isinstance(LEDGER_RECORDS, LedgerRecordCodecInterface)
    assert LEDGER_RECORDS.field_names == RECORD_FIELDS


def test_every_stored_field_is_written_as_json_types() -> None:
    event = _event()
    fields = LEDGER_RECORDS.to_fields(event)

    assert set(fields) == RECORD_FIELDS
    assert fields["event_id"] == str(event.event_id)
    assert fields["phase"] == "review"
    assert fields["kind"] == "FindingRaised"
    assert fields["engine_id"] == "codexloop"
    assert fields["provenance"] == "agent"
    assert fields["produced_at"] == "2026-09-18T12:00:00+02:00"


def test_a_record_reads_back_as_the_event_it_was() -> None:
    event = _event()
    assert LEDGER_RECORDS.from_fields(LEDGER_RECORDS.to_fields(event)) == event


def test_absent_optional_ids_read_back_as_none() -> None:
    event = _event(engine_id=None, job_id=None, causation_id=None)
    fields = LEDGER_RECORDS.to_fields(event)

    assert fields["engine_id"] is None
    assert LEDGER_RECORDS.from_fields(fields) == event


def _fields(**changes: object) -> dict[str, object]:
    fields = LedgerRecordCodec().to_fields(_event())
    fields.update(changes)
    return fields


def test_a_missing_field_is_named() -> None:
    fields = _fields()
    del fields["digest"], fields["seq"]
    with pytest.raises(InvalidLedgerRecord, match="missing field\\(s\\): digest, seq"):
        LEDGER_RECORDS.from_fields(fields)


def test_an_unknown_field_is_named() -> None:
    with pytest.raises(InvalidLedgerRecord, match="unknown field\\(s\\): extra"):
        LEDGER_RECORDS.from_fields(_fields(extra=1))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"payload": ["not", "an", "object"]}, "'payload' must be a JSON object"),
        ({"digest": 5}, "'digest' must be a string, not int"),
        ({"seq": True}, "'seq' must be an integer, not bool"),
        ({"cycle": "2"}, "'cycle' must be an integer, not str"),
        ({"event_id": "not-a-uuid"}, "'event_id' is not a UUID"),
        ({"job_id": "nope"}, "'job_id' is not a UUID"),
        ({"phase": 3}, "'phase' must be a string, not int"),
        ({"engine_id": 9}, "'engine_id' must be a string, not int"),
        ({"produced_at": "yesterday"}, "'produced_at' is not an ISO-8601 time"),
        ({"produced_at": "2026-09-18T12:00:00"}, "'produced_at' has no zone"),
    ],
)
def test_a_mistyped_or_unreadable_field_is_refused(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(InvalidLedgerRecord, match=message):
        LEDGER_RECORDS.from_fields(_fields(**changes))


def test_a_retired_or_newer_value_is_kept_whole_and_written_back_unchanged() -> None:
    """ADR-0078 retired `agyloop`; the ledger it left behind is real and must stay readable."""
    fields = _fields(phase="sideways", engine_id="agyloop", kind="FutureKind", provenance="alien")
    read = LEDGER_RECORDS.from_fields(fields)
    assert isinstance(read.phase, UnrecognizedPhase) and read.phase.value == "sideways"
    assert isinstance(read.engine_id, UnrecognizedEngineId) and read.engine_id.value == "agyloop"
    assert isinstance(read.kind, UnrecognizedEventKind) and read.kind.value == "FutureKind"
    assert isinstance(read.provenance, UnrecognizedProvenance) and read.provenance.value == "alien"
    assert LEDGER_RECORDS.to_fields(read) == fields


def test_a_utc_time_reads_back_aware() -> None:
    event = _event(produced_at=datetime(2026, 9, 18, tzinfo=UTC))
    read = LEDGER_RECORDS.from_fields(LEDGER_RECORDS.to_fields(event))
    assert read.produced_at.utcoffset() == timedelta(0)
