# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The test harness's two database roles (ADR-0055).

The owner is whoever ``VIBEY_TEST_DATABASE_URL`` names. The application role is
``vibey_test_app`` unless ``VIBEY_TEST_APP_ROLE`` renames it; set it empty to run the
suite as one role, the way a single-DSN install does.
"""

import asyncio
import fcntl
import hashlib
import os
import tempfile
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import asyncpg

from vibey.infrastructure.db.ledger_guard import DatabaseRoleReconciler


class ClusterParameterAclLock:
    """Serializes, across every xdist worker on this machine, what grants or revokes a
    parameter privilege for the shared application role.

    `pg_parameter_acl` and roles exist once per server, not per database, and every worker
    shares the one application role. So one worker's reconcile (`REVOKE SET ON PARAMETER
    session_replication_role FROM PUBLIC, <app role>`) strips a grant another worker's test
    made a moment earlier -- `test_finding_8` failed four ways on 2026-10-01 (three server
    errors on PostgreSQL 16/18 and, on 17, an inspector that found the grant already gone).
    Workers are processes on one host, so an exclusive `flock` on a file named for the server
    covers them all. Reentrant within a process: the holder may reconcile while holding it.
    """

    _depth = 0
    _handle: int | None = None

    @staticmethod
    def _path() -> Path:
        server = os.environ.get("VIBEY_TEST_DATABASE_URL", "")
        digest = hashlib.sha256(server.encode()).hexdigest()[:16]
        return Path(tempfile.gettempdir()) / f"vibey-test-parameter-acl-{digest}.lock"

    @classmethod
    @asynccontextmanager
    async def held(cls) -> AsyncIterator[None]:
        if cls._depth == 0:
            handle = os.open(cls._path(), os.O_CREAT | os.O_RDWR, 0o600)
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    await asyncio.sleep(0.05)
            cls._handle = handle
        cls._depth += 1
        try:
            yield
        finally:
            cls._depth -= 1
            if cls._depth == 0 and cls._handle is not None:
                fcntl.flock(cls._handle, fcntl.LOCK_UN)
                os.close(cls._handle)
                cls._handle = None


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

    async def restore(self, owner_dsn: str, migrations_dir: object) -> None:
        """Bring this worker's database back to migrated-and-granted, as the owner.

        Some tests drop `public` and rebuild it as the owner, which drops the
        application role's grants with it. `build_app` no longer reconciles them (only
        `vibey migrate` holds the owner's DSN), so a test that runs as the application
        role after one of those puts them back first."""
        from pathlib import Path

        from vibey.infrastructure.db.migrator import apply_migrations, discover_migrations

        owner = await asyncpg.connect(owner_dsn)
        try:
            await apply_migrations(owner, discover_migrations(Path(str(migrations_dir))))
            await self.grant(owner)
        finally:
            await owner.close()

    async def grant(self, owner: asyncpg.Connection) -> None:
        """The declared grants, exactly as `vibey migrate` makes them."""
        if self.split:
            async with ClusterParameterAclLock.held():
                await DatabaseRoleReconciler().reconcile(owner, app_role=self.app_role)
