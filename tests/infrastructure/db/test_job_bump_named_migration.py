# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Migration 0015 carries a queue bumped under 0014's `bump_origin` into the derived lane
(ADR-0054 item 6): the named set is what was bumped by name, and a pulled job no named
job still needs -- an orphan the per-bump rule could leave -- leaves the lane."""

from pathlib import Path
from uuid import UUID

import asyncpg

from vibey.infrastructure.db.migrator import apply_migrations, discover_migrations

MIGRATIONS = discover_migrations(Path(__file__).resolve().parents[3] / "migrations")


async def _job(conn: asyncpg.Connection, pid: UUID, key: str, state: str = "ready") -> UUID:
    job_id = await conn.fetchval(
        "INSERT INTO job (project_id, cycle, phase, kind, idempotency_key, state) "
        "VALUES ($1, 1, 'build', 'build.implement', $2, $3::job_state) RETURNING id",
        pid,
        key,
        state,
    )
    return UUID(str(job_id))


async def _bump(conn: asyncpg.Connection, job: UUID, origin: UUID) -> None:
    await conn.execute(
        "UPDATE job SET bump_seq = nextval('job_bump_seq'), bump_origin = $2 WHERE id = $1",
        job,
        origin,
    )


# Every column the 0014 release's `JobRowMapper.to_record` reads from a `job` row -- the
# mapper an old worker still runs while a rolling upgrade replaces it.
READ_BY_THE_0014_MAPPER = (
    "id", "project_id", "cycle", "phase", "kind", "state", "priority", "work_item_id",
    "payload", "requirement", "idempotency_key", "attempts", "max_attempts", "run_after",
    "lease_owner", "lease_expires_at", "assigned_engine", "last_error", "created_at",
    "updated_at", "bump_seq", "bump_origin",
)  # fmt: skip


async def _migrated_with_a_0014_lane(pg_conn: asyncpg.Connection) -> dict[str, UUID]:
    before = [m for m in MIGRATIONS if m.version <= "0014_job_bump"]
    await apply_migrations(pg_conn, before)
    pid = await pg_conn.fetchval(
        "INSERT INTO project (name, repo_path, config) VALUES ('m', '/tmp/m', '{}') RETURNING id"
    )
    d = await _job(pg_conn, pid, "d")
    b = await _job(pg_conn, pid, "b")
    orphan = await _job(pg_conn, pid, "orphan")
    await pg_conn.execute("INSERT INTO job_dependency VALUES ($1, $2)", b, d)
    await _bump(pg_conn, d, b)  # pulled in for b
    await _bump(pg_conn, b, b)  # b, by name
    await _bump(pg_conn, orphan, UUID(int=1))  # pulled for a job since un-bumped
    await apply_migrations(pg_conn, MIGRATIONS)
    return {"project": UUID(str(pid)), "d": d, "b": b, "orphan": orphan}


async def test_an_old_worker_still_reads_every_row_after_0015(
    pg_conn: asyncpg.Connection,
) -> None:
    """Finding 1: 0015 expands, it does not contract. An old worker mid-upgrade reads
    `bump_origin` from every `SELECT *` and `RETURNING *`; dropping it would crash-loop
    every old pod on its next claim."""
    await _migrated_with_a_0014_lane(pg_conn)

    for row in await pg_conn.fetch("SELECT * FROM job"):
        for column in READ_BY_THE_0014_MAPPER:
            row[column]  # an old mapper's read: raises KeyError if the column is gone
    claimed = await pg_conn.fetchrow(
        "UPDATE job SET state = 'leased', lease_owner = 'old', "
        "lease_expires_at = now() + interval '30 seconds' "
        "WHERE id = (SELECT id FROM job WHERE state = 'ready' LIMIT 1) RETURNING *"
    )
    assert claimed is not None
    assert set(READ_BY_THE_0014_MAPPER) <= set(claimed.keys())


async def test_0015_maps_the_named_set_and_changes_no_lane_membership(
    pg_conn: asyncpg.Connection,
) -> None:
    """Finding 3: a migration cannot write a faithful ledger event (the digest and the
    correlation id are the Python writer's), so 0015 changes no priority state. The
    orphan 0014 left stays in the lane until the project's next reorder request sweeps
    it -- recorded, as every correction is."""
    ids = await _migrated_with_a_0014_lane(pg_conn)

    rows = {
        r["id"]: (r["bump_seq"] is not None, r["bump_named"])
        for r in await pg_conn.fetch("SELECT id, bump_seq, bump_named FROM job")
    }
    assert rows == {
        ids["d"]: (True, False),
        ids["b"]: (True, True),
        ids["orphan"]: (True, False),
    }
    assert await pg_conn.fetchval("SELECT count(*) FROM event") == 0
