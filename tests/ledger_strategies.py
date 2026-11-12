# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hypothesis strategies for ledger payloads and events, shared by the round-trip properties.

Every strategy here draws values PostgreSQL's jsonb can hold (no U+0000, no lone
surrogate, no NaN or infinity), so an event built from them is one a real append could
store. Floats are finite and otherwise unrestricted because the properties that use
them run on the in-memory ledger or on no ledger at all: jsonb rewrites a float of
magnitude 1e16 and up, and -0.0, on read-back, which breaks digest verification against
PostgreSQL (vibey#1883). A property that goes through the real repository must narrow
the floats itself and cite that issue.
"""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from hypothesis import strategies as st

from vibey.domain.engine import EngineId, UnrecognizedEngineId
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    UnrecognizedProvenance,
    digest_event,
)
from vibey.domain.phase import Phase, UnrecognizedPhase

JSON_TEXT = st.text(
    alphabet=st.characters(blacklist_characters="\x00", blacklist_categories=("Cs",)), max_size=12
)
"""Any text jsonb can store."""

PLAIN_WORDS = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789 ", max_size=12)
"""Text that cannot contain a vendor-shaped secret: every pattern needs an upper-case
letter, a dash, an underscore or a dot."""


def _json_values(text: st.SearchStrategy[str], keys: st.SearchStrategy[str]) -> st.SearchStrategy:
    leaves = st.one_of(
        st.none(),
        st.booleans(),
        st.integers(-(2**53), 2**53),
        st.floats(allow_nan=False, allow_infinity=False),
        text,
    )
    return st.recursive(
        leaves,
        lambda children: st.one_of(
            st.lists(children, max_size=4), st.dictionaries(keys, children, max_size=4)
        ),
        max_leaves=12,
    )


def json_values() -> st.SearchStrategy[object]:
    """Any JSON value, as a payload member."""
    return _json_values(JSON_TEXT, JSON_TEXT)


def json_payloads() -> st.SearchStrategy[dict[str, object]]:
    """A ledger payload: a JSON object of arbitrary depth."""
    return st.dictionaries(JSON_TEXT, _json_values(JSON_TEXT, JSON_TEXT), max_size=4)


def plain_payloads() -> st.SearchStrategy[dict[str, object]]:
    """A payload that holds no secret: nothing in it can match a key or value pattern."""
    return st.dictionaries(PLAIN_WORDS, _json_values(PLAIN_WORDS, PLAIN_WORDS), max_size=4)


_KNOWN_VALUES = frozenset(
    member.value for vocabulary in (EventKind, Phase, EngineId, Provenance) for member in vocabulary
)
_UNKNOWN_TEXT = JSON_TEXT.filter(lambda value: value not in _KNOWN_VALUES)
_ENGINES: list[EngineId | None] = [None, *EngineId]
_UTC_OFFSETS = st.builds(
    lambda minutes: timezone(timedelta(minutes=minutes)), st.integers(-23 * 60, 23 * 60)
)
_INSTANTS = st.builds(
    lambda base, micros, zone: (base + timedelta(microseconds=micros)).astimezone(zone),
    st.just(datetime(2026, 9, 18, 12, 0, tzinfo=UTC)),
    st.integers(-(10**14), 10**14),
    _UTC_OFFSETS,
)


@st.composite
def ledger_events(
    draw: st.DrawFn,
    *,
    project_id: UUID | None = None,
    seq: int | None = None,
    payloads: st.SearchStrategy[dict[str, object]] | None = None,
    unknown_values: bool = False,
) -> LedgerEvent:
    """One event. With `unknown_values`, the closed vocabularies may hold text this vibey
    has no member for (vibey#275, #287), as a newer vibey's rows do; `digest` is always the
    digest of the payload, as a row the appender wrote."""
    payload = draw(payloads if payloads is not None else json_payloads())
    phase: Phase | UnrecognizedPhase = draw(st.sampled_from(list(Phase)))
    kind: EventKind | UnrecognizedEventKind = draw(st.sampled_from(list(EventKind)))
    provenance: Provenance | UnrecognizedProvenance = draw(st.sampled_from(list(Provenance)))
    engine_id: EngineId | UnrecognizedEngineId | None = draw(st.sampled_from(_ENGINES))
    if unknown_values:
        phase = draw(st.just(phase) | st.builds(UnrecognizedPhase, _UNKNOWN_TEXT))
        kind = draw(st.just(kind) | st.builds(UnrecognizedEventKind, _UNKNOWN_TEXT))
        provenance = draw(st.just(provenance) | st.builds(UnrecognizedProvenance, _UNKNOWN_TEXT))
        engine_id = draw(st.just(engine_id) | st.builds(UnrecognizedEngineId, _UNKNOWN_TEXT))
    return LedgerEvent(
        event_id=draw(st.uuids()),
        project_id=project_id if project_id is not None else draw(st.uuids()),
        cycle=draw(st.integers(1, 9)),
        phase=phase,
        seq=seq if seq is not None else draw(st.integers(1, 10_000)),
        kind=kind,
        engine_id=engine_id,
        job_id=draw(st.none() | st.uuids()),
        causation_id=draw(st.none() | st.uuids()),
        correlation_id=draw(st.uuids()),
        provenance=provenance,
        produced_at=draw(_INSTANTS),
        payload=payload,
        digest=digest_event(payload),
    )
