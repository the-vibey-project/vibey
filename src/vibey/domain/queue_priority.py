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

The lane is derived (contract item 6): it is exactly the jobs bumped (or enqueued
prioritised) BY NAME and not since un-bumped, plus all their unfinished transitive
dependencies, ordered first-in-first-out by when each first entered it. `job.bump_named`
marks the named ones. Un-bumping a job removes it from the named set, and is refused while
another named job depends on it; every pulled job the remaining named jobs no longer need
leaves with it, so no orphan can remain.

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
    """Enqueue a job already bumped (contract item 7). Bumping or re-enqueueing a job
    that has already finished is a recorded no-op, the way a plain re-enqueue is."""


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
    bump_named: bool = False
    """Bumped by name and not since un-bumped; false for a job pulled into the lane."""
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
        """In the named set: bumped by name, rather than pulled in for another job."""
        return self.bumped and self.bump_named


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
    """True when the target was already in the lane as another job's dependency and is
    now bumped by name: it keeps its place, and joins the named set."""
    swept: tuple[UUID, ...] = ()
    """Lane members the lane no longer derives -- left behind by a named job that was
    cancelled or failed with its dependencies unfinished -- cleared by this request."""
    skipped: tuple[UUID, ...] = ()
    """Jobs the sweep would clear but will not write: their phase is one this vibey does
    not know (vibey#287). They stay where they are, and the request says so."""


@dataclass(frozen=True, slots=True)
class UnbumpPlan:
    """What an un-bump returns to normal order: the target first, then every pulled job
    the remaining named jobs no longer need, in claim order."""

    target: UUID
    moved: tuple[UUID, ...]
    """The jobs the un-bump itself clears: the target, then the pulled jobs the
    remaining named jobs no longer need because the target left, in claim order."""
    swept: tuple[UUID, ...] = ()
    """Lane members the lane no longer derived before this request, cleared by it."""
    skipped: tuple[UUID, ...] = ()
    """Jobs it would clear but will not write, their phase unknown to this vibey."""


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

    @staticmethod
    def _alive_named(jobs: Mapping[UUID, QueuedJob]) -> set[UUID]:
        """The named set that still counts: named jobs that have not finished. A named
        job in a state this vibey does not know is kept, not guessed finished."""
        return {j.id for j in jobs.values() if j.named and j.state not in FINISHED_STATES}

    def _orphans(self, jobs: Mapping[UUID, QueuedJob], named: set[UUID]) -> set[UUID]:
        """Unfinished lane members the lane, derived from `named`, does not contain."""
        derived: set[UUID] = set()
        for job_id in named:
            derived |= set(self._needs(jobs, jobs[job_id]))
        return {j.id for j in jobs.values() if j.bumped and j.movable and j.id not in derived}

    def _clearable(
        self, jobs: Mapping[UUID, QueuedJob], ids: set[UUID]
    ) -> tuple[tuple[UUID, ...], tuple[UUID, ...]]:
        """`ids` in claim order, split into those it may clear and those in a phase this
        vibey does not know, which it leaves alone rather than refuse the request."""
        ordered = self._order.sort(jobs[job_id] for job_id in ids)
        return (
            tuple(j.id for j in ordered if j.phase_known),
            tuple(j.id for j in ordered if not j.phase_known),
        )

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
        orphans = self._orphans(jobs, self._alive_named(jobs))
        if finished_ok and job.state in FINISHED_STATES:
            swept, skipped = self._clearable(jobs, orphans)
            return BumpPlan(target=target, moved=(), swept=swept, skipped=skipped)
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
        swept, skipped = self._clearable(jobs, orphans - set(members))
        return BumpPlan(
            target=target,
            moved=moved,
            kept=tuple(m.id for m in ordered if m.bumped and m.id != target),
            named=job.bumped and not job.named,
            swept=swept,
            skipped=skipped,
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
    """Removes a job from the named set, and re-derives the lane (contract item 6).

    The lane is exactly the named jobs plus all their unfinished transitive dependencies.
    Un-bumping a job is refused, naming them, while another named job depends on it. It
    otherwise clears the job and every pulled job the remaining named jobs no longer need
    -- wherever it was pulled from -- so the lane afterwards is the derivation, with no
    orphan left over. `jobs` is the target and every unfinished job of its project.
    """

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> UnbumpPlan:
        root = self._target(jobs, target)
        named = self._alive_named(jobs)
        orphans = self._orphans(jobs, named) - {target}
        swept, skipped = self._clearable(jobs, orphans)
        if not root.bumped:
            return UnbumpPlan(target=target, moved=(), swept=swept, skipped=skipped)
        remaining = named - {target}
        dependents = sorted(
            job_id for job_id in remaining if target in self._needs(jobs, jobs[job_id])
        )
        if dependents:
            raise DependentsStillBumped(target, tuple(dependents))
        released = self._orphans(jobs, remaining) - orphans - {target}
        cleared, held = self._clearable(jobs, released)
        return UnbumpPlan(
            target=target,
            moved=(target, *cleared),
            swept=swept,
            skipped=tuple(sorted({*held, *skipped})),
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
    swept: tuple[MovedJob, ...] = ()
    """Lane members the lane no longer derived, cleared by this request (finding: a
    named job cancelled or failed with its dependencies unfinished)."""
    skipped: tuple[UUID, ...] = ()
    """Jobs left in the lane because their phase is one this vibey does not know."""

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
