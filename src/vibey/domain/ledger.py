# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The append-only, vendor-neutral event ledger (ADR-0003). This module is
pure projection logic over an in-memory event sequence -- persistence lives
in infrastructure/.

**Readers are forward compatible; writers are strict (vibey#275).** The ledger is
shared by every vibey in the fleet, and during a rolling upgrade or after a
rollback some of them are older than the rows they read. A kind this version has
no `EventKind` member for is read as an `UnrecognizedEventKind` carrying the
stored text: kept, never dropped and never raised, so it still reaches every full
ledger handed on and every digest folded over the range. Every projection here
matches kinds by identity against `EventKind` members, so an unrecognized kind
matches none of them and is skipped. Writing stays strict: a draft carries an
`EventKind`, so vibey can only ever append a kind it knows.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from vibey.domain.engine import EngineId
from vibey.domain.interfaces.ledger_interface import EventKindParserInterface
from vibey.domain.phase import Phase


class EventKind(StrEnum):
    SESSION_SEEDED = "SessionSeeded"
    TURN_REQUESTED = "TurnRequested"
    TURN_COMPLETED = "TurnCompleted"
    TOOL_INVOKED = "ToolInvoked"
    FILE_EDITED = "FileEdited"
    VERDICT_RENDERED = "VerdictRendered"
    CAPACITY_REJECTED = "CapacityRejected"
    QUESTION_ASKED = "QuestionAsked"
    ANSWER_GIVEN = "AnswerGiven"
    DECISION_RECORDED = "DecisionRecorded"
    ASSUMPTION_STATED = "AssumptionStated"
    FINDING_RAISED = "FindingRaised"
    FINDING_RESOLVED = "FindingResolved"
    ARTIFACT_PRODUCED = "ArtifactProduced"
    SAVEPOINT_CREATED = "SavePointCreated"
    HANDOFF_INITIATED = "HandoffInitiated"
    HANDOFF_ACCEPTED = "HandoffAccepted"
    PHASE_TRANSITIONED = "PhaseTransitioned"
    BUDGET_SPENT = "BudgetSpent"
    VISUAL_DESIGN_OPTED_IN = "VisualDesignOptedIn"
    VISUAL_DESIGN_DECLINED = "VisualDesignDeclined"
    VISUAL_DESIGN_ACCEPTED = "VisualDesignAccepted"
    VISUAL_DESIGN_WAIVED = "VisualDesignWaived"
    DEPLOYMENT_OPTED_IN = "DeploymentOptedIn"
    DEPLOYMENT_DECLINED = "DeploymentDeclined"


_KNOWN_KIND_VALUES: Final = frozenset(kind.value for kind in EventKind)


@dataclass(frozen=True, slots=True)
class UnrecognizedEventKind:
    """A stored event kind this version of vibey has no `EventKind` member for.

    A newer vibey wrote it -- the newer pods of a rolling upgrade, or the release
    a rollback stepped back from -- or an older one did and a later release
    retired the kind. Either way the row is real, append-only history. A reader
    keeps it, so it reaches every full ledger handed on and every range digest;
    what no reader can do is interpret it, so every projection skips it.

    Never names a known kind: construction refuses one, so a known event can
    never hide behind this type and slip past an `is EventKind.X` check.
    """

    value: str
    """The kind exactly as stored -- the same text a newer vibey would read as its
    own member's value, so a hash chain or a JSON record built from `.value`
    comes out identical on both versions."""

    def __post_init__(self) -> None:
        if self.value in _KNOWN_KIND_VALUES:
            raise ValueError(
                f"{self.value!r} is a known event kind; read it as EventKind({self.value!r})"
            )

    def __str__(self) -> str:
        return self.value


type LedgerEventKind = EventKind | UnrecognizedEventKind
"""What a stored event's kind reads as: a member this vibey knows, or the text of
one it does not. Narrow with `isinstance(kind, EventKind)` before using anything
only a member has (its `name`, `CLOSABLE`, a `Mapping[EventKind, ...]` key)."""


class EventKindParser:
    """Reads a stored kind. Never raises: a value this vibey knows is its
    `EventKind` member, and anything else is an `UnrecognizedEventKind` carrying
    the exact text. Matching is exact -- `event.kind` holds a member's value
    verbatim, so a case variant is not that member, it is another kind."""

    def parse(self, raw: str) -> LedgerEventKind:
        if raw in _KNOWN_KIND_VALUES:
            return EventKind(raw)
        return UnrecognizedEventKind(raw)


EVENT_KIND_PARSER: Final[EventKindParserInterface] = EventKindParser()
"""The parser every ledger reader shares. Stateless, so one instance serves."""


CLOSABLE: frozenset[EventKind] = frozenset(
    {
        EventKind.QUESTION_ASKED,
        EventKind.DECISION_RECORDED,
        EventKind.ASSUMPTION_STATED,
        EventKind.FINDING_RAISED,
    }
)

CLOSES: Mapping[EventKind, EventKind] = {
    EventKind.ANSWER_GIVEN: EventKind.QUESTION_ASKED,
    EventKind.FINDING_RESOLVED: EventKind.FINDING_RAISED,
}

# The payload field carrying the id minted for each closable/closing kind.
_ID_FIELD: Mapping[EventKind, str] = {
    EventKind.QUESTION_ASKED: "question_id",
    EventKind.ANSWER_GIVEN: "question_id",
    EventKind.DECISION_RECORDED: "decision_id",
    EventKind.ASSUMPTION_STATED: "assumption_id",
    EventKind.FINDING_RAISED: "finding_id",
    EventKind.FINDING_RESOLVED: "finding_id",
}


class Provenance(StrEnum):
    TRUSTED = "trusted"
    AGENT = "agent"
    UNTRUSTED = "untrusted"


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    event_id: UUID
    project_id: UUID
    cycle: int
    phase: Phase
    seq: int
    kind: LedgerEventKind
    engine_id: EngineId | None
    job_id: UUID | None
    causation_id: UUID | None
    correlation_id: UUID
    provenance: Provenance
    produced_at: datetime
    payload: Mapping[str, object]
    digest: str


def canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()


def digest_event(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def digest_range(events: Sequence[LedgerEvent]) -> str:
    """Order-sensitive Merkle-ish fold. Rule R6 depends on this."""
    h = hashlib.sha256()
    for e in sorted(events, key=lambda x: x.seq):
        h.update(str(e.seq).encode())
        h.update(b"\x00")
        h.update(e.digest.encode())
    return h.hexdigest()


def open_items(events: Sequence[LedgerEvent], kind: EventKind) -> tuple[str, ...]:
    """Ids opened by `kind` and not yet closed or superseded. The gate's
    primitive."""
    if kind not in CLOSABLE:
        raise ValueError(f"{kind} is not a closable event kind")

    closing_kind = next((k for k, closes in CLOSES.items() if closes is kind), None)
    id_field = _ID_FIELD[kind]

    opened: dict[str, int] = {}
    for e in sorted(events, key=lambda x: x.seq):
        if e.kind is kind:
            item_id = str(e.payload[id_field])
            opened[item_id] = e.seq
            if kind is EventKind.DECISION_RECORDED:
                superseded = e.payload.get("supersedes")
                if superseded is not None:
                    opened.pop(str(superseded), None)
        elif closing_kind is not None and e.kind is closing_kind:
            item_id = str(e.payload[id_field])
            opened.pop(item_id, None)

    return tuple(sorted(opened, key=lambda item_id: opened[item_id]))
