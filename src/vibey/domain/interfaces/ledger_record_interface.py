# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for a ledger event as a JSON object.

Mirrors `vibey/domain/ledger_record.py` (ADR-0016). Interfaces declare; they never
consume. The ledger type the seam is declared over is imported under TYPE_CHECKING
only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping

    from vibey.domain.ledger import LedgerEvent


@runtime_checkable
class LedgerRecordCodecInterface(Protocol):
    """Turns a `LedgerEvent` into the one JSON object every ledger file carries, and back."""

    @property
    def field_names(self) -> frozenset[str]:
        """Exactly the keys `to_fields` writes and `from_fields` accepts."""
        ...

    def to_fields(self, event: LedgerEvent) -> dict[str, object]:
        """Every stored field, as JSON types: ids as strings, enums as their values."""
        ...

    def from_fields(self, fields: Mapping[str, object]) -> LedgerEvent:
        """The event those fields describe. Raises `InvalidLedgerRecord` on anything
        missing, extra, mistyped or unreadable -- the fields may come from a file
        anyone could have edited."""
        ...
