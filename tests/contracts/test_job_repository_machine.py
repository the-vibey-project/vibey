# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""State machine: the job repository fake and PostgreSQL, driven by one random sequence.

``test_job_repository_contract.py`` pins the cases somebody thought of. This drives
``FakeJobRepository`` (the reference) and ``PostgresJobRepository`` (the subject) through
the SAME random sequence of ``enqueue``, ``claim``, ``heartbeat``, ``ack``, ``nack``,
``defer``, ``park``, ``grant_attempts``, ``assign_engine`` and ``reap`` calls, and after
every step asserts that both returned the same thing and that both job tables read the same
once normalised. So a fake that drifts from the SQL in a sequence nobody wrote down still
fails here, instead of letting a false-green through every faked-mode test.

Normalisation. Ids are generated on each side, so a job is named by the order it was first
enqueued (its index) and every id a call returns is mapped back through that order. Times
come from two clocks, so a lease reads as live, lapsed or none, and ``run_after`` as due or
not due, rather than as an instant -- each side's read against that side's own clock
(``Side.clock``: the database's ``clock_timestamp()`` for PostgreSQL), and every instant the
machine chooses given as an offset from that side's own start. A database clock skewed
against this host therefore changes no reading.

Time. No step sleeps. ``claim`` and ``heartbeat`` take ``lease`` as an interval added to the
database clock (``now() + $n::interval``), so a lease is made to lapse by granting it a
negative one (one second in the past); a live lease is an hour. ``advance_lease`` lapses a
held lease through its holder's own heartbeat. ``run_after`` moves through the one seam the
interface lacks, ``Side.pin``: ``advance_clock`` makes every waiting job due, and ``nack``'s
backoff -- ``now() + least(2^attempts * 2s, 15min) * random()`` in PostgreSQL -- is first
checked against that window and then pinned to one instant on both sides, because a random
backoff would otherwise make the next claim a coin toss. Every instant the machine chooses
is distinct, so ``_CLAIM_ORDER``'s last resort, the generated id, never decides a claim.

Laws (checked after every step, on both sides; the source of each in brackets):
- the claim never hands out a job someone holds [``claim``: "Claims the highest-priority
  ready job"; SQL ``_CLAIMABLE``: ``j.state = 'ready'``]: no job is leased by two owners;
- a job is leased exactly when it has a holder and a lease [SQL: ``claim`` sets
  ``state='leased'`` with ``lease_owner`` and ``lease_expires_at``; every release nulls both];
- a job is in exactly one state, and ``queue_depth`` counts every job once [``queue_depth``:
  "the number of jobs by state ... Every ``JobState`` member is present"];
- ``count_unsettled`` is the number of jobs not succeeded, failed or cancelled
  [``count_unsettled``];
- ``ack`` is terminal: an acked job never changes again [SQL ``ack``: ``state='succeeded'``,
  ``lease_owner = NULL``, and every write is guarded by ``lease_owner = $2``];
- a caller that does not hold the lease can change nothing [SQL: ``WHERE id = $1 AND
  lease_owner = $2`` on every guarded write];
- ``claimable_projects`` lists the project exactly when a ready, due job has every
  dependency succeeded [``claimable_projects``; SQL ``_CLAIMABLE``].

The negative controls run the same machine with a deliberately wrong fake as the reference
and the correct fake as the subject, without a database, and require Hypothesis to find the
divergence: they are what shows the machine can fail. One wrong fake per kind of check: a
wrong claim (the claim comparison), a wrong guard (the guarded-write comparison), and a
wrong row behind right answers (the job-table comparison, which nothing else sees).
"""

import asyncio
from collections import Counter
from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any, Protocol
from uuid import UUID, uuid4

import asyncpg
import pytest
from hypothesis import Phase as HypothesisPhase
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
    run_state_machine_as_test,
)

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.interfaces.queue import JobRepository
from vibey.domain.engine import EngineId
from vibey.domain.job import JobState, StoredJobState
from vibey.domain.phase import Phase
from vibey.infrastructure.db.job_repository import PostgresJobRepository

LIVE = timedelta(hours=1)
LAPSED = timedelta(seconds=-1)
OWNERS = ("w1", "w2", "w3")
HOLDER = "holder"
"""An owner choice that resolves to whoever holds the picked job's lease right now."""
CALLERS = st.sampled_from((HOLDER, HOLDER, *OWNERS))
"""Who calls a guarded write: the holder more often than not (counting a named owner who
happens to hold it), so the successful write is exercised as well as the refused one."""
CYCLE = 1
KIND = "build.implement"
TERMINAL = frozenset({JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED})
ERROR: Mapping[str, object] = {"reason": "boom"}

MACHINE_SETTINGS = settings(max_examples=25, stateful_step_count=20, deadline=None)
CONTROL_SETTINGS = settings(
    max_examples=200,
    stateful_step_count=20,
    deadline=None,
    database=None,
    derandomize=True,
    phases=[HypothesisPhase.generate, HypothesisPhase.shrink],
)
"""The controls are deterministic (``derandomize``) and record nothing in the example
database, so a control's verdict never depends on what an earlier run remembered. They
skip Hypothesis' explain phase, which only annotates the report and was most of their
time."""


class Runner(Protocol):
    """Runs one coroutine to completion from the machine's (synchronous) thread."""

    def __call__[T](self, coro: Coroutine[Any, Any, T], /) -> T: ...


@dataclass(frozen=True)
class Side:
    """One repository under the machine, and the moves its interface deliberately lacks:
    ``pin`` sets a job's ``run_after``, ``reset`` empties the queue, and ``clock`` reads the
    clock that side judges time by (the database's for PostgreSQL), so no reading ever
    compares one host's clock with another's."""

    name: str
    repo: JobRepository
    pin: Callable[[UUID, datetime], Coroutine[Any, Any, None]]
    reset: Callable[[], Coroutine[Any, Any, None]]
    clock: Callable[[], Coroutine[Any, Any, datetime]]


@dataclass(frozen=True)
class Row:
    """One job as both sides must agree on it: no generated id, no clock reading."""

    index: int
    state: StoredJobState
    owner: str | None
    lease: str
    attempts: int
    max_attempts: int
    due: bool
    payload: dict[str, object]
    last_error: dict[str, object] | None
    engine: str | None


class FakeSides:
    """Builds a fresh fake as a ``Side`` -- a new instance per example is its reset."""

    @staticmethod
    def of(repo: FakeJobRepository, name: str = "fake") -> Side:
        async def pin(job_id: UUID, at: datetime) -> None:
            repo._jobs[job_id] = replace(repo._jobs[job_id], run_after=at)

        async def reset() -> None:
            repo._jobs.clear()
            repo.dependencies.clear()

        async def clock() -> datetime:
            return datetime.now(UTC)

        return Side(name, repo, pin, reset, clock)


class LeaseBlindJobRepository(FakeJobRepository):
    """WRONG ON PURPOSE (negative control): ``claim`` ignores the lease, so a job another
    owner still holds is handed out again, as though it were ready."""

    async def claim(self, project_id: UUID, *, owner: str, lease: timedelta) -> JobRecord | None:
        for job in self._jobs.values():
            if job.project_id == project_id and job.state is JobState.LEASED:
                taken = replace(
                    job,
                    lease_owner=owner,
                    lease_expires_at=datetime.now(UTC) + lease,
                    attempts=job.attempts + 1,
                )
                self._jobs[job.id] = taken
                return taken
        return await super().claim(project_id, owner=owner, lease=lease)


class OwnerBlindAckJobRepository(FakeJobRepository):
    """WRONG ON PURPOSE (negative control): ``ack`` by someone who does not hold the lease
    succeeds, as long as somebody holds it."""

    async def ack(self, job_id: UUID, *, owner: str) -> bool:
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner is None:
            return False
        return await super().ack(job_id, owner=job.lease_owner)


class RefundlessDeferJobRepository(FakeJobRepository):
    """WRONG ON PURPOSE (negative control): ``defer`` answers True and releases the lease,
    but keeps the attempt it should refund. Every value it returns is right; only the row it
    leaves behind is wrong, so only the job-table comparison can see it."""

    async def defer(
        self, job_id: UUID, *, owner: str, retry_at: datetime, error: Mapping[str, object]
    ) -> bool:
        job = self._jobs.get(job_id)
        done = await super().defer(job_id, owner=owner, retry_at=retry_at, error=error)
        if done and job is not None:
            self._jobs[job_id] = replace(self._jobs[job_id], attempts=job.attempts)
        return done


class JobRepositoryMachine(RuleBasedStateMachine):
    """The reference and the subject, driven in lockstep; see the module docstring."""

    def __init__(
        self, sides: Callable[[], tuple[Side, Side]], run: Runner, project_id: UUID
    ) -> None:
        super().__init__()
        self.run = run
        self.reference, self.subject = sides()
        run(self.reference.reset())
        run(self.subject.reset())
        self.project_id = project_id
        self.ids: list[tuple[UUID, UUID]] = []
        self.index: tuple[dict[UUID, int], dict[UUID, int]] = ({}, {})
        self.dependencies: dict[int, int] = {}
        self.acked: dict[int, Row] = {}
        self.instants = count(1)
        self.starts = (run(self.reference.clock()), run(self.subject.clock()))

    # -- helpers ---------------------------------------------------------------------------

    @property
    def sides(self) -> tuple[Side, Side]:
        return (self.reference, self.subject)

    def _offset(self, *, future: bool) -> timedelta:
        """A due (past) or waiting (future) offset no other offset of this run equals."""
        step = timedelta(milliseconds=next(self.instants))
        return (LIVE if future else -LIVE) + step

    def _at(self, side: int, offset: timedelta) -> datetime:
        """The instant ``offset`` names on one side: from that side's own start, read on its
        own clock, so a database clock skewed against this host shifts nothing."""
        return self.starts[side] + offset

    def _now(self, side: int) -> datetime:
        return self.run(self.sides[side].clock())

    def _job(self, pick: int) -> tuple[int | None, UUID, UUID]:
        """The picked job's index and its id on each side; an unknown id when there is none.

        A held job is four times as likely to be picked as any other, so the guarded writes
        meet a lease -- the case they exist for -- more often than a settled row."""
        if not self.ids:
            ghost = uuid4()
            return None, ghost, ghost
        held = [row.index for row in self._rows(0) if row.owner is not None]
        candidates = held * 3 + list(range(len(self.ids)))
        index = candidates[pick % len(candidates)]
        return (index, *self.ids[index])

    def _row(self, index: int, record: JobRecord, now: datetime) -> Row:
        lease = (
            "none"
            if record.lease_expires_at is None
            else ("lapsed" if record.lease_expires_at < now else "live")
        )
        return Row(
            index=index,
            state=record.state,
            owner=record.lease_owner,
            lease=lease,
            attempts=record.attempts,
            max_attempts=record.max_attempts,
            due=record.run_after <= now,
            payload=dict(record.payload),
            last_error=dict(record.last_error) if record.last_error is not None else None,
            engine=record.assigned_engine,
        )

    def _returned(self, side: int, record: JobRecord | None) -> Row | None:
        if record is None:
            return None
        index = self.index[side].get(record.id)
        assert index is not None, f"{self.sides[side].name} returned a job never enqueued"
        return self._row(index, record, self._now(side))

    def _rows(self, side: int) -> list[Row]:
        repo = self.sides[side].repo
        now = self._now(side)
        rows = []
        for index, ids in enumerate(self.ids):
            record = self.run(repo.get(ids[side]))
            assert record is not None, f"{self.sides[side].name} lost job {index}"
            rows.append(self._row(index, record, now))
        listed = self.run(repo.list_for_cycle(self.project_id, cycle=CYCLE, kind=KIND))
        named = sorted(self.index[side].get(job.id, -1) for job in listed)
        assert named == list(range(len(self.ids))), (
            f"{self.sides[side].name} lists jobs {named}, enqueued {len(self.ids)} "
            "(-1 is a job never enqueued)"
        )
        return rows

    def _request(self, key: int, max_attempts: int) -> EnqueueRequest:
        return EnqueueRequest(
            project_id=self.project_id,
            cycle=CYCLE,
            phase=Phase.BUILD,
            kind=KIND,
            idempotency_key=f"k{key}",
            payload={"n": next(self.instants)},
            max_attempts=max_attempts,
        )

    def _guarded(
        self,
        name: str,
        pick: int,
        who: str,
        call: Callable[[int, JobRepository, UUID, str], Coroutine[Any, Any, bool]],
    ) -> tuple[int | None, bool]:
        """One lease-guarded write on both sides (``call`` gets the side's number, its repository,
        the job's id there and the caller). Both must answer alike, and a caller that does not
        hold the lease must get False and leave the row exactly as it was."""
        index, *ids = self._job(pick)
        before = [self.run(side.repo.get(ids[n])) for n, side in enumerate(self.sides)]
        holder = before[0].lease_owner if before[0] is not None else None
        owner = (holder or OWNERS[0]) if who == HOLDER else who
        results = [self.run(call(n, side.repo, ids[n], owner)) for n, side in enumerate(self.sides)]
        assert results[0] == results[1], (
            f"{name} diverged on job {index} by {owner}: "
            f"{self.reference.name} {results[0]}, {self.subject.name} {results[1]}"
        )
        for n, side in enumerate(self.sides):
            was = before[n]
            if was is None or was.lease_owner != owner:
                assert not results[n], f"{side.name}: {name} by non-owner {owner} succeeded"
                after = self.run(side.repo.get(ids[n]))
                assert after == was, f"{side.name}: {name} by non-owner {owner} wrote"
        return index, results[0]

    # -- rules -----------------------------------------------------------------------------

    @initialize(
        jobs=st.integers(min_value=1, max_value=3),
        holders=st.lists(st.sampled_from(OWNERS), max_size=3),
    )
    def seed(self, jobs: int, holders: list[str]) -> None:
        """A queue with work in it, some of it already held, so the guarded writes meet a
        lease from the first step rather than only after a lucky enqueue-then-claim."""
        for key in range(jobs):
            self.enqueue(key=key, when="now", dependency=None, max_attempts=3)
        for owner in holders:
            self.claim(owner=owner, lease=LIVE)

    @rule(
        key=st.integers(min_value=0, max_value=5),
        when=st.sampled_from(["now", "past", "future"]),
        dependency=st.none() | st.integers(min_value=0, max_value=100),
        max_attempts=st.integers(min_value=1, max_value=3),
    )
    def enqueue(self, key: int, when: str, dependency: int | None, max_attempts: int) -> None:
        offset = None if when == "now" else self._offset(future=when == "future")
        depends_on: list[tuple[UUID, ...]] = [(), ()]
        depends_index = None
        if dependency is not None and self.ids:
            depends_index = dependency % len(self.ids)
            depends_on = [(self.ids[depends_index][0],), (self.ids[depends_index][1],)]
        request = self._request(key, max_attempts)
        made = [
            self.run(
                side.repo.enqueue(
                    replace(
                        request,
                        depends_on=depends_on[n],
                        run_after=None if offset is None else self._at(n, offset),
                    )
                )
            )
            for n, side in enumerate(self.sides)
        ]
        known = [self.index[n].get(made[n].id) for n in range(2)]
        assert known[0] == known[1], f"enqueue of k{key} diverged: {known[0]} vs {known[1]}"
        if known[0] is None:
            index = len(self.ids)
            self.ids.append((made[0].id, made[1].id))
            self.index[0][made[0].id] = index
            self.index[1][made[1].id] = index
            if depends_index is not None:
                self.dependencies[index] = depends_index
        rows = [self._row(self.index[n][made[n].id], made[n], self._now(n)) for n in range(2)]
        assert rows[0] == rows[1], f"enqueue of k{key} returned {rows[0]} vs {rows[1]}"

    @rule(owner=st.sampled_from(OWNERS), lease=st.sampled_from([LIVE, LAPSED]))
    def claim(self, owner: str, lease: timedelta) -> None:
        before = [self._rows(0), self._rows(1)]
        claimed = [
            self._returned(n, self.run(side.repo.claim(self.project_id, owner=owner, lease=lease)))
            for n, side in enumerate(self.sides)
        ]
        assert claimed[0] == claimed[1], (
            f"claim diverged for {owner}: "
            f"{self.reference.name} {claimed[0]}, {self.subject.name} {claimed[1]}"
        )
        for n, row in enumerate(claimed):
            if row is not None:
                was = before[n][row.index]
                assert was.state is JobState.READY, (
                    f"{self.sides[n].name}: claim gave {owner} job {row.index}, "
                    f"which was {was.state} held by {was.owner}"
                )

    @rule(
        pick=st.integers(min_value=0, max_value=100),
        who=CALLERS,
        lease=st.sampled_from([LIVE, LAPSED]),
    )
    def heartbeat(self, pick: int, who: str, lease: timedelta) -> None:
        self._guarded(
            "heartbeat",
            pick,
            who,
            lambda _, repo, job, owner: repo.heartbeat(job, owner=owner, lease=lease),
        )

    @rule(pick=st.integers(min_value=0, max_value=100), who=CALLERS)
    def ack(self, pick: int, who: str) -> None:
        index, done = self._guarded(
            "ack", pick, who, lambda _, repo, job, owner: repo.ack(job, owner=owner)
        )
        if done and index is not None:
            self.acked[index] = self._rows(0)[index]

    @rule(pick=st.integers(min_value=0, max_value=100), who=CALLERS)
    def nack(self, pick: int, who: str) -> None:
        started = [self._now(n) for n in range(2)]
        index, done = self._guarded(
            "nack", pick, who, lambda _, repo, job, owner: repo.nack(job, owner=owner, error=ERROR)
        )
        if not done or index is None:
            return
        finished = [self._now(n) for n in range(2)]
        settled = self._offset(future=True)
        for n, side in enumerate(self.sides):
            record = self.run(side.repo.get(self.ids[index][n]))
            assert record is not None
            # SQL `nack`: run_after = now() + least(2^attempts * 2s, 15min) * random().
            cap = min(timedelta(seconds=2 * 2**record.attempts), timedelta(minutes=15))
            slack = timedelta(milliseconds=500)
            low, high = started[n] - slack, finished[n] + cap + slack
            assert low <= record.run_after <= high, (
                f"{side.name}: nack backoff {record.run_after} outside [{low}, {high}]"
            )
            self.run(side.pin(self.ids[index][n], self._at(n, settled)))

    @rule(
        pick=st.integers(min_value=0, max_value=100),
        who=CALLERS,
        later=st.booleans(),
    )
    def defer(self, pick: int, who: str, later: bool) -> None:
        retry = self._offset(future=later)
        self._guarded(
            "defer",
            pick,
            who,
            lambda n, repo, job, owner: repo.defer(
                job, owner=owner, retry_at=self._at(n, retry), error=ERROR
            ),
        )

    @rule(pick=st.integers(min_value=0, max_value=100), who=CALLERS)
    def park(self, pick: int, who: str) -> None:
        self._guarded("park", pick, who, lambda _, repo, job, owner: repo.park(job, owner=owner))

    @rule(
        pick=st.integers(min_value=0, max_value=100),
        who=CALLERS,
        bound=st.integers(min_value=1, max_value=5),
    )
    def grant_attempts(self, pick: int, who: str, bound: int) -> None:
        self._guarded(
            "grant_attempts",
            pick,
            who,
            lambda _, repo, job, owner: repo.grant_attempts(job, owner=owner, max_attempts=bound),
        )

    @rule(
        pick=st.integers(min_value=0, max_value=100),
        who=CALLERS,
        engine=st.sampled_from(EngineId),
    )
    def assign_engine(self, pick: int, who: str, engine: EngineId) -> None:
        self._guarded(
            "assign_engine",
            pick,
            who,
            lambda _, repo, job, owner: repo.assign_engine(job, owner=owner, engine_id=engine),
        )

    @rule()
    def reap(self) -> None:
        reaped = [self.run(side.repo.reap()) for side in self.sides]
        assert reaped[0] == reaped[1], f"reap diverged: {reaped[0]} vs {reaped[1]}"

    @rule(pick=st.integers(min_value=0, max_value=100))
    def advance_lease(self, pick: int) -> None:
        """Time passes for one held lease: its holder's heartbeat grants it a lapsed one."""
        held = [row for row in self._rows(0) if row.owner is not None]
        if not held:
            return
        row = held[pick % len(held)]
        owner = row.owner
        assert owner is not None
        for n, side in enumerate(self.sides):
            assert self.run(side.repo.heartbeat(self.ids[row.index][n], owner=owner, lease=LAPSED))

    @rule()
    def advance_clock(self) -> None:
        """Time passes for every waiting job: each becomes due, in index order."""
        for row in self._rows(0):
            if not row.due:
                offset = self._offset(future=False)
                for n, side in enumerate(self.sides):
                    self.run(side.pin(self.ids[row.index][n], self._at(n, offset)))

    # -- invariants ------------------------------------------------------------------------

    @invariant()
    def both_sides_agree_and_keep_the_queue_laws(self) -> None:
        rows = [self._rows(0), self._rows(1)]
        assert rows[0] == rows[1], (
            f"job tables diverged:\n{self.reference.name}: {rows[0]}\n"
            f"{self.subject.name}: {rows[1]}"
        )
        for n, side in enumerate(self.sides):
            self._laws(side, rows[n])

    def _laws(self, side: Side, rows: list[Row]) -> None:
        for row in rows:
            leased = row.state is JobState.LEASED
            assert leased == (row.owner is not None) == (row.lease != "none"), (
                f"{side.name}: job {row.index} is {row.state} with holder {row.owner} "
                f"and a {row.lease} lease"
            )
            assert isinstance(row.state, JobState), f"{side.name}: job {row.index} {row.state}"
        for index, at_ack in self.acked.items():
            assert rows[index] == at_ack, f"{side.name}: acked job {index} changed"
        depth = dict(self.run(side.repo.queue_depth(self.project_id)))
        expected: dict[StoredJobState, int] = {state: 0 for state in JobState}
        expected.update(Counter(row.state for row in rows))
        assert depth == expected, f"{side.name}: queue_depth {depth}, jobs {expected}"
        assert sum(depth.values()) == len(rows), f"{side.name}: a job in no state, or two"
        unsettled = self.run(
            side.repo.count_unsettled(self.project_id, cycle=CYCLE, phase=Phase.BUILD)
        )
        assert unsettled == sum(row.state not in TERMINAL for row in rows), (
            f"{side.name}: count_unsettled {unsettled}"
        )
        claimable = any(
            row.state is JobState.READY
            and row.due
            and (
                row.index not in self.dependencies
                or rows[self.dependencies[row.index]].state is JobState.SUCCEEDED
            )
            for row in rows
        )
        projects = self.run(side.repo.claimable_projects())
        assert projects == ((self.project_id,) if claimable else ()), (
            f"{side.name}: claimable_projects {projects}, claimable {claimable}"
        )


class MachineHarness:
    """Runs the (synchronous) machine on a worker thread, every coroutine on this loop.

    The PostgreSQL pool belongs to the test's event loop, so the machine cannot start a
    loop of its own: each call is handed back to the test's loop and waited for. This is
    what ``JobRepositoryMachine.TestCase`` would run (its ``runTest`` is
    ``run_state_machine_as_test``), as a pytest test so it can take the database fixtures:
    a unittest ``TestCase`` cannot, and the per-worker database is only known to them."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def __call__[T](self, coro: Coroutine[Any, Any, T], /) -> T:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    async def check(
        self, sides: Callable[[], tuple[Side, Side]], project_id: UUID, config: settings
    ) -> None:
        await asyncio.to_thread(
            run_state_machine_as_test,
            lambda: JobRepositoryMachine(sides, self, project_id),
            settings=config,
        )


# -- the fake against PostgreSQL ---------------------------------------------------------


async def test_the_fake_and_postgres_agree_through_random_operation_sequences(
    migrated_pool: asyncpg.Pool, project_id: UUID, database_url: str
) -> None:
    # Migrated once, by the fixture; each example then starts from an empty job table. The
    # owner deletes the rows (the application role holds no DELETE, ADR-0055); the ledger
    # events `reap` appends stay, as the append-only ledger requires, and name no job row.
    owner = await asyncpg.connect(database_url)
    postgres = PostgresJobRepository(migrated_pool)

    async def pin(job_id: UUID, at: datetime) -> None:
        await migrated_pool.execute("UPDATE job SET run_after = $2 WHERE id = $1", job_id, at)

    async def reset() -> None:
        await owner.execute("DELETE FROM job")

    async def clock() -> datetime:
        # The clock `claim`, `reap` and `nack` judge by: the database's, never this host's.
        at: datetime = await migrated_pool.fetchval("SELECT clock_timestamp()")
        return at

    def sides() -> tuple[Side, Side]:
        return FakeSides.of(FakeJobRepository()), Side("postgres", postgres, pin, reset, clock)

    try:
        await MachineHarness(asyncio.get_running_loop()).check(sides, project_id, MACHINE_SETTINGS)
    finally:
        await owner.close()


# -- controls, without a database ----------------------------------------------------------


async def test_the_machine_passes_the_fake_against_itself() -> None:
    # Positive control: two correct fakes never diverge, so a failure below is the bug's.
    def sides() -> tuple[Side, Side]:
        return FakeSides.of(FakeJobRepository(), "fake-a"), FakeSides.of(FakeJobRepository())

    await MachineHarness(asyncio.get_running_loop()).check(sides, uuid4(), CONTROL_SETTINGS)


@pytest.mark.parametrize(
    ("wrong", "found"),
    [
        (LeaseBlindJobRepository, r"^claim diverged for w\d"),
        (OwnerBlindAckJobRepository, r"^ack diverged on job \d+ by w\d"),
        # Right answers, wrong row: only the job-table comparison can find this one.
        (RefundlessDeferJobRepository, r"^job tables diverged"),
    ],
)
async def test_the_machine_finds_a_wrong_reference(
    wrong: type[FakeJobRepository], found: str
) -> None:
    # Negative control (Review Focus 2): the same machine over a deliberately wrong
    # reference, against the correct fake, must find the divergence.
    def sides() -> tuple[Side, Side]:
        return FakeSides.of(wrong(), "wrong"), FakeSides.of(FakeJobRepository())

    with pytest.raises(AssertionError, match=found):
        await MachineHarness(asyncio.get_running_loop()).check(sides, uuid4(), CONTROL_SETTINGS)
