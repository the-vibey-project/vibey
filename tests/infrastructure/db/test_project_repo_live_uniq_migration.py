# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Migration 0021 applies on a database that already holds projects, and from then on an
abandoned project lets its checkout go while a live one still holds its own (live on
#963, where an abandoned project reserved `triaged-963` for ever)."""

import asyncpg
import pytest

from vibey.infrastructure.db.migration_catalog import MigrationCatalog
from vibey.infrastructure.db.migrator import apply_migrations, discover_migrations
from vibey.infrastructure.db.project_repository import LIVE_CHECKOUT_INDEX

MIGRATIONS = discover_migrations(MigrationCatalog.packaged().directory)
VERSION = "0021_project_repo_live_uniq"


async def _project(conn: asyncpg.Connection, name: str, path: str, phase: str) -> None:
    await conn.execute(
        "INSERT INTO project (name, repo_path, phase, config) VALUES ($1, $2, $3::phase, '{}')",
        name,
        path,
        phase,
    )


async def test_before_0021_an_abandoned_project_reserves_its_checkout(
    pg_conn: asyncpg.Connection,
) -> None:
    """The defect, pinned where it lived: under 0001's index the abandoned row still
    counts, so a fresh project in its checkout is refused."""
    await apply_migrations(pg_conn, tuple(m for m in MIGRATIONS if m.version < VERSION))
    await _project(pg_conn, "gone", "/work/triaged-963", "abandoned")

    with pytest.raises(asyncpg.exceptions.UniqueViolationError) as refused:
        await _project(pg_conn, "retry", "/work/triaged-963", "intake")

    assert refused.value.constraint_name == "project_repo_uniq"


async def test_0021_frees_an_abandoned_checkout_and_keeps_a_live_one_held(
    pg_conn: asyncpg.Connection,
) -> None:
    before = tuple(m for m in MIGRATIONS if m.version < VERSION)
    assert [m.version for m in MIGRATIONS if m.version >= VERSION][0] == VERSION
    await apply_migrations(pg_conn, before)
    await _project(pg_conn, "gone", "/work/abandoned", "abandoned")
    await _project(pg_conn, "live", "/work/live", "build")
    await _project(pg_conn, "finished", "/work/done", "done")

    applied = await apply_migrations(pg_conn, MIGRATIONS)

    assert VERSION in applied
    # Every row the old index admitted survives the new one untouched.
    assert await pg_conn.fetchval("SELECT count(*) FROM project") == 3
    await _project(pg_conn, "retry", "/work/abandoned", "intake")
    for path in ("/work/live", "/work/done"):
        with pytest.raises(asyncpg.exceptions.UniqueViolationError) as refused:
            await _project(pg_conn, "second", path, "intake")
        assert refused.value.constraint_name == LIVE_CHECKOUT_INDEX
    indexes = {
        row["indexname"]
        for row in await pg_conn.fetch(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'project'"
        )
    }
    assert LIVE_CHECKOUT_INDEX in indexes
    assert "project_repo_uniq" not in indexes


async def test_after_0021_a_retry_can_itself_be_abandoned_and_retried_again(
    pg_conn: asyncpg.Connection,
) -> None:
    """Any number of abandoned projects may share a checkout, beside at most one live."""
    await apply_migrations(pg_conn, MIGRATIONS)
    path = "/work/again"
    for name in ("one", "two", "three"):
        await _project(pg_conn, name, path, "abandoned")
    await _project(pg_conn, "live", path, "design")

    rows = await pg_conn.fetch(
        "SELECT name FROM project WHERE repo_path = $1 AND phase <> 'abandoned'", path
    )

    assert [row["name"] for row in rows] == ["live"]
