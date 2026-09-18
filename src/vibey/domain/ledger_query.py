# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A ledger search, as a value that cannot be built invalid.

Sub-doctrine 7.a (the searchable ledger) says anyone can search the ledger by
record id, content hash, actor, time range, record kind and free text over the
payload. This module is the pure half of that: what a searcher asks for, checked
before anything touches storage, plus the two small vocabularies a searcher types
by hand -- who did it (an actor label) and what happened (an event kind label).
The storage half compiles a `LedgerQuery` to one parameterised statement
(`infrastructure/db/ledger_search_repository.py`).

Two facts about the ledger shape the query:

- **A digest names a payload, not a record.** `event.digest` is the SHA-256 of the
  canonical payload only (`domain/ledger.py::digest_event`), so two events with the
  same payload -- `{}` is common -- share a digest. A digest search therefore
  returns a set, and a record is identified by its `event_id`, never its digest.
- **"Actor" is not a column.** Who did something is recorded two ways today: the
  engine that produced it (`engine_id`, `NULL` when vibey wrote the event on its own
  account) and the trust class it arrived with (`provenance`). An actor label
  resolves to exactly one of those three readings (`ActorResolver`).
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from vibey.domain.engine import EngineId
from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.ledger_query_interface import (
    ActorInterface,
    ActorResolverInterface,
    EventKindResolverInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance

DEFAULT_SEARCH_LIMIT: Final = 50
"""How many events a search returns when the searcher does not say. The same
default `vibey ledger show` uses, so the two commands answer alike."""

SELF_ACTOR: Final = "vibey"
"""The actor label for events vibey wrote on its own account (`engine_id IS NULL`).
A deployment that wants another word passes one to `ActorResolver` (ADR-0018)."""

DIGEST_HEX_LENGTH: Final = hashlib.sha256().digest_size * 2
"""The length of a full ledger digest in hex. Derived from the algorithm
`digest_event` uses rather than written as 64, so the two cannot disagree."""

_HEX_DIGITS: Final = frozenset("0123456789abcdef")


class InvalidLedgerQuery(VibeyError):
    """A search that cannot be run as asked. Raised before any I/O.

    An exception type, so it has no interface beside it: a `Protocol` cannot be
    raised or caught, and the seam an error crosses is its type.
    """


class ActorScope(StrEnum):
    """Which of the ledger's two "who" columns an actor label names."""

    ENGINE = "engine"
    """`event.engine_id` equals the name."""
    SELF = "self"
    """`event.engine_id IS NULL`: vibey wrote the event on its own account."""
    PROVENANCE = "provenance"
    """`event.provenance` equals the name."""


@dataclass(frozen=True, slots=True)
class Actor:
    """One resolved actor: the column it reads and the value it matches."""

    scope: ActorScope
    name: str


class ActorResolver:
    """Resolves a typed actor label to the one reading it names.

    Case-insensitive, surrounding whitespace ignored. Precedence when a label
    could mean two things: the self label, then an engine id, then a provenance.
    The engine and provenance vocabularies are closed enums, so no two of them
    collide today; the order only matters if a deployment picks a self label
    that is also one of theirs, and then the deployment's choice wins.
    """

    def __init__(self, self_name: str = SELF_ACTOR) -> None:
        self._self_name = self_name

    @property
    def self_name(self) -> str:
        """The label that means "vibey itself"."""
        return self._self_name

    def resolve(self, label: str) -> Actor:
        needle = label.strip().lower()
        if needle == self._self_name.lower():
            return Actor(ActorScope.SELF, self._self_name)
        for engine in EngineId:
            if needle == engine.value:
                return Actor(ActorScope.ENGINE, engine.value)
        for provenance in Provenance:
            if needle == provenance.value:
                return Actor(ActorScope.PROVENANCE, provenance.value)
        engines = ", ".join(e.value for e in EngineId)
        provenances = ", ".join(p.value for p in Provenance)
        raise InvalidLedgerQuery(
            f"unknown actor {label!r}: expected an engine ({engines}), "
            f"a provenance ({provenances}), or {self._self_name!r} for events "
            "vibey wrote itself"
        )


class EventKindResolver:
    """Resolves a typed kind label -- the value or the enum name, any case --
    the way `vibey ledger show --kind` has always read one."""

    def resolve(self, label: str) -> EventKind:
        needle = label.strip().lower()
        for kind in EventKind:
            if needle in (kind.value.lower(), kind.name.lower()):
                return kind
        raise InvalidLedgerQuery(
            f"unknown event kind {label!r}: expected one of "
            + ", ".join(k.value for k in EventKind)
        )


ACTORS: Final[ActorResolverInterface] = ActorResolver()
"""The default resolver. Stateless beyond its self label, so one instance serves."""

EVENT_KINDS: Final[EventKindResolverInterface] = EventKindResolver()
"""The default kind resolver. Stateless, so one instance serves."""


@dataclass(frozen=True, slots=True)
class LedgerQuery:
    """What to look for in one project's ledger. Every criterion is optional and
    they combine with AND; no criterion at all means "the latest `limit` events".

    `since` is inclusive and `until` exclusive -- the half-open window, so two
    adjacent windows never both claim an event produced on their shared edge.
    Both must carry a timezone: a naive bound would be read in whatever zone the
    reading machine is in, and the same query would mean different things on two
    machines.
    """

    event_id: UUID | None = None
    digest: str | None = None
    actor: ActorInterface | None = None
    since: datetime | None = None
    until: datetime | None = None
    kinds: frozenset[EventKind] = frozenset()
    text: str | None = None
    limit: int = DEFAULT_SEARCH_LIMIT

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise InvalidLedgerQuery(f"limit must be at least 1, got {self.limit}")
        if self.digest is not None:
            # Frozen, so the normalised digest goes in through object.__setattr__ --
            # the one sanctioned way to finish constructing a frozen dataclass.
            object.__setattr__(self, "digest", self._normalised_digest(self.digest))
        for name, bound in (("since", self.since), ("until", self.until)):
            if bound is not None and bound.utcoffset() is None:
                raise InvalidLedgerQuery(f"{name} must carry a timezone, got {bound.isoformat()}")
        if self.since is not None and self.until is not None and self.since >= self.until:
            raise InvalidLedgerQuery(
                f"since ({self.since.isoformat()}) must be before until "
                f"({self.until.isoformat()}); the window is empty"
            )
        if self.text == "":
            raise InvalidLedgerQuery("text must not be empty; an empty needle matches everything")

    @staticmethod
    def _normalised_digest(digest: str) -> str:
        value = digest.strip().lower()
        if len(value) != DIGEST_HEX_LENGTH or not set(value) <= _HEX_DIGITS:
            raise InvalidLedgerQuery(
                f"digest must be a full {DIGEST_HEX_LENGTH}-character hex SHA-256, got {digest!r}"
            )
        return value


@dataclass(frozen=True, slots=True)
class LedgerSearchResult:
    """The events a search matched, oldest first, and whether older matches
    were left out because the limit was reached."""

    events: tuple[LedgerEvent, ...]
    truncated: bool
