# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The dispatch store on PostgreSQL (ADR-0079): slots counted across workers from the
queue's own leases, holds once per job and attempt, and a daily cap that stays exact
when several workers reserve at once."""

from __future__ import annotations

import asyncio
import dataclasses
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest, JobRecord, ProjectRecord
from vibey.application.interfaces import EngineDispatchStorePort
from vibey.domain.engine import EngineId
from vibey.domain.engine_dispatch import LocalSession
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.infrastructure.db.engine_dispatch_store import PostgresEngineDispatchStore
from vibey.infrastructure.db.interfaces.engine_dispatch_store_interface import (
    PostgresEngineDispatchStoreInterface,
)
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft

LEASE = timedelta(minutes=10)
EXPIRED = timedelta(seconds=-1)
NOW = datetime.now(UTC)
DAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)


def _request(project_id: UUID, subject: str) -> EnqueueRequest:
    return EnqueueRequest(
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        kind="build.implement",
        idempotency_key=f"key-{subject}",
    )


async def _kinds(pool: asyncpg.Pool, project_id: UUID, kind: EventKind) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "SELECT * FROM event WHERE project_id = $1 AND kind = $2 ORDER BY seq",
                project_id,
                kind.value,
            )
        )


async def _claimed(
    repo: PostgresJobRepository, project_id: UUID, owner: str, engine: EngineId
) -> JobRecord:
    job = await repo.claim(project_id, owner=owner, lease=LEASE)
    assert job is not None
    assert await repo.assign_engine(job.id, owner=owner, engine_id=engine)
    return job


def test_the_store_satisfies_its_seams() -> None:
    store = PostgresEngineDispatchStore(None)  # type: ignore[arg-type]
    assert isinstance(store, PostgresEngineDispatchStoreInterface)
    assert isinstance(store, EngineDispatchStorePort)


async def test_slots_are_counted_across_two_workers_from_live_leases_only(
    migrated_pool: asyncpg.Pool, owner_pool: asyncpg.Pool, project_id: UUID
) -> None:
    worker_a = PostgresJobRepository(migrated_pool)
    worker_b = PostgresJobRepository(migrated_pool)
    for subject in ("one", "two", "three", "four", "five", "six"):
        await worker_a.enqueue(_request(project_id, subject))

    # Two workers claim under FOR UPDATE SKIP LOCKED: each gets its own rows, never one twice.
    first, second = await asyncio.gather(
        _claimed(worker_a, project_id, "worker-a", EngineId.GPTOSSLOOP),
        _claimed(worker_b, project_id, "worker-b", EngineId.GPTOSSLOOP),
    )
    assert first.id != second.id
    await _claimed(worker_b, project_id, "worker-b", EngineId.CLAUDELOOP)
    selecting = await worker_a.claim(project_id, owner="worker-a", lease=LEASE)
    assert selecting is not None
    # A lease that expired is no slot in use: its worker is gone.
    gone = await _claimed(worker_a, project_id, "worker-a", EngineId.GPTOSSLOOP)
    async with owner_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET lease_expires_at = now() - interval '1 second' WHERE id = $1",
            gone.id,
        )
    # An engine a newer vibey assigned is not counted by this one.
    martian = await worker_b.claim(project_id, owner="worker-b", lease=LEASE)
    assert martian is not None
    async with owner_pool.acquire() as conn:
        await conn.execute("UPDATE job SET assigned_engine = 'martian' WHERE id = $1", martian.id)

    store = PostgresEngineDispatchStore(migrated_pool)
    taken = await store.in_flight(excluding=selecting.id)
    assert taken == {EngineId.GPTOSSLOOP: 2, EngineId.CLAUDELOOP: 1}
    # The job being selected never counts against itself.
    assert (await store.in_flight(excluding=first.id))[EngineId.GPTOSSLOOP] == 1


async def test_a_hold_is_recorded_once_per_job_and_attempt(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id, "held"))
    job = await repo.claim(project_id, owner="w", lease=LEASE)
    assert job is not None
    store = PostgresEngineDispatchStore(migrated_pool)
    assert await store.slot_wait_started(project_id, job.id, job.attempts) is None

    started = await store.record_slot_wait(job, payload={"attempt": job.attempts}, at=NOW)
    again = await store.record_slot_wait(
        job, payload={"attempt": job.attempts}, at=NOW + timedelta(minutes=1)
    )
    assert started == again
    assert await store.slot_wait_started(project_id, job.id, job.attempts) == started
    # The next attempt waits afresh.
    assert await store.slot_wait_started(project_id, job.id, job.attempts + 1) is None

    (event,) = await _kinds(migrated_pool, project_id, EventKind.ENGINE_SLOT_WAIT_STARTED)
    assert event["job_id"] == job.id and event["provenance"] == "trusted"
    assert event["phase"] == "build" and event["engine_id"] is None


async def test_the_cap_is_exact_when_several_workers_reserve_at_once(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    jobs: list[JobRecord] = []
    for i in range(8):
        await repo.enqueue(_request(project_id, f"overflow-{i}"))
        claimed = await repo.claim(project_id, owner=f"w{i}", lease=LEASE)
        assert claimed is not None
        jobs.append(claimed)
    stores = [PostgresEngineDispatchStore(migrated_pool) for _ in jobs]

    granted = await asyncio.gather(
        *(
            store.reserve_overflow(
                job,
                engine_id=EngineId.CLAUDELOOP,
                payload={"reason": "every eligible local slot is occupied"},
                cap=3,
                since=DAY,
                at=NOW,
            )
            for store, job in zip(stores, jobs, strict=True)
        )
    )
    assert sorted(granted) == [False] * 5 + [True] * 3
    events = await _kinds(migrated_pool, project_id, EventKind.ENGINE_OVERFLOW_SELECTED)
    assert len(events) == 3
    remaining = sorted(json.loads(e["payload"])["cap_remaining_after"] for e in events)
    assert remaining == [0, 1, 2]
    assert all(e["engine_id"] == "claudeloop" for e in events)
    assert await stores[0].paid_overflow_count(project_id, since=DAY) == 3
    # Yesterday's overflows are not today's.
    assert await stores[0].paid_overflow_count(project_id, since=NOW + timedelta(days=1)) == 0


async def test_measurements_are_appended_and_the_latest_is_read(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresEngineDispatchStore(migrated_pool)
    assert await store.latest_measurement(project_id) is None
    await store.record_measurement(project_id, payload={"winner": "singleton"}, at=NOW)
    await store.record_measurement(project_id, payload={"winner": "hybrid"}, at=NOW)
    assert await store.latest_measurement(project_id) == {"winner": "hybrid"}
    events = await _kinds(migrated_pool, project_id, EventKind.ENGINE_DISPATCH_MEASURED)
    assert len(events) == 2, "append-only: a new measurement never replaces an old one"


async def test_a_record_for_an_unknown_project_is_refused(migrated_pool: asyncpg.Pool) -> None:
    store = PostgresEngineDispatchStore(migrated_pool)
    with pytest.raises(UnknownProject):
        await store.record_measurement(uuid4(), payload={}, at=NOW)


async def test_local_sessions_are_each_jobs_first_and_last_build_event(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    ledger = PostgresLedgerRepository(migrated_pool)
    job_a, job_b = uuid4(), uuid4()

    async def event(
        job_id: UUID | None, engine: EngineId | None, minutes: int, phase: Phase = Phase.BUILD
    ) -> None:
        payload: dict[str, object] = {"n": minutes}
        await ledger.append(
            LedgerEventDraft(
                project_id=project_id,
                cycle=1,
                phase=phase,
                kind=EventKind.TURN_COMPLETED,
                engine_id=engine,
                job_id=job_id,
                causation_id=None,
                correlation_id=uuid4(),
                provenance=Provenance.AGENT,
                produced_at=NOW + timedelta(minutes=minutes),
                payload=payload,
                digest=digest_event(payload),
            )
        )

    await event(job_a, EngineId.GPTOSSLOOP, 0)
    await event(job_a, EngineId.GPTOSSLOOP, 30)
    await event(job_b, EngineId.GPTOSSLOOP, 10)
    await event(job_b, EngineId.GPTOSSLOOP, 50)
    await event(job_b, EngineId.CLAUDELOOP, 20)  # not a local engine asked about
    await event(None, EngineId.GPTOSSLOOP, 25)  # no job
    await event(job_a, EngineId.GPTOSSLOOP, 40, Phase.REVIEW)  # not BUILD
    await event(job_a, EngineId.GPTOSSLOOP, 200)  # outside the window

    store = PostgresEngineDispatchStore(migrated_pool)
    sessions = await store.local_sessions(
        project_id,
        (EngineId.GPTOSSLOOP,),
        since=NOW - timedelta(minutes=1),
        until=NOW + timedelta(minutes=100),
    )
    assert sorted(sessions, key=lambda s: s.started_at) == [
        LocalSession(EngineId.GPTOSSLOOP, NOW, NOW + timedelta(minutes=30)),
        LocalSession(EngineId.GPTOSSLOOP, NOW + timedelta(minutes=10), NOW + timedelta(minutes=50)),
    ]


# --- a phase this vibey does not know records nothing --------------------------------


class _Conn:
    async def fetchrow(self, query: str, *args: object) -> object:
        return {"row": True}

    @asynccontextmanager
    async def transaction(self):  # type: ignore[no-untyped-def]
        yield


class _Pool:
    @asynccontextmanager
    async def acquire(self):  # type: ignore[no-untyped-def]
        yield _Conn()


class _Rows:
    def __init__(self, record: ProjectRecord) -> None:
        self.record = record

    def to_record(self, row: object) -> ProjectRecord:
        return self.record


async def test_an_unknown_project_phase_records_no_measurement() -> None:
    record = ProjectRecord(
        project_id=uuid4(),
        name="p",
        repo_path=Path("/w/p"),
        phase=UnrecognizedPhase("hyperspace"),
        cycle=1,
        max_cycles=3,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    store = PostgresEngineDispatchStore(_Pool(), rows=_Rows(record))  # type: ignore[arg-type]
    with pytest.raises(WrongPhase, match="hyperspace"):
        await store.record_measurement(record.project_id, payload={}, at=NOW)


async def test_a_job_of_an_unknown_phase_records_no_hold_and_no_overflow(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id, "odd"))
    job = await repo.claim(project_id, owner="w", lease=LEASE)
    assert job is not None
    odd = dataclasses.replace(job, phase=UnrecognizedPhase("hyperspace"))
    store = PostgresEngineDispatchStore(migrated_pool)
    with pytest.raises(WrongPhase, match="hyperspace"):
        await store.record_slot_wait(odd, payload={}, at=NOW)
    with pytest.raises(WrongPhase, match="hyperspace"):
        await store.reserve_overflow(
            odd, engine_id=EngineId.CLAUDELOOP, payload={}, cap=1, since=DAY, at=NOW
        )
