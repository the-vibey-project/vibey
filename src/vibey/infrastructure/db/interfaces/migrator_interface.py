# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for bringing one database's schema up to date.

Mirrors `vibey/infrastructure/db/migrator.py` (ADR-0016). Interfaces declare;
they never consume. The seam names the asyncpg connection and the `Migration`
record it is declared over, imported under TYPE_CHECKING so the module has no
runtime dependency on the code that implements it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg

    from vibey.infrastructure.db.migrator import Migration

    type OwnedConnection = asyncpg.pool.PoolConnectionProxy | asyncpg.Connection


@runtime_checkable
class MigratorInterface(Protocol):
    """Applies pending migrations, serialized against every other process
    migrating the same database.

    The serialization is part of the contract, not an implementation detail:
    `build_app()` runs this on every start, and replicas start together.
    """

    async def apply(
        self,
        conn: OwnedConnection,
        migrations: tuple[Migration, ...],
        *,
        check_only: bool = False,
    ) -> tuple[str, ...]:
        """Apply what is pending on `conn` -- a connection with no open
        transaction -- and return the versions applied by this call (empty in
        `check_only` mode, which verifies checksums and applies nothing)."""
        ...
