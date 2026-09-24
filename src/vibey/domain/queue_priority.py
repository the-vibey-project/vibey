# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority: who may move a job ahead, and what moves with it (ADR-0054).

A **bump** puts a job next in line: after whatever is running, behind every job bumped
before it, ahead of all un-bumped waiting work. The ordering is one nullable column,
`job.bump_seq`, drawn from a database sequence at the moment of the bump; the claim
orders `bump_seq ASC NULLS LAST` before everything it ordered by already. A bump
changes order and nothing else: it never takes a lease from the worker holding it
(8.c), never shortens a capacity deferral, and never makes a job claimable before its
dependencies succeed -- which is why it pulls unfinished dependencies forward with it,
and refuses outright when one of them can never finish.

`job.bump_origin` records which bump moved a job: its own id when it was bumped by
name, the named job's id when it was pulled forward as a dependency. An un-bump undoes
exactly what a bump moved -- the job, and the dependencies pulled forward for it that
no other still-bumped job needs -- and refuses while a bumped job still needs it.

Only the operator, verified as the account that owns the project's reviewed
configuration, and the sources that configuration declares, may bump (12.h, 12.j).
Everything here is pure: the snapshot and the caller come in, a plan or a decision
goes out.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from vibey.domain.errors import (
    DependencyCannotFinish,
    DependencyCycle,
    DependentsStillBumped,
    NotReorderable,
)
from vibey.domain.interfaces.queue_priority_interface import (
    BumpPlannerInterface,
    CallerInterface,
    ClaimOrderInterface,
    UnbumpPlannerInterface,
)
from vibey.domain.job import JobState, StoredJobState
from vibey.domain.phase import Phase

OPERATOR_SOURCE: Final = "operator"
"""Reserved: never a declarable source name. The operator names no source at all;
the operator is whoever the uid check says it is."""

MOVABLE_STATES: Final = frozenset(
    {JobState.READY, JobState.LEASED, JobState.AWAITING_HUMAN, JobState.AWAITING_CAPACITY}
)
"""The states a job can still be claimed from, now or later. A leased job is here:
bumping it takes nothing from the worker holding it, and keeps its place if the
attempt returns it to the queue."""

FINISHED_STATES: Final = frozenset({JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED})


class PriorityAction(StrEnum):
    BUMP = "bump"
    UNBUMP = "unbump"
    ENQUEUE = "enqueue"
    """Enqueue a job already bumped (contract item 7). Re-enqueueing a job that has
    already finished is a recorded no-op, the way a plain re-enqueue is a no-op."""


@dataclass(frozen=True, slots=True)
class Caller:
    """The account a request runs as: the process's uid, and that uid's account name
    from the password database -- never an environment variable, which the caller
    sets for itself."""

    uid: int
    name: str


@dataclass(frozen=True, slots=True)
class PriorityDecision:
    """What the grant made of one request. `principal` is who asked, as the ledger
    records it -- `operator:NAME`, `source:NAME` or `account:NAME` -- admitted or not."""

    admitted: bool
    principal: str
    reason: str = ""


class PriorityGrant:
    """Who may reorder a project's queue.

    The operator is the account that owns the project's reviewed configuration
    (`anchor`): a tangible check -- the uid of the process against the owner of a
    file -- not a claim (SD-01 §2). An automation names itself with a source, which is
    admitted only when the configuration declares it AND the request runs as that same
    account; a declared name is not a credential, and a stranger's process cannot borrow
    one. The absence of a declaration is refusal (12.f): with nothing declared, only the
    operator may reorder. An anchor nobody owns (`owner_uid` None) admits nobody.
    """

    def __init__(self, declared: Iterable[str] = (), *, owner_uid: int | None, anchor: str) -> None:
        self._declared = tuple(declared)
        self._owner_uid = owner_uid
        self._anchor = anchor

    @property
    def declared(self) -> frozenset[str]:
        return frozenset(self._declared)

    @property
    def anchor(self) -> str:
        return self._anchor

    def decide(self, source: str | None, caller: CallerInterface) -> PriorityDecision:
        owner = self._owner_uid is not None and caller.uid == self._owner_uid
        if source is None:
            if owner:
                return PriorityDecision(admitted=True, principal=f"operator:{caller.name}")
            return PriorityDecision(
                admitted=False,
                principal=f"account:{caller.name}",
                reason=(
                    f"the account {caller.name} does not own {self._anchor}, so it is not the "
                    "operator; an automation must name a source declared in "
                    "[queue.priority] sources"
                ),
            )
        principal = f"source:{source}"
        if source not in self._declared:
            declared = ", ".join(self._declared) or "none"
            return PriorityDecision(
                admitted=False,
                principal=principal,
                reason=(
                    f"source {source!r} is not declared in [queue.priority] sources in "
                    f"{self._anchor} (declared: {declared})"
                ),
            )
        if not owner:
            return PriorityDecision(
                admitted=False,
                principal=principal,
                reason=(
                    f"source {source!r} was named by the account {caller.name}, which does "
                    f"not own {self._anchor}; a declared source runs as the operator's account"
                ),
            )
        return PriorityDecision(admitted=True, principal=principal)


@dataclass(frozen=True, slots=True)
class QueuedJob:
    """The part of a job row that decides its place in the queue."""

    id: UUID
    state: StoredJobState
    priority: int
    run_after: datetime
    bump_seq: int | None = None
    depends_on: tuple[UUID, ...] = ()
    bump_origin: UUID | None = None
    """The job whose bump moved this one: itself when bumped by name, the named job
    when it was pulled forward as a dependency, None when not bumped."""
    phase_known: bool = True
    """False for a phase a newer vibey wrote; such a job is never written (vibey#287)."""

    @property
    def bumped(self) -> bool:
        return self.bump_seq is not None

    @property
    def movable(self) -> bool:
        return self.state in MOVABLE_STATES

    @property
    def named(self) -> bool:
        """Bumped by name, rather than pulled forward for another job."""
        return self.bumped and self.bump_origin == self.id


class ClaimOrder:
    """The claim query's ORDER BY, as a sort key.

    `bump_seq ASC NULLS LAST, priority DESC, run_after ASC, id ASC`. A UUID sorts by its
    128-bit integer, which is the byte order Postgres compares `uuid` in, so the key and
    the query agree on every tie (tests/infrastructure/db pins it).
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
    """Dependencies already bumped. They keep the place they have."""
    named: bool = False
    """True when the target was already bumped as another job's dependency and is now
    bumped by name: its place is kept, and it no longer goes back with that job."""


@dataclass(frozen=True, slots=True)
class UnbumpPlan:
    """What an un-bump returns to normal order: the target first, then the dependencies
    its own bumps pulled forward that nothing else still needs, in claim order."""

    target: UUID
    moved: tuple[UUID, ...]
    reattributed: tuple[tuple[UUID, UUID], ...] = ()
    """Dependencies the target's bumps pulled forward that another bumped job still
    needs: each stays bumped, and now belongs to the bump by name that holds it --
    `(dependency, new origin)`. The target's set resets: it owns nothing afterwards."""


class _SnapshotPlanner:
    """Lookups over a locked snapshot, shared by both planners.

    A job the snapshot lacks is a caller bug: the store fetches what it hands in, so a
    gap means it fetched the wrong rows, and guessing at the missing job's state would
    be worse than stopping. Private, with no public surface: each planner's interface is
    its whole contract.
    """

    def __init__(self, order: ClaimOrderInterface = CLAIM_ORDER) -> None:
        self._order = order

    @staticmethod
    def _get(jobs: Mapping[UUID, QueuedJob], job_id: UUID) -> QueuedJob:
        job = jobs.get(job_id)
        if job is None:
            raise LookupError(f"job {job_id} is not in the snapshot the plan was given")
        return job

    @staticmethod
    def _writable(job: QueuedJob) -> None:
        if not job.phase_known:
            raise NotReorderable(job.id, "its phase is one this vibey does not know")

    def _target(self, jobs: Mapping[UUID, QueuedJob], job_id: UUID) -> QueuedJob:
        job = self._get(jobs, job_id)
        if not job.movable:
            raise NotReorderable(
                job_id, f"it is {job.state.value}, and only an unfinished job can be moved"
            )
        self._writable(job)
        return job

    def _needs(self, jobs: Mapping[UUID, QueuedJob], root: QueuedJob) -> dict[UUID, QueuedJob]:
        """`root` and every unfinished job it depends on, transitively."""
        reached: dict[UUID, QueuedJob] = {}
        stack = [root]
        while stack:
            job = stack.pop()
            if job.id in reached:
                continue
            reached[job.id] = job
            for dep_id in job.depends_on:
                dep = self._get(jobs, dep_id)
                if dep.movable:
                    stack.append(dep)
        return reached


class BumpPlanner(_SnapshotPlanner):
    """Moves a job to the front, and its unfinished dependencies ahead of it."""

    def plan(
        self, target: UUID, jobs: Mapping[UUID, QueuedJob], *, finished_ok: bool = False
    ) -> BumpPlan:
        job = self._get(jobs, target)
        if finished_ok and job.state in FINISHED_STATES:
            return BumpPlan(target=target, moved=())
        self._target(jobs, target)
        members = self._needs(jobs, job)
        blockers = sorted(
            {
                dep_id
                for member in members.values()
                for dep_id in member.depends_on
                if not jobs[dep_id].movable and jobs[dep_id].state is not JobState.SUCCEEDED
            }
        )
        if blockers:
            raise DependencyCannotFinish(
                target, tuple((dep_id, jobs[dep_id].state.value) for dep_id in blockers)
            )
        ordered = self._dependencies_first(members)
        moved = tuple(member.id for member in ordered if not member.bumped)
        for moving in moved:
            self._writable(jobs[moving])
        return BumpPlan(
            target=target,
            moved=moved,
            kept=tuple(m.id for m in ordered if m.bumped and m.id != target),
            named=job.bumped and not job.named,
        )

    def _dependencies_first(self, members: Mapping[UUID, QueuedJob]) -> list[QueuedJob]:
        """Every job after the members it depends on; among those free to go next, the
        one the claim would take first, so pulled jobs keep their relative order."""
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
    """Undoes exactly what a job's bumps moved (contract item 6).

    The target goes back, with each dependency its own bumps pulled forward -- the jobs
    whose `bump_origin` is the target. A dependency stays when a still-bumped job needs
    it (transitively, while unfinished), or when it was bumped by name and not since
    un-bumped. A dependency that stays for another bump is handed to the bump by name
    that holds it, so the target's set resets and no job is left bumped for a bump that
    went back. Un-bumping a job that a bumped job still depends on is refused, naming
    those jobs. `jobs` is the target and every unfinished job of its project.
    """

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> UnbumpPlan:
        root = self._target(jobs, target)
        if not root.bumped:
            return UnbumpPlan(target=target, moved=())
        needs = {
            job.id: self._needs(jobs, job) for job in jobs.values() if job.bumped and job.movable
        }
        dependents = sorted(
            job_id for job_id, reach in needs.items() if job_id != target and target in reach
        )
        if dependents:
            raise DependentsStillBumped(target, tuple(dependents))
        pulled = {
            job_id: job
            for job_id, job in needs[target].items()
            if job_id != target and job.bumped and job.bump_origin == target
        }
        holders = self._order.sort(
            jobs[job_id] for job_id in needs if job_id != target and job_id not in pulled
        )
        cleared: list[QueuedJob] = []
        kept: list[tuple[UUID, UUID]] = []
        for job_id, job in pulled.items():
            holder = next((h for h in holders if job_id in needs[h.id]), None)
            if holder is None:
                self._writable(job)
                cleared.append(job)
            else:
                owner = holder.id if holder.named else holder.bump_origin
                kept.append((job_id, owner or holder.id))
        return UnbumpPlan(
            target=target,
            moved=(target, *(job.id for job in self._order.sort(cleared))),
            reattributed=tuple(sorted(kept)),
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
    """What a bump or an un-bump did. Nothing moved means nothing changed; the request
    is recorded all the same (contract item 5)."""

    action: PriorityAction
    requested_by: str
    target: UUID
    moved: tuple[MovedJob, ...]
    kept: tuple[UUID, ...] = ()
    named: bool = False
    note: str = ""
    """Why nothing moved, when nothing did."""
    reattributed: tuple[tuple[UUID, UUID], ...] = ()
    """For an un-bump: `(dependency, new origin)` for each dependency it kept for
    another bump that still needs it."""

    @property
    def changed(self) -> bool:
        return bool(self.moved) or self.named


@dataclass(frozen=True, slots=True)
class PriorityContext:
    """Where a request is recorded: the project it names, filed under the project's
    current cycle and phase, and who asked."""

    project_id: UUID
    cycle: int
    phase: Phase
    requested_by: str


@dataclass(frozen=True, slots=True)
class PriorityRefusal:
    """A refused reorder request, as the ledger records it. `job_id` is the job the
    request named -- which may not exist -- or None for an enqueue refused before the
    job was made."""

    context: PriorityContext
    job_id: UUID | None
    action: PriorityAction
    reason: str
