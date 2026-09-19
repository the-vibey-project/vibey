# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for compiling a ledger search to SQL.

Mirrors `vibey/infrastructure/db/ledger_search_repository.py` (ADR-0016).
Interfaces declare; they never consume.

The repository itself is declared where it is consumed, as the application
port `vibey.application.interfaces.LedgerSearch`; declaring the same method a
second time here would be a copy that could drift. What this module declares is
the seam inside the adapter: the compiler that turns a query into one
parameterised statement, which a test can exercise without a database and a
later storage tier (vibey#114) can replace without touching the repository.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from vibey.domain.interfaces.ledger_query_interface import LedgerQueryInterface


@runtime_checkable
class SearchStatementInterface(Protocol):
    """One statement: SQL text with `$n` placeholders, and the values bound to them."""

    @property
    def sql(self) -> str:
        """Placeholders only -- no value a searcher typed ever appears in it."""
        ...

    @property
    def args(self) -> tuple[object, ...]:
        """The values, in placeholder order: `args[0]` binds `$1`."""
        ...


@runtime_checkable
class LedgerSearchCompilerInterface(Protocol):
    """Compiles a ledger query, scoped to one project, to one statement."""

    def compile(
        self, project_id: UUID, query: LedgerQueryInterface, *, fetch: int
    ) -> SearchStatementInterface:
        """Select at most `fetch` events, newest first."""
        ...
