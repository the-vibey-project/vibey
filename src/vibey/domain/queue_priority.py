# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority: who may move a job ahead, and what moves with it (ADR-0054).

A **bump** puts a job at the front of its project's queue, behind every job bumped
before it and ahead of all un-bumped waiting work. The ordering is one nullable
column, `job.bump_seq`, drawn from a database sequence at the moment of the bump:
the claim orders `bump_seq ASC NULLS LAST` before everything it ordered by already.
A bump changes order and nothing else. It never takes a lease away from the worker
holding it (sub-doctrine 8.c: one run at a time, and whatever is running finishes),
never shortens a `run_after` a capacity deferral set, and never makes a job
claimable before its dependencies have succeeded -- the claim's dependency check is
untouched, which is why a bump also pulls the job's unfinished dependencies forward:
a bumped job whose dependency waits at the back of the queue has not been moved at
all.

Only the operator, and the sources the operator declares in `[queue.priority]
sources`, may bump (sub-doctrines 12.h and 12.j). Everything here is pure: the
snapshot comes in, a plan goes out, and the store that locked the snapshot applies
it inside the same transaction.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from vibey.domain.errors import DependencyCycle, NotReorderable
from vibey.domain.interfaces.queue_priority_interface import (
    BumpPlannerInterface,
    ClaimOrderInterface,
    UnbumpPlannerInterface,
)
from vibey.domain.job import JobState, StoredJobState
from vibey.domain.phase import Phase

OPERATOR_SOURCE: Final = "operator"
"""The source every command the operator runs speaks as. Admitted without being
declared, and never declarable: `[queue.priority] sources` names the others."""

MOVABLE_STATES: Final = frozenset(
    {JobState.READY, JobState.LEASED, JobState.AWAITING_HUMAN, JobState.AWAITING_CAPACITY}
)
"""The states a job can still be claimed from, now or later. A leased job is here:
bumping it takes nothing from the worker holding it, and keeps its place if the
attempt returns it to the queue."""


class PriorityAction(StrEnum):
    BUMP = "bump"
    UNBUMP = "unbump"
    ENQUEUE = "enqueue"
    """Enqueue a job already bumped: an enqueue followed by a bump of what it made."""


class PriorityGrant:
    """Who may move a job ahead: the operator, and the sources declared in config.

    Absence of a declaration is refusal (12.f, 12.j): with nothing declared, the
    operator is the only source admitted. Matching is exact, so a source is admitted
    under the name the operator wrote and no other.
    """

    def __init__(self, declared: Iterable[str] = ()) -> None:
        self._declared = frozenset(declared)

    @property
    def declared(self) -> frozenset[str]:
        return self._declared

    def admits(self, source: str) -> bool:
        return source == OPERATOR_SOURCE or source in self._declared

    def refusal(self, source: str) -> str:
        return (
            f"source {source!r} may not reorder the queue: only the {OPERATOR_SOURCE} "
            "and the sources declared in `[queue.priority] sources` in vibey.toml may"
        )


@dataclass(frozen=True, slots=True)
class QueuedJob:
    """The part of a job row that decides its place in the queue."""

    id: UUID
    state: StoredJobState
    priority: int
    run_after: datetime
    bump_seq: int | None = None
    depends_on: tuple[UUID, ...] = ()

    @property
    def bumped(self) -> bool:
        return self.bump_seq is not None

    @property
    def movable(self) -> bool:
        return self.state in MOVABLE_STATES


class ClaimOrder:
    """The claim query's ORDER BY, as a sort key.

    `bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC`. A UUID sorts by
    its 128-bit integer, which is the byte order Postgres compares `uuid` in, so the
    key and the query agree on every tie (tests/infrastructure/db pins it).
    """

    def key(self, job: QueuedJob) -> tuple[bool, int, int, datetime, UUID]:
        return (job.bump_seq is None, job.bump_seq or 0, -job.priority, job.run_after, job.id)

    def sort(self, jobs: Iterable[QueuedJob]) -> tuple[QueuedJob, ...]:
        return tuple(sorted(jobs, key=self.key))


CLAIM_ORDER: Final[ClaimOrderInterface] = ClaimOrder()
"""The order every reader shares. Stateless, so one instance serves."""


@dataclass(frozen=True, slots=True)
class BumpPlan:
    """What a bump moves, in the order the moved jobs take their bump numbers."""

    target: UUID
    moved: tuple[UUID, ...]
    """Jobs to give a bump number, dependencies before what needs them."""
    kept: tuple[UUID, ...] = ()
    """Jobs of the closure already bumped. They keep the place they have."""
    blocked_by: tuple[UUID, ...] = ()
    """Dependencies that have not succeeded and cannot be moved -- failed, cancelled,
    or in a state this vibey does not know. The target waits on them regardless."""


@dataclass(frozen=True, slots=True)
class UnbumpPlan:
    """What an un-bump returns to normal order."""

    target: UUID
    moved: tuple[UUID, ...]


class _SnapshotPlanner:
    """Lookups over a locked snapshot, shared by both planners.

    A job the snapshot lacks is a caller bug: the store fetches the closure it hands
    in, so a gap means it fetched the wrong one, and guessing at the missing job's
    state would be worse than stopping. Private, and with no public surface of its
    own: each planner's interface is its whole contract.
    """

    def __init__(self, order: ClaimOrderInterface = CLAIM_ORDER) -> None:
        self._order = order

    @staticmethod
    def _get(jobs: Mapping[UUID, QueuedJob], job_id: UUID) -> QueuedJob:
        job = jobs.get(job_id)
        if job is None:
            raise LookupError(f"job {job_id} is not in the snapshot the plan was given")
        return job

    def _target(self, jobs: Mapping[UUID, QueuedJob], job_id: UUID) -> QueuedJob:
        job = self._get(jobs, job_id)
        if not job.movable:
            raise NotReorderable(
                job_id, f"it is {job.state.value}, and only an unfinished job can be moved"
            )
        return job


class BumpPlanner(_SnapshotPlanner):
    """Moves a job to the front, and its unfinished dependencies ahead of it."""

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> BumpPlan:
        members: dict[UUID, QueuedJob] = {}
        blocked: dict[UUID, None] = {}
        stack = [self._target(jobs, target)]
        while stack:
            job = stack.pop()
            if job.id in members:
                continue
            members[job.id] = job
            for dep_id in job.depends_on:
                dep = self._get(jobs, dep_id)
                if dep.movable:
                    stack.append(dep)
                elif dep.state is not JobState.SUCCEEDED:
                    blocked[dep_id] = None
        ordered = self._dependencies_first(members)
        return BumpPlan(
            target=target,
            moved=tuple(job.id for job in ordered if not job.bumped),
            kept=tuple(job.id for job in ordered if job.bumped),
            blocked_by=tuple(sorted(blocked)),
        )

    def _dependencies_first(self, members: Mapping[UUID, QueuedJob]) -> list[QueuedJob]:
        """Every job after the members it depends on; among those free to go next,
        the one the claim would take first, so pulled jobs keep their relative order."""
        pending = {
            job_id: {dep for dep in job.depends_on if dep in members}
            for job_id, job in members.items()
        }
        ordered: list[QueuedJob] = []
        while pending:
            free = [members[job_id] for job_id, deps in pending.items() if not deps]
            if not free:
                raise DependencyCycle(self._ring(pending))
            nxt = min(free, key=self._order.key)
            ordered.append(nxt)
            del pending[nxt.id]
            for deps in pending.values():
                deps.discard(nxt.id)
        return ordered

    @staticmethod
    def _ring(pending: Mapping[UUID, set[UUID]]) -> tuple[UUID, ...]:
        """The jobs on the ring itself: what is left once every job that nothing
        remaining depends on -- the ring's victims downstream -- is peeled away."""
        remaining = {job_id: set(deps) for job_id, deps in pending.items()}
        while True:
            needed = set().union(*remaining.values())
            victims = [job_id for job_id in remaining if job_id not in needed]
            if not victims:
                return tuple(sorted(remaining))
            for job_id in victims:
                del remaining[job_id]


class UnbumpPlanner(_SnapshotPlanner):
    """Returns a job to normal order, and every bumped job that needs it.

    A bumped job that depends on an un-bumped one cannot run before it, so its bump
    would claim a place it cannot use. The un-bump sends it back too -- the mirror of
    a bump pulling dependencies forward -- and keeps the invariant that a bumped job's
    unfinished dependencies are bumped.
    """

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> UnbumpPlan:
        root = self._target(jobs, target)
        dependents: dict[UUID, list[QueuedJob]] = {}
        for job in jobs.values():
            for dep_id in job.depends_on:
                dependents.setdefault(dep_id, []).append(job)
        reached: dict[UUID, QueuedJob] = {}
        stack = [root]
        while stack:
            job = stack.pop()
            if job.id in reached:
                continue
            reached[job.id] = job
            stack.extend(dependents.get(job.id, ()))
        cleared = [
            job for job in reached.values() if job.id != target and job.bumped and job.movable
        ]
        head = (target,) if root.bumped else ()
        return UnbumpPlan(
            target=target,
            moved=head + tuple(job.id for job in self._order.sort(cleared)),
        )


BUMP_PLANNER: Final[BumpPlannerInterface] = BumpPlanner()
UNBUMP_PLANNER: Final[UnbumpPlannerInterface] = UnbumpPlanner()


@dataclass(frozen=True, slots=True)
class MovedJob:
    """One job a change moved: its bump number after the change, and before it."""

    job_id: UUID
    bump_seq: int | None
    previous: int | None


@dataclass(frozen=True, slots=True)
class PriorityChange:
    """What a bump or an un-bump did. `moved` empty means nothing changed and
    nothing was recorded: a replayed request is a no-op (every job idempotent)."""

    action: PriorityAction
    source: str
    target: UUID
    moved: tuple[MovedJob, ...]
    kept: tuple[UUID, ...] = ()
    blocked_by: tuple[UUID, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.moved)


@dataclass(frozen=True, slots=True)
class PriorityRefusal:
    """A reorder request from a source with no grant, as the ledger records it.

    `job_id` is None for an enqueue refused before the job existed; the project,
    cycle and phase are then the request's.
    """

    project_id: UUID
    cycle: int
    phase: Phase
    job_id: UUID | None
    action: PriorityAction
    source: str
    reason: str
