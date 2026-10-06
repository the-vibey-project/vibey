# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`PostgresStateStore` against a real, migrated database (ADR-0086).

The store runs as the schema's owner: the sync writes tables the application role may not
(ADR-0055). Every table the migrations create is either synced or named as not synced, so
a migration that adds one without deciding fails here.
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.bootstrap import migrations_dir
from vibey.domain.state_sync import (
    NOT_SYNCED,
    TABLES,
    RowChange,
    Snapshot,
    SnapshotDiff,
    SnapshotDiffer,
    StateMoved,
)
from vibey.infrastructure.db.migrator import apply_migrations, discover_migrations
from vibey.infrastructure.state.postgres_state_store import PostgresStateStore, quote

pytestmark = pytest.mark.asyncio

CORRELATION = "00000000-0000-0000-0000-0000000000c0"


async def _seed(conn: asyncpg.Connection) -> UUID:
    """A row in every synced table, with the shapes that are easy to lose on the way:
    exact decimals, floats, arrays, jsonb, a self-reference, a reserved column name."""
    pid = UUID(
        str(
            await conn.fetchval(
                "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, $3::jsonb) "
                "RETURNING id",
                "demo",
                "/repos/demo",
                json.dumps({"budget": {"usd": 12.5}, "note": "ü"}),
            )
        )
    )
    for n in range(3):
        await conn.fetchval(
            "SELECT append_event($1, 1, 'design', 'Note', NULL, NULL, NULL, $2, 'trusted', "
            "$3::timestamptz, $4::jsonb, $5)",
            pid,
            UUID(CORRELATION),
            datetime.fromisoformat(f"2026-10-06T12:00:0{n}.12345+00:00"),
            json.dumps({"n": n, "cost": 0.1, "exact": 1.50}),
            f"digest-{n}",
        )
    job, other = uuid4(), uuid4()
    for jid, key in ((job, "k1"), (other, "k2")):
        await conn.execute(
            "INSERT INTO job (id, project_id, cycle, phase, kind, idempotency_key, bump_seq) "
            "VALUES ($1, $2, 1, 'build', 'implement', $3, nextval('job_bump_seq'))",
            jid,
            pid,
            key,
        )
    await conn.execute("INSERT INTO job_dependency VALUES ($1, $2)", job, other)
    await conn.execute(
        "INSERT INTO work_item (item_id, project_id, cycle, title, acceptance_ids, depends_on) "
        "VALUES ('W1', $1, 1, 'a title', ARRAY['AC-1','AC-2'], ARRAY[]::text[])",
        pid,
    )
    for item, superseded in (("Q2", None), ("Q1", "Q2")):
        await conn.execute(
            "INSERT INTO open_item (item_id, project_id, kind, opened_seq, superseded_by, body, "
            "normalized) VALUES ($1, $2, 'question', 1, $3, '{}'::jsonb, $1)",
            item,
            pid,
            superseded,
        )
    await conn.execute(
        "INSERT INTO handoff (project_id, cycle, phase, job_id, to_engine, reason, from_seq, "
        "to_seq, range_digest, envelope, gate_mode) VALUES ($1, 1, 'build', $2, 'codexloop', "
        "'credits', 1, 3, 'd', '{}'::jsonb, 'compact')",
        pid,
        job,
    )
    await conn.execute(
        "INSERT INTO engine_health (project_id, engine_id, ewma_failure, cost_usd_cycle) "
        "VALUES ($1, 'claudeloop', 0.1, 3.1416)",
        pid,
    )
    await conn.execute(
        'INSERT INTO rotation_cursor (project_id, engine_id, "order") VALUES ($1, $2, 1)',
        pid,
        "claudeloop",
    )
    await conn.execute(
        "INSERT INTO human_gate (project_id, job_id, kind, prompt) VALUES ($1, $2, 'q', 'p')",
        pid,
        job,
    )
    await conn.execute(
        "INSERT INTO artifact (project_id, cycle, kind, path, digest, seq) "
        "VALUES ($1, 1, 'spec', 'spec.md', 'd', 1)",
        pid,
    )
    await conn.execute(
        "INSERT INTO budget_ledger (project_id, cycle, phase, engine_id, dollars) "
        "VALUES ($1, 1, 'build', 'claudeloop', 1.2300)",
        pid,
    )
    await conn.execute(
        "INSERT INTO triaged_ticket (repository, issue_number, title, issue_url, priority_rank, "
        "bump_seq, project_id) VALUES ('o/r', 7, 't', 'https://github.com/o/r/issues/7', 1, "
        "nextval('triaged_ticket_bump_seq'), $1)",
        pid,
    )
    return pid


async def _wipe(conn: asyncpg.Connection) -> None:
    await conn.execute("DROP SCHEMA public CASCADE")
    await conn.execute("CREATE SCHEMA public")
    await apply_migrations(conn, discover_migrations(migrations_dir()))


async def test_every_table_the_migrations_make_is_synced_or_named_as_not(
    owner_pool: asyncpg.Pool,
) -> None:
    async with owner_pool.acquire() as conn:
        found = {
            str(r["relname"])
            for r in await conn.fetch(
                "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
                "AND relkind IN ('r', 'p') AND NOT relispartition"
            )
        }
    assert found == {spec.name for spec in TABLES} | NOT_SYNCED


async def test_a_snapshot_restored_into_an_empty_database_reads_back_the_same(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url)
    async with owner_pool.acquire() as conn:
        pid = await _seed(conn)
    before = await store.snapshot()
    assert before.row_count == 17
    row = next(iter(before.rows("engine_health").values()))
    assert row["cost_usd_cycle"] == Decimal("3.1416")
    assert isinstance(row["ewma_failure"], Decimal)

    async with owner_pool.acquire() as conn:
        await _wipe(conn)
    assert await store.is_empty()
    empty = await store.snapshot()
    await store.apply(SnapshotDiffer().diff(empty, before))

    after = await store.snapshot()
    assert after == before
    async with owner_pool.acquire() as conn:
        # The ledger, the queue's bump order and the triage order go on from where they were.
        assert await conn.fetchval("SELECT next_seq FROM event_seq WHERE project_id = $1", pid) == 4
        assert await conn.fetchval("SELECT nextval('job_bump_seq')") == 3
        assert await conn.fetchval("SELECT nextval('triaged_ticket_bump_seq')") == 2
        assert (
            await conn.fetchval(
                "SELECT append_event($1, 1, 'design', 'Note', NULL, NULL, NULL, $2, 'trusted', "
                "'{}'::jsonb, 'd')",
                pid,
                UUID(CORRELATION),
            )
            == 4
        )
        assert (
            await conn.fetchval("SELECT superseded_by FROM open_item WHERE item_id = 'Q1'") == "Q2"
        )


async def test_an_apply_over_a_row_that_changed_since_the_read_writes_nothing(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url)
    async with owner_pool.acquire() as conn:
        pid = await _seed(conn)
    read = await store.snapshot()
    wanted = _with(read, "project", name="renamed")
    async with owner_pool.acquire() as conn:
        await conn.execute("UPDATE project SET name = 'a worker wrote this' WHERE id = $1", pid)

    with pytest.raises(StateMoved, match="project"):
        await store.apply(SnapshotDiffer().diff(read, wanted))

    async with owner_pool.acquire() as conn:
        assert await conn.fetchval("SELECT name FROM project") == "a worker wrote this"


async def test_rows_are_updated_and_deleted_and_a_key_only_table_is_left_alone(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url)
    async with owner_pool.acquire() as conn:
        await _seed(conn)
    read = await store.snapshot()
    gone = next(iter(read.rows("job_dependency")))
    tables = {name: dict(rows) for name, rows in read.tables.items()}
    del tables["job_dependency"][gone]
    target = _with(Snapshot(read.schema, tables), "project", name="renamed")
    # A dependency already there is written again with nothing to update.
    again = SnapshotDiff(
        (
            RowChange(
                "job_dependency",
                gone,
                read.rows("job_dependency")[gone],
                read.rows("job_dependency")[gone],
            ),
        )
    )
    await store.apply(again)

    await store.apply(SnapshotDiffer().diff(read, target))

    assert await store.snapshot() == target
    await store.apply(SnapshotDiff())


async def test_a_table_held_by_a_writer_past_the_lock_timeout_is_a_merge_again(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url, lock_timeout_ms=50)
    async with owner_pool.acquire() as conn:
        await _seed(conn)
    read = await store.snapshot()
    async with owner_pool.acquire() as holder, holder.transaction():
        await holder.execute("LOCK TABLE project IN ROW EXCLUSIVE MODE")
        with pytest.raises(StateMoved, match="busy"):
            await store.apply(SnapshotDiffer().diff(read, _with(read, "project", name="x")))


async def test_a_generated_column_is_neither_read_nor_written(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url)
    async with owner_pool.acquire() as conn:
        await _seed(conn)
        await conn.execute(
            "ALTER TABLE artifact ADD COLUMN loud text GENERATED ALWAYS AS (upper(path)) STORED"
        )
    read = await store.snapshot()
    assert all("loud" not in row for row in read.rows("artifact").values())
    async with owner_pool.acquire() as conn:
        await conn.execute("DELETE FROM artifact")
    await store.apply(SnapshotDiffer().diff(_without(read, "artifact"), read))
    async with owner_pool.acquire() as conn:
        assert await conn.fetchval("SELECT loud FROM artifact") == "SPEC.MD"


async def test_the_watermark_is_recorded_moved_and_forgotten(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url)
    assert await store.base("o/r:vibey-state") is None
    await store.set_base("o/r:vibey-state", "a" * 40)
    await store.set_base("o/r:vibey-state", "a" * 40)
    await store.set_base("o/r:vibey-state", "b" * 40)
    assert await store.base("o/r:vibey-state") == "b" * 40
    await store.set_base("o/r:vibey-state", None)
    assert await store.base("o/r:vibey-state") is None


async def test_a_database_holding_any_synced_row_is_not_empty(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    store = PostgresStateStore(database_url)
    assert await store.is_empty()
    async with owner_pool.acquire() as conn:
        await _seed(conn)
    assert not await store.is_empty()


async def test_the_store_refuses_no_database_and_no_lock_timeout() -> None:
    with pytest.raises(ValueError, match="VIBEY_STATE_PG_URL"):
        PostgresStateStore("")
    with pytest.raises(ValueError, match="lock timeout"):
        PostgresStateStore("postgresql://x", lock_timeout_ms=0)
    assert quote('a"b') == '"a""b"'


async def test_two_syncs_applying_at_once_serialise_on_the_tables(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    async with owner_pool.acquire() as conn:
        await _seed(conn)
    store = PostgresStateStore(database_url)
    read = await store.snapshot()
    first = SnapshotDiffer().diff(read, _with(read, "project", name="first"))
    second = SnapshotDiffer().diff(read, _with(read, "project", name="second"))
    results = await asyncio.gather(store.apply(first), store.apply(second), return_exceptions=True)
    assert sum(isinstance(r, StateMoved) for r in results) == 1


def _with(snapshot: Snapshot, table: str, **values: object) -> Snapshot:
    tables = {name: dict(rows) for name, rows in snapshot.tables.items()}
    key, row = next(iter(tables[table].items()))
    tables[table][key] = {**row, **values}  # type: ignore[dict-item]
    return Snapshot(snapshot.schema, tables)


def _without(snapshot: Snapshot, table: str) -> Snapshot:
    return Snapshot(
        snapshot.schema, {name: rows for name, rows in snapshot.tables.items() if name != table}
    )
