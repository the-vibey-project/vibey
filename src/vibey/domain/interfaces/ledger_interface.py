# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading a stored event kind forward-compatibly.

Mirrors `vibey/domain/ledger.py` (ADR-0016) for the two types vibey#275 added
there; the older types in that module converge module by module. Interfaces
declare; they never consume. `LedgerEventKind` is imported under TYPE_CHECKING
only, so this module has no runtime dependency on the code that implements it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.ledger import LedgerEventKind


@runtime_checkable
class UnrecognizedEventKindInterface(Protocol):
    """A stored kind this vibey has no `EventKind` member for."""

    @property
    def value(self) -> str:
        """The kind exactly as stored."""
        ...


@runtime_checkable
class EventKindParserInterface(Protocol):
    """Reads the stored text of an event's kind."""

    def parse(self, raw: str) -> LedgerEventKind:
        """The known member, or the unrecognized text preserved. Never raises."""
        ...
