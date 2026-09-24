# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The PostgreSQL side of queue reaping, against a real database (ADR-0056).

The lease reap is the same judgement the broker's held deliveries get: requeued while
attempts remain, parked with a `delivery_exhausted` gate once they are spent -- each move
and its `QueueReaped` event in one transaction.
"""

import asyncio
import json
from datetime import timedelta
from uuid import UUID

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.domain.queue_reap import (
    DeadLetter,
    ReapAction,
    ReapCondition,
    ReapThresholds,
    ReapVerdict,
)
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.interfaces import (
    PostgresQueueReapStoreInterface,
    ReapEventDraftBuilderInterface,
)
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.queue_reap_store import (
    REAP_EVENT_DRAFTS,
    PostgresQueueReapStore,
)

EXPIRED = timedelta(seconds=-1)


def _request(project_id: UUID, subject: str, **overrides: object) -> EnqueueRequest:
    values: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": "build.implement",
        "idempotency_key": f"key-{subject}",
        "payload": {"subject": subject},
    }
    values.update(overrides)
    return EnqueueRequest(**values)  # type: ignore[arg-type]


async def _events(pool: asyncpg.Pool, project_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "SELECT kind, job_id, provenance, payload FROM event "
                "WHERE project_id = $1 AND kind = 'QueueReaped' ORDER BY seq",
                project_id,
            )
        )


async def _gates(pool: asyncpg.Pool, job_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "SELECT kind, prompt, options FROM human_gate WHERE job_id = $1", job_id
            )
        )


def test_the_store_and_its_draft_builder_satisfy_their_seams() -> None:
    assert isinstance(REAP_EVENT_DRAFTS, ReapEventDraftBuilderInterface)
    store = PostgresQueueReapStore(pool=None)  # type: ignore[arg-type]
    assert isinstance(store, PostgresQueueReapStoreInterface)


# -- leases ----------------------------------------------------------------------------


async def test_an_expired_lease_with_attempts_left_is_requeued_and_recorded(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, "a"))
    await repo.claim(project_id, owner="w", lease=EXPIRED)

    assert await repo.reap() == 1

    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.READY
    assert record.lease_owner is None
    assert record.attempts == 1, "the claim counted the attempt; the reap does not refund it"
    (event,) = await _events(migrated_pool, project_id)
    assert event["job_id"] == job.id
    assert event["provenance"] == "trusted"
    payload = json.loads(event["payload"])
    assert payload["object"] == str(job.id)
    assert payload["queue"] == f"job:{project_id}"
    assert payload["condition"] == "lease_expired"
    assert payload["action"] == "requeue"
    assert payload["unit"] == "seconds past deadline"
    assert payload["measured"] > payload["threshold"] == 0


async def test_an_expired_lease_with_no_attempts_left_is_parked_with_a_gate(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """A job that kills its worker every time is bounded, not re-claimed forever."""
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, "poison", max_attempts=2))
    await repo.claim(project_id, owner="w1", lease=EXPIRED)
    await repo.reap()
    await repo.claim(project_id, owner="w2", lease=EXPIRED)

    assert await repo.reap() == 1

    record = await repo.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN
    assert record.attempts == 1, "one attempt is refunded, so an answer buys one delivery"
    (gate,) = await _gates(migrated_pool, job.id)
    assert gate["kind"] == "delivery_exhausted"
    assert "'build.implement'" in gate["prompt"]
    assert "its limit of 2" in gate["prompt"]
    first, second = await _events(migrated_pool, project_id)
    assert json.loads(first["payload"])["action"] == "requeue"
    parked = json.loads(second["payload"])
    assert (parked["condition"], parked["action"]) == ("poison", "park")
    assert (parked["measured"], parked["threshold"], parked["unit"]) == (2, 2, "attempts")

    # The answer re-readies it; the next claim is its one more delivery.
    gates = PostgresHumanGateRepository(migrated_pool)
    (open_gate,) = await gates.open_for_project(project_id)
    await gates.answer(open_gate.gate_id, answer={"text": "go"}, answered_by="operator")
    claimed = await repo.claim(project_id, owner="w3", lease=EXPIRED)
    assert claimed is not None and claimed.attempts == 2
    assert await repo.reap() == 1
    again = await repo.get(job.id)
    assert again is not None and again.state is JobState.AWAITING_HUMAN


async def test_a_lease_within_its_grace_is_left_alone(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(
        migrated_pool, reap_thresholds=ReapThresholds(lease_grace_seconds=3600)
    )
    job = await repo.enqueue(_request(project_id, "graced"))
    await repo.claim(project_id, owner="w", lease=EXPIRED)

    assert await repo.reap() == 0

    record = await repo.get(job.id)
    assert record is not None and record.state is JobState.LEASED
    assert await _events(migrated_pool, project_id) == []


async def test_a_live_lease_is_never_reaped(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id, "live"))
    await repo.claim(project_id, owner="w", lease=timedelta(minutes=5))
    store = PostgresQueueReapStore(migrated_pool)
    assert await store.preview_leases() == ()
    assert await store.reap_leases() == ()


async def test_a_preview_judges_and_writes_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, "preview", max_attempts=1))
    await repo.claim(project_id, owner="w", lease=EXPIRED)
    store = PostgresQueueReapStore(migrated_pool)

    (verdict,) = await store.preview_leases()

    assert verdict.subject == str(job.id)
    assert (verdict.condition, verdict.action) == (ReapCondition.POISON, ReapAction.PARK)
    record = await repo.get(job.id)
    assert record is not None and record.state is JobState.LEASED
    assert await _events(migrated_pool, project_id) == []
    assert await _gates(migrated_pool, job.id) == []


async def test_two_reapers_at_once_reap_each_lease_exactly_once(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """`FOR UPDATE SKIP LOCKED` splits the work: replayed reaps never double a move."""
    repo = PostgresJobRepository(migrated_pool)
    for n in range(12):
        await repo.enqueue(_request(project_id, f"race-{n}"))
        await repo.claim(project_id, owner=f"w{n}", lease=EXPIRED)
    one, two = PostgresQueueReapStore(migrated_pool), PostgresQueueReapStore(migrated_pool)

    first, second = await asyncio.gather(one.reap_leases(), two.reap_leases())

    subjects = [v.subject for v in (*first, *second)]
    assert len(subjects) == len(set(subjects)) == 12
    assert len(await _events(migrated_pool, project_id)) == 12


async def test_a_lease_in_a_phase_this_vibey_does_not_know_is_left_for_a_newer_one(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    async with migrated_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'hyperdrive'")
        job_id = await conn.fetchval(
            """
            INSERT INTO job (project_id, cycle, phase, kind, state, idempotency_key,
                             lease_owner, lease_expires_at, attempts)
            VALUES ($1, 1, 'hyperdrive', 'future.kind', 'leased', 'future',
                    'newer', now() - interval '1 hour', 1)
            RETURNING id
            """,
            project_id,
        )
    store = PostgresQueueReapStore(migrated_pool)
    assert await store.preview_leases() == ()
    assert await store.reap_leases() == ()
    async with migrated_pool.acquire() as conn:
        state = await conn.fetchval("SELECT state::text FROM job WHERE id = $1", job_id)
    assert state == "leased"


# -- (d): ready work -------------------------------------------------------------------


async def test_ready_depths_measure_claimable_work_and_its_age(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresQueueReapStore(migrated_pool)
    assert await store.ready_depths(project_id) == ()

    old = await repo.enqueue(_request(project_id, "old"))
    await repo.enqueue(_request(project_id, "blocked", depends_on=(old.id,)))
    await repo.enqueue(_request(project_id, "later"))
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET run_after = now() - interval '2 hours', "
            "updated_at = now() - interval '2 hours' WHERE id = $1",
            old.id,
        )
        await conn.execute(
            "UPDATE job SET run_after = now() + interval '1 hour' WHERE idempotency_key = 'key-later'"
        )

    (depth,) = await store.ready_depths(project_id)

    assert depth.queue == f"job:{project_id}"
    assert depth.ready == 1, "a job waiting on a dependency, or not yet due, is not claimable"
    assert depth.consumers is None
    assert depth.oldest_ready_age_seconds is not None
    assert 7_190 <= depth.oldest_ready_age_seconds <= 7_300


async def test_ready_depths_date_a_released_job_from_its_dependency(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    upstream = await repo.enqueue(_request(project_id, "up"))
    await repo.enqueue(_request(project_id, "down", depends_on=(upstream.id,)))
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET run_after = now() - interval '3 hours', "
            "updated_at = now() - interval '3 hours'"
        )
        await conn.execute(
            "UPDATE job SET state = 'succeeded', updated_at = now() - interval '10 minutes' "
            "WHERE id = $1",
            upstream.id,
        )

    (depth,) = await PostgresQueueReapStore(migrated_pool).ready_depths(project_id)

    assert depth.ready == 1
    assert depth.oldest_ready_age_seconds is not None
    assert 590 <= depth.oldest_ready_age_seconds <= 700


# -- (e): dead letters -----------------------------------------------------------------


def _dead_letter(**overrides: object) -> DeadLetter:
    values: dict[str, object] = {
        "queue": "vibey.jobs.dlq",
        "origin_queue": "vibey.jobs",
        "reason": "rejected",
        "body": '{"job_id": "x"}',
        "message_id": "m1",
        "first_death_at": "10",
    }
    values.update(overrides)
    return DeadLetter(**values)  # type: ignore[arg-type]


def _park_verdict(item: DeadLetter) -> ReapVerdict:
    return ReapVerdict(
        subject=item.identity,
        queue=item.queue,
        condition=ReapCondition.DEAD_LETTERED,
        measured=1.0,
        threshold=1.0,
        unit="messages",
        action=ReapAction.PARK,
        detail={"origin_queue": item.origin_queue, "reason": item.reason},
    )


async def test_a_dead_letter_becomes_a_parked_job_a_gate_and_an_event_once(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    item = _dead_letter()

    job_id = await store.park_dead_letter(project_id, item, _park_verdict(item))

    assert job_id is not None
    job = await PostgresJobRepository(migrated_pool).get(job_id)
    assert job is not None
    assert (job.kind, job.state, job.phase, job.cycle) == (
        "bus.dead_letter",
        JobState.AWAITING_HUMAN,
        Phase.INTAKE,
        1,
    )
    assert job.payload["payload"] == {"job_id": "x"}
    assert job.payload["origin_queue"] == "vibey.jobs"
    assert job.payload["identity"] == "id:m1"
    assert "body" not in job.payload
    (gate,) = await _gates(migrated_pool, job_id)
    assert gate["kind"] == "bus_dead_lettered"
    assert json.loads(gate["options"]) == ["replay", "dismiss"]
    (event,) = await _events(migrated_pool, project_id)
    assert event["job_id"] == job_id
    assert event["provenance"] == "untrusted", "its queue and reason are the publisher's words"
    assert json.loads(event["payload"])["action"] == "park"

    assert await store.park_dead_letter(project_id, item, _park_verdict(item)) is None
    assert len(await _events(migrated_pool, project_id)) == 1


async def test_a_dead_letter_that_is_not_a_json_object_keeps_its_text(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    item = _dead_letter(body="<xml/>", message_id=None)

    job_id = await store.park_dead_letter(project_id, item, _park_verdict(item))

    assert job_id is not None
    job = await PostgresJobRepository(migrated_pool).get(job_id)
    assert job is not None
    assert job.payload["payload"] is None
    assert job.payload["body"] == "<xml/>"
    (gate,) = await _gates(migrated_pool, job_id)
    assert json.loads(gate["options"]) == ["dismiss"]


async def test_a_surfaced_verdict_is_recorded_under_the_project(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    verdict = ReapVerdict(
        subject="celery",
        queue="celery",
        condition=ReapCondition.STALE_READY,
        measured=1_000.0,
        threshold=900.0,
        unit="seconds ready with no consumer",
        action=ReapAction.SURFACE,
    )
    await PostgresQueueReapStore(migrated_pool).record(project_id, verdict)
    (event,) = await _events(migrated_pool, project_id)
    assert event["job_id"] is None
    assert event["provenance"] == "trusted"
    assert json.loads(event["payload"]) == json.loads(json.dumps(verdict.payload()))


async def test_recording_under_a_project_that_does_not_exist_raises(
    migrated_pool: asyncpg.Pool,
) -> None:
    missing = UUID(int=0)
    item = _dead_letter()
    store = PostgresQueueReapStore(migrated_pool)
    with pytest.raises(LookupError, match="no project"):
        await store.park_dead_letter(missing, item, _park_verdict(item))
    with pytest.raises(LookupError, match="no project"):
        await store.record(missing, _park_verdict(item))
