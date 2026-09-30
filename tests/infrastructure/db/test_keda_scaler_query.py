# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The KEDA scaler's SQL counts exactly the jobs a worker of that release can claim.

The chart's ScaledObject (deploy/helm/vibey/templates/keda-scaledobject.yaml) says it is
"deliberately identical in spirit to JobRepository.claim's SELECT arm". Nothing held it to
that, and it drifted: the scaler counted claimable jobs in EVERY project while a worker
claims only its own (`j.project_id = $3`), so another project's backlog scaled up workers
that could never take it. This binds the rendered SQL to the real schema and the real
claim, so the next drift fails here instead of in a cluster.

The SQL is read from the committed goldens rather than rendered, so this needs no helm;
the `chart` CI job is what keeps those goldens equal to what the chart renders
(deploy/helm/golden/render.sh). Module-level test functions rather than a class with an
interface beside it (ADR-0016), following tests/meta/: the rule is about production code.
"""

from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
import yaml

from vibey.infrastructure.db.job_repository import _CLAIMABLE, PostgresJobRepository
from vibey.infrastructure.db.project_repository import PostgresProjectRepository

GOLDEN = Path(__file__).resolve().parents[3] / "deploy" / "helm" / "golden"
# The project id the keda-project profile binds (render.sh's PROJECT).
BOUND = UUID("6f1c2a4e-0000-4000-8000-000000000000")
LEASE = timedelta(seconds=30)


def _scaler_query(profile: str) -> str:
    documents = yaml.safe_load_all((GOLDEN / f"{profile}.yaml").read_text(encoding="utf-8"))
    scaled = [d for d in documents if d and d.get("kind") == "ScaledObject"]
    assert len(scaled) == 1, f"{profile}: expected exactly one ScaledObject"
    query: str = scaled[0]["spec"]["triggers"][0]["metadata"]["query"]
    return query


async def _project(conn: asyncpg.Connection, pid: UUID, name: str, age: timedelta) -> None:
    await conn.execute(
        "INSERT INTO project (id, name, repo_path, config, created_at) "
        "VALUES ($1, $2, $3, '{}'::jsonb, now() - $4::interval)",
        pid,
        name,
        f"/tmp/{name}",
        age,
    )


async def _job(
    conn: asyncpg.Connection,
    pid: UUID,
    key: str,
    *,
    state: str = "ready",
    run_after: timedelta = timedelta(seconds=-1),
) -> UUID:
    job_id = await conn.fetchval(
        "INSERT INTO job (project_id, cycle, phase, kind, idempotency_key, state, run_after) "
        "VALUES ($1, 1, 'build', 'build.implement', $2, $3::job_state, now() + $4::interval) "
        "RETURNING id",
        pid,
        key,
        state,
        run_after,
    )
    return UUID(str(job_id))


async def _seed(pool: asyncpg.Pool) -> UUID:
    """Two projects that disagree about everything, and one of each kind of job.

    The bound project is the OLDER one, so "newest project" and "bound project" name
    different rows: a query that confused the two could not pass both tests below.
    """
    newest = uuid4()
    async with pool.acquire() as conn:
        await _project(conn, BOUND, "bound", timedelta(hours=1))
        await _project(conn, newest, "newest", timedelta(0))
        await _job(conn, BOUND, "claimable-1")
        await _job(conn, BOUND, "claimable-2")
        await _job(conn, BOUND, "not-due", run_after=timedelta(hours=1))
        failed = await _job(conn, BOUND, "failed-dependency", state="failed")
        blocked = await _job(conn, BOUND, "blocked")
        await conn.execute(
            "INSERT INTO job_dependency (job_id, depends_on_job_id) VALUES ($1, $2)",
            blocked,
            failed,
        )
        for key in ("n-1", "n-2", "n-3"):
            await _job(conn, newest, key)
    # A job in a phase this release does not know (a newer vibey wrote it): the claim
    # never takes it (vibey#287), so the scaler must not count it either.
    # ALTER TYPE is the owner's (ADR-0055); `pool` is the application role's.
    owner = await asyncpg.connect(os.environ["VIBEY_TEST_DATABASE_URL"])
    try:
        await owner.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'triage'")
    finally:
        await owner.close()
    async with pool.acquire() as conn:
        for pid, key in ((BOUND, "unknown-phase"), (newest, "n-unknown-phase")):
            stranger = await _job(conn, pid, key)
            await conn.execute("UPDATE job SET phase = 'triage' WHERE id = $1", stranger)
    return newest


async def _claim_all(pool: asyncpg.Pool, project_id: UUID) -> int:
    repo = PostgresJobRepository(pool)
    claimed = 0
    while await repo.claim(project_id, owner="scaler-test", lease=LEASE) is not None:
        claimed += 1
    return claimed


async def test_a_bound_scaler_counts_what_that_projects_worker_can_claim(
    migrated_pool: asyncpg.Pool,
) -> None:
    await _seed(migrated_pool)
    async with migrated_pool.acquire() as conn:
        counted = await conn.fetchval(_scaler_query("keda-project"))

    claimed = await _claim_all(migrated_pool, BOUND)

    assert (counted, claimed) == (2, 2)


async def test_an_unbound_scaler_counts_the_project_an_unbound_worker_binds_to(
    migrated_pool: asyncpg.Pool,
) -> None:
    newest = await _seed(migrated_pool)
    latest = await PostgresProjectRepository(migrated_pool).get_latest()
    assert latest is not None
    async with migrated_pool.acquire() as conn:
        counted = await conn.fetchval(_scaler_query("keda-latest"))

    claimed = await _claim_all(migrated_pool, latest.project_id)

    assert (latest.project_id, counted, claimed) == (newest, 3, 3)


def test_the_scaler_counts_exactly_the_phases_the_claim_takes() -> None:
    """The chart spells the known phases out; the claim reads them from `Phase`. Pin the
    two together so a new phase cannot reach one and not the other."""
    import re

    from vibey.infrastructure.db.job_repository import KNOWN_PHASES

    for profile in ("keda-project", "keda-latest"):
        listed = re.search(r"j\.phase::text IN \(([^)]*)\)", _scaler_query(profile))
        assert listed is not None, f"{profile}: the scaler has no known-phase filter"
        phases = tuple(p.strip().strip("'") for p in listed.group(1).split(","))
        assert phases == KNOWN_PHASES


@pytest.mark.parametrize("profile", ["keda-project", "keda-latest"])
async def test_a_scaler_counts_nothing_for_an_abandoned_project(
    migrated_pool: asyncpg.Pool, profile: str
) -> None:
    """`vibey abandon` makes a project's jobs unclaimable; a ready one a handler enqueued
    afterwards would otherwise hold a worker up for work that will never run."""
    newest = await _seed(migrated_pool)
    served = BOUND if profile == "keda-project" else newest
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE project SET phase = 'abandoned' WHERE id = $1", served)
        counted = await conn.fetchval(_scaler_query(profile))

    claimed = await _claim_all(migrated_pool, served)

    assert (counted, claimed) == (0, 0)


def _not_exists_clauses(sql: str) -> list[str]:
    """Every top-level `NOT EXISTS (...)` of `sql`, whitespace-normalised."""
    clauses = []
    for start in (m.start() for m in re.finditer(r"NOT EXISTS\s*\(", sql)):
        depth, end = 0, start
        for end in range(sql.index("(", start), len(sql)):
            depth += {"(": 1, ")": -1}.get(sql[end], 0)
            if depth == 0:
                break
        clauses.append(_normalised(sql[start : end + 1]))
    return [c for c in clauses if not any(c != o and c in o for o in clauses)]


def _normalised(sql: str) -> str:
    return re.sub(r"\s*\)", ")", re.sub(r"\(\s*", "(", " ".join(sql.split())))


def test_the_scaler_excludes_exactly_what_the_claim_excludes() -> None:
    """Each `NOT EXISTS` the claim applies -- the abandoned-project exclusion and the
    unsatisfied-dependency one -- appears word for word in both scaler queries, so an
    exclusion added to the claim and not to the chart fails here."""
    claim = _not_exists_clauses(_CLAIMABLE)
    assert any("pr.phase = 'abandoned'" in clause for clause in claim)
    assert any("job_dependency" in clause for clause in claim)
    for profile in ("keda-project", "keda-latest"):
        assert _not_exists_clauses(_scaler_query(profile)) == claim, profile


async def test_an_unbound_scaler_with_no_project_counts_nothing(
    migrated_pool: asyncpg.Pool,
) -> None:
    async with migrated_pool.acquire() as conn:
        counted = await conn.fetchval(_scaler_query("keda-latest"))

    assert counted == 0
