# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A job's failures on a real ledger: one `JobFailed` per failed run, read back newest
first by the ledger's own order."""

import json
from dataclasses import replace
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import JobRecord
from vibey.domain.defect import FAILURE_NORMALIZER
from vibey.domain.phase import UnrecognizedPhase
from vibey.infrastructure.db.interfaces import (
    JobFailedDraftBuilderInterface,
    PostgresJobFailureHistoryInterface,
)
from vibey.infrastructure.db.job_failure_history import (
    DETAIL_LIMIT,
    JOB_FAILED_DRAFTS,
    PostgresJobFailureHistory,
)
from vibey.infrastructure.db.job_repository import PostgresJobRepository

from .test_job_repository import LEASE, _request


async def _claimed(pool: asyncpg.Pool, project_id: UUID) -> JobRecord:
    jobs = PostgresJobRepository(pool)
    await jobs.enqueue(_request(project_id))
    claimed = await jobs.claim(project_id, owner="w1", lease=LEASE)
    assert claimed is not None
    return claimed


def test_the_history_and_its_drafts_satisfy_their_declared_seams(
    migrated_pool: asyncpg.Pool,
) -> None:
    assert isinstance(PostgresJobFailureHistory(migrated_pool), PostgresJobFailureHistoryInterface)
    assert isinstance(JOB_FAILED_DRAFTS, JobFailedDraftBuilderInterface)


async def test_failures_are_read_back_newest_first(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    history = PostgresJobFailureHistory(migrated_pool)
    job = await _claimed(migrated_pool, project_id)
    details = ["ImportError one", "ImportError two", "AssertionError three"]
    for detail in details:
        await history.record(job, FAILURE_NORMALIZER.signature("work", detail), detail=detail)

    recent = await history.recent(job, limit=2)

    assert [signature.excerpt for signature in recent] == [
        "AssertionError three",
        "ImportError two",
    ]
    # Another job's failures are its own.
    other = replace(job, id=uuid4())
    assert await history.recent(other, limit=5) == ()


async def test_a_failure_is_recorded_under_the_job_and_its_detail_is_bounded(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    history = PostgresJobFailureHistory(migrated_pool)
    job = await _claimed(migrated_pool, project_id)
    detail = "x" * (DETAIL_LIMIT + 50)
    await history.record(job, FAILURE_NORMALIZER.signature("engine", detail), detail=detail)

    async with migrated_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT kind, job_id, cycle, phase::text AS phase, provenance::text AS provenance, "
            "payload FROM event WHERE project_id = $1 AND kind = 'JobFailed'",
            project_id,
        )
    assert row is not None
    assert row["job_id"] == job.id
    assert (row["cycle"], row["phase"], row["provenance"]) == (job.cycle, "build", "trusted")
    payload = json.loads(row["payload"])
    assert payload["attempt"] == job.attempts == 1
    assert payload["failure_class"] == "engine"
    assert len(payload["detail"]) == DETAIL_LIMIT


async def test_a_record_no_vibey_wrote_as_a_failure_is_skipped(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    history = PostgresJobFailureHistory(migrated_pool)
    job = await _claimed(migrated_pool, project_id)
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            """
            SELECT append_event($1, 1, 'build', 'JobFailed', NULL, $2, NULL, $3,
                                'trusted', '{"note": "hand-written"}'::jsonb, 'digest')
            """,
            project_id,
            job.id,
            uuid4(),
        )
    assert await history.recent(job, limit=3) == ()


async def test_a_job_in_an_unknown_phase_is_refused(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    job = await _claimed(migrated_pool, project_id)
    newer = replace(job, phase=UnrecognizedPhase("orbit"))
    with pytest.raises(ValueError, match="unknown here"):
        await PostgresJobFailureHistory(migrated_pool).record(
            newer, FAILURE_NORMALIZER.signature("work", "boom"), detail="boom"
        )
