# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority against real Postgres (ADR-0054): the claim order a bump makes, the
dependency pull-forward, the no-preemption rule, the ledger record, and the order
holding under `FOR UPDATE SKIP LOCKED` with workers claiming at once."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.interfaces import JobPriorityStore
from vibey.domain.errors import DependencyCycle, NotReorderable, UnknownJob
from vibey.domain.job import JobState, UnrecognizedJobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import (
    CLAIM_ORDER,
    OPERATOR_SOURCE,
    PriorityAction,
    PriorityChange,
    PriorityRefusal,
    QueuedJob,
)
from vibey.infrastructure.db.interfaces import (
    JobRowMapperInterface,
    PriorityEventDraftBuilderInterface,
)
from vibey.infrastructure.db.job_priority_repository import (
    PRIORITY_EVENT_DRAFTS,
    PostgresJobPriorityStore,
)
from vibey.infrastructure.db.job_repository import JOB_ROWS, PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft

LEASE = timedelta(seconds=30)
AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _request(project_id: UUID, subject: str, **overrides: object) -> EnqueueRequest:
    fields: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": "build.implement",
        "idempotency_key": f"key-{subject}",
        "payload": {"subject": subject},
        "work_item_id": subject,
    }
    fields.update(overrides)
    return EnqueueRequest(**fields)  # type: ignore[arg-type]


async def _enqueue(repo: PostgresJobRepository, project_id: UUID, *subjects: str) -> list[UUID]:
    return [(await repo.enqueue(_request(project_id, s))).id for s in subjects]


async def _claim_all(repo: PostgresJobRepository, project_id: UUID) -> list[UUID]:
    """Claim one at a time until nothing is claimable; the order the queue gave."""
    claimed: list[UUID] = []
    while (job := await repo.claim(project_id, owner="w", lease=LEASE)) is not None:
        claimed.append(job.id)
    return claimed


async def _events(pool: asyncpg.Pool, project_id: UUID) -> list[LedgerEvent]:
    return [
        e
        for e in await PostgresLedgerRepository(pool).all_for_project(project_id)
        if e.kind
        in {
            EventKind.JOB_PRIORITY_BUMPED,
            EventKind.JOB_PRIORITY_UNBUMPED,
            EventKind.JOB_PRIORITY_REFUSED,
        }
    ]


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(PRIORITY_EVENT_DRAFTS, PriorityEventDraftBuilderInterface)
    assert isinstance(JOB_ROWS, JobRowMapperInterface)


# -- the claim order a bump makes ---------------------------------------------------


async def test_a_bumped_job_is_claimed_next_ahead_of_everything_waiting(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    assert isinstance(store, JobPriorityStore)
    first, second, third = await _enqueue(repo, project_id, "a", "b", "c")
    urgent = (await repo.enqueue(_request(project_id, "urgent", priority=-10))).id

    change = await store.bump(urgent, source=OPERATOR_SOURCE, at=AT)

    assert change.changed
    assert [m.job_id for m in change.moved] == [urgent]
    assert change.moved[0].previous is None
    assert change.moved[0].bump_seq is not None
    assert await _claim_all(repo, project_id) == [urgent, first, second, third]


async def test_bumped_jobs_run_in_the_order_they_were_bumped(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    a, b, c, d = await _enqueue(repo, project_id, "a", "b", "c", "d")
    high = (await repo.enqueue(_request(project_id, "high", priority=50))).id

    await store.bump(d, source=OPERATOR_SOURCE, at=AT)
    await store.bump(b, source=OPERATOR_SOURCE, at=AT)

    assert await _claim_all(repo, project_id) == [d, b, high, a, c]


async def test_a_bump_pulls_its_unfinished_dependencies_forward_and_never_jumps_them(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    other = (await repo.enqueue(_request(project_id, "other"))).id
    base = (await repo.enqueue(_request(project_id, "base"))).id
    done = (await repo.enqueue(_request(project_id, "done"))).id
    claimed = await repo.claim(project_id, owner="w", lease=LEASE)
    assert claimed is not None and claimed.id == other
    # `done` must finish first: bump it alone, claim it, ack it.
    await store.bump(done, source=OPERATOR_SOURCE, at=AT)
    got = await repo.claim(project_id, owner="w", lease=LEASE)
    assert got is not None and got.id == done
    await repo.ack(done, owner="w")
    await repo.ack(other, owner="w")
    tail = (await repo.enqueue(_request(project_id, "tail"))).id
    middle = (
        await repo.enqueue(_request(project_id, "middle", depends_on=(base, done), priority=-1))
    ).id
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(middle,)))).id

    change = await store.bump(target, source=OPERATOR_SOURCE, at=AT)

    assert [m.job_id for m in change.moved] == [base, middle, target]
    seqs = [m.bump_seq for m in change.moved]
    assert seqs == sorted(seqs)
    first = await repo.claim(project_id, owner="w", lease=LEASE)
    assert first is not None and first.id == base
    # `middle` and `target` wait on `base`: the queue hands out `tail` meanwhile.
    stalled = await repo.claim(project_id, owner="w", lease=LEASE)
    assert stalled is not None and stalled.id == tail
    await repo.ack(base, owner="w")
    assert await _claim_all(repo, project_id) == [middle]
    await repo.ack(middle, owner="w")
    assert await _claim_all(repo, project_id) == [target]


async def test_a_bump_never_preempts_the_job_that_is_running(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    running, waiting = await _enqueue(repo, project_id, "running", "waiting")
    leased = await repo.claim(project_id, owner="w-1", lease=LEASE)
    assert leased is not None and leased.id == running

    await store.bump(waiting, source=OPERATOR_SOURCE, at=AT)
    change = await store.bump(running, source=OPERATOR_SOURCE, at=AT)

    after = await repo.get(running)
    assert after is not None
    assert after.state is JobState.LEASED
    assert after.lease_owner == "w-1"
    assert after.lease_expires_at == leased.lease_expires_at
    assert after.bump_seq == change.moved[0].bump_seq
    # The running job keeps its place if its attempt returns it to the queue --
    # behind the job bumped before it, ahead of everything else.
    assert await repo.nack(running, owner="w-1", error={"why": "flaky"})
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET run_after = now() WHERE id = $1", running)
    assert await _claim_all(repo, project_id) == [waiting, running]


async def test_a_bump_changes_order_only_and_never_shortens_a_deferral(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    later = (
        await repo.enqueue(
            _request(project_id, "later", run_after=datetime.now(UTC) + timedelta(hours=1))
        )
    ).id
    now = (await repo.enqueue(_request(project_id, "now"))).id

    await store.bump(later, source=OPERATOR_SOURCE, at=AT)

    assert await _claim_all(repo, project_id) == [now]
    record = await repo.get(later)
    assert record is not None and record.state is JobState.READY and record.bump_seq is not None


async def test_bumping_a_parked_job_keeps_it_parked_until_its_gate_is_answered(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    parked, other = await _enqueue(repo, project_id, "parked", "other")
    got = await repo.claim(project_id, owner="w", lease=LEASE)
    assert got is not None and got.id == parked
    assert await repo.park(parked, owner="w")

    await store.bump(parked, source=OPERATOR_SOURCE, at=AT)

    assert await _claim_all(repo, project_id) == [other]
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET state = 'ready' WHERE id = $1", parked)
    assert await _claim_all(repo, project_id) == [parked]


# -- what a bump refuses, and replay --------------------------------------------------


async def test_a_finished_job_cannot_be_bumped_and_nothing_is_recorded(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "done")
    await repo.claim(project_id, owner="w", lease=LEASE)
    await repo.ack(job, owner="w")

    with pytest.raises(NotReorderable, match="succeeded"):
        await store.bump(job, source=OPERATOR_SOURCE, at=AT)
    with pytest.raises(NotReorderable, match="succeeded"):
        await store.unbump(job, source=OPERATOR_SOURCE, at=AT)
    assert await _events(migrated_pool, project_id) == []


async def test_an_unknown_job_is_reported_not_guessed(migrated_pool: asyncpg.Pool) -> None:
    store = PostgresJobPriorityStore(migrated_pool)
    missing = uuid4()
    with pytest.raises(UnknownJob) as caught:
        await store.bump(missing, source=OPERATOR_SOURCE, at=AT)
    assert caught.value.job_id == missing
    with pytest.raises(UnknownJob):
        await store.unbump(missing, source=OPERATOR_SOURCE, at=AT)


async def test_a_replayed_bump_is_a_no_op_and_is_recorded_once(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")

    first = await store.bump(job, source=OPERATOR_SOURCE, at=AT)
    again = await store.bump(job, source=OPERATOR_SOURCE, at=AT)

    assert first.changed and not again.changed
    assert again.kept == (job,)
    record = await repo.get(job)
    assert record is not None and record.bump_seq == first.moved[0].bump_seq
    assert len(await _events(migrated_pool, project_id)) == 1


async def test_a_dependency_ring_is_refused_and_nothing_changes(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    a, b = await _enqueue(repo, project_id, "a", "b")
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO job_dependency VALUES ($1, $2), ($2, $1)",
            a,
            b,
        )

    with pytest.raises(DependencyCycle):
        await store.bump(a, source=OPERATOR_SOURCE, at=AT)
    record = await repo.get(a)
    assert record is not None and record.bump_seq is None


async def test_a_job_in_a_phase_this_vibey_does_not_know_is_not_written(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")
    async with migrated_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE 'triage'")
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET phase = 'triage' WHERE id = $1", job)

    with pytest.raises(NotReorderable, match="triage"):
        await store.bump(job, source=OPERATOR_SOURCE, at=AT)
    with pytest.raises(NotReorderable, match="triage"):
        await store.unbump(job, source=OPERATOR_SOURCE, at=AT)


# -- the ledger record ----------------------------------------------------------------


async def test_a_bump_appends_one_event_listing_everything_it_moved(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    dep = (await repo.enqueue(_request(project_id, "dep"))).id
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id

    change = await store.bump(target, source="storm", at=AT, action=PriorityAction.ENQUEUE)

    (event,) = await _events(migrated_pool, project_id)
    assert event.kind is EventKind.JOB_PRIORITY_BUMPED
    assert event.job_id == target
    assert event.phase is Phase.BUILD
    assert event.cycle == 1
    assert event.provenance is Provenance.TRUSTED
    assert event.produced_at == AT
    assert event.payload == {
        "action": "enqueue",
        "source": "storm",
        "target": str(target),
        "moved": [
            {"job_id": str(m.job_id), "bump_seq": m.bump_seq, "previous": None}
            for m in change.moved
        ],
        "kept": [],
        "blocked_by": [],
    }


async def test_the_rows_and_the_event_commit_together_or_not_at_all(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    class Failing:
        async def append(
            self,
            conn: asyncpg.pool.PoolConnectionProxy | asyncpg.Connection,
            draft: LedgerEventDraft,
        ) -> LedgerEvent:
            raise RuntimeError("the ledger is unreachable")

    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool, appender=Failing())
    (job,) = await _enqueue(repo, project_id, "x")

    with pytest.raises(RuntimeError, match="unreachable"):
        await store.bump(job, source=OPERATOR_SOURCE, at=AT)
    record = await repo.get(job)
    assert record is not None and record.bump_seq is None


async def test_a_refusal_is_recorded_as_untrusted_with_its_reason(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")

    await store.refuse(
        PriorityRefusal(
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            job_id=job,
            action=PriorityAction.BUMP,
            source="github-label",
            reason="not declared",
        ),
        at=AT,
    )
    await store.refuse(
        PriorityRefusal(
            project_id=project_id,
            cycle=2,
            phase=Phase.REVIEW,
            job_id=None,
            action=PriorityAction.ENQUEUE,
            source="issue-comment",
            reason="not declared",
        ),
        at=AT,
    )

    first, second = await _events(migrated_pool, project_id)
    assert first.kind is EventKind.JOB_PRIORITY_REFUSED
    assert first.provenance is Provenance.UNTRUSTED
    assert first.job_id == job
    assert first.payload == {
        "action": "bump",
        "source": "github-label",
        "target": str(job),
        "reason": "not declared",
    }
    assert second.job_id is None
    assert second.phase is Phase.REVIEW
    assert second.payload["target"] is None
    record = await repo.get(job)
    assert record is not None and record.bump_seq is None


# -- un-bumping -------------------------------------------------------------------------


async def test_an_unbump_returns_the_job_and_its_bumped_dependents_to_normal_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    plain = (await repo.enqueue(_request(project_id, "plain"))).id
    dep = (await repo.enqueue(_request(project_id, "dep"))).id
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id
    await store.bump(target, source=OPERATOR_SOURCE, at=AT)

    change = await store.unbump(dep, source="storm", at=AT)

    assert change.action is PriorityAction.UNBUMP
    assert [m.job_id for m in change.moved] == [dep, target]
    assert all(m.bump_seq is None and m.previous is not None for m in change.moved)
    unbumped = (await _events(migrated_pool, project_id))[-1]
    assert unbumped.kind is EventKind.JOB_PRIORITY_UNBUMPED
    assert unbumped.payload["source"] == "storm"
    assert await _claim_all(repo, project_id) == [plain, dep]


async def test_unbumping_a_job_that_is_not_bumped_moves_and_records_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")

    change = await store.unbump(job, source=OPERATOR_SOURCE, at=AT)

    assert not change.changed
    assert await _events(migrated_pool, project_id) == []


# -- the queue as the operator sees it ----------------------------------------------------


async def test_the_queue_lists_running_work_then_waiting_work_in_claim_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    running, done, plain, dep = await _enqueue(repo, project_id, "running", "done", "plain", "dep")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id
    await repo.claim(project_id, owner="w", lease=LEASE)
    got = await repo.claim(project_id, owner="w", lease=LEASE)
    assert got is not None and got.id == done
    await repo.ack(done, owner="w")
    await store.bump(target, source=OPERATOR_SOURCE, at=AT)
    async with migrated_pool.acquire() as conn:
        await conn.execute("ALTER TYPE job_state ADD VALUE 'quarantined'")
    stranger = (await repo.enqueue(_request(project_id, "stranger"))).id
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET state = 'quarantined' WHERE id = $1", stranger)

    entries = await store.queue(project_id)

    assert [e.job.id for e in entries] == [running, dep, target, plain, stranger]
    assert entries[0].job.state is JobState.LEASED
    assert entries[2].waiting_on == (dep,)
    assert entries[1].waiting_on == ()
    assert entries[4].job.state == UnrecognizedJobState("quarantined")
    assert await store.queue(uuid4()) == ()


# -- concurrency: SKIP LOCKED keeps the order -------------------------------------------


async def test_concurrent_claims_under_skip_locked_take_the_front_of_the_queue_in_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    subjects = [f"job-{n:02d}" for n in range(12)]
    ids = await _enqueue(repo, project_id, *subjects)
    bumped = [ids[9], ids[2], ids[7]]
    for job in bumped:
        await store.bump(job, source=OPERATOR_SOURCE, at=AT)
    expected = bumped + [j for j in ids if j not in bumped]

    workers = 5
    first_wave = await asyncio.gather(
        *(repo.claim(project_id, owner=f"w-{n}", lease=LEASE) for n in range(workers))
    )

    taken = {job.id for job in first_wave if job is not None}
    assert len(taken) == workers, "SKIP LOCKED gave two workers one job, or one none"
    assert taken == set(expected[:workers])
    assert await _claim_all(repo, project_id) == expected[workers:]


async def test_concurrent_bumps_draw_distinct_places_and_keep_their_bump_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    ids = await _enqueue(repo, project_id, *(f"j{n}" for n in range(8)))

    changes = await asyncio.gather(
        *(store.bump(job, source=OPERATOR_SOURCE, at=AT) for job in ids[::-1])
    )

    by_seq = sorted(changes, key=lambda c: c.moved[0].bump_seq or 0)
    assert len({c.moved[0].bump_seq for c in changes}) == len(ids)
    assert await _claim_all(repo, project_id) == [c.target for c in by_seq]


async def test_a_bump_waits_for_a_claim_holding_the_row_then_sees_it_running(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "contended")

    async with migrated_pool.acquire() as holder:
        tx = holder.transaction()
        await tx.start()
        await holder.execute("SELECT 1 FROM job WHERE id = $1 FOR UPDATE", job)
        bump = asyncio.create_task(store.bump(job, source=OPERATOR_SOURCE, at=AT))
        await asyncio.sleep(0.3)
        assert not bump.done(), "the bump read a row a claim still held"
        await holder.execute(
            """UPDATE job SET state = 'leased', lease_owner = 'w',
               lease_expires_at = now() + interval '30 seconds' WHERE id = $1""",
            job,
        )
        await tx.commit()
    change: PriorityChange = await bump

    assert [m.job_id for m in change.moved] == [job]
    record = await repo.get(job)
    assert record is not None and record.state is JobState.LEASED
    assert record.lease_owner == "w"


async def test_the_domain_claim_order_is_the_claim_query_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """`ClaimOrder` is the planner's picture of the claim query. If the two ever
    disagree, pulled dependencies stop keeping their relative order, so pin them."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    past = datetime.now(UTC) - timedelta(minutes=5)
    specs = [(p, s) for p in (-1, 0, 2) for s in (0, 30, 30, 60)]
    ids: list[UUID] = []
    for n, (priority, offset) in enumerate(specs):
        request = _request(
            project_id, f"s{n}", priority=priority, run_after=past + timedelta(seconds=offset)
        )
        ids.append((await repo.enqueue(request)).id)
    for job in (ids[4], ids[0], ids[11]):
        await store.bump(job, source=OPERATOR_SOURCE, at=AT)
    snapshot: list[QueuedJob] = []
    for job in ids:
        record: JobRecord | None = await repo.get(job)
        assert record is not None
        snapshot.append(
            QueuedJob(
                id=record.id,
                state=record.state,
                priority=record.priority,
                run_after=record.run_after,
                bump_seq=record.bump_seq,
            )
        )

    assert await _claim_all(repo, project_id) == [j.id for j in CLAIM_ORDER.sort(snapshot)]
