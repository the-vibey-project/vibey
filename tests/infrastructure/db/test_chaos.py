# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The single most important test in M2 (implementation-plan.md 2.8).

The plan calls for 8 workers processing 500 jobs while a random worker is
SIGKILLed every 2 seconds. Reaching for `docker`/testcontainers to spin up
separate OS processes and kill -9 them is out of reach in this environment
(no docker daemon available), so this is a scoped-down but still real
chaos test: 8 concurrent asyncio workers against a real local Postgres,
each of which randomly abandons a claimed job mid-flight -- exactly the
observable effect of a SIGKILLed worker, since the worker never gets to
ack, nack, or heartbeat again and the lease is left to expire. A
concurrent reaper reclaims those expired leases, same as production.

What's verified is the property the real chaos test exists to protect:
zero double-commit, zero lost jobs, every job reaches a terminal state.

Delivery is at-least-once, and the test counts it honestly instead of hiding
it. A worker slower than its lease (a loaded machine is enough) has its job
reaped and claimed again by another worker, so the work can run twice. What
must never happen twice is the commit: ack is fenced on lease_owner, so a
stale ack is refused and exactly one ack per job returns True. The test
therefore tallies COMMITTED executions -- acks that returned True -- and
asserts that none was committed twice and none was lost, keeping the raw
execution count for information only. Lengthening the lease would make the
duplicates vanish on an idle machine and mask the very fence under test.
"""

import asyncio
import random
from datetime import timedelta
from uuid import UUID

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.infrastructure.db.job_repository import PostgresJobRepository

JOB_COUNT = 500
WORKER_COUNT = 8
LEASE = timedelta(milliseconds=150)
CRASH_PROBABILITY = 0.2
TEST_TIMEOUT_SECONDS = 45.0
DRAIN_TIMEOUT_SECONDS = 10.0


@pytest.mark.slow
async def test_chaos_zero_double_commit_zero_lost_jobs(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)

    job_ids: set[UUID] = set()
    for i in range(JOB_COUNT):
        job = await repo.enqueue(
            EnqueueRequest(
                project_id=project_id,
                cycle=1,
                phase=Phase.BUILD,
                kind="build.implement",
                idempotency_key=f"chaos-{i}",
                payload={"i": i},
                max_attempts=1000,
            )
        )
        job_ids.add(job.id)

    # One event loop, so these appends never interleave and need no lock.
    executions: list[UUID] = []  # every time a worker did the work
    commits: list[UUID] = []  # acks the lease-owner fence accepted
    refused: list[UUID] = []  # stale acks the fence turned away
    stop = asyncio.Event()
    rng = random.Random(1234)

    async def worker(name: str) -> None:
        while not stop.is_set():
            job = await repo.claim(project_id, owner=name, lease=LEASE)
            if job is None:
                await asyncio.sleep(0.01)
                continue

            if rng.random() < CRASH_PROBABILITY:
                # Simulate SIGKILL: the process dies here. No ack, no nack,
                # no further heartbeat -- the lease is simply abandoned and
                # must expire on its own.
                continue

            executions.append(job.id)
            if await repo.ack(job.id, owner=name):
                commits.append(job.id)
            else:
                refused.append(job.id)

    async def reaper() -> None:
        while not stop.is_set():
            await repo.reap()
            await asyncio.sleep(0.05)

    async def wait_until_all_terminal() -> None:
        while True:
            async with migrated_pool.acquire() as conn:
                remaining = await conn.fetchval(
                    "SELECT count(*) FROM job WHERE project_id = $1 "
                    "AND state NOT IN ('succeeded', 'failed')",
                    project_id,
                )
            if remaining == 0:
                return
            await asyncio.sleep(0.05)

    worker_tasks = [asyncio.ensure_future(worker(f"worker-{i}")) for i in range(WORKER_COUNT)]
    reaper_task = asyncio.ensure_future(reaper())

    try:
        await asyncio.wait_for(wait_until_all_terminal(), timeout=TEST_TIMEOUT_SECONDS)
    finally:
        stop.set()
        # Let each task finish the iteration it is in rather than cancelling
        # it: a worker cancelled after the database committed its ack, but
        # before the ack returned, would drop that commit from the tally and
        # read as a lost job.
        _, pending = await asyncio.wait([*worker_tasks, reaper_task], timeout=DRAIN_TIMEOUT_SECONDS)
        for t in pending:
            t.cancel()
        outcomes = await asyncio.gather(*worker_tasks, reaper_task, return_exceptions=True)

    crashed = [o for o in outcomes if isinstance(o, BaseException)]
    assert not crashed, f"a worker or the reaper raised: {crashed!r}"

    # The raw execution count is informational and has no bound: under load,
    # claim-to-ack outlives the lease and the work runs again. That is
    # at-least-once delivery, not a defect. The tally itself must balance.
    # Printed so `pytest -rP` shows it on a pass; every failure message has it.
    tally = (
        f"{len(executions)} raw executions = {len(commits)} committed"
        f" + {len(refused)} stale acks refused"
    )
    print(f"chaos tally: {tally}")
    assert len(executions) == len(commits) + len(refused), f"an ack went untallied: {tally}"

    # Zero double-commit: no job's ack was accepted twice.
    double_committed = len(commits) - len(set(commits))
    assert double_committed == 0, f"{double_committed} job(s) committed more than once: {tally}"

    # Zero lost jobs: every job committed, so every refused ack was a stale
    # one whose job another ack carried home.
    lost = job_ids - set(commits)
    assert not lost, f"{len(lost)} job(s) never committed: {tally}"
    assert len(commits) == JOB_COUNT, f"expected {JOB_COUNT} commits: {tally}"

    async with migrated_pool.acquire() as conn:
        states = await conn.fetch(
            "SELECT state, count(*) AS n FROM job WHERE project_id = $1 GROUP BY state",
            project_id,
        )
        succeeded = await conn.fetchval(
            "SELECT count(*) FROM job WHERE project_id = $1 AND state = 'succeeded'",
            project_id,
        )
        leased_or_ready = await conn.fetchval(
            "SELECT count(*) FROM job WHERE project_id = $1 AND state IN ('ready', 'leased')",
            project_id,
        )

    state_counts = {row["state"]: row["n"] for row in states}
    assert leased_or_ready == 0, f"jobs stuck non-terminal: {state_counts}"
    assert succeeded == JOB_COUNT, f"expected all {JOB_COUNT} to succeed, got {state_counts}"
    assert JobState.FAILED.value not in state_counts, f"unexpected failures: {state_counts}"
