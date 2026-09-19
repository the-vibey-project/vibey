# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for appending one ledger event on a caller-owned connection,
and for reading one back out of a row.

Mirrors `vibey/infrastructure/db/ledger_repository.py` (ADR-0016): the
directory gains an `interfaces/` child and the module an `_interface` suffix.

Interfaces declare; they never consume. The seam names the driver types it is
declared over -- an asyncpg connection and a ledger draft -- because a seam
whose argument is `Any` constrains nothing, which is the one thing it exists
to do. Both are imported under TYPE_CHECKING so the module stays free of
runtime dependencies on the code that implements it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg

    from vibey.domain.ledger import LedgerEvent
    from vibey.infrastructure.engines.tailer import LedgerEventDraft

    type OwnedConnection = asyncpg.pool.PoolConnectionProxy | asyncpg.Connection


@runtime_checkable
class EventAppenderInterface(Protocol):
    """Appends one event on a connection the caller owns.

    Taking the connection rather than acquiring one is the whole point: it
    lets the append join a transaction that is already open, so a write that
    must be atomic with the event -- a phase compare-and-set, say -- commits
    with it or not at all.
    """

    async def append(self, conn: OwnedConnection, draft: LedgerEventDraft) -> LedgerEvent:
        """Persist `draft` on `conn` and return the event as it landed."""
        ...


@runtime_checkable
class EventRowMapperInterface(Protocol):
    """Maps one row of the `event` table to the domain's `LedgerEvent`."""

    def to_event(self, row: asyncpg.Record) -> LedgerEvent:
        """Every column, typed; the payload decoded from its JSON text. A kind
        this vibey does not know is kept as an `UnrecognizedEventKind`, never
        raised (vibey#275)."""
        ...
