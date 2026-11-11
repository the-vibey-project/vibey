# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contract test: FakeJobRepository behaves like PostgresJobRepository.

Every worker, handler and phase test that fakes the queue stands on
``FakeJobRepository``. This runs ONE body against both it and the real
repository, so a fake that drifts from the SQL fails here instead of letting a
false-green through every faked-mode test. Where the two disagree the fake is
made faithful (it is the reference only because it is the one that can be
wrong); each test names the source of its expectation: the
``JobRepository`` docstring (``queue.py``) or the SQL in ``job_repository.py`` /
``queue_reap_store.py``.

Time. ``claim`` takes ``lease`` as an interval added to the database clock, and
``reap`` judges a lease against the database clock too. No test sleeps: a lease
that must be *lapsed* is claimed with a negative lease (expires one second in
the past), a lease that must be *live* with an hour, and ``run_after`` is
driven through ``EnqueueRequest.run_after`` with past and future instants.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.interfaces.queue import JobRepository
from vibey.domain.engine import EngineId
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.infrastructure.db.job_repository import PostgresJobRepository

LIVE = timedelta(hours=1)
LAPSED = timedelta(seconds=-1)
ERROR: dict[str, object] = {"reason": "boom"}


@dataclass
class Queue:
    """One repository plus the setup moves the interface deliberately lacks."""

    repo: JobRepository
    set_priority: Callable[[UUID, int], Awaitable[None]]
    new_project: Callable[[], Awaitable[UUID]]


@pytest.fixture(params=["fake", "postgres"])
def queue(request: pytest.FixtureRequest) -> Queue:
    if request.param == "fake":
        fake = FakeJobRepository()

        async def fake_priority(job_id: UUID, priority: int) -> None:
            from dataclasses import replace

            fake._jobs[job_id] = replace(fake._jobs[job_id], priority=priority)

        async def fake_project() -> UUID:
            return uuid4()

        return Queue(fake, fake_priority, fake_project)

    pool: asyncpg.Pool = request.getfixturevalue("migrated_pool")

    async def pg_priority(job_id: UUID, priority: int) -> None:
        await pool.execute("UPDATE job SET priority = $2 WHERE id = $1", job_id, priority)

    async def pg_project() -> UUID:
        name = f"contract-{uuid4()}"
        pid = await pool.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) "
            "RETURNING id",
            name,
            f"/tmp/{name}",
        )
        return UUID(str(pid))

    return Queue(PostgresJobRepository(pool), pg_priority, pg_project)


def req(project_id: UUID, key: str, **overrides: object) -> EnqueueRequest:
    fields: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": "build.implement",
        "idempotency_key": key,
    }
    fields.update(overrides)
    return EnqueueRequest(**fields)  # type: ignore[arg-type]


async def leased(
    queue: Queue, project_id: UUID, key: str = "a", *, lease: timedelta = LIVE, **overrides: object
) -> JobRecord:
    """Enqueue one job and claim it as ``w1``."""
    await queue.repo.enqueue(req(project_id, key, **overrides))
    job = await queue.repo.claim(project_id, owner="w1", lease=lease)
    assert job is not None
    return job


# --- claim ------------------------------------------------------------------------------


async def test_claim_returns_none_when_nothing_is_enqueued(queue: Queue, project_id: UUID) -> None:
    # queue.py claim: "or None if there is nothing claimable right now".
    assert await queue.repo.claim(project_id, owner="w1", lease=LIVE) is None


async def test_claim_leases_the_job_to_the_owner_and_counts_the_attempt(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `claim`: state='leased', lease_owner=$2, lease_expires_at=now()+$3, attempts+1.
    before = datetime.now(UTC)
    job = await leased(queue, project_id)
    assert job.state is JobState.LEASED
    assert job.lease_owner == "w1"
    assert job.attempts == 1
    assert job.lease_expires_at is not None and job.lease_expires_at > before + timedelta(
        minutes=59
    )
    assert await queue.repo.get(job.id) == job


async def test_claim_prefers_the_higher_priority_job(queue: Queue, project_id: UUID) -> None:
    # SQL _CLAIM_ORDER: `j.priority DESC` after the bump position.
    low = await queue.repo.enqueue(req(project_id, "low"))
    high = await queue.repo.enqueue(req(project_id, "high"))
    await queue.set_priority(high.id, 9)
    first = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert first is not None and first.id == high.id
    second = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert second is not None and second.id == low.id


async def test_claim_breaks_a_priority_tie_by_the_earlier_due_time(
    queue: Queue, project_id: UUID
) -> None:
    # SQL _CLAIM_ORDER: `j.run_after ASC` after priority.
    now = datetime.now(UTC)
    later = await queue.repo.enqueue(req(project_id, "later", run_after=now - timedelta(minutes=1)))
    sooner = await queue.repo.enqueue(
        req(project_id, "sooner", run_after=now - timedelta(minutes=10))
    )
    first = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert first is not None and first.id == sooner.id
    second = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert second is not None and second.id == later.id


async def test_claim_skips_a_job_that_is_not_yet_due(queue: Queue, project_id: UUID) -> None:
    # SQL _CLAIMABLE: `j.run_after <= now()`.
    await queue.repo.enqueue(req(project_id, "future", run_after=datetime.now(UTC) + LIVE))
    assert await queue.repo.claim(project_id, owner="w1", lease=LIVE) is None


async def test_claim_waits_for_every_dependency_to_succeed(queue: Queue, project_id: UUID) -> None:
    # queue.py claim: "whose dependencies have all succeeded"; SQL _CLAIMABLE
    # `p.state <> 'succeeded'`.
    dependency = await queue.repo.enqueue(req(project_id, "dep"))
    dependent = await queue.repo.enqueue(req(project_id, "dependent", depends_on=(dependency.id,)))
    first = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert first is not None and first.id == dependency.id
    assert await queue.repo.claim(project_id, owner="w2", lease=LIVE) is None
    assert await queue.repo.ack(dependency.id, owner="w1")
    second = await queue.repo.claim(project_id, owner="w2", lease=LIVE)
    assert second is not None and second.id == dependent.id


async def test_a_claimed_job_is_invisible_to_a_second_owner_until_it_is_reaped(
    queue: Queue, project_id: UUID
) -> None:
    # `claim` takes only state='ready' rows, even when the lease has lapsed; only
    # `reap` ("Reclaims jobs whose lease has expired") puts it back.
    job = await leased(queue, project_id, lease=LAPSED)
    assert await queue.repo.claim(project_id, owner="w2", lease=LIVE) is None
    assert await queue.repo.reap() == 1
    again = await queue.repo.claim(project_id, owner="w2", lease=LIVE)
    assert again is not None and again.id == job.id
    assert again.lease_owner == "w2" and again.attempts == 2


async def test_claim_is_scoped_to_its_project(queue: Queue, project_id: UUID) -> None:
    # SQL `claim`: `j.project_id = $4`.
    other = await queue.new_project()
    await queue.repo.enqueue(req(other, "elsewhere"))
    assert await queue.repo.claim(project_id, owner="w1", lease=LIVE) is None


# --- claimable_projects -----------------------------------------------------------------


async def test_claimable_projects_lists_projects_with_a_job_claim_would_hand_out(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py claimable_projects: "ordered by that project's next job in the claim's own
    # order"; SQL shares _CLAIMABLE with claim, so a leased or not-due job does not count.
    other = await queue.new_project()
    idle = await queue.new_project()
    await queue.repo.enqueue(req(project_id, "a"))
    high = await queue.repo.enqueue(req(other, "b"))
    await queue.set_priority(high.id, 5)
    await queue.repo.enqueue(req(idle, "future", run_after=datetime.now(UTC) + LIVE))
    assert await queue.repo.claimable_projects() == (other, project_id)
    await queue.repo.claim(other, owner="w1", lease=LIVE)
    assert await queue.repo.claimable_projects() == (project_id,)


# --- ownership guards -------------------------------------------------------------------


async def test_every_lease_guarded_write_by_a_non_owner_returns_false_and_changes_nothing(
    queue: Queue, project_id: UUID
) -> None:
    # SQL: ack/nack/park/defer/heartbeat/grant_attempts/assign_engine all carry
    # `WHERE id = $1 AND lease_owner = $2`.
    job = await leased(queue, project_id)
    before = await queue.repo.get(job.id)
    retry = datetime.now(UTC) + LIVE
    assert not await queue.repo.ack(job.id, owner="intruder")
    assert not await queue.repo.nack(job.id, owner="intruder", error=ERROR)
    assert not await queue.repo.defer(job.id, owner="intruder", retry_at=retry, error=ERROR)
    assert not await queue.repo.park(job.id, owner="intruder")
    assert not await queue.repo.heartbeat(job.id, owner="intruder", lease=LIVE * 2)
    assert not await queue.repo.grant_attempts(job.id, owner="intruder", max_attempts=99)
    assert not await queue.repo.assign_engine(
        job.id, owner="intruder", engine_id=EngineId.CLAUDELOOP
    )
    assert await queue.repo.get(job.id) == before


async def test_writes_to_an_unknown_job_return_false(queue: Queue) -> None:
    # SQL: an UPDATE that matches no row reports 0 rows, so the method returns False.
    ghost = uuid4()
    assert not await queue.repo.ack(ghost, owner="w1")
    assert not await queue.repo.heartbeat(ghost, owner="w1", lease=LIVE)
    assert await queue.repo.get(ghost) is None


# --- ack / nack / defer / park ----------------------------------------------------------


async def test_ack_by_the_owner_settles_the_job_and_releases_the_lease(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `ack`: state='succeeded', lease_owner/lease_expires_at NULL.
    job = await leased(queue, project_id)
    assert await queue.repo.ack(job.id, owner="w1")
    done = await queue.repo.get(job.id)
    assert done is not None
    assert done.state is JobState.SUCCEEDED
    assert done.lease_owner is None and done.lease_expires_at is None
    assert not await queue.repo.ack(job.id, owner="w1")


async def test_nack_requeues_while_attempts_remain_and_records_the_error(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `nack`: state='ready' when attempts < max_attempts; lease cleared;
    # run_after = now() + backoff (never earlier than now); last_error stored.
    job = await leased(queue, project_id)
    before = datetime.now(UTC) - timedelta(seconds=1)
    assert await queue.repo.nack(job.id, owner="w1", error=ERROR)
    retried = await queue.repo.get(job.id)
    assert retried is not None
    assert retried.state is JobState.READY
    assert retried.lease_owner is None and retried.lease_expires_at is None
    assert retried.last_error == ERROR
    assert retried.attempts == 1
    assert retried.run_after >= before


async def test_nack_fails_the_job_once_its_attempts_are_spent(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `nack`: state='failed' when attempts >= max_attempts.
    job = await leased(queue, project_id, max_attempts=1)
    assert await queue.repo.nack(job.id, owner="w1", error=ERROR)
    failed = await queue.repo.get(job.id)
    assert failed is not None and failed.state is JobState.FAILED


async def test_defer_releases_the_lease_without_costing_an_attempt(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py defer: "Releases a capacity-blocked lease without consuming a failure
    # attempt"; SQL: attempts = greatest(attempts - 1, 0), run_after = $3.
    job = await leased(queue, project_id)
    retry_at = (datetime.now(UTC) + LIVE).replace(microsecond=0)
    assert await queue.repo.defer(job.id, owner="w1", retry_at=retry_at, error=ERROR)
    deferred = await queue.repo.get(job.id)
    assert deferred is not None
    assert deferred.state is JobState.READY
    assert deferred.attempts == 0
    assert deferred.run_after == retry_at
    assert deferred.last_error == ERROR
    assert deferred.lease_owner is None and deferred.lease_expires_at is None


async def test_park_awaits_a_human_and_refunds_the_attempt(queue: Queue, project_id: UUID) -> None:
    # queue.py park: "Marks the job awaiting_human and releases its lease immediately,
    # without counting as a failure attempt".
    job = await leased(queue, project_id)
    assert await queue.repo.park(job.id, owner="w1")
    parked = await queue.repo.get(job.id)
    assert parked is not None
    assert parked.state is JobState.AWAITING_HUMAN
    assert parked.attempts == 0
    assert parked.lease_owner is None and parked.lease_expires_at is None


# --- heartbeat / reap / grant_attempts / assign_engine ----------------------------------


async def test_heartbeat_extends_the_lease_for_the_owner_only(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `heartbeat`: lease_expires_at = now() + $2 WHERE lease_owner = $3 AND
    # state = 'leased'. A lapsed-but-unreaped lease is revived by its owner.
    job = await leased(queue, project_id, lease=LAPSED)
    assert await queue.repo.heartbeat(job.id, owner="w1", lease=LIVE)
    renewed = await queue.repo.get(job.id)
    assert renewed is not None and job.lease_expires_at is not None
    assert renewed.lease_expires_at is not None and renewed.lease_expires_at > job.lease_expires_at
    assert await queue.repo.reap() == 0


async def test_heartbeat_after_the_job_settled_returns_false(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `heartbeat`: `AND state = 'leased'`; ack also nulls lease_owner.
    job = await leased(queue, project_id)
    assert await queue.repo.ack(job.id, owner="w1")
    assert not await queue.repo.heartbeat(job.id, owner="w1", lease=LIVE)


async def test_reap_requeues_only_lapsed_leases_and_returns_the_count(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py reap: "Reclaims jobs whose lease has expired. Returns the count reclaimed";
    # queue_reap_store `_EXPIRED`/`_REQUEUE`: lease_expires_at < now(), back to 'ready'.
    lapsed_one = await leased(queue, project_id, "a", lease=LAPSED)
    await queue.repo.enqueue(req(project_id, "b"))
    lapsed_two = await queue.repo.claim(project_id, owner="w2", lease=LAPSED)
    assert lapsed_two is not None
    await queue.repo.enqueue(req(project_id, "c"))
    live = await queue.repo.claim(project_id, owner="w3", lease=LIVE)
    assert live is not None
    assert await queue.repo.reap() == 2
    for lapsed in (lapsed_one, lapsed_two):
        back = await queue.repo.get(lapsed.id)
        assert back is not None
        assert back.state is JobState.READY
        assert back.lease_owner is None and back.lease_expires_at is None
        assert back.attempts == 1
    still = await queue.repo.get(live.id)
    assert still is not None and still.state is JobState.LEASED and still.lease_owner == "w3"
    assert await queue.repo.reap() == 0


async def test_reap_parks_a_lapsed_job_whose_attempts_are_spent(
    queue: Queue, project_id: UUID
) -> None:
    # queue_reap_store module docstring: "Once its attempts are spent it is parked ... The
    # park refunds one attempt"; the QueueReapPolicy POISON verdict at attempts >= limit.
    job = await leased(queue, project_id, lease=LAPSED, max_attempts=1)
    assert await queue.repo.reap() == 1
    parked = await queue.repo.get(job.id)
    assert parked is not None
    assert parked.state is JobState.AWAITING_HUMAN
    assert parked.attempts == 0
    assert parked.lease_owner is None and parked.lease_expires_at is None


async def test_grant_attempts_raises_the_bound_for_the_owner_and_never_narrows(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py grant_attempts: "never narrows: a value at or below the current bound is a
    # no-op returning False"; SQL `max_attempts < $3`.
    job = await leased(queue, project_id, max_attempts=3)
    assert await queue.repo.grant_attempts(job.id, owner="w1", max_attempts=5)
    granted = await queue.repo.get(job.id)
    assert granted is not None and granted.max_attempts == 5
    assert not await queue.repo.grant_attempts(job.id, owner="w1", max_attempts=5)
    assert not await queue.repo.grant_attempts(job.id, owner="w1", max_attempts=2)
    unchanged = await queue.repo.get(job.id)
    assert unchanged is not None and unchanged.max_attempts == 5


async def test_a_granted_bound_outlives_the_next_nack(queue: Queue, project_id: UUID) -> None:
    # queue.py grant_attempts: "`nack` decides 'failed' from the row's own max_attempts".
    job = await leased(queue, project_id, max_attempts=1)
    assert await queue.repo.grant_attempts(job.id, owner="w1", max_attempts=2)
    assert await queue.repo.nack(job.id, owner="w1", error=ERROR)
    retried = await queue.repo.get(job.id)
    assert retried is not None and retried.state is JobState.READY


async def test_assign_engine_records_the_selection_while_leased(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py assign_engine: guarded by the lease; SQL: `AND state = 'leased'`.
    job = await leased(queue, project_id)
    assert await queue.repo.assign_engine(job.id, owner="w1", engine_id=EngineId.CODEXLOOP)
    chosen = await queue.repo.get(job.id)
    assert chosen is not None and chosen.assigned_engine == EngineId.CODEXLOOP.value
    assert await queue.repo.ack(job.id, owner="w1")
    assert not await queue.repo.assign_engine(job.id, owner="w1", engine_id=EngineId.CLAUDELOOP)


# --- enqueue / enqueue_batch / list_for_cycle -------------------------------------------


async def test_enqueue_is_idempotent_on_the_idempotency_key(queue: Queue, project_id: UUID) -> None:
    # queue.py enqueue: "a second enqueue with the same (project_id, idempotency_key)
    # returns the existing row rather than creating a duplicate".
    first = await queue.repo.enqueue(req(project_id, "same", payload={"n": 1}))
    second = await queue.repo.enqueue(req(project_id, "same", payload={"n": 2}))
    assert second.id == first.id
    assert second.payload == {"n": 1}
    assert len(await queue.repo.list_for_cycle(project_id, cycle=1, kind="build.implement")) == 1


async def test_enqueue_records_the_request_as_a_ready_unleased_job(
    queue: Queue, project_id: UUID
) -> None:
    # SQL `INSERT`: state defaults to ready, attempts 0, no lease.
    job = await queue.repo.enqueue(
        req(project_id, "k", work_item_id="W-1", payload={"a": 1}, requirement={"b": 2})
    )
    assert job.state is JobState.READY
    assert job.attempts == 0 and job.max_attempts == 7
    assert job.lease_owner is None and job.assigned_engine is None
    assert (job.work_item_id, dict(job.payload), dict(job.requirement)) == (
        "W-1",
        {"a": 1},
        {"b": 2},
    )


async def test_enqueue_batch_is_in_order_and_idempotent_on_replay(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py enqueue_batch: "Each request is idempotent exactly as `enqueue` is, so
    # replaying a batch returns the rows it already made"; "one record per request, in
    # request order"; depends_on_keys may name an earlier request of the batch.
    batch = [
        req(project_id, "one"),
        req(project_id, "two", depends_on_keys=("one",)),
    ]
    made = await queue.repo.enqueue_batch(batch)
    assert [job.idempotency_key for job in made] == ["one", "two"]
    replayed = await queue.repo.enqueue_batch(batch)
    assert [job.id for job in replayed] == [job.id for job in made]
    first = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert first is not None and first.id == made[0].id
    assert await queue.repo.claim(project_id, owner="w2", lease=LIVE) is None


async def test_enqueue_batch_is_all_or_nothing(queue: Queue, project_id: UUID) -> None:
    # queue.py enqueue_batch: "a key that names neither raises LookupError and rolls the
    # batch back".
    with pytest.raises(LookupError):
        await queue.repo.enqueue_batch(
            [req(project_id, "kept?"), req(project_id, "bad", depends_on_keys=("missing",))]
        )
    assert await queue.repo.list_for_cycle(project_id, cycle=1, kind="build.implement") == ()
    assert await queue.repo.claim(project_id, owner="w1", lease=LIVE) is None


async def test_list_for_cycle_filters_by_cycle_and_kind_oldest_first(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py list_for_cycle: "Every job of `kind` in this project's `cycle`, whatever its
    # state, oldest first."
    first = await queue.repo.enqueue(req(project_id, "1"))
    await queue.repo.enqueue(req(project_id, "other-cycle", cycle=2))
    await queue.repo.enqueue(req(project_id, "other-kind", kind="build.verify"))
    second = await queue.repo.enqueue(req(project_id, "2"))
    claimed = await queue.repo.claim(project_id, owner="w1", lease=LIVE)
    assert claimed is not None
    listed = await queue.repo.list_for_cycle(project_id, cycle=1, kind="build.implement")
    assert [job.id for job in listed] == [first.id, second.id]


# --- count_unsettled / queue_depth ------------------------------------------------------


async def test_count_unsettled_skips_terminal_jobs_and_honours_exclude(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py count_unsettled: "not yet in a terminal state (succeeded/failed/cancelled).
    # `exclude` lets the caller ask 'am I the last one?'"; scoped by cycle and phase.
    done = await leased(queue, project_id, "done")
    assert await queue.repo.ack(done.id, owner="w1")
    mine = await queue.repo.enqueue(req(project_id, "mine"))
    await queue.repo.enqueue(req(project_id, "theirs"))
    await queue.repo.enqueue(req(project_id, "other-cycle", cycle=2))
    await queue.repo.enqueue(req(project_id, "other-phase", phase=Phase.REVIEW))
    assert await queue.repo.count_unsettled(project_id, cycle=1, phase=Phase.BUILD) == 2
    assert (
        await queue.repo.count_unsettled(project_id, cycle=1, phase=Phase.BUILD, exclude=mine.id)
        == 1
    )


async def test_queue_depth_reports_every_state_with_zero_for_the_empty_ones(
    queue: Queue, project_id: UUID
) -> None:
    # queue.py queue_depth: "Every `JobState` member is present".
    assert dict(await queue.repo.queue_depth(project_id)) == {state: 0 for state in JobState}
    done = await leased(queue, project_id, "done")
    assert await queue.repo.ack(done.id, owner="w1")
    await queue.repo.enqueue(req(project_id, "r1"))
    await queue.repo.enqueue(req(project_id, "r2"))
    depth = dict(await queue.repo.queue_depth(project_id))
    assert depth == {
        **{state: 0 for state in JobState},
        JobState.SUCCEEDED: 1,
        JobState.READY: 2,
    }
