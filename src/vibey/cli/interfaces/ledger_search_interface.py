# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey ledger search`.

Mirrors `vibey/cli/ledger_search.py` (ADR-0016). Interfaces declare; they never
consume. The domain types the seams are declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.interfaces.ledger_query_interface import (
        LedgerQueryInterface,
        LedgerSearchResultInterface,
    )
    from vibey.domain.ledger import LedgerEvent, LedgerEventKind


@runtime_checkable
class TimeBoundParserInterface(Protocol):
    """Reads a `--since` / `--until` value into an instant."""

    def parse(self, value: str) -> datetime:
        """Always timezone-aware. Raises `InvalidLedgerQuery` on unreadable input."""
        ...


@runtime_checkable
class LedgerSearchPresenterInterface(Protocol):
    """Renders a search result: for a person first, for a program second."""

    def human(self, result: LedgerSearchResultInterface) -> list[str]:
        """One line per event, oldest first, then one line saying what was found."""
        ...

    def machine(self, project_id: UUID, result: LedgerSearchResultInterface) -> str:
        """The same result as a JSON document, every field of every event."""
        ...

    def record(self, event: LedgerEvent) -> dict[str, object]:
        """One event as `--json` and the hub's live feed both carry it."""
        ...

    def kind_notes(self, kinds: Iterable[LedgerEventKind]) -> list[str]:
        """One line per kind this vibey does not know, saying it is matched
        exactly as written -- the only sign a mistyped `--kind` gives."""
        ...


@runtime_checkable
class LedgerSearchCommandInterface(Protocol):
    """Builds the query from raw options, then runs it and prints the result."""

    def query(
        self,
        *,
        event_id: UUID | None,
        digest: str | None,
        actor: str | None,
        since: str | None,
        until: str | None,
        kinds: list[str],
        text: str | None,
        limit: int,
    ) -> LedgerQueryInterface:
        """Raises a usage error on anything invalid -- before any I/O."""
        ...

    async def run(
        self, project_id: UUID | None, query: LedgerQueryInterface, *, as_json: bool
    ) -> None:
        """Search `project_id`, or the latest project, and print the result."""
        ...
