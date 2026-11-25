# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey install --database` against a real PostgreSQL, through a real `psql`.

The test server's own administrator stands in for the local one. The roles and the database
are named for this test alone and dropped after it, and the password file is the test's own:
nothing of the person's `~/.pgpass` is read or written.
"""

import asyncio
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit
from uuid import uuid4

import asyncpg
import pytest

from tests.db_roles import ClusterParameterAclLock
from vibey.domain.local_database import LocalDatabaseNames, PgPass, PgPassEntry
from vibey.infrastructure.db.local_database_setup import LocalDatabaseSetup
from vibey.infrastructure.db.pgpass_file import PgPassFile
from vibey.infrastructure.db.postgres_admin import PostgresAdmin

pytestmark = pytest.mark.skipif(shutil.which("psql") is None, reason="psql is not installed")


async def _drop(admin_dsn: str, names: LocalDatabaseNames) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            names.database,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{names.database}"')
        for role in names.roles:
            await conn.execute(f'DROP ROLE IF EXISTS "{role}"')
    finally:
        await conn.close()


async def test_a_local_database_is_made_migrated_guarded_and_made_again_unchanged(
    database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = urlsplit(database_url)
    host, port = server.hostname or "localhost", server.port or 5432
    monkeypatch.setenv("PGHOST", host)
    monkeypatch.setenv("PGPORT", str(port))
    if server.username:
        monkeypatch.setenv("PGUSER", unquote(server.username))
    if server.password:
        # psql reads the administrator's password from a file of the test's own, so the
        # person's ~/.pgpass is never touched (and PGPASSWORD, which asyncpg would try
        # for every role, is never set).
        admin_file = tmp_path / "admin.pgpass"
        admin_file.write_text(
            PgPass().with_entry(
                "", PgPassEntry("*", "*", "*", unquote(server.username or ""), server.password)
            )
        )
        admin_file.chmod(0o600)
        monkeypatch.setenv("PGPASSFILE", str(admin_file))

    suffix = uuid4().hex[:10]
    names = LocalDatabaseNames(
        f"vibey_it_{suffix}", f"vibey_it_o_{suffix}", f"vibey_it_a_{suffix}", host, port
    )
    pgpass = PgPassFile(environ={"PGPASSFILE": str(tmp_path / "vibey.pgpass")})
    admin_dsn = database_url.rsplit("/", 1)[0] + "/postgres"

    def setup() -> LocalDatabaseSetup:
        return LocalDatabaseSetup(admin=PostgresAdmin(("psql",)), pgpass=pgpass, names=names)

    try:
        async with ClusterParameterAclLock.held():
            first = await asyncio.to_thread(setup().apply)
            again = await asyncio.to_thread(setup().apply)

        assert first.created_roles == names.roles and first.database_created
        assert first.migration.applied, "a new database gets every migration"
        assert first.migration.guard is not None and first.migration.guard.in_force, (
            first.migration.guard.describe()
        )
        assert again.created_roles == () and not again.database_created
        assert again.migration.applied == ()
        assert again.migration.guard is not None and again.migration.guard.in_force

        # The password-free DSN connects with the file alone, as the application role.
        conn = await asyncpg.connect(names.app_dsn, passfile=str(pgpass.path()))
        try:
            assert await conn.fetchval("SELECT current_user") == names.app_role
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute("DELETE FROM event")
        finally:
            await conn.close()
        assert oct(pgpass.path().stat().st_mode & 0o777) == "0o600"
        assert len(PgPass().entries(pgpass.read())) == 2  # the second run added nothing
    finally:
        await _drop(admin_dsn, names)
