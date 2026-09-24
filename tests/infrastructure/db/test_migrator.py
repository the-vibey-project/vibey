# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import hashlib
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio

from vibey.infrastructure.db.interfaces import MigratorInterface
from vibey.infrastructure.db.migrator import (
    InvalidMigrationLockTimeout,
    MigrationChecksumError,
    MigrationInsideTransaction,
    MigrationLockTimeout,
    PostgresMigrator,
    apply_migrations,
    discover_migrations,
)

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"
LOCK_KEY = PostgresMigrator.LOCK_KEY


def _write_migration(tmp_path: Path, name: str, sql: str) -> Path:
    path = tmp_path / name
    path.write_text(sql)
    return path


async def test_discover_migrations_returns_real_migrations_in_lexical_order() -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)

    versions = [m.version for m in migrations]
    assert versions == sorted(versions)
    assert versions[0] == "0001_project"
    assert "0008_human_gate_artifact_budget" in versions


async def test_apply_all_real_migrations_to_a_fresh_database(pg_conn: asyncpg.Connection) -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)

    applied = await apply_migrations(pg_conn, migrations)

    assert applied == tuple(m.version for m in migrations)

    tables = await pg_conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    table_names = {row["tablename"] for row in tables}
    for expected in (
        "project",
        "event",
        "job",
        "job_dependency",
        "work_item",
        "open_item",
        "handoff",
        "engine_health",
        "rotation_cursor",
        "human_gate",
        "artifact",
        "budget_ledger",
        "schema_migration",
    ):
        assert expected in table_names


async def test_event_partition_migration_preserves_append_only_live_schema(
    pg_conn: asyncpg.Connection,
) -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)
    await apply_migrations(pg_conn, tuple(m for m in migrations if m.version < "0013"))
    project_id = await pg_conn.fetchval(
        "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) RETURNING id",
        "partitioned",
        "/tmp/partitioned",
    )
    old_seq = await pg_conn.fetchval(
        """
        SELECT append_event(
            $1, 1, 'build'::phase, 'BeforePartition', NULL, NULL, NULL, $1,
            'agent'::provenance, '{}'::jsonb, 'before'
        )
        """,
        project_id,
    )
    assert old_seq == 1

    await apply_migrations(pg_conn, migrations)
    assert (
        await pg_conn.fetchval("SELECT relkind FROM pg_class WHERE oid = 'event'::regclass") == b"p"
    )
    assert (
        await pg_conn.fetchval(
            "SELECT digest FROM event WHERE project_id = $1 AND seq = 1", project_id
        )
        == "before"
    )

    seq = await pg_conn.fetchval(
        """
        SELECT append_event(
            $1, 1, 'build'::phase, 'Partitioned', NULL, NULL, NULL, $1,
            'agent'::provenance, '{}'::jsonb, 'digest'
        )
        """,
        project_id,
    )
    assert seq == 2
    assert (
        await pg_conn.fetchval("SELECT count(*) FROM event WHERE project_id = $1", project_id) == 2
    )

    # Append-only survives the swap: since 0016 by triggers that refuse, loudly.
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="append-only"):
        await pg_conn.execute(
            "UPDATE event SET digest = 'changed' WHERE project_id = $1", project_id
        )
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="append-only"):
        await pg_conn.execute("DELETE FROM event WHERE project_id = $1", project_id)
    assert (
        await pg_conn.fetchval(
            "SELECT digest FROM event WHERE project_id = $1 AND seq = 2", project_id
        )
        == "digest"
    )


async def test_applying_migrations_twice_is_a_no_op(pg_conn: asyncpg.Connection) -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)

    first = await apply_migrations(pg_conn, migrations)
    second = await apply_migrations(pg_conn, migrations)

    assert first == tuple(m.version for m in migrations)
    assert second == ()


async def test_applying_migrations_over_seeded_fixture_data(pg_conn: asyncpg.Connection) -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)
    await apply_migrations(pg_conn, migrations)

    project_id = await pg_conn.fetchval(
        "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, $3::jsonb) RETURNING id",
        "demo",
        "/tmp/demo",
        "{}",
    )
    assert project_id is not None

    # Re-applying over a database with real rows must still be a no-op, not
    # a destructive re-run.
    applied_again = await apply_migrations(pg_conn, migrations)
    assert applied_again == ()

    name = await pg_conn.fetchval("SELECT name FROM project WHERE id = $1", project_id)
    assert name == "demo"


async def test_edited_migration_fails_the_checksum_guard(
    pg_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    original_sql = "CREATE TABLE t (id serial PRIMARY KEY);"
    path = _write_migration(tmp_path, "0001_t.sql", original_sql)
    migrations = discover_migrations(tmp_path)
    await apply_migrations(pg_conn, migrations)

    # Edit the already-applied migration on disk.
    path.write_text("CREATE TABLE t (id serial PRIMARY KEY, extra text);")
    edited_migrations = discover_migrations(tmp_path)

    with pytest.raises(MigrationChecksumError) as exc_info:
        await apply_migrations(pg_conn, edited_migrations)

    assert exc_info.value.version == "0001_t"


async def test_check_only_mode_does_not_apply_pending_migrations(
    pg_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    _write_migration(tmp_path, "0001_t.sql", "CREATE TABLE t (id serial PRIMARY KEY);")
    migrations = discover_migrations(tmp_path)

    applied = await apply_migrations(pg_conn, migrations, check_only=True)

    assert applied == ()
    exists = await pg_conn.fetchval("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 't')")
    assert exists is False


async def test_check_only_mode_still_catches_a_checksum_mismatch(
    pg_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    path = _write_migration(tmp_path, "0001_t.sql", "CREATE TABLE t (id serial PRIMARY KEY);")
    migrations = discover_migrations(tmp_path)
    await apply_migrations(pg_conn, migrations)

    path.write_text("CREATE TABLE t (id serial PRIMARY KEY, extra text);")
    edited_migrations = discover_migrations(tmp_path)

    with pytest.raises(MigrationChecksumError):
        await apply_migrations(pg_conn, edited_migrations, check_only=True)


# --- The migration lock (#114): replicas that start together take turns. ---


@pytest_asyncio.fixture
async def other_conn(
    pg_conn: asyncpg.Connection, database_url: str
) -> AsyncIterator[asyncpg.Connection]:
    """A second session on the same (freshly emptied) database: another pod."""
    conn = await asyncpg.connect(database_url)
    try:
        yield conn
    finally:
        await conn.close()


async def _backend_pid(conn: asyncpg.Connection) -> int:
    pid = await conn.fetchval("SELECT pg_backend_pid()")
    assert isinstance(pid, int)
    return pid


async def _until_waiting_on_an_advisory_lock(observer: asyncpg.Connection, pid: int) -> None:
    for _ in range(400):
        waiting = await observer.fetchval(
            "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = $1 AND NOT granted",
            pid,
        )
        if waiting:
            return
        await asyncio.sleep(0.025)
    pytest.fail(f"backend {pid} never queued on the migration lock")


async def _table_exists(conn: asyncpg.Connection, name: str) -> bool:
    exists = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = $1)",
        name,
    )
    return bool(exists)


def test_the_lock_key_is_pinned_and_derived_the_way_the_integrate_key_is() -> None:
    # A rolling upgrade runs old and new releases against one database: if the
    # key moved between them they would stop excluding each other, silently.
    derived = int.from_bytes(hashlib.sha256(b"vibey.migrate").digest()[:8], "big", signed=True)
    assert LOCK_KEY == -1686359016981790252
    assert derived == LOCK_KEY
    assert -(2**63) <= LOCK_KEY < 2**63


def test_the_migrator_is_its_declared_seam() -> None:
    assert isinstance(PostgresMigrator(), MigratorInterface)


async def test_two_starts_racing_on_one_database_apply_each_migration_once(
    pg_conn: asyncpg.Connection, other_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    # Slow enough that, unserialized, both starts read an empty applied set and
    # both try to create the table: without the lock this raises instead.
    _write_migration(tmp_path, "0001_slow.sql", "CREATE TABLE t (id int); SELECT pg_sleep(0.5);")
    migrations = discover_migrations(tmp_path)

    results = await asyncio.gather(
        apply_migrations(pg_conn, migrations),
        apply_migrations(other_conn, migrations),
    )

    assert sorted(results) == [(), ("0001_slow",)]
    rows = await pg_conn.fetch("SELECT version FROM schema_migration")
    assert [row["version"] for row in rows] == ["0001_slow"]


async def test_a_second_start_waits_for_the_first_then_finds_the_schema_settled(
    pg_conn: asyncpg.Connection, other_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    _write_migration(tmp_path, "0001_t.sql", "CREATE TABLE t (id int);")
    migrations = discover_migrations(tmp_path)
    waiter_pid = await _backend_pid(other_conn)
    await pg_conn.execute("SELECT pg_advisory_lock($1)", LOCK_KEY)

    waiter = asyncio.create_task(
        PostgresMigrator(lock_timeout_seconds=0).apply(other_conn, migrations)
    )
    try:
        await _until_waiting_on_an_advisory_lock(pg_conn, waiter_pid)
        assert not waiter.done()
        # It is queued before touching anything: not even schema_migration.
        assert await _table_exists(pg_conn, "schema_migration") is False
    finally:
        await pg_conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)

    assert await asyncio.wait_for(waiter, timeout=10) == ("0001_t",)


@pytest.mark.parametrize("wait", [0.2, 0.0001], ids=["bounded", "sub-millisecond-rounds-up"])
async def test_a_wedged_holder_fails_the_waiter_loudly_and_names_it(
    pg_conn: asyncpg.Connection, other_conn: asyncpg.Connection, tmp_path: Path, wait: float
) -> None:
    # 0.0001s is the case that matters: rounded down it would be 0ms, which
    # Postgres reads as "wait forever", and only the 10s guard would end it.
    _write_migration(tmp_path, "0001_t.sql", "CREATE TABLE t (id int);")
    migrations = discover_migrations(tmp_path)
    await pg_conn.execute("SELECT pg_advisory_lock($1)", LOCK_KEY)
    holder = await _backend_pid(pg_conn)

    try:
        with pytest.raises(MigrationLockTimeout) as exc_info:
            await asyncio.wait_for(
                PostgresMigrator(lock_timeout_seconds=wait).apply(other_conn, migrations),
                timeout=10,
            )
    finally:
        released = await pg_conn.fetchval("SELECT pg_advisory_unlock($1)", LOCK_KEY)

    assert released is True
    error = exc_info.value
    assert (error.key, error.timeout_seconds, error.holders) == (LOCK_KEY, wait, (holder,))
    assert str(holder) in str(error)
    assert PostgresMigrator.LOCK_TIMEOUT_ENV in str(error)
    # Nothing ran, and the waiter's session came back clean: no transaction
    # left open, no lock_timeout left behind for whatever it runs next.
    assert await _table_exists(pg_conn, "t") is False
    assert other_conn.is_in_transaction() is False
    assert await other_conn.fetchval("SHOW lock_timeout") == "0"


def test_the_timeout_names_no_holder_when_it_let_go_as_the_wait_ended() -> None:
    error = MigrationLockTimeout(LOCK_KEY, 1.5, ())

    assert "held by backend pid(s): none" in str(error)
    assert "1.5s" in str(error)


async def test_the_lock_is_released_after_a_run(
    pg_conn: asyncpg.Connection, other_conn: asyncpg.Connection
) -> None:
    await apply_migrations(pg_conn, discover_migrations(MIGRATIONS_DIR))

    assert await other_conn.fetchval("SELECT pg_try_advisory_lock($1)", LOCK_KEY) is True
    await other_conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)


async def test_the_lock_is_released_when_a_migration_fails(
    pg_conn: asyncpg.Connection, other_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    _write_migration(tmp_path, "0001_broken.sql", "SELECT * FROM no_such_table;")

    with pytest.raises(asyncpg.exceptions.UndefinedTableError):
        await apply_migrations(pg_conn, discover_migrations(tmp_path))

    # A failed migration must not wedge every later start behind it.
    assert await other_conn.fetchval("SELECT pg_try_advisory_lock($1)", LOCK_KEY) is True
    await other_conn.execute("SELECT pg_advisory_unlock($1)", LOCK_KEY)


async def test_migrations_do_not_run_under_the_lock_wait_bound(
    pg_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    # The bound is for waiting on another pod. A migration that itself waits
    # on a table lock must not inherit it and fail half-way through a rollout.
    _write_migration(
        tmp_path,
        "0001_seen.sql",
        "CREATE TABLE seen AS SELECT current_setting('lock_timeout') AS v;",
    )

    await PostgresMigrator(lock_timeout_seconds=7).apply(pg_conn, discover_migrations(tmp_path))

    assert await pg_conn.fetchval("SELECT v FROM seen") == "0"


async def test_a_connection_inside_a_transaction_is_refused(
    pg_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    # Inside an outer transaction nothing commits until after the lock is
    # released, so a second pod could read the old applied set anyway.
    _write_migration(tmp_path, "0001_t.sql", "CREATE TABLE t (id int);")

    async with pg_conn.transaction():
        with pytest.raises(MigrationInsideTransaction):
            await apply_migrations(pg_conn, discover_migrations(tmp_path))

    assert await _table_exists(pg_conn, "t") is False


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({}, PostgresMigrator.DEFAULT_LOCK_TIMEOUT_SECONDS),
        ({PostgresMigrator.LOCK_TIMEOUT_ENV: "   "}, PostgresMigrator.DEFAULT_LOCK_TIMEOUT_SECONDS),
        ({PostgresMigrator.LOCK_TIMEOUT_ENV: " 12.5 "}, 12.5),
        ({PostgresMigrator.LOCK_TIMEOUT_ENV: "0"}, 0.0),
        ({PostgresMigrator.LOCK_TIMEOUT_ENV: "2147483.647"}, 2147483.647),
    ],
    ids=["unset", "blank", "fractional", "zero-waits-indefinitely", "postgres-ceiling"],
)
def test_the_wait_comes_from_the_environment(environ: dict[str, str], expected: float) -> None:
    assert PostgresMigrator.from_environ(environ).lock_timeout_seconds == expected


@pytest.mark.parametrize("raw", ["soon", "-1", "nan", "inf", "2147483.648", "1e400"])
def test_an_unusable_wait_fails_loudly_rather_than_falling_back(raw: str) -> None:
    with pytest.raises(InvalidMigrationLockTimeout) as exc_info:
        PostgresMigrator.from_environ({PostgresMigrator.LOCK_TIMEOUT_ENV: raw})

    assert PostgresMigrator.LOCK_TIMEOUT_ENV in str(exc_info.value)


def test_the_constructor_refuses_a_negative_wait() -> None:
    with pytest.raises(InvalidMigrationLockTimeout):
        PostgresMigrator(lock_timeout_seconds=-0.5)
