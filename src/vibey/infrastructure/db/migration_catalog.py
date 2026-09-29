# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the schema's migrations live, and the refusal to migrate from none of them.

The SQL is package data: it ships in `vibey/infrastructure/db/migrations/`, beside the
code that applies it, so a source checkout, the container image and a wheel installed
from PyPI all read the same files from the same place. It used to live at the repository
root and be found by walking up from `bootstrap.py`. That worked from a checkout and from
the image -- whose Dockerfile copied the directory by hand -- and nowhere else: the
published wheel carried no `.sql` at all, so `vibey migrate` on a `pip install` found
nothing, printed `applied 0 migration(s)`, and left an empty schema behind it.

That is the second half of the fix. An empty set of migrations is not a schema that is up
to date, it is a missing install, and `migrations()` says so by raising rather than
returning `()` for the caller to apply as nothing. Automation that reports success it
did not observe is a liability wearing its clothes (sub-doctrine 12.e).
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import ClassVar

from vibey.domain.errors import VibeyError
from vibey.infrastructure.db.migrator import Migration, discover_migrations


class NoMigrationsFound(VibeyError):
    """The migrations directory holds no `.sql`: the install is incomplete."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        super().__init__(
            f"no migrations found at {directory}: this install is missing the schema's "
            "SQL, so there is nothing to apply and no schema to verify. Reinstall "
            "vibey-engine; an empty directory is never reported as a migrated database"
        )


class MigrationCatalog:
    """The migrations one directory holds, in the order they apply.

    The directory is a constructor argument, not a constant: `packaged()` names the one
    the distribution ships, and anything else -- a test's scratch directory, an adopter's
    own layout -- passes its own.
    """

    PACKAGE: ClassVar[str] = "vibey.infrastructure.db"
    DIRECTORY_NAME: ClassVar[str] = "migrations"

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    @classmethod
    def packaged(cls) -> MigrationCatalog:
        """The migrations this distribution ships, resolved through the import system.

        `importlib.resources` rather than `__file__` arithmetic: it asks the package
        where it was imported from, which is the same answer for an editable checkout,
        the image's venv and a wheel in site-packages.
        """
        return cls(Path(str(files(cls.PACKAGE) / cls.DIRECTORY_NAME)))

    @property
    def directory(self) -> Path:
        return self._directory

    def migrations(self) -> tuple[Migration, ...]:
        """Every migration in the directory, or `NoMigrationsFound` when there are none."""
        found = discover_migrations(self._directory)
        if not found:
            raise NoMigrationsFound(self._directory)
        return found
