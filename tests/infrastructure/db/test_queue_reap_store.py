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
    ReapSource,
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
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    # Widening an enum is the owner's act (ADR-0055); the rows are the application's.
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'hyperdrive'")
    async with migrated_pool.acquire() as conn:
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


# -- (d): claimable, unclaimed work (#1108 review finding 5) ----------------------------


async def _new_project(pool: asyncpg.Pool, name: str) -> UUID:
    async with pool.acquire() as conn:
        pid = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) "
            "RETURNING id",
            name,
            f"/tmp/{name}",
        )
    return UUID(str(pid))


async def test_ready_depths_measure_claimable_work_and_its_age(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresQueueReapStore(migrated_pool)
    assert await store.ready_depths() == ()

    old = await repo.enqueue(_request(project_id, "old"))
    await repo.enqueue(_request(project_id, "blocked", depends_on=(old.id,)))
    await repo.enqueue(_request(project_id, "later"))
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET run_after = now() - interval '2 hours' WHERE id = $1", old.id
        )
        await conn.execute(
            "UPDATE job SET run_after = now() + interval '1 hour' WHERE idempotency_key = 'key-later'"
        )

    ((project, depth),) = await store.ready_depths()

    assert project == project_id
    assert depth.queue == f"job:{project_id}"
    assert depth.source is ReapSource.JOB_QUEUE
    assert depth.ready == 1, "a job waiting on a dependency, or not yet due, is not claimable"
    assert depth.consumers is None
    assert depth.oldest_ready_age_seconds is not None
    assert 7_190 <= depth.oldest_ready_age_seconds <= 7_300


async def test_every_project_is_measured_whether_or_not_it_has_a_worker(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Finding 5: the worker's reaper runs only when its own project has nothing
    claimable, so measuring only that project could never fire. Every project is."""
    orphan = await _new_project(migrated_pool, "no-worker")
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(orphan, "waiting"))
    await repo.enqueue(_request(project_id, "mine"))
    measured = dict(await PostgresQueueReapStore(migrated_pool).ready_depths())
    assert set(measured) == {orphan, project_id}
    assert measured[orphan].queue == f"job:{orphan}"


async def test_a_bump_does_not_reset_how_long_work_has_waited(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Finding 5: the age was read from `updated_at`, which a bump writes."""
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, "waited"))
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET run_after = now() - interval '1 hour', updated_at = now() "
            "WHERE id = $1",
            job.id,
        )
    ((_, depth),) = await PostgresQueueReapStore(migrated_pool).ready_depths()
    assert depth.oldest_ready_age_seconds is not None
    assert depth.oldest_ready_age_seconds >= 3_590


async def test_work_made_claimable_again_is_aged_from_then(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The lease reap, a gate answer and `vibey recover` move `run_after` up to now, so
    re-readied work is not reported as waiting since it was first due."""
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id, "requeued"))
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET run_after = now() - interval '5 hours' WHERE id = $1", job.id
        )
    await repo.claim(project_id, owner="w", lease=EXPIRED)
    await repo.reap()
    ((_, depth),) = await PostgresQueueReapStore(migrated_pool).ready_depths()
    assert depth.oldest_ready_age_seconds is not None
    assert depth.oldest_ready_age_seconds < 60


async def test_ready_depths_date_a_released_job_from_its_dependency(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    upstream = await repo.enqueue(_request(project_id, "up"))
    await repo.enqueue(_request(project_id, "down", depends_on=(upstream.id,)))
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET run_after = now() - interval '3 hours'")
        await conn.execute(
            "UPDATE job SET state = 'succeeded', updated_at = now() - interval '10 minutes' "
            "WHERE id = $1",
            upstream.id,
        )

    ((_, depth),) = await PostgresQueueReapStore(migrated_pool).ready_depths()

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

    job_id = await store.park_dead_letter(project_id, item, _park_verdict(item), origin_owned=True)

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
    assert job.payload["origin_owned"] is True
    assert job.payload["identity"] == "id:m1"
    assert "body" not in job.payload
    (gate,) = await _gates(migrated_pool, job_id)
    assert gate["kind"] == "bus_dead_lettered"
    assert json.loads(gate["options"]) == ["replay", "dismiss"]
    (event,) = await _events(migrated_pool, project_id)
    assert event["job_id"] == job_id
    assert event["provenance"] == "untrusted", "its queue and reason are the publisher's words"
    assert json.loads(event["payload"])["action"] == "park"
    assert await store.parked_count("vibey.jobs.dlq") == 1
    assert await store.parked_count("vibey.other.dlq") == 0

    again = await store.park_dead_letter(project_id, item, _park_verdict(item), origin_owned=True)
    assert again is None
    assert len(await _events(migrated_pool, project_id)) == 1


async def test_p1_one_dead_letter_is_parked_once_across_projects(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Finding 9 (P1): the same dead letter, read by two projects' workers, was parked --
    and gated -- once per project. One dead letter is one decision."""
    other = await _new_project(migrated_pool, "other")
    store = PostgresQueueReapStore(migrated_pool)
    item = _dead_letter()
    first, second = await asyncio.gather(
        store.park_dead_letter(project_id, item, _park_verdict(item), origin_owned=True),
        store.park_dead_letter(other, item, _park_verdict(item), origin_owned=True),
    )
    assert [first is None, second is None].count(True) == 1
    async with migrated_pool.acquire() as conn:
        jobs = await conn.fetchval("SELECT count(*) FROM job WHERE kind = 'bus.dead_letter'")
        gates = await conn.fetchval(
            "SELECT count(*) FROM human_gate WHERE kind = 'bus_dead_lettered'"
        )
    assert (jobs, gates) == (1, 1)


async def test_a_dead_letter_that_is_not_a_json_object_keeps_its_text(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    item = _dead_letter(body="<xml/>", message_id=None)

    job_id = await store.park_dead_letter(project_id, item, _park_verdict(item), origin_owned=True)

    assert job_id is not None
    job = await PostgresJobRepository(migrated_pool).get(job_id)
    assert job is not None
    assert job.payload["payload"] is None
    assert job.payload["body"] == "<xml/>"
    (gate,) = await _gates(migrated_pool, job_id)
    assert json.loads(gate["options"]) == ["dismiss"]


async def test_a_dead_letter_naming_a_foreign_queue_is_never_offered_for_replay(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    item = _dead_letter(origin_queue="celery", message_id="forged-1")
    job_id = await store.park_dead_letter(project_id, item, _park_verdict(item), origin_owned=False)
    assert job_id is not None
    (gate,) = await _gates(migrated_pool, job_id)
    assert json.loads(gate["options"]) == ["dismiss"]


# -- sightings, recorded once for the fleet (#1108 review finding 4) -------------------


def _sighting(
    source: ReapSource = ReapSource.BROKER, queue: str = "celery", episode: str = ""
) -> ReapVerdict:
    return ReapVerdict(
        subject=queue,
        queue=queue,
        condition=ReapCondition.STALE_READY,
        measured=1_000.0,
        threshold=900.0,
        unit="seconds ready with no consumer",
        action=ReapAction.SURFACE,
        source=source,
        episode=episode,
    )


async def test_p3_a_sighting_is_recorded_once_whichever_process_and_project_sees_it(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Finding 4 (P3): one continuous sighting was recorded three times -- two pods and
    the CLI -- and a broker sighting once per project, as trusted. The ledger now holds it
    open, fleet-wide, and a broker sighting is untrusted."""
    other = await _new_project(migrated_pool, "other")
    stores = [PostgresQueueReapStore(migrated_pool) for _ in range(3)]
    verdict = _sighting()
    results = await asyncio.gather(
        stores[0].record_sighting(project_id, verdict),
        stores[1].record_sighting(project_id, verdict),
        stores[2].record_sighting(other, verdict),
    )
    assert results.count(True) == 1
    async with migrated_pool.acquire() as conn:
        rows = await conn.fetch("SELECT provenance, payload FROM event WHERE kind = 'QueueReaped'")
    assert len(rows) == 1
    assert rows[0]["provenance"] == "untrusted"
    assert json.loads(rows[0]["payload"])["source"] == "broker"


async def test_an_open_sighting_is_listed_closed_once_and_then_recordable_again(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    job_queue = _sighting(ReapSource.JOB_QUEUE, queue=f"job:{project_id}")
    assert await store.record_sighting(project_id, job_queue)
    assert await store.open_sightings() == ((project_id, job_queue),)

    closes = await asyncio.gather(
        store.record_cleared(project_id, job_queue), store.record_cleared(project_id, job_queue)
    )
    assert sorted(closes) == [False, True]
    assert await store.open_sightings() == ()
    assert await store.record_sighting(project_id, job_queue), "its return is a new sighting"
    async with migrated_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT provenance, payload->>'action' AS action FROM event "
            "WHERE kind = 'QueueReaped' ORDER BY seq"
        )
    assert [(r["provenance"], r["action"]) for r in rows] == [
        ("trusted", "surface"),
        ("trusted", "cleared"),
        ("trusted", "surface"),
    ]


async def test_a_grown_remainder_is_a_new_sighting(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    assert await store.record_sighting(project_id, _sighting(episode="50"))
    assert await store.record_sighting(project_id, _sighting(episode="80"))
    assert not await store.record_sighting(project_id, _sighting(episode="80"))
    assert {v.episode for _, v in await store.open_sightings()} == {"50", "80"}


async def test_reaps_and_parks_are_never_mistaken_for_sightings(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id, "leased"))
    await repo.claim(project_id, owner="w", lease=EXPIRED)
    await repo.reap()
    store = PostgresQueueReapStore(migrated_pool)
    item = _dead_letter()
    await store.park_dead_letter(project_id, item, _park_verdict(item), origin_owned=True)
    assert await store.open_sightings() == ()


async def test_a_sighting_record_no_vibey_wrote_is_skipped(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    store = PostgresQueueReapStore(migrated_pool)
    await store.record_sighting(project_id, _sighting())
    async with owner_pool.acquire() as conn:
        # An older vibey's record: no `source`, no `episode`, a condition this one lacks.
        # Written as the owner, past the ledger's own guard, as only a migration could.
        await conn.execute("ALTER TABLE event DISABLE TRIGGER USER")
        await conn.execute(
            "UPDATE event SET payload = jsonb_set(payload::jsonb, '{condition}', '\"gone\"')"
        )
        await conn.execute("ALTER TABLE event ENABLE TRIGGER USER")
    assert await store.open_sightings() == ()


async def test_recording_under_a_project_that_does_not_exist_raises(
    migrated_pool: asyncpg.Pool,
) -> None:
    missing = UUID(int=0)
    item = _dead_letter()
    store = PostgresQueueReapStore(migrated_pool)
    with pytest.raises(LookupError, match="no project"):
        await store.park_dead_letter(missing, item, _park_verdict(item), origin_owned=True)
    with pytest.raises(LookupError, match="no project"):
        await store.record_sighting(missing, _sighting())
    with pytest.raises(LookupError, match="no project"):
        await store.record_cleared(missing, _sighting())


# -- #1108 review, finding 8: one bad row never blocks the rest ------------------------


class _FailingFor:
    """An appender that refuses one job's event, as a row the ledger will not take."""

    def __init__(self, job_id: UUID) -> None:
        from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER

        self._job_id = job_id
        self._inner = DEFAULT_EVENT_APPENDER

    async def append(self, conn: object, draft: object) -> object:
        if getattr(draft, "job_id", None) == self._job_id:
            raise RuntimeError("the ledger refused this one")
        return await self._inner.append(conn, draft)  # type: ignore[arg-type]


async def test_a_lease_that_cannot_be_reaped_rolls_back_alone(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    from vibey.domain.errors import LeaseReapIncomplete

    repo = PostgresJobRepository(migrated_pool)
    bad = await repo.enqueue(_request(project_id, "bad"))
    good = await repo.enqueue(_request(project_id, "good"))
    await repo.claim(project_id, owner="w1", lease=EXPIRED)
    await repo.claim(project_id, owner="w2", lease=EXPIRED)
    store = PostgresQueueReapStore(migrated_pool, appender=_FailingFor(bad.id))  # type: ignore[arg-type]

    with pytest.raises(LeaseReapIncomplete) as caught:
        await store.reap_leases()

    assert [v.subject for v in caught.value.reaped] == [str(good.id)]  # type: ignore[attr-defined]
    (failure,) = caught.value.failures
    assert failure.startswith(f"{bad.id}: RuntimeError: the ledger refused this one")
    kept = await repo.get(bad.id)
    moved = await repo.get(good.id)
    assert kept is not None and kept.state is JobState.LEASED, "its transaction rolled back"
    assert moved is not None and moved.state is JobState.READY
    assert [e["job_id"] for e in await _events(migrated_pool, project_id)] == [good.id]


async def test_p4_concurrent_reapers_across_projects_never_deadlock(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """P4: eight reapers over six projects' expired leases deadlocked twice in fifteen
    rounds, because one transaction held several projects' ledgers. One lease per
    transaction holds one."""
    projects = [project_id]
    async with migrated_pool.acquire() as conn:
        for k in range(5):
            projects.append(
                await conn.fetchval(
                    "INSERT INTO project (name, repo_path, config) "
                    "VALUES ($1, $2, '{}'::jsonb) RETURNING id",
                    f"p{k}",
                    f"/tmp/p{k}",
                )
            )
    repo = PostgresJobRepository(migrated_pool)
    reaped = 0
    for rnd in range(6):
        for n in range(8):
            for p in projects:
                await repo.enqueue(_request(p, f"r{rnd}-{n}-{p}", max_attempts=99))
                await repo.claim(p, owner=f"w{n}", lease=EXPIRED)
        results = await asyncio.gather(
            *(PostgresQueueReapStore(migrated_pool).reap_leases() for _ in range(8)),
            return_exceptions=True,
        )
        failed = [r for r in results if isinstance(r, BaseException)]
        assert failed == [], failed
        reaped += sum(len(r) for r in results if isinstance(r, tuple))
    assert reaped == 6 * 8 * len(projects)
