# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest
from vibey.domain.engine import EngineId
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.infrastructure.db.job_repository import PostgresJobRepository

LEASE = timedelta(seconds=30)


def _request(project_id: UUID, subject: str = "item-001", **overrides: object) -> EnqueueRequest:
    defaults: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": "build.implement",
        "idempotency_key": f"key-{subject}",
        "payload": {"subject": subject},
    }
    defaults.update(overrides)
    return EnqueueRequest(**defaults)  # type: ignore[arg-type]


async def test_enqueue_creates_a_ready_job(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    repo = PostgresJobRepository(migrated_pool)

    job = await repo.enqueue(_request(project_id))

    assert job.state is JobState.READY
    assert job.project_id == project_id
    assert job.kind == "build.implement"
    assert job.payload["subject"] == "item-001"


async def test_enqueue_is_idempotent(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    repo = PostgresJobRepository(migrated_pool)
    request = _request(project_id)

    first = await repo.enqueue(request)
    second = await repo.enqueue(request)

    assert first.id == second.id

    async with migrated_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM job WHERE project_id = $1 AND idempotency_key = $2",
            project_id,
            request.idempotency_key,
        )
    assert count == 1


async def test_claim_leases_the_highest_priority_ready_job(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id, subject="low", priority=0))
    high = await repo.enqueue(_request(project_id, subject="high", priority=10))

    claimed = await repo.claim(project_id, owner="worker-1", lease=LEASE)

    assert claimed is not None
    assert claimed.id == high.id
    assert claimed.state is JobState.LEASED
    assert claimed.lease_owner == "worker-1"
    assert claimed.attempts == 1


async def test_claim_returns_none_when_nothing_ready(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    assert await repo.claim(project_id, owner="worker-1", lease=LEASE) is None


async def test_two_workers_never_claim_the_same_job(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))

    results = await asyncio.gather(
        repo.claim(project_id, owner="worker-1", lease=LEASE),
        repo.claim(project_id, owner="worker-2", lease=LEASE),
    )

    non_none = [r for r in results if r is not None]
    assert len(non_none) == 1
    assert non_none[0].id == job.id


async def test_heartbeat_extends_the_lease(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    claimed = await repo.claim(project_id, owner="worker-1", lease=LEASE)
    assert claimed is not None

    ok = await repo.heartbeat(job.id, owner="worker-1", lease=LEASE)

    assert ok is True


async def test_heartbeat_fails_for_wrong_owner(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    ok = await repo.heartbeat(job.id, owner="worker-2", lease=LEASE)

    assert ok is False


async def test_ack_marks_succeeded_and_releases_lease(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    ok = await repo.ack(job.id, owner="worker-1")

    assert ok is True
    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.SUCCEEDED
    assert record.lease_owner is None


async def test_nack_reschedules_as_ready_when_attempts_remain(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, max_attempts=7))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    ok = await repo.nack(job.id, owner="worker-1", error={"message": "boom"})

    assert ok is True
    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.READY
    assert record.last_error == {"message": "boom"}


async def test_nack_marks_failed_once_max_attempts_reached(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, max_attempts=1))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    await repo.nack(job.id, owner="worker-1", error={"message": "boom"})

    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.FAILED


async def test_grant_attempts_widens_the_bound_so_the_next_nack_retries(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """ADR-0024: the grant has to reach the row, because nack decides
    'failed' from the row's own max_attempts."""
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, max_attempts=1))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    assert await repo.grant_attempts(job.id, owner="worker-1", max_attempts=4) is True
    await repo.nack(job.id, owner="worker-1", error={"message": "boom"})

    record = await repo.get(job.id)
    assert record is not None
    assert record.max_attempts == 4
    assert record.state is JobState.READY


async def test_grant_attempts_never_narrows_the_bound(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, max_attempts=7))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    assert await repo.grant_attempts(job.id, owner="worker-1", max_attempts=7) is False
    assert await repo.grant_attempts(job.id, owner="worker-1", max_attempts=2) is False

    record = await repo.get(job.id)
    assert record is not None
    assert record.max_attempts == 7


async def test_grant_attempts_refuses_a_lease_it_does_not_hold(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, max_attempts=1))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    assert await repo.grant_attempts(job.id, owner="worker-2", max_attempts=9) is False

    record = await repo.get(job.id)
    assert record is not None
    assert record.max_attempts == 1


async def test_park_sets_awaiting_human_and_releases_lease(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    ok = await repo.park(job.id, owner="worker-1")

    assert ok is True
    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN
    assert record.lease_owner is None
    assert record.attempts == 0

    # A parked job is not claimable -- it is not 'ready'.
    assert await repo.claim(project_id, owner="worker-2", lease=LEASE) is None


async def test_defer_capacity_releases_lease_without_consuming_attempt(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)
    retry_at = datetime(2026, 8, 14, 20, 10, tzinfo=UTC)

    assert await repo.defer(
        job.id,
        owner="worker-1",
        retry_at=retry_at,
        error={"class": "capacity", "detail": "window exhausted"},
    )
    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.READY
    assert record.attempts == 0
    assert record.run_after == retry_at
    assert record.last_error == {"class": "capacity", "detail": "window exhausted"}


async def test_reap_reclaims_expired_leases(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    await repo.claim(project_id, owner="worker-1", lease=timedelta(seconds=-1))

    reclaimed = await repo.reap()

    assert reclaimed == 1
    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.READY
    assert record.lease_owner is None


async def test_dependency_gating_blocks_claim_until_dependency_succeeds(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    upstream = await repo.enqueue(_request(project_id, subject="upstream"))
    downstream = await repo.enqueue(
        _request(project_id, subject="downstream", depends_on=(upstream.id,))
    )

    # Only the upstream job is claimable; downstream must never be offered.
    first_claim = await repo.claim(project_id, owner="worker-1", lease=LEASE)
    assert first_claim is not None
    assert first_claim.id == upstream.id

    second_claim = await repo.claim(project_id, owner="worker-1", lease=LEASE)
    assert second_claim is None

    await repo.ack(upstream.id, owner="worker-1")

    third_claim = await repo.claim(project_id, owner="worker-1", lease=LEASE)
    assert third_claim is not None
    assert third_claim.id == downstream.id


async def test_get_returns_none_for_unknown_job(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresJobRepository(migrated_pool)
    assert await repo.get(uuid4()) is None


async def test_queue_depth_counts_jobs_by_state(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    j1 = await repo.enqueue(_request(project_id, subject="a"))
    j2 = await repo.enqueue(_request(project_id, subject="b"))
    await repo.enqueue(_request(project_id, subject="c", max_attempts=1))

    await repo.claim(project_id, owner="w1", lease=LEASE)
    await repo.ack(j1.id, owner="w1")

    await repo.claim(project_id, owner="w1", lease=LEASE)
    await repo.nack(j2.id, owner="w1", error={"msg": "fail"})

    depths = await repo.queue_depth(project_id)
    assert depths[JobState.SUCCEEDED] == 1
    assert depths[JobState.READY] >= 1
    assert all(isinstance(v, int) for v in depths.values())


async def test_queue_depth_returns_all_zeros_for_empty_project(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    depths = await repo.queue_depth(uuid4())
    assert all(v == 0 for v in depths.values())
    assert set(depths.keys()) == set(JobState)


async def test_enqueue_raises_lookup_error_when_both_fetchrows_return_none() -> None:
    class _NullConn:
        async def fetchrow(self, *a: object, **kw: object) -> None:
            return None

        async def execute(self, *a: object, **kw: object) -> None:
            pass

        def transaction(self) -> "_NullTx":
            return _NullTx()

    class _NullTx:
        async def __aenter__(self) -> "_NullTx":
            return self

        async def __aexit__(self, *a: object) -> None:
            pass

    class _NullPool:
        def acquire(self) -> "_NullPool":
            return self

        async def __aenter__(self) -> _NullConn:
            return _NullConn()

        async def __aexit__(self, *a: object) -> None:
            pass

    repo = PostgresJobRepository(_NullPool())  # type: ignore[arg-type]
    with pytest.raises(LookupError, match="conflicting idempotency key"):
        await repo.enqueue(_request(uuid4()))


async def test_assign_engine_records_selection_on_leased_job(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id))
    job = await repo.claim(project_id, owner="w1", lease=LEASE)
    assert job is not None

    ok = await repo.assign_engine(job.id, owner="w1", engine_id=EngineId.CLAUDELOOP)

    assert ok is True
    fetched = await repo.get(job.id)
    assert fetched is not None
    assert fetched.assigned_engine == "claudeloop"


async def test_assign_engine_refuses_wrong_owner(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id))
    job = await repo.claim(project_id, owner="w1", lease=LEASE)
    assert job is not None

    ok = await repo.assign_engine(job.id, owner="somebody-else", engine_id=EngineId.AGYLOOP)

    assert ok is False
    fetched = await repo.get(job.id)
    assert fetched is not None
    assert fetched.assigned_engine is None


async def test_assign_engine_refuses_unleased_job(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))

    ok = await repo.assign_engine(job.id, owner="w1", engine_id=EngineId.CLAUDELOOP)

    assert ok is False


async def test_count_unsettled_scopes_by_cycle_phase_and_terminal_states(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    settled = await repo.enqueue(_request(project_id, subject="done-item"))
    open_job = await repo.enqueue(_request(project_id, subject="open-item"))
    await repo.enqueue(_request(project_id, subject="other-cycle", cycle=2))
    await repo.enqueue(
        _request(project_id, subject="other-phase", phase=Phase.REVIEW, kind="review.demo")
    )

    claimed = await repo.claim(project_id, owner="w1", lease=LEASE)
    assert claimed is not None and claimed.id == settled.id
    # A leased job still counts as unsettled.
    assert await repo.count_unsettled(project_id, cycle=1, phase=Phase.BUILD) == 2
    await repo.ack(settled.id, owner="w1")

    assert await repo.count_unsettled(project_id, cycle=1, phase=Phase.BUILD) == 1
    assert (
        await repo.count_unsettled(project_id, cycle=1, phase=Phase.BUILD, exclude=open_job.id) == 0
    )


async def test_count_unsettled_treats_failed_as_settled(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    failing = await repo.enqueue(_request(project_id, subject="failing-item", max_attempts=1))

    claimed = await repo.claim(project_id, owner="w1", lease=LEASE)
    assert claimed is not None and claimed.id == failing.id
    await repo.nack(failing.id, owner="w1", error={"class": "work", "detail": "x"})

    failed = await repo.get(failing.id)
    assert failed is not None and failed.state is JobState.FAILED
    assert await repo.count_unsettled(project_id, cycle=1, phase=Phase.BUILD) == 0


# --- enqueue_batch: the fan-out is one transaction (#265) ---


async def _dependencies(pool: asyncpg.Pool, job_id: UUID) -> set[UUID]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT depends_on_job_id FROM job_dependency WHERE job_id = $1", job_id
        )
    return {row["depends_on_job_id"] for row in rows}


async def _count_keys(pool: asyncpg.Pool, project_id: UUID, keys: list[str]) -> dict[str, int]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT idempotency_key, count(*) AS n FROM job
            WHERE project_id = $1 AND idempotency_key = ANY($2::text[])
            GROUP BY idempotency_key
            """,
            project_id,
            keys,
        )
    return {row["idempotency_key"]: row["n"] for row in rows}


def _plan(project_id: UUID) -> list[EnqueueRequest]:
    return [
        _request(project_id, subject="skeleton"),
        _request(project_id, subject="item-2", depends_on_keys=("key-skeleton",)),
        _request(project_id, subject="item-3", depends_on_keys=("key-skeleton", "key-item-2")),
    ]


async def test_enqueue_batch_commits_every_request_with_its_key_dependencies(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)

    skeleton, item_2, item_3 = await repo.enqueue_batch(_plan(project_id))

    assert [job.payload["subject"] for job in (skeleton, item_2, item_3)] == [
        "skeleton",
        "item-2",
        "item-3",
    ]
    assert await _dependencies(migrated_pool, skeleton.id) == set()
    assert await _dependencies(migrated_pool, item_2.id) == {skeleton.id}
    assert await _dependencies(migrated_pool, item_3.id) == {skeleton.id, item_2.id}

    # The edges gate the queue exactly as id-named ones do.
    first = await repo.claim(project_id, owner="w1", lease=LEASE)
    assert first is not None and first.id == skeleton.id
    assert await repo.claim(project_id, owner="w1", lease=LEASE) is None


async def test_a_crash_mid_batch_commits_nothing_and_a_replay_makes_one_job_per_item(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    plan = _plan(project_id)
    keys = [request.idempotency_key for request in plan]
    # Two rows are written inside the transaction, then the third request
    # blows up before its INSERT -- a worker dying mid-fan-out.
    poisoned = [*plan[:2], _request(project_id, subject="item-3", payload={"x": object()})]

    with pytest.raises(TypeError):
        await repo.enqueue_batch(poisoned)
    assert await _count_keys(migrated_pool, project_id, keys) == {}

    first = await repo.enqueue_batch(plan)
    replayed = await repo.enqueue_batch(plan)

    assert await _count_keys(migrated_pool, project_id, keys) == dict.fromkeys(keys, 1)
    assert [job.id for job in replayed] == [job.id for job in first]
    assert await _dependencies(migrated_pool, first[2].id) == {first[0].id, first[1].id}


async def test_enqueue_batch_rolls_back_when_a_key_names_no_job(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    # A dependency listed AFTER its dependent is not visible yet: the batch is
    # processed in order, and a key that resolves to nothing undoes it all.
    out_of_order = [
        _request(project_id, subject="skeleton"),
        _request(project_id, subject="item-2", depends_on_keys=("key-item-3",)),
        _request(project_id, subject="item-3"),
    ]

    with pytest.raises(LookupError, match="'key-item-3'"):
        await repo.enqueue_batch(out_of_order)

    assert await repo.list_for_cycle(project_id, cycle=1, kind="build.implement") == ()


async def test_depends_on_keys_resolve_against_jobs_already_committed(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    upstream = await repo.enqueue(_request(project_id, subject="upstream"))

    (batched,) = await repo.enqueue_batch(
        [_request(project_id, subject="batched", depends_on_keys=("key-upstream",))]
    )
    single = await repo.enqueue(
        _request(project_id, subject="single", depends_on_keys=("key-upstream",))
    )

    assert await _dependencies(migrated_pool, batched.id) == {upstream.id}
    assert await _dependencies(migrated_pool, single.id) == {upstream.id}


async def test_enqueue_with_a_key_that_names_no_job_inserts_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)

    with pytest.raises(LookupError, match="neither an earlier request"):
        await repo.enqueue(_request(project_id, depends_on_keys=("key-ghost",)))

    assert await repo.list_for_cycle(project_id, cycle=1, kind="build.implement") == ()


async def test_list_for_cycle_scopes_by_project_cycle_and_kind_oldest_first(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    first = await repo.enqueue(_request(project_id, subject="first"))
    second = await repo.enqueue(_request(project_id, subject="second"))
    await repo.enqueue(_request(project_id, subject="other-cycle", cycle=2))
    await repo.enqueue(_request(project_id, subject="other-kind", kind="build.verify"))
    claimed = await repo.claim(project_id, owner="w1", lease=LEASE)
    assert claimed is not None

    listed = await repo.list_for_cycle(project_id, cycle=1, kind="build.implement")

    assert [job.id for job in listed] == [first.id, second.id]
    assert await repo.list_for_cycle(uuid4(), cycle=1, kind="build.implement") == ()
