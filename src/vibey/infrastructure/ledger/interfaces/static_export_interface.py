# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts inside the shard file and the static site writer.

Mirrors `vibey/infrastructure/ledger/static_export.py` (ADR-0016). Interfaces
declare; they never consume.

The shard store and the site writer themselves are declared where they are
consumed, as the application ports `LedgerShardStore` and `LedgerSiteWriter`;
declaring the same methods a second time here would be a copy that could drift.
What this module declares is the seams inside the adapter: the header codec a
test can drive without a file, and the JSON encoder every served document goes
through.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.interfaces.ledger_publication_interface import ShardHeaderInterface


@runtime_checkable
class ShardHeaderCodecInterface(Protocol):
    """Turns a shard header into the JSON object on a shard's first line, and back."""

    def to_document(self, header: ShardHeaderInterface) -> dict[str, object]:
        """Every header field, as JSON types."""
        ...

    def from_document(self, document: object) -> ShardHeaderInterface:
        """Raises `InvalidLedgerShard`, naming the field, for anything missing,
        mistyped or unknown -- the document comes from a file anyone could edit."""
        ...


@runtime_checkable
class HtmlSafeJsonInterface(Protocol):
    """Encodes a document for serving: deterministic, and inert inside HTML."""

    def dumps(self, document: object) -> str:
        """Sorted keys, ASCII only, `<`, `>` and `&` escaped, one trailing newline."""
        ...
