# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A ledger event as a JSON object: one mapping, written one way and read back one way.

The handoff ledger (`<worktree>/.vibey/handoff/ledger.jsonl`, written by
`infrastructure/ledger/full_ledger_writer.py`) and the published shard (`vibey ledger
export`, sub-doctrine 7.a) carry the same object per event: every stored field, ids as
strings, enums as their values, `produced_at` in ISO-8601. This module is that object,
so the two files cannot drift apart and a reader of either needs one parser.

Reading is strict because the object may come from a file anyone could have edited --
a shard is committed to a repository and read by a site build that trusts nothing it
did not check. A missing field, an unknown one, a wrong type, an unknown enum value, a
malformed id or a time without a zone is refused with the field's name, never guessed.
"""

from collections.abc import Callable, Mapping
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from vibey.domain.engine import EngineId
from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.ledger_record_interface import LedgerRecordCodecInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase

RECORD_FIELDS: Final = frozenset(
    {
        "event_id",
        "project_id",
        "cycle",
        "phase",
        "seq",
        "kind",
        "engine_id",
        "job_id",
        "causation_id",
        "correlation_id",
        "provenance",
        "produced_at",
        "payload",
        "digest",
    }
)
"""Every field a record carries. The same set `LedgerEvent` stores, by name."""


class InvalidLedgerRecord(VibeyError):
    """A JSON object that is not a ledger record. Names the field at fault.

    An exception type, so it has no interface beside it: a `Protocol` cannot be
    raised or caught, and the seam an error crosses is its type.
    """


class LedgerRecordCodec:
    """Writes and reads the per-event JSON object. Stateless."""

    @property
    def field_names(self) -> frozenset[str]:
        return RECORD_FIELDS

    def to_fields(self, event: LedgerEvent) -> dict[str, object]:
        return {
            "event_id": str(event.event_id),
            "project_id": str(event.project_id),
            "cycle": event.cycle,
            "phase": event.phase.value,
            "seq": event.seq,
            "kind": event.kind.value,
            "engine_id": event.engine_id.value if event.engine_id is not None else None,
            "job_id": str(event.job_id) if event.job_id is not None else None,
            "causation_id": str(event.causation_id) if event.causation_id is not None else None,
            "correlation_id": str(event.correlation_id),
            "provenance": event.provenance.value,
            "produced_at": event.produced_at.isoformat(),
            "payload": event.payload,
            "digest": event.digest,
        }

    def from_fields(self, fields: Mapping[str, object]) -> LedgerEvent:
        missing = RECORD_FIELDS - fields.keys()
        if missing:
            raise InvalidLedgerRecord(f"missing field(s): {', '.join(sorted(missing))}")
        extra = fields.keys() - RECORD_FIELDS
        if extra:
            raise InvalidLedgerRecord(f"unknown field(s): {', '.join(sorted(extra))}")
        payload = fields["payload"]
        if not isinstance(payload, Mapping):
            raise InvalidLedgerRecord("'payload' must be a JSON object")
        return LedgerEvent(
            event_id=self._uuid(fields, "event_id"),
            project_id=self._uuid(fields, "project_id"),
            cycle=self._integer(fields, "cycle"),
            phase=self._member(fields, "phase", Phase),
            seq=self._integer(fields, "seq"),
            kind=self._member(fields, "kind", EventKind),
            engine_id=self._optional(
                fields, "engine_id", lambda key: self._member(fields, key, EngineId)
            ),
            job_id=self._optional(fields, "job_id", lambda key: self._uuid(fields, key)),
            causation_id=self._optional(
                fields, "causation_id", lambda key: self._uuid(fields, key)
            ),
            correlation_id=self._uuid(fields, "correlation_id"),
            provenance=self._member(fields, "provenance", Provenance),
            produced_at=self._instant(fields, "produced_at"),
            payload=dict(payload),
            digest=self._text(fields, "digest"),
        )

    @staticmethod
    def _text(fields: Mapping[str, object], key: str) -> str:
        value = fields[key]
        if not isinstance(value, str):
            raise InvalidLedgerRecord(f"{key!r} must be a string, not {type(value).__name__}")
        return value

    @staticmethod
    def _integer(fields: Mapping[str, object], key: str) -> int:
        value = fields[key]
        # bool is an int subclass; `true` is not a sequence number.
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidLedgerRecord(f"{key!r} must be an integer, not {type(value).__name__}")
        return value

    def _uuid(self, fields: Mapping[str, object], key: str) -> UUID:
        text = self._text(fields, key)
        try:
            return UUID(text)
        except ValueError as exc:
            raise InvalidLedgerRecord(f"{key!r} is not a UUID: {text!r}") from exc

    def _member[E: StrEnum](self, fields: Mapping[str, object], key: str, enum: type[E]) -> E:
        text = self._text(fields, key)
        try:
            return enum(text)
        except ValueError as exc:
            raise InvalidLedgerRecord(f"{key!r} has no member {text!r}") from exc

    @staticmethod
    def _optional[T](fields: Mapping[str, object], key: str, read: Callable[[str], T]) -> T | None:
        return None if fields[key] is None else read(key)

    def _instant(self, fields: Mapping[str, object], key: str) -> datetime:
        text = self._text(fields, key)
        try:
            moment = datetime.fromisoformat(text)
        except ValueError as exc:
            raise InvalidLedgerRecord(f"{key!r} is not an ISO-8601 time: {text!r}") from exc
        if moment.utcoffset() is None:
            raise InvalidLedgerRecord(f"{key!r} has no zone: {text!r}")
        return moment


LEDGER_RECORDS: Final[LedgerRecordCodecInterface] = LedgerRecordCodec()
"""The codec every ledger file shares. Annotated with the interface so `mypy --strict`
checks the class against its declared seam; stateless, so one instance serves."""
