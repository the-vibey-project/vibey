# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority against real Postgres (ADR-0054): the claim order a bump makes, the
dependency pull-forward, the no-preemption rule, un-bump undoing exactly what a bump
moved, every request on the ledger, the locks it takes, and the order holding under
`FOR UPDATE SKIP LOCKED` with workers claiming at once."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.interfaces import JobPriorityStore
from vibey.domain.errors import (
    DependencyCannotFinish,
    DependencyCycle,
    DependentsStillBumped,
    NotReorderable,
    ReorderConflict,
    UnknownJob,
)
from vibey.domain.job import JobState, UnrecognizedJobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.domain.queue_priority import (
    CLAIM_ORDER,
    PriorityAction,
    PriorityChange,
    PriorityContext,
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
from vibey.infrastructure.db.job_repository import JOB_ROWS, STRICT_JOB_ROWS, PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import (
    DEFAULT_EVENT_APPENDER,
    PostgresLedgerRepository,
)
from vibey.infrastructure.engines.tailer import LedgerEventDraft

LEASE = timedelta(seconds=30)
AT = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _context(project_id: UUID, by: str = "operator:adam") -> PriorityContext:
    return PriorityContext(project_id=project_id, cycle=1, phase=Phase.BUILD, requested_by=by)


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


async def _prioritise(pool: asyncpg.Pool, job: UUID, priority: int) -> None:
    """Set the band directly: no request can (ADR-0054)."""
    async with pool.acquire() as conn:
        await conn.execute("UPDATE job SET priority = $2 WHERE id = $1", job, priority)


async def _enqueue(repo: PostgresJobRepository, project_id: UUID, *subjects: str) -> list[UUID]:
    return [(await repo.enqueue(_request(project_id, s))).id for s in subjects]


async def _claim_all(repo: PostgresJobRepository, project_id: UUID) -> list[UUID]:
    """Claim one at a time until nothing is claimable; the order the queue gave."""
    claimed: list[UUID] = []
    while (job := await repo.claim(project_id, owner="w", lease=LEASE)) is not None:
        claimed.append(job.id)
    return claimed


async def _events(pool: asyncpg.Pool, project_id: UUID) -> list[LedgerEvent]:
    kinds = {
        EventKind.JOB_PRIORITY_BUMPED,
        EventKind.JOB_PRIORITY_UNBUMPED,
        EventKind.JOB_PRIORITY_REFUSED,
    }
    events = await PostgresLedgerRepository(pool).all_for_project(project_id)
    return [e for e in events if e.kind in kinds]


async def _blocked_on_a_row_lock(pool: asyncpg.Pool) -> None:
    """Wait until some backend of this database is waiting on a row lock -- the reorder
    under test -- instead of guessing with a sleep. A loaded machine (the parallel suite)
    can take longer than any fixed sleep to get the reorder that far."""
    async with pool.acquire() as conn:
        for _ in range(200):
            waiting = await conn.fetchval(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if waiting:
                return
            await asyncio.sleep(0.05)
    raise AssertionError("the reorder never waited on the held row")


async def _set_state(pool: asyncpg.Pool, job: UUID, state: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET state = $2::job_state, lease_owner = NULL, lease_expires_at = NULL "
            "WHERE id = $1",
            job,
            state,
        )


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(PRIORITY_EVENT_DRAFTS, PriorityEventDraftBuilderInterface)
    assert isinstance(JOB_ROWS, JobRowMapperInterface)
    assert isinstance(STRICT_JOB_ROWS, JobRowMapperInterface)


# -- the claim order a bump makes (items 1-2) -----------------------------------------------


async def test_a_bumped_job_is_claimed_next_ahead_of_everything_waiting(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    assert isinstance(store, JobPriorityStore)
    first, second, third = await _enqueue(repo, project_id, "a", "b", "c")
    urgent = (await repo.enqueue(_request(project_id, "urgent"))).id
    await _prioritise(migrated_pool, urgent, -10)

    change = await store.bump(urgent, context=_context(project_id), at=AT)

    assert change.changed
    assert [m.job_id for m in change.moved] == [urgent]
    assert change.moved[0].previous is None
    record = await repo.get(urgent)
    assert record is not None and record.bump_named
    assert await _claim_all(repo, project_id) == [urgent, first, second, third]


async def test_bumped_jobs_run_in_the_order_they_were_bumped(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    a, b, c, d = await _enqueue(repo, project_id, "a", "b", "c", "d")
    high = (await repo.enqueue(_request(project_id, "high"))).id
    await _prioritise(migrated_pool, high, 50)

    await store.bump(d, context=_context(project_id), at=AT)
    await store.bump(b, context=_context(project_id), at=AT)

    assert await _claim_all(repo, project_id) == [d, b, high, a, c]


# -- dependencies (item 3) ----------------------------------------------------------------------


async def test_a_bump_pulls_its_unfinished_dependencies_forward_and_never_jumps_them(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    base, done = await _enqueue(repo, project_id, "base", "done")
    await _set_state(migrated_pool, done, "succeeded")
    tail = (await repo.enqueue(_request(project_id, "tail"))).id
    middle = (await repo.enqueue(_request(project_id, "middle", depends_on=(base, done)))).id
    await _prioritise(migrated_pool, middle, -1)
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(middle,)))).id

    change = await store.bump(target, context=_context(project_id), at=AT)

    assert [m.job_id for m in change.moved] == [base, middle, target]
    seqs = [m.bump_seq or 0 for m in change.moved]
    assert seqs == sorted(seqs)
    for pulled in (base, middle):
        record = await repo.get(pulled)
        assert record is not None and not record.bump_named, "pulled in, not named"
    first = await repo.claim(project_id, owner="w", lease=LEASE)
    assert first is not None and first.id == base
    stalled = await repo.claim(project_id, owner="w", lease=LEASE)
    assert stalled is not None and stalled.id == tail, "middle and target wait on base"
    await repo.ack(base, owner="w")
    assert await _claim_all(repo, project_id) == [middle]
    await repo.ack(middle, owner="w")
    assert await _claim_all(repo, project_id) == [target]


@pytest.mark.parametrize("state", ["failed", "cancelled"])
async def test_a_dependency_that_can_never_finish_refuses_the_bump(
    migrated_pool: asyncpg.Pool, project_id: UUID, state: str
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (dead,) = await _enqueue(repo, project_id, "dead")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dead,)))).id
    await _set_state(migrated_pool, dead, state)

    with pytest.raises(DependencyCannotFinish) as caught:
        await store.bump(target, context=_context(project_id), at=AT)

    assert caught.value.blockers == ((dead, state),)
    record = await repo.get(target)
    assert record is not None and record.bump_seq is None
    assert await _events(migrated_pool, project_id) == []


async def test_the_closure_stops_at_finished_rows_and_never_locks_past_them(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    beyond, done = await _enqueue(repo, project_id, "beyond", "done")
    async with migrated_pool.acquire() as conn:
        await conn.execute("INSERT INTO job_dependency VALUES ($1, $2)", done, beyond)
    await _set_state(migrated_pool, done, "succeeded")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(done,)))).id

    async with migrated_pool.acquire() as holder, holder.transaction():
        await holder.execute("SELECT 1 FROM job WHERE id = $1 FOR UPDATE", beyond)
        # A bump that locked `beyond` would wait for as long as the holder lives, so any
        # finite bound proves it did not; 5s tripped under a loaded pre-push run.
        change = await asyncio.wait_for(
            store.bump(target, context=_context(project_id), at=AT), timeout=60
        )

    assert [m.job_id for m in change.moved] == [target]


async def test_a_dependency_ring_is_refused_and_nothing_changes(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    a, b = await _enqueue(repo, project_id, "a", "b")
    async with migrated_pool.acquire() as conn:
        await conn.execute("INSERT INTO job_dependency VALUES ($1, $2), ($2, $1)", a, b)

    with pytest.raises(DependencyCycle):
        await store.bump(a, context=_context(project_id), at=AT)
    record = await repo.get(a)
    assert record is not None and record.bump_seq is None


# -- no preemption, no bypass (items 1 and 4) ---------------------------------------------------


async def test_a_bump_never_preempts_the_job_that_is_running(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    running, waiting = await _enqueue(repo, project_id, "running", "waiting")
    leased = await repo.claim(project_id, owner="w-1", lease=LEASE)
    assert leased is not None and leased.id == running

    await store.bump(waiting, context=_context(project_id), at=AT)
    change = await store.bump(running, context=_context(project_id), at=AT)

    after = await repo.get(running)
    assert after is not None
    assert after.state is JobState.LEASED
    assert after.lease_owner == "w-1"
    assert after.lease_expires_at == leased.lease_expires_at
    assert after.bump_seq == change.moved[0].bump_seq
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

    await store.bump(later, context=_context(project_id), at=AT)

    assert await _claim_all(repo, project_id) == [now]


async def test_bumping_a_parked_job_keeps_it_parked_until_its_gate_is_answered(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    parked, other = await _enqueue(repo, project_id, "parked", "other")
    got = await repo.claim(project_id, owner="w", lease=LEASE)
    assert got is not None and got.id == parked
    assert await repo.park(parked, owner="w")

    await store.bump(parked, context=_context(project_id), at=AT)

    assert await _claim_all(repo, project_id) == [other]
    await _set_state(migrated_pool, parked, "ready")
    assert await _claim_all(repo, project_id) == [parked]


# -- what a request refuses (items 3 and 6) -------------------------------------------------------


async def test_bumping_a_finished_job_is_a_recorded_no_op(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """As the storm does (ADR-0054 item 7): nothing moves, and the record says why."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "done")
    await _set_state(migrated_pool, job, "succeeded")

    change = await store.bump(job, context=_context(project_id), at=AT)

    assert not change.changed
    assert change.note == "it is succeeded; nothing to move"
    (event,) = await _events(migrated_pool, project_id)
    assert event.kind is EventKind.JOB_PRIORITY_BUMPED
    assert event.payload["moved"] == [] and event.payload["note"] == change.note
    record = await repo.get(job)
    assert record is not None and record.bump_seq is None
    with pytest.raises(NotReorderable, match="succeeded"):
        await store.unbump(job, context=_context(project_id), at=AT)


async def test_a_job_outside_the_named_project_is_unknown(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")
    elsewhere = uuid4()
    for request in (
        store.bump(job, context=_context(elsewhere), at=AT),
        store.unbump(job, context=_context(elsewhere), at=AT),
        store.bump(uuid4(), context=_context(project_id), at=AT),
    ):
        with pytest.raises(UnknownJob):
            await request


async def test_a_job_in_a_phase_this_vibey_does_not_know_is_not_written(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE 'triage'")
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET phase = 'triage' WHERE id = $1", job)

    with pytest.raises(NotReorderable, match="phase"):
        await store.bump(job, context=_context(project_id), at=AT)
    with pytest.raises(NotReorderable, match="phase"):
        await store.unbump(job, context=_context(project_id), at=AT)


# -- every request is recorded (item 5) --------------------------------------------------------------


async def test_a_bump_appends_one_event_naming_who_asked_and_everything_moved(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    dep = (await repo.enqueue(_request(project_id, "dep"))).id
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id

    change = await store.bump(
        target, context=_context(project_id, "source:storm"), at=AT, action=PriorityAction.ENQUEUE
    )

    (event,) = await _events(migrated_pool, project_id)
    assert event.kind is EventKind.JOB_PRIORITY_BUMPED
    assert event.job_id == target
    assert (event.phase, event.cycle) == (Phase.BUILD, 1)
    assert event.provenance is Provenance.TRUSTED
    assert event.produced_at == AT
    assert event.payload == {
        "action": "enqueue",
        "by": "source:storm",
        "target": str(target),
        "moved": [
            {"job_id": str(m.job_id), "bump_seq": m.bump_seq, "previous": None}
            for m in change.moved
        ],
        "kept": [],
        "named": False,
        "note": "",
        "removed": [],
        "skipped": [],
    }


async def test_a_request_that_moves_nothing_is_recorded_all_the_same(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")

    first = await store.bump(job, context=_context(project_id), at=AT)
    again = await store.bump(job, context=_context(project_id), at=AT)
    not_bumped = await store.unbump(
        (await _enqueue(repo, project_id, "y"))[0], context=_context(project_id), at=AT
    )

    assert first.changed and not again.changed and not not_bumped.changed
    assert again.note == "it is already bumped; nothing moved"
    assert not_bumped.note == "it is not bumped; nothing moved"
    record = await repo.get(job)
    assert record is not None and record.bump_seq == first.moved[0].bump_seq
    notes = [e.payload["note"] for e in await _events(migrated_pool, project_id)]
    assert notes == ["", again.note, not_bumped.note]


async def test_re_enqueueing_a_finished_job_with_priority_is_a_recorded_no_op(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "done")
    await _set_state(migrated_pool, job, "succeeded")

    change = await store.bump(
        job, context=_context(project_id), at=AT, action=PriorityAction.ENQUEUE
    )

    assert not change.changed
    assert change.note == "it is succeeded; nothing to move"
    (event,) = await _events(migrated_pool, project_id)
    assert event.payload["note"] == change.note


async def test_a_refusal_is_recorded_as_untrusted_with_its_reason(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresJobPriorityStore(migrated_pool)
    nowhere = uuid4()

    await store.refuse(
        PriorityRefusal(
            context=_context(project_id, "account:mallory"),
            job_id=nowhere,
            action=PriorityAction.BUMP,
            reason="not the operator",
        ),
        at=AT,
    )
    await store.refuse(
        PriorityRefusal(
            context=PriorityContext(project_id, 2, Phase.REVIEW, "source:issue-comment"),
            job_id=None,
            action=PriorityAction.ENQUEUE,
            reason="not declared",
        ),
        at=AT,
    )

    first, second = await _events(migrated_pool, project_id)
    assert first.kind is EventKind.JOB_PRIORITY_REFUSED
    assert first.provenance is Provenance.UNTRUSTED
    assert first.job_id == nowhere
    assert first.payload == {
        "action": "bump",
        "by": "account:mallory",
        "target": str(nowhere),
        "reason": "not the operator",
    }
    assert second.job_id is None and second.phase is Phase.REVIEW
    assert second.payload["target"] is None


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
        await store.bump(job, context=_context(project_id), at=AT)
    record = await repo.get(job)
    assert record is not None and record.bump_seq is None


# -- un-bumping (item 6) ------------------------------------------------------------------------


async def test_an_unbump_undoes_exactly_what_the_bump_moved(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    plain, dep, own = await _enqueue(repo, project_id, "plain", "dep", "own")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep, own)))).id
    await store.bump(own, context=_context(project_id), at=AT)
    await store.bump(target, context=_context(project_id), at=AT)

    change = await store.unbump(target, context=_context(project_id, "source:storm"), at=AT)

    assert change.action is PriorityAction.UNBUMP
    assert [m.job_id for m in change.moved] == [target, dep]
    assert all(m.bump_seq is None and m.previous is not None for m in change.moved)
    event = (await _events(migrated_pool, project_id))[-1]
    assert event.kind is EventKind.JOB_PRIORITY_UNBUMPED
    assert event.payload["by"] == "source:storm"
    own_record = await repo.get(own)
    assert own_record is not None and own_record.bump_named, "bumped by name, kept"
    for back in (target, dep):
        record = await repo.get(back)
        assert record is not None and (record.bump_seq, record.bump_named) == (None, False)
    assert (await _claim_all(repo, project_id))[:2] == [own, plain]


async def test_an_unbump_keeps_a_pulled_dependency_another_bumped_job_needs(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (shared,) = await _enqueue(repo, project_id, "shared")
    first = (await repo.enqueue(_request(project_id, "first", depends_on=(shared,)))).id
    second = (await repo.enqueue(_request(project_id, "second", depends_on=(shared,)))).id
    await store.bump(first, context=_context(project_id), at=AT)
    await store.bump(second, context=_context(project_id), at=AT)

    change = await store.unbump(first, context=_context(project_id), at=AT)

    assert [m.job_id for m in change.moved] == [first]
    record = await repo.get(shared)
    assert record is not None and record.bump_seq is not None


async def test_bumping_a_pulled_job_by_name_keeps_it_when_its_puller_goes_back(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (dep,) = await _enqueue(repo, project_id, "dep")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id
    await store.bump(target, context=_context(project_id), at=AT)
    before = await repo.get(dep)

    named = await store.bump(dep, context=_context(project_id), at=AT)
    back = await store.unbump(target, context=_context(project_id), at=AT)

    assert named.changed and named.named and named.moved == ()
    assert [m.job_id for m in back.moved] == [target]
    after = await repo.get(dep)
    assert before is not None and after is not None
    assert after.bump_seq == before.bump_seq, "it keeps its place"
    assert after.bump_named


async def test_the_reviewers_sequence_leaves_no_orphan_and_records_what_it_cleared(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """x, d, a (needs d), b (needs d): bump a, bump b, un-bump a, un-bump b. The lane is
    derived, so d leaves with b; each un-bump's event lists exactly what it cleared."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    x, d = await _enqueue(repo, project_id, "x", "d")
    a = (await repo.enqueue(_request(project_id, "a", depends_on=(d,)))).id
    b = (await repo.enqueue(_request(project_id, "b", depends_on=(d,)))).id

    await store.bump(a, context=_context(project_id), at=AT)
    await store.bump(b, context=_context(project_id), at=AT)
    first = await store.unbump(a, context=_context(project_id), at=AT)
    kept = await repo.get(d)
    second = await store.unbump(b, context=_context(project_id), at=AT)

    assert [m.job_id for m in first.moved] == [a]
    assert kept is not None and kept.bump_seq is not None, "b still needs d"
    assert {m.job_id for m in second.moved} == {b, d}
    for job in (x, d, a, b):
        record = await repo.get(job)
        assert record is not None and record.bump_seq is None and not record.bump_named
    assert await _claim_all(repo, project_id) == [x, d], "back to plain order"
    removed = [
        e.payload["removed"]
        for e in await _events(migrated_pool, project_id)
        if e.kind is EventKind.JOB_PRIORITY_UNBUMPED
    ]
    assert removed == [[str(a)], [str(m.job_id) for m in second.moved]]


@pytest.mark.parametrize("request_kind", ["bump another job", "unbump a job not bumped"])
async def test_a_cancelled_named_job_leaves_nothing_behind_after_the_next_request(
    migrated_pool: asyncpg.Pool, project_id: UUID, request_kind: str
) -> None:
    """Finding 2: enqueue d, enqueue a(d), bump a, cancel a. The next request of any kind
    sweeps d -- the lane no longer derives it -- and its event lists d as removed."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    d, x = await _enqueue(repo, project_id, "d", "x")
    a = (await repo.enqueue(_request(project_id, "a", depends_on=(d,)))).id
    await store.bump(a, context=_context(project_id), at=AT)
    await _set_state(migrated_pool, a, "cancelled")

    if request_kind == "bump another job":
        change = await store.bump(x, context=_context(project_id), at=AT)
    else:
        change = await store.unbump(x, context=_context(project_id), at=AT)

    assert [m.job_id for m in change.swept] == [d]
    record = await repo.get(d)
    assert record is not None and record.bump_seq is None and not record.bump_named
    assert (await _events(migrated_pool, project_id))[-1].payload["removed"] == [str(d)]


async def test_an_unbump_leaves_a_job_in_an_unknown_phase_and_records_it(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    """Finding 4: a pulled job in a phase this vibey does not know is never written, and
    no longer refuses the whole un-bump: it is left, and the record names it."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (d,) = await _enqueue(repo, project_id, "d")
    a = (await repo.enqueue(_request(project_id, "a", depends_on=(d,)))).id
    await store.bump(a, context=_context(project_id), at=AT)
    # ALTER TYPE is the owner's (ADR-0055); `migrated_pool` is the application role's.
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'triage'")
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET phase = 'triage' WHERE id = $1", d)

    change = await store.unbump(a, context=_context(project_id), at=AT)

    assert [m.job_id for m in change.moved] == [a]
    assert change.skipped == (d,)
    assert "left in the lane" in change.note
    event = (await _events(migrated_pool, project_id))[-1]
    assert event.payload["skipped"] == [str(d)]
    async with migrated_pool.acquire() as conn:
        assert await conn.fetchval("SELECT bump_seq FROM job WHERE id = $1", d) is not None


async def test_the_lane_runs_through_a_dependency_in_an_unknown_state(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    """a, named, needs c, which needs d. c moves to a state a newer vibey wrote: the next
    request must not sweep d, which a still needs, and d cannot be un-bumped."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (d,) = await _enqueue(repo, project_id, "d")
    c = (await repo.enqueue(_request(project_id, "c", depends_on=(d,)))).id
    a = (await repo.enqueue(_request(project_id, "a", depends_on=(c,)))).id
    (x,) = await _enqueue(repo, project_id, "x")
    await store.bump(a, context=_context(project_id), at=AT)
    # ALTER TYPE is the owner's (ADR-0055); `migrated_pool` is the application role's.
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE job_state ADD VALUE IF NOT EXISTS 'quarantined'")
    await _set_state(migrated_pool, c, "quarantined")

    change = await store.bump(x, context=_context(project_id), at=AT)
    assert change.swept == () and change.skipped == ()
    with pytest.raises(DependentsStillBumped):
        await store.unbump(d, context=_context(project_id), at=AT)
    async with migrated_pool.acquire() as conn:
        assert await conn.fetchval("SELECT bump_seq FROM job WHERE id = $1", d) is not None


async def test_a_sweep_leaves_what_a_skipped_job_still_needs(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    """a, named, needed u, which needs d; a is cancelled, and u is in a phase this vibey
    does not know. u is left -- so d, which u waits on, is left with it, and both named."""
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (d,) = await _enqueue(repo, project_id, "d")
    u = (await repo.enqueue(_request(project_id, "u", depends_on=(d,)))).id
    a = (await repo.enqueue(_request(project_id, "a", depends_on=(u,)))).id
    (x,) = await _enqueue(repo, project_id, "x")
    await store.bump(a, context=_context(project_id), at=AT)
    # ALTER TYPE is the owner's (ADR-0055); `migrated_pool` is the application role's.
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'triage'")
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET phase = 'triage' WHERE id = $1", u)
    await _set_state(migrated_pool, a, "cancelled")

    change = await store.bump(x, context=_context(project_id), at=AT)

    assert change.swept == () and set(change.skipped) == {d, u}
    event = (await _events(migrated_pool, project_id))[-1]
    assert set(event.payload["skipped"]) == {str(d), str(u)}
    async with migrated_pool.acquire() as conn:
        seqs = await conn.fetch("SELECT bump_seq FROM job WHERE id = ANY($1::uuid[])", [d, u])
    assert all(row["bump_seq"] is not None for row in seqs)


async def test_unbumping_a_job_a_bumped_job_needs_is_refused_naming_it(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (dep,) = await _enqueue(repo, project_id, "dep")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id
    await store.bump(target, context=_context(project_id), at=AT)

    with pytest.raises(DependentsStillBumped) as caught:
        await store.unbump(dep, context=_context(project_id), at=AT)

    assert caught.value.dependents == (target,)
    record = await repo.get(dep)
    assert record is not None and record.bump_seq is not None


# -- locks ----------------------------------------------------------------------------------------


async def test_a_bump_holding_its_locks_never_blocks_an_enqueue_naming_its_rows(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """`FOR NO KEY UPDATE`, not `FOR UPDATE`: an enqueue's foreign key takes `KEY SHARE`
    on the job it depends on, and must not wait for a reorder to commit."""
    release = asyncio.Event()
    entered = asyncio.Event()

    class Holding:
        async def append(
            self,
            conn: asyncpg.pool.PoolConnectionProxy | asyncpg.Connection,
            draft: LedgerEventDraft,
        ) -> LedgerEvent:
            entered.set()
            await release.wait()
            return await DEFAULT_EVENT_APPENDER.append(conn, draft)

    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool, appender=Holding())
    (held,) = await _enqueue(repo, project_id, "held")

    bump = asyncio.create_task(store.bump(held, context=_context(project_id), at=AT))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        dependent = await asyncio.wait_for(
            repo.enqueue(_request(project_id, "dependent", depends_on=(held,))), timeout=5
        )
    finally:
        release.set()
        await bump

    assert dependent.state is JobState.READY


async def test_a_deadlock_the_database_breaks_is_a_clean_refusal_not_a_traceback(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    (dep,) = await _enqueue(repo, project_id, "dep")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id
    low, high = sorted((dep, target))

    async with owner_pool.acquire() as holder:
        # The holder waits longest before checking, so the bump's backend is the one
        # that finds the cycle and is aborted.
        await holder.execute("SET deadlock_timeout = '30s'")
        tx = holder.transaction()
        await tx.start()
        await holder.execute("SELECT 1 FROM job WHERE id = $1 FOR UPDATE", high)
        bump = asyncio.create_task(store.bump(target, context=_context(project_id), at=AT))
        await _blocked_on_a_row_lock(migrated_pool)
        cross = asyncio.create_task(
            holder.execute("SELECT 1 FROM job WHERE id = $1 FOR UPDATE", low)
        )
        with pytest.raises(ReorderConflict) as caught:
            await asyncio.wait_for(bump, timeout=20)
        await asyncio.wait_for(cross, timeout=20)
        await tx.rollback()

    assert caught.value.job_id == target
    assert "retry" in str(caught.value)


# -- the queue as the operator sees it --------------------------------------------------------------


async def test_the_queue_lists_running_work_then_waiting_work_in_claim_order(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    running, done, plain, dep = await _enqueue(repo, project_id, "running", "done", "plain", "dep")
    target = (await repo.enqueue(_request(project_id, "target", depends_on=(dep,)))).id
    await repo.claim(project_id, owner="w", lease=LEASE)
    await _set_state(migrated_pool, done, "succeeded")
    await store.bump(target, context=_context(project_id), at=AT)
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE job_state ADD VALUE 'quarantined'")
        await conn.execute("ALTER TYPE phase ADD VALUE 'triage'")
    stranger = (await repo.enqueue(_request(project_id, "stranger"))).id
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "UPDATE job SET state = 'quarantined', phase = 'triage' WHERE id = $1", stranger
        )

    entries = await store.queue(project_id)

    assert [e.job.id for e in entries] == [running, dep, target, plain, stranger]
    assert entries[0].job.state is JobState.LEASED
    assert not entries[1].job.bump_named and entries[2].job.bump_named
    assert entries[2].waiting_on == (dep,)
    assert entries[4].job.state == UnrecognizedJobState("quarantined")
    assert entries[4].job.phase == UnrecognizedPhase("triage")
    assert await store.queue(uuid4()) == ()


async def test_a_worker_is_never_handed_a_job_in_a_phase_it_does_not_know(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    (job,) = await _enqueue(repo, project_id, "x")
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE 'triage'")
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE job SET phase = 'triage' WHERE id = $1", job)

    assert await repo.claim(project_id, owner="w", lease=LEASE) is None
    async with migrated_pool.acquire() as conn:
        assert await conn.fetchval("SELECT state FROM job WHERE id = $1", job) == "ready"
    with pytest.raises(ValueError, match="triage"):
        await repo.get(job)


# -- concurrency: SKIP LOCKED keeps the order ----------------------------------------------------------


async def test_concurrent_claims_under_skip_locked_take_the_front_of_the_queue_in_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    store = PostgresJobPriorityStore(migrated_pool)
    ids = await _enqueue(repo, project_id, *(f"job-{n:02d}" for n in range(12)))
    bumped = [ids[9], ids[2], ids[7]]
    for job in bumped:
        await store.bump(job, context=_context(project_id), at=AT)
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
        *(store.bump(job, context=_context(project_id), at=AT) for job in ids[::-1])
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
        bump = asyncio.create_task(store.bump(job, context=_context(project_id), at=AT))
        await _blocked_on_a_row_lock(migrated_pool)
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
        request = _request(project_id, f"s{n}", run_after=past + timedelta(seconds=offset))
        ids.append((await repo.enqueue(request)).id)
        await _prioritise(migrated_pool, ids[-1], priority)
    for job in (ids[4], ids[0], ids[11]):
        await store.bump(job, context=_context(project_id), at=AT)
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
