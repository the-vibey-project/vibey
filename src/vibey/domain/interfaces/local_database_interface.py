# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for a local vibey database's names and libpq's password-file format.

Mirrors `vibey/domain/local_database.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.local_database import PgPassEntry


@runtime_checkable
class LocalDatabaseNamesInterface(Protocol):
    database: str
    owner_role: str
    app_role: str
    host: str
    port: int

    @property
    def roles(self) -> tuple[str, str]:
        """The owner, then the application role."""
        ...

    def dsn(self, role: str) -> str:
        """The password-free DSN `role` connects with."""
        ...

    @property
    def owner_dsn(self) -> str:
        """The owner's DSN, for `vibey migrate` alone."""
        ...

    @property
    def app_dsn(self) -> str:
        """The application role's DSN (`VIBEY_PG_URL`)."""
        ...


@runtime_checkable
class PgPassInterface(Protocol):
    def entries(self, text: str) -> tuple[PgPassEntry, ...]:
        """Every well-formed line of a password file, in order."""
        ...

    def password_for(self, text: str, host: str, port: int, database: str, user: str) -> str | None:
        """The password libpq would use for that connection, or None."""
        ...

    def with_entry(self, text: str, entry: PgPassEntry) -> str:
        """The file's text with one more line at its end."""
        ...
