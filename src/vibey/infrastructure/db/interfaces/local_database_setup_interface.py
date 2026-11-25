# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for making a local vibey database (`vibey install --database`).

Mirrors `vibey/infrastructure/db/local_database_setup.py` (ADR-0016, ADR-0055). Interfaces
declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg

    from vibey.infrastructure.db.local_database_setup import LocalDatabaseReport


@runtime_checkable
class LocalDatabaseSetupInterface(Protocol):
    def apply(self) -> LocalDatabaseReport:
        """Make the roles and the database if missing, keep their passwords, migrate; again
        and again with the same result."""
        ...


@runtime_checkable
class PassfileConnectorInterface(Protocol):
    async def __call__(self, dsn: str) -> asyncpg.Connection:
        """Connect with `dsn`, the password read from one password file."""
        ...
