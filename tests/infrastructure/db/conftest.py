# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import getpass
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
import pytest_asyncio

from tests.db_roles import TestDatabaseRoles
from vibey.infrastructure.db.migrator import apply_migrations, discover_migrations

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        item.add_marker(pytest.mark.integration)


@pytest.fixture
def database_url() -> str:
    """This worker's database URL, read when a test runs and never at import.

    Point pytest straight at this directory and this conftest becomes an
    initial conftest. Pytest imports it before the root conftest's
    ``pytest_configure`` repoints ``VIBEY_TEST_DATABASE_URL`` at the worker's
    clone. A module-level read then captured the controller's database, and
    every xdist worker shared it, dropping ``public`` from under the others.
    """
    return os.environ.get(
        "VIBEY_TEST_DATABASE_URL",
        f"postgresql://{getpass.getuser()}@localhost:5432/vibey_test",
    )


@pytest_asyncio.fixture
async def pg_conn(database_url: str) -> AsyncIterator[asyncpg.Connection]:
    conn = await asyncpg.connect(database_url)
    await conn.execute("DROP SCHEMA public CASCADE")
    await conn.execute("CREATE SCHEMA public")
    try:
        yield conn
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def pg_pool(database_url: str) -> AsyncIterator[asyncpg.Pool]:
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
    assert pool is not None
    async with pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture
async def owner_pool(pg_pool: asyncpg.Pool) -> asyncpg.Pool:
    """The migrated schema, as its owner: for setting up or inspecting state the
    application itself never touches."""
    async with pg_pool.acquire() as conn:
        migrations = discover_migrations(MIGRATIONS_DIR)
        await apply_migrations(conn, migrations)
        await TestDatabaseRoles.from_environ(os.environ).grant(conn)
    return pg_pool


@pytest_asyncio.fixture
async def migrated_pool(owner_pool: asyncpg.Pool, database_url: str) -> AsyncIterator[asyncpg.Pool]:
    """The migrated schema, as the application role -- the grants production runs
    under (ADR-0055) -- so a repository query that needs an undeclared privilege
    fails here."""
    roles = TestDatabaseRoles.from_environ(os.environ)
    if not roles.split:
        yield owner_pool
        return
    pool = await asyncpg.create_pool(roles.app_dsn(database_url), min_size=1, max_size=10)
    assert pool is not None
    try:
        yield pool
    finally:
        await pool.close()


@pytest_asyncio.fixture
async def project_id(migrated_pool: asyncpg.Pool) -> UUID:
    async with migrated_pool.acquire() as conn:
        pid = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, $3::jsonb) RETURNING id",
            "demo",
            "/tmp/demo",
            "{}",
        )
        assert pid is not None
        return UUID(str(pid))
