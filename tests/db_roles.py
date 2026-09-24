# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The test harness's two database roles (ADR-0055).

The owner is whoever ``VIBEY_TEST_DATABASE_URL`` names. The application role is
``vibey_test_app`` unless ``VIBEY_TEST_APP_ROLE`` renames it; set it empty to run the
suite as one role, the way a single-DSN install does.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import quote, urlsplit, urlunsplit

import asyncpg

from vibey.infrastructure.db.ledger_guard import DatabaseRoleReconciler


@dataclass(frozen=True, slots=True)
class TestDatabaseRoles:
    __test__ = False  # not a test class, whatever its name

    app_role: str
    app_password: str

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> "TestDatabaseRoles":
        role = environ.get("VIBEY_TEST_APP_ROLE", "vibey_test_app").strip()
        return cls(app_role=role, app_password=role)

    @property
    def split(self) -> bool:
        return bool(self.app_role)

    def app_dsn(self, owner_dsn: str) -> str:
        """`owner_dsn` with the application role's credentials, or unchanged when the
        roles are not split."""
        if not self.split:
            return owner_dsn
        parts = urlsplit(owner_dsn)
        host = parts.hostname or ""
        netloc = f"{quote(self.app_role)}:{quote(self.app_password)}@{host}"
        if parts.port is not None:
            netloc += f":{parts.port}"
        return urlunsplit(parts._replace(netloc=netloc))

    async def ensure(self, admin: asyncpg.Connection) -> None:
        """Create the application role once per server; it never owns anything."""
        if not self.split:
            return
        if await admin.fetchval("SELECT 1 FROM pg_roles WHERE rolname = $1", self.app_role):
            return
        ddl = await admin.fetchval(
            "SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', $1::text, $2::text)",
            self.app_role,
            self.app_password,
        )
        await admin.execute(ddl)

    async def grant(self, owner: asyncpg.Connection) -> None:
        """The declared grants, exactly as `vibey migrate` makes them."""
        if self.split:
            await DatabaseRoleReconciler().reconcile(owner, app_role=self.app_role)
