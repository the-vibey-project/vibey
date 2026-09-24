# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for bringing a database to the migrated, guarded state.

Mirrors `vibey/infrastructure/db/database_setup.py` (ADR-0016, ADR-0055). Interfaces
declare; they never consume.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.infrastructure.db.migrator import Migration, OwnedConnection

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibey.infrastructure.db.database_setup import MigrationReport
    from vibey.infrastructure.db.ledger_guard import DatabaseEndpoints, LedgerGuardStatus


@runtime_checkable
class SchemaPreparerInterface(Protocol):
    """What `build_app()` runs on every start."""

    async def prepare(
        self,
        app: OwnedConnection,
        endpoints: "DatabaseEndpoints",
        migrations: tuple[Migration, ...],
    ) -> "LedgerGuardStatus":
        """Migrate with the role allowed to, or verify nothing is pending; return the
        guard as the application's connection sees it."""
        ...


@runtime_checkable
class OwnerMigrationInterface(Protocol):
    """`vibey migrate`."""

    async def run(
        self,
        *,
        owner_url: str,
        app: "DatabaseEndpoints | None",
        migrations: tuple[Migration, ...],
    ) -> "MigrationReport":
        """Migrate as the owner, reconcile the application role, inspect the guard."""
        ...
