# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The #1108 post-merge review's probes, as regression tests (ADR-0056).

Each is the reviewer's probe end to end -- the real reaper, the real PostgreSQL store and
ledger, the in-memory bus with the adapter's semantics -- with its assertion turned from
"the finding reproduces" to "it is fixed". P4 (concurrent reapers deadlocking) is in
test_queue_reap_store.py and P7 (a queue gate's answer read as the job's) in
test_queue_gate_answers.py.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg

from vibey.application.dto import EnqueueRequest
from vibey.application.queue_reaper import QueueReaper
from vibey.domain.config import QueueReapConfig
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.infrastructure.bus.in_memory import InMemoryBus
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.queue_reap_store import PostgresQueueReapStore

EXPIRED = timedelta(seconds=-1)


class _Clock:
    def __init__(self) -> None:
        self.t = datetime(2026, 9, 24, tzinfo=UTC)

    def now(self) -> datetime:
        return self.t


class _Log:
    def bind(self, **kw: Any) -> "_Log":
        return self

    def debug(self, event: str, **kw: Any) -> None:
        pass

    def info(self, event: str, **kw: Any) -> None:
        pass

    def warning(self, event: str, **kw: Any) -> None:
        pass

    def error(self, event: str, **kw: Any) -> None:
        pass


async def _new_project(pool: asyncpg.Pool, name: str) -> UUID:
    async with pool.acquire() as conn:
        pid = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) "
            "RETURNING id",
            name,
            f"/tmp/{name}",
        )
    return UUID(str(pid))


async def _reaped(pool: asyncpg.Pool) -> list[dict[str, object]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT payload FROM event WHERE kind = 'QueueReaped' ORDER BY produced_at, seq"
        )
    return [json.loads(r["payload"]) for r in rows]


async def _dl_jobs(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch("SELECT project_id, payload FROM job WHERE kind = 'bus.dead_letter'")
        )


def _reaper(pool: asyncpg.Pool, bus: InMemoryBus, clock: _Clock) -> QueueReaper:
    return QueueReaper(
        store=PostgresQueueReapStore(pool),
        bus=bus,
        config=QueueReapConfig(),
        clock=clock,
        logger=_Log(),
    )


async def _dead_letters(bus: InMemoryBus, queue: str, n: int, start: int = 0) -> None:
    await bus.declare_queue(queue)
    for i in range(start, start + n):
        await bus.publish(queue, {"i": i})
    for _ in range(n):
        await bus.reject(queue)


async def test_p1_one_broker_two_projects_one_park(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Before: two `bus.dead_letter` jobs and two gates for one dead letter."""
    other = await _new_project(migrated_pool, "other")
    clock = _Clock()
    bus = InMemoryBus(clock=clock.now)
    await _dead_letters(bus, "vibey.shared", 1)
    await _reaper(migrated_pool, bus, clock).run(project_id)
    await _reaper(migrated_pool, bus, clock).run(other)
    jobs = await _dl_jobs(migrated_pool)
    async with migrated_pool.acquire() as conn:
        gates = await conn.fetchval(
            "SELECT count(*) FROM human_gate WHERE kind = 'bus_dead_lettered'"
        )
    assert (len(jobs), gates) == (1, 1)


async def test_p2_every_dead_letter_is_parked_and_growth_is_recorded(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Before: 100 of 180 ever parked, and the remainder's growth (50 to 80) recorded once."""
    clock = _Clock()
    bus = InMemoryBus(clock=clock.now)
    await _dead_letters(bus, "vibey.capq", 150)
    reaper = _reaper(migrated_pool, bus, clock)

    first = await reaper.run(project_id)
    second = await reaper.run(project_id)
    await _dead_letters(bus, "vibey.capq", 130, start=150)
    third = await reaper.run(project_id)
    fourth = await reaper.run(project_id)

    assert [len(r.acted) for r in (first, second, third, fourth)] == [100, 50, 100, 30]
    parked = sorted(json.loads(j["payload"])["payload"]["i"] for j in await _dl_jobs(migrated_pool))
    assert parked == list(range(280))
    unread = [e for e in await _reaped(migrated_pool) if "past the read limit" in str(e["unit"])]
    assert [(e["action"], e["episode"]) for e in unread] == [
        ("surface", "50"),
        ("cleared", "50"),
        ("surface", "30"),
        ("cleared", "30"),
    ]


async def test_p3_one_continuous_sighting_is_one_event(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Before: three `stale_ready` events for one sighting -- two pods and the CLI."""
    clock = _Clock()
    bus = InMemoryBus(clock=clock.now)
    await bus.declare_queue("vibey.stale", dead_letter=False)
    await bus.publish("vibey.stale", {"x": 1})
    clock.t += timedelta(hours=1)
    pod_a, pod_b = _reaper(migrated_pool, bus, clock), _reaper(migrated_pool, bus, clock)
    await pod_a.run(project_id)
    await pod_a.run(project_id)
    await pod_b.run(project_id)
    await _reaper(migrated_pool, bus, clock).run(project_id)  # `vibey queue reap`
    stale = [e for e in await _reaped(migrated_pool) if e["condition"] == "stale_ready"]
    assert len(stale) == 1
    assert stale[0]["source"] == "broker"


async def test_p5_a_live_handler_that_outlives_its_last_lease_is_parked_and_fenced(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Pinned, not a defect: a handler that lets its lease lapse -- no heartbeat, which a
    live worker sends every third of the lease -- has lost the job. At its last attempt
    that is a park; its late heartbeat and ack are refused by the lease fence, exactly as
    the requeue's always were. The gate asks a person; no work is committed twice."""
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            kind="build.implement",
            idempotency_key="slow",
            max_attempts=1,
        )
    )
    await repo.claim(project_id, owner="alive", lease=EXPIRED)
    await repo.reap()
    assert not await repo.heartbeat(job.id, owner="alive", lease=timedelta(minutes=5))
    assert not await repo.ack(job.id, owner="alive")
    record = await repo.get(job.id)
    assert record is not None and record.state is JobState.AWAITING_HUMAN


async def test_p6_the_lease_reap_is_bounded_even_with_the_reaper_switched_off(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Pinned and documented (ADR-0056, configuration.md): `enabled = false` switches off
    the reaper's own pass -- claimable-work and broker sightings -- but not the lease reap.
    That is the job queue's crash recovery, which predates ADR-0056 and cannot be turned
    off without stranding every dead worker's job; its bound, the park, comes with it."""
    config = QueueReapConfig(enabled=False)
    repo = PostgresJobRepository(migrated_pool, reap_thresholds=config.thresholds())
    job = await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            kind="build.implement",
            idempotency_key="dis",
            max_attempts=1,
        )
    )
    await repo.claim(project_id, owner="w", lease=EXPIRED)
    await repo.reap()
    record = await repo.get(job.id)
    assert record is not None and record.state is JobState.AWAITING_HUMAN
