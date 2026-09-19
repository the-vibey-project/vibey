# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for one ledger event per line of JSON.

Mirrors `vibey/infrastructure/ledger/full_ledger_writer.py` (ADR-0016). Interfaces
declare; they never consume. The ledger type is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.ledger import LedgerEvent


@runtime_checkable
class LedgerLinesInterface(Protocol):
    """Encodes an event as one line of JSON, and decodes one back."""

    def encode(self, event: LedgerEvent) -> str:
        """The shared ledger record, keys sorted, no whitespace, no newline."""
        ...

    def decode(self, line: str) -> LedgerEvent:
        """Raises `InvalidLedgerRecord` for a line that is not a ledger record."""
        ...
