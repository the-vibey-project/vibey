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


async def test_the_named_set_survives_and_an_orphan_leaves_the_lane(
    pg_conn: asyncpg.Connection,
) -> None:
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

    rows = {
        r["id"]: (r["bump_seq"] is not None, r["bump_named"])
        for r in await pg_conn.fetch("SELECT id, bump_seq, bump_named FROM job")
    }
    assert rows == {d: (True, False), b: (True, True), orphan: (False, False)}
    columns = {
        r["column_name"]
        for r in await pg_conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'job'"
        )
    }
    assert "bump_origin" not in columns
