# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for keeping the ledger append-only by the database.

Mirrors `vibey/infrastructure/db/ledger_guard.py` (ADR-0016, ADR-0055). Interfaces
declare; they never consume.
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.infrastructure.db.migrator import OwnedConnection

if TYPE_CHECKING:  # pragma: no cover - typing only
    from vibey.infrastructure.db.ledger_guard import AppRoleGrants, LedgerGuardStatus


@runtime_checkable
class RoleIdentifierInterface(Protocol):
    """Quotes a role or relation name for DDL."""

    @staticmethod
    def quote(name: str) -> str:
        """`name` as a quoted identifier; raises ValueError on an unusable one."""
        ...


@runtime_checkable
class DatabaseEndpointsInterface(Protocol):
    """The application role's DSN and, on a split install, the owner's."""

    @property
    def app_url(self) -> str: ...

    @property
    def migrate_url(self) -> str | None: ...

    @property
    def app_role(self) -> str | None:
        """The role the application DSN names, when it names one."""
        ...

    @property
    def app_password(self) -> str | None: ...


@runtime_checkable
class LedgerGuardInspectorInterface(Protocol):
    """Reports whether the connecting role can rewrite the ledger."""

    async def inspect(self, conn: OwnedConnection) -> "LedgerGuardStatus":
        """The guard as `conn`'s role sees it: in force, or every reason it is not."""
        ...


@runtime_checkable
class DatabaseRoleReconcilerInterface(Protocol):
    """Makes the application role's privileges exactly the declared ones."""

    @property
    def grants(self) -> "AppRoleGrants": ...

    async def reconcile(
        self, owner: OwnedConnection, *, app_role: str, app_password: str | None = None
    ) -> None:
        """On the owner's connection: create `app_role` if it is missing and a password
        is given, refuse one that is a superuser or the owner, then revoke everything
        and grant exactly the declared privileges."""
        ...
