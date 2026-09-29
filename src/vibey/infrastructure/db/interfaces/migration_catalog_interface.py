# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for finding the schema's migrations.

Mirrors `vibey/infrastructure/db/migration_catalog.py` (ADR-0016). Interfaces declare;
they never consume. `Migration` is imported under TYPE_CHECKING so the module has no
runtime dependency on the code that implements it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from vibey.infrastructure.db.migrator import Migration


@runtime_checkable
class MigrationCatalogInterface(Protocol):
    """The migrations one directory holds.

    An empty directory is a refusal, not an empty tuple: a caller that applied `()`
    would report a database with no schema as migrated.
    """

    @property
    def directory(self) -> Path:
        """The directory the migrations are read from."""
        ...

    def migrations(self) -> tuple[Migration, ...]:
        """Every migration, in apply order; raises `NoMigrationsFound` when there are none."""
        ...
