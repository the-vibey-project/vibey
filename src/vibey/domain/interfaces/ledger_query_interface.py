# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for a ledger search: the query, its result, and the two label
vocabularies a searcher types by hand.

Mirrors `vibey/domain/ledger_query.py` (ADR-0016). Interfaces declare; they never
consume. The vocabulary types a seam is declared over -- `EventKind`, `ActorScope`,
`LedgerEvent` -- are imported under TYPE_CHECKING only, so this module has no
runtime dependency on the code that implements it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.ledger import EventKind, LedgerEvent
    from vibey.domain.ledger_query import ActorScope


@runtime_checkable
class ActorInterface(Protocol):
    """Who did it: which "who" column to read, and the value to match."""

    @property
    def scope(self) -> ActorScope:
        """Engine, provenance, or vibey itself."""
        ...

    @property
    def name(self) -> str:
        """The engine id or provenance value; the self label for vibey itself."""
        ...


@runtime_checkable
class ActorResolverInterface(Protocol):
    """Resolves a typed actor label to the one reading it names."""

    def resolve(self, label: str) -> ActorInterface:
        """Raises `InvalidLedgerQuery` for a label that names nothing."""
        ...


@runtime_checkable
class EventKindResolverInterface(Protocol):
    """Resolves a typed event-kind label, by value or name, any case."""

    def resolve(self, label: str) -> EventKind:
        """Raises `InvalidLedgerQuery` for a label that names no kind."""
        ...


@runtime_checkable
class LedgerQueryInterface(Protocol):
    """What to look for in one project's ledger. Criteria combine with AND."""

    @property
    def event_id(self) -> UUID | None:
        """Exactly this record."""
        ...

    @property
    def digest(self) -> str | None:
        """Every record whose payload has this digest -- a set, not one record."""
        ...

    @property
    def actor(self) -> ActorInterface | None:
        """Records this actor produced."""
        ...

    @property
    def since(self) -> datetime | None:
        """Produced at or after this instant (inclusive, timezone-aware)."""
        ...

    @property
    def until(self) -> datetime | None:
        """Produced before this instant (exclusive, timezone-aware)."""
        ...

    @property
    def kinds(self) -> frozenset[EventKind]:
        """Any of these kinds; empty means every kind."""
        ...

    @property
    def text(self) -> str | None:
        """Appears, literally and case-insensitively, in the payload's JSON text."""
        ...

    @property
    def limit(self) -> int:
        """At most this many events, the most recent matches."""
        ...


@runtime_checkable
class LedgerSearchResultInterface(Protocol):
    """The matched events, oldest first, and whether the limit cut older ones."""

    @property
    def events(self) -> tuple[LedgerEvent, ...]:
        """Ordered by `seq`, ascending."""
        ...

    @property
    def truncated(self) -> bool:
        """True when more events matched than the limit let through."""
        ...
