# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority: who may move a job ahead, and what moves with it (ADR-0054)."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from vibey.domain.errors import (
    DependencyCannotFinish,
    DependencyCycle,
    DependentsStillBumped,
    NotReorderable,
    PriorityRefused,
    ReorderConflict,
    ReorderRefused,
    UnknownJob,
    VibeyError,
)
from vibey.domain.interfaces import (
    BumpPlanInterface,
    BumpPlannerInterface,
    CallerInterface,
    ClaimOrderInterface,
    MovedJobInterface,
    PriorityChangeInterface,
    PriorityContextInterface,
    PriorityDecisionInterface,
    PriorityGrantInterface,
    PriorityRefusalInterface,
    QueueConfigInterface,
    QueuedJobInterface,
    UnbumpPlanInterface,
    UnbumpPlannerInterface,
)
from vibey.domain.job import JobState, UnrecognizedJobState
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import (
    BUMP_PLANNER,
    CLAIM_ORDER,
    FINISHED_STATES,
    MOVABLE_STATES,
    UNBUMP_PLANNER,
    BumpPlan,
    BumpPlanner,
    Caller,
    ClaimOrder,
    MovedJob,
    PriorityAction,
    PriorityChange,
    PriorityContext,
    PriorityGrant,
    PriorityRefusal,
    QueuedJob,
    UnbumpPlan,
    UnbumpPlanner,
)

T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
OWNER = Caller(uid=501, name="adam")
STRANGER = Caller(uid=502, name="mallory")
ANCHOR = "/repo/vibey.toml"


def _id(n: int) -> UUID:
    return UUID(int=n)


def _job(
    n: int,
    *,
    state: JobState | UnrecognizedJobState = JobState.READY,
    bump_seq: int | None = None,
    origin: int | None = None,
    priority: int = 0,
    after: int = 0,
    deps: tuple[int, ...] = (),
    phase_known: bool = True,
) -> QueuedJob:
    return QueuedJob(
        id=_id(n),
        state=state,
        priority=priority,
        run_after=T0 + timedelta(seconds=after),
        bump_seq=bump_seq,
        depends_on=tuple(_id(d) for d in deps),
        bump_origin=_id(origin if origin is not None else n) if bump_seq is not None else None,
        phase_known=phase_known,
    )


def _index(*jobs: QueuedJob) -> Mapping[UUID, QueuedJob]:
    return {job.id: job for job in jobs}


def _grant(*declared: str, owner: int | None = OWNER.uid) -> PriorityGrant:
    return PriorityGrant(declared, owner_uid=owner, anchor=ANCHOR)


# -- the shared instances and values satisfy their declared seams ----------------------


def test_every_shared_instance_and_value_satisfies_its_interface() -> None:
    from vibey.domain.config import QueueConfig

    assert isinstance(CLAIM_ORDER, ClaimOrderInterface)
    assert isinstance(BUMP_PLANNER, BumpPlannerInterface)
    assert isinstance(UNBUMP_PLANNER, UnbumpPlannerInterface)
    assert isinstance(_grant(), PriorityGrantInterface)
    assert isinstance(OWNER, CallerInterface)
    assert isinstance(_grant().decide(None, OWNER), PriorityDecisionInterface)
    assert isinstance(_job(1), QueuedJobInterface)
    assert isinstance(BumpPlan(target=_id(1), moved=()), BumpPlanInterface)
    assert isinstance(UnbumpPlan(target=_id(1), moved=()), UnbumpPlanInterface)
    moved = MovedJob(job_id=_id(1), bump_seq=1, previous=None)
    assert isinstance(moved, MovedJobInterface)
    change = PriorityChange(
        action=PriorityAction.BUMP, requested_by="operator:adam", target=_id(1), moved=(moved,)
    )
    assert isinstance(change, PriorityChangeInterface)
    context = PriorityContext(
        project_id=_id(9), cycle=1, phase=Phase.BUILD, requested_by="account:mallory"
    )
    assert isinstance(context, PriorityContextInterface)
    refusal = PriorityRefusal(
        context=context, job_id=None, action=PriorityAction.ENQUEUE, reason="no"
    )
    assert isinstance(refusal, PriorityRefusalInterface)
    assert isinstance(QueueConfig(), QueueConfigInterface)
    assert frozenset(JobState) == FINISHED_STATES | MOVABLE_STATES


# -- who may reorder the queue (contract item 4) ----------------------------------------


def test_the_account_that_owns_the_reviewed_config_is_the_operator() -> None:
    decision = _grant().decide(None, OWNER)
    assert decision.admitted
    assert decision.principal == "operator:adam"
    assert decision.reason == ""


def test_any_other_account_naming_no_source_is_refused() -> None:
    decision = _grant("storm").decide(None, STRANGER)
    assert not decision.admitted
    assert decision.principal == "account:mallory"
    assert "does not own /repo/vibey.toml" in decision.reason
    assert "[queue.priority] sources" in decision.reason


def test_a_declared_source_is_admitted_only_from_the_owner_account() -> None:
    grant = _grant("storm", "nightly")
    admitted = grant.decide("storm", OWNER)
    assert admitted.admitted and admitted.principal == "source:storm"
    borrowed = grant.decide("storm", STRANGER)
    assert not borrowed.admitted
    assert borrowed.principal == "source:storm"
    assert "named by the account mallory" in borrowed.reason
    assert grant.declared == frozenset({"storm", "nightly"})
    assert grant.anchor == ANCHOR


def test_an_undeclared_source_is_refused_even_from_the_owner() -> None:
    decision = _grant("storm").decide("github-label", OWNER)
    assert not decision.admitted
    assert decision.principal == "source:github-label"
    assert "(declared: storm)" in decision.reason
    assert "(declared: none)" in _grant().decide("Storm", OWNER).reason


def test_an_anchor_nobody_owns_admits_nobody() -> None:
    assert not _grant("storm", owner=None).decide(None, OWNER).admitted
    assert not _grant("storm", owner=None).decide("storm", OWNER).admitted


# -- claim order --------------------------------------------------------------------------


def test_claim_order_puts_every_bumped_job_first_in_bump_order() -> None:
    plain_high = _job(1, priority=100)
    early = _job(2, after=-60)
    bumped_second = _job(3, bump_seq=9, priority=-5)
    bumped_first = _job(4, bump_seq=2, after=60)
    ordered = CLAIM_ORDER.sort([plain_high, early, bumped_second, bumped_first])
    assert [job.id for job in ordered] == [_id(4), _id(3), _id(1), _id(2)]


def test_claim_order_among_unbumped_jobs_is_priority_then_run_after_then_id() -> None:
    order = ClaimOrder()
    a = _job(7, priority=1, after=30)
    b = _job(5, priority=1, after=10)
    c = _job(6, priority=1, after=10)
    d = _job(8, priority=2, after=99)
    assert [job.id for job in order.sort([a, b, c, d])] == [_id(8), _id(5), _id(6), _id(7)]


# -- bumping (contract items 1-3) ----------------------------------------------------------


def test_bumping_a_lone_job_moves_just_that_job() -> None:
    plan = BUMP_PLANNER.plan(_id(1), _index(_job(1)))
    assert plan == BumpPlan(target=_id(1), moved=(_id(1),))


def test_bumping_pulls_unfinished_dependencies_forward_first_and_transitively() -> None:
    jobs = _index(
        _job(1),
        _job(2, deps=(1,)),
        _job(4, state=JobState.SUCCEEDED),
        _job(3, deps=(2, 4)),
    )
    assert BUMP_PLANNER.plan(_id(3), jobs).moved == (_id(1), _id(2), _id(3))


def test_pulled_dependencies_keep_their_relative_claim_order() -> None:
    jobs = _index(
        _job(1, after=10),
        _job(2, after=20),
        _job(3, priority=5),
        _job(9, deps=(1, 2, 3)),
    )
    assert BUMP_PLANNER.plan(_id(9), jobs).moved == (_id(3), _id(1), _id(2), _id(9))


def test_a_diamond_moves_each_shared_dependency_once() -> None:
    jobs = _index(_job(1), _job(2, deps=(1,)), _job(3, deps=(1,)), _job(4, deps=(2, 3)))
    assert BUMP_PLANNER.plan(_id(4), jobs).moved == (_id(1), _id(2), _id(3), _id(4))


def test_running_and_parked_dependencies_are_pulled_forward_too() -> None:
    jobs = _index(
        _job(1, state=JobState.LEASED),
        _job(2, state=JobState.AWAITING_HUMAN),
        _job(3, state=JobState.AWAITING_CAPACITY),
        _job(4, deps=(1, 2, 3)),
    )
    assert set(BUMP_PLANNER.plan(_id(4), jobs).moved) == {_id(1), _id(2), _id(3), _id(4)}


def test_already_bumped_dependencies_keep_their_place() -> None:
    jobs = _index(_job(1, bump_seq=4), _job(2, deps=(1,)))
    plan = BUMP_PLANNER.plan(_id(2), jobs)
    assert plan.moved == (_id(2),)
    assert plan.kept == (_id(1),)
    assert not plan.named


def test_bumping_a_job_already_bumped_by_name_moves_nothing() -> None:
    plan = BUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=3)))
    assert plan == BumpPlan(target=_id(1), moved=())


def test_bumping_a_pulled_job_by_name_keeps_its_place_and_marks_it_named() -> None:
    plan = BUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=3, origin=2)))
    assert plan.moved == ()
    assert plan.named


@pytest.mark.parametrize(
    "state",
    [JobState.FAILED, JobState.CANCELLED, UnrecognizedJobState("quarantined")],
)
def test_a_dependency_that_can_never_finish_refuses_the_bump_naming_it(
    state: JobState | UnrecognizedJobState,
) -> None:
    jobs = _index(_job(1, state=state), _job(2, deps=(1,)), _job(3, deps=(2,)))
    with pytest.raises(DependencyCannotFinish) as caught:
        BUMP_PLANNER.plan(_id(3), jobs)
    assert caught.value.blockers == ((_id(1), state.value),)
    assert str(_id(1)) in str(caught.value) and state.value in str(caught.value)


@pytest.mark.parametrize(
    "state",
    [JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED, UnrecognizedJobState("q")],
)
def test_a_finished_or_unknown_target_cannot_be_bumped(
    state: JobState | UnrecognizedJobState,
) -> None:
    with pytest.raises(NotReorderable) as caught:
        BUMP_PLANNER.plan(_id(1), _index(_job(1, state=state)))
    assert caught.value.job_id == _id(1)
    assert state.value in str(caught.value)


def test_re_enqueueing_a_finished_job_is_a_no_op_when_asked_for() -> None:
    jobs = _index(_job(1, state=JobState.SUCCEEDED))
    assert BUMP_PLANNER.plan(_id(1), jobs, finished_ok=True) == BumpPlan(target=_id(1), moved=())
    with pytest.raises(NotReorderable):
        BUMP_PLANNER.plan(
            _id(1), _index(_job(1, state=UnrecognizedJobState("q"))), finished_ok=True
        )


def test_a_job_in_an_unknown_phase_is_never_written() -> None:
    with pytest.raises(NotReorderable, match="phase"):
        BUMP_PLANNER.plan(_id(1), _index(_job(1, phase_known=False)))
    with pytest.raises(NotReorderable, match="phase") as caught:
        BUMP_PLANNER.plan(_id(2), _index(_job(1, phase_known=False), _job(2, deps=(1,))))
    assert caught.value.job_id == _id(1)


def test_a_job_missing_from_the_snapshot_is_a_caller_bug() -> None:
    with pytest.raises(LookupError, match="not in the snapshot"):
        BUMP_PLANNER.plan(_id(1), _index(_job(2)))
    with pytest.raises(LookupError, match="not in the snapshot"):
        BUMP_PLANNER.plan(_id(2), _index(_job(2, deps=(1,))))


def test_a_dependency_cycle_is_refused_naming_only_the_ring() -> None:
    jobs = _index(_job(1, deps=(2,)), _job(2, deps=(1,)), _job(3, deps=(1,)))
    with pytest.raises(DependencyCycle) as caught:
        BumpPlanner().plan(_id(3), jobs)
    assert set(caught.value.job_ids) == {_id(1), _id(2)}


# -- un-bumping (contract item 6) -----------------------------------------------------------


def test_unbumping_returns_a_lone_job_to_normal_order() -> None:
    assert UNBUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=3))).moved == (_id(1),)


def test_unbumping_a_job_that_is_not_bumped_moves_nothing() -> None:
    assert UNBUMP_PLANNER.plan(_id(1), _index(_job(1))) == UnbumpPlan(target=_id(1), moved=())


def test_unbumping_undoes_exactly_what_the_bump_pulled_forward() -> None:
    # 3 was bumped by name and pulled 1 and 2 forward; 5 was bumped by name on its own
    # and is a dependency of 3 as well. Un-bumping 3 returns 3, 2 and 1 -- not 5.
    jobs = _index(
        _job(1, bump_seq=1, origin=3),
        _job(2, bump_seq=2, origin=3, deps=(1,)),
        _job(5, bump_seq=3),
        _job(3, bump_seq=4, deps=(2, 5)),
        _job(9),
    )
    assert UnbumpPlanner().plan(_id(3), jobs).moved == (_id(3), _id(1), _id(2))


def test_a_pulled_dependency_another_bumped_job_needs_stays_bumped() -> None:
    # 1 was pulled forward for 3, and 4 (bumped later, by name) needs it too.
    jobs = _index(
        _job(1, bump_seq=1, origin=3),
        _job(3, bump_seq=2, deps=(1,)),
        _job(4, bump_seq=3, deps=(1,)),
    )
    plan = UNBUMP_PLANNER.plan(_id(3), jobs)
    assert plan.moved == (_id(3),)
    # 3's set resets: 1 now belongs to the bump that still needs it, so un-bumping 4
    # later returns it, and nothing is left bumped for a job that went back.
    assert plan.reattributed == ((_id(1), _id(4)),)


def test_an_unbump_leaves_what_another_bump_pulled_forward() -> None:
    # 1 was pulled forward for 4, which still needs it; 3 needs it too. Un-bumping 3
    # returns only 3: it did not pull 1 forward.
    jobs = _index(
        _job(1, bump_seq=1, origin=4),
        _job(4, bump_seq=2, deps=(1,)),
        _job(3, bump_seq=3, deps=(1,)),
    )
    plan = UNBUMP_PLANNER.plan(_id(3), jobs)
    assert plan.moved == (_id(3),)
    assert plan.reattributed == ()


def test_a_kept_dependency_goes_to_the_named_bump_behind_the_job_that_needs_it() -> None:
    # 1 was pulled for 3. 2 was pulled for 5 and also needs 1. Un-bumping 3 keeps 1 for
    # 2 -- and so for 5, the named bump that holds 2 -- never for 2, which is not named.
    jobs = _index(
        _job(1, bump_seq=1, origin=3),
        _job(3, bump_seq=2, deps=(1,)),
        _job(2, bump_seq=3, origin=5, deps=(1,)),
        _job(5, bump_seq=4, deps=(2,)),
    )
    plan = UNBUMP_PLANNER.plan(_id(3), jobs)
    assert plan.moved == (_id(3),)
    assert plan.reattributed == ((_id(1), _id(5)),)


def test_unbumping_a_job_a_bumped_job_needs_is_refused_naming_the_dependents() -> None:
    jobs = _index(
        _job(1, bump_seq=1, origin=3),
        _job(2, deps=(1,)),
        _job(3, bump_seq=2, deps=(2,)),
        _job(4, bump_seq=3, deps=(1,)),
        _job(6, bump_seq=5, deps=(1,), state=JobState.SUCCEEDED),
    )
    with pytest.raises(DependentsStillBumped) as caught:
        UNBUMP_PLANNER.plan(_id(1), jobs)
    assert caught.value.dependents == (_id(3), _id(4))
    assert "un-bump them first" in str(caught.value)


def test_a_finished_or_missing_target_cannot_be_unbumped() -> None:
    with pytest.raises(NotReorderable):
        UNBUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=2, state=JobState.SUCCEEDED)))
    with pytest.raises(LookupError):
        UNBUMP_PLANNER.plan(_id(1), _index())


def test_an_unbump_never_writes_a_job_in_an_unknown_phase() -> None:
    jobs = _index(_job(1, bump_seq=1, origin=2, phase_known=False), _job(2, bump_seq=2, deps=(1,)))
    with pytest.raises(NotReorderable, match="phase"):
        UNBUMP_PLANNER.plan(_id(2), jobs)


# -- the records a change leaves behind -------------------------------------------------------


def test_a_change_reports_whether_anything_changed() -> None:
    moved = PriorityChange(
        action=PriorityAction.BUMP,
        requested_by="operator:adam",
        target=_id(1),
        moved=(MovedJob(job_id=_id(1), bump_seq=7, previous=None),),
    )
    assert moved.changed
    named = PriorityChange(
        action=PriorityAction.BUMP,
        requested_by="operator:adam",
        target=_id(1),
        moved=(),
        named=True,
    )
    assert named.changed
    still = PriorityChange(
        action=PriorityAction.UNBUMP, requested_by="source:storm", target=_id(1), moved=()
    )
    assert not still.changed
    assert still.note == "" and still.kept == ()


def test_every_refusal_is_a_reorder_refusal_and_says_what_happened() -> None:
    errors: list[ReorderRefused] = [
        UnknownJob(_id(5)),
        NotReorderable(_id(5), "why"),
        DependencyCycle((_id(1),)),
        DependencyCannotFinish(_id(5), ((_id(1), "failed"),)),
        DependentsStillBumped(_id(5), (_id(6),)),
        ReorderConflict(_id(5)),
        PriorityRefused("account:mallory", "not the operator"),
    ]
    assert all(isinstance(error, VibeyError) for error in errors)
    assert str(errors[0]) == f"unknown job {_id(5)}"
    assert "retry" in str(errors[5])
    refused = errors[6]
    assert isinstance(refused, PriorityRefused)
    assert refused.requested_by == "account:mallory"
    assert str(refused) == "refused: not the operator"


# -- properties ------------------------------------------------------------------------------

_STATES = st.sampled_from(
    [JobState.READY, JobState.READY, JobState.LEASED, JobState.AWAITING_HUMAN, JobState.SUCCEEDED]
)


@st.composite
def _dag(draw: st.DrawFn) -> tuple[Mapping[UUID, QueuedJob], UUID]:
    """A random acyclic queue: job n may depend only on jobs numbered below it."""
    size = draw(st.integers(min_value=1, max_value=12))
    jobs: dict[UUID, QueuedJob] = {}
    for n in range(1, size + 1):
        deps = (
            draw(st.lists(st.integers(min_value=1, max_value=n - 1), max_size=3)) if n > 1 else []
        )
        jobs[_id(n)] = _job(
            n,
            state=draw(_STATES) if n < size else JobState.READY,
            bump_seq=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=50))),
            priority=draw(st.integers(min_value=-2, max_value=2)),
            after=draw(st.integers(min_value=-5, max_value=5)),
            deps=tuple(deps),
        )
    return jobs, _id(size)


@given(_dag())
def test_every_planned_dependency_is_bumped_before_whatever_needs_it(
    case: tuple[Mapping[UUID, QueuedJob], UUID],
) -> None:
    jobs, target = case
    plan = BUMP_PLANNER.plan(target, jobs)
    order = [*plan.kept, *plan.moved]
    assert len(order) == len(set(order))
    position = {job_id: index for index, job_id in enumerate(plan.moved)}
    for job_id in plan.moved:
        for dep in jobs[job_id].depends_on:
            if dep in position:
                assert position[dep] < position[job_id]
    for job_id in order:
        assert jobs[job_id].state in MOVABLE_STATES


@given(_dag())
def test_a_bump_then_an_unbump_leaves_the_queue_as_it_was(
    case: tuple[Mapping[UUID, QueuedJob], UUID],
) -> None:
    """Contract item 6 as a property: starting from nothing bumped, an un-bump undoes
    exactly what the bump moved."""
    jobs, target = case
    clean = {job_id: _unbumped(job) for job_id, job in jobs.items()}
    plan = BUMP_PLANNER.plan(target, clean)
    after = dict(clean)
    for seq, job_id in enumerate(plan.moved, start=1):
        job = clean[job_id]
        after[job_id] = QueuedJob(
            id=job.id,
            state=job.state,
            priority=job.priority,
            run_after=job.run_after,
            bump_seq=seq,
            depends_on=job.depends_on,
            bump_origin=target,
        )
    undone = UNBUMP_PLANNER.plan(target, after)
    assert set(undone.moved) == set(plan.moved)


def _unbumped(job: QueuedJob) -> QueuedJob:
    return QueuedJob(
        id=job.id,
        state=job.state,
        priority=job.priority,
        run_after=job.run_after,
        depends_on=job.depends_on,
    )


# -- the invariants, over any sequence of bumps and un-bumps (items 3 and 6) ----------------


class QueueMachine(RuleBasedStateMachine):
    """Random bumps and un-bumps over a random acyclic queue, overlapping freely.

    After every step: every unfinished dependency of a bumped job is bumped, and every
    job pulled forward belongs to a bump by name that still needs it. At any point,
    un-bumping every job bumped by name clears the whole queue.
    """

    def __init__(self) -> None:
        super().__init__()
        self.jobs: dict[UUID, QueuedJob] = {}
        self.seq = 0

    @initialize(
        deps=st.lists(
            st.lists(st.integers(min_value=0, max_value=30), max_size=3),
            min_size=2,
            max_size=9,
        )
    )
    def build(self, deps: list[list[int]]) -> None:
        for n, wanted in enumerate(deps, start=1):
            chosen = tuple(sorted({(d % (n - 1)) + 1 for d in wanted})) if n > 1 else ()
            self.jobs[_id(n)] = _job(n, deps=chosen)

    def _set(self, job_id: UUID, *, seq: int | None, origin: UUID | None) -> None:
        job = self.jobs[job_id]
        self.jobs[job_id] = QueuedJob(
            id=job.id,
            state=job.state,
            priority=job.priority,
            run_after=job.run_after,
            bump_seq=seq,
            depends_on=job.depends_on,
            bump_origin=origin,
        )

    def _bump(self, target: UUID) -> None:
        plan = BUMP_PLANNER.plan(target, self.jobs)
        for moving in plan.moved:
            self.seq += 1
            self._set(moving, seq=self.seq, origin=target)
        if plan.named:
            self._set(target, seq=self.jobs[target].bump_seq, origin=target)

    def _unbump(self, target: UUID) -> bool:
        try:
            plan = UNBUMP_PLANNER.plan(target, self.jobs)
        except DependentsStillBumped:
            return False
        for moving in plan.moved:
            self._set(moving, seq=None, origin=None)
        for dep, owner in plan.reattributed:
            self._set(dep, seq=self.jobs[dep].bump_seq, origin=owner)
        return True

    @rule(pick=st.integers(min_value=0, max_value=100))
    def bump(self, pick: int) -> None:
        ids = sorted(self.jobs)
        self._bump(ids[pick % len(ids)])

    @rule(pick=st.integers(min_value=0, max_value=100))
    def unbump(self, pick: int) -> None:
        ids = sorted(self.jobs)
        self._unbump(ids[pick % len(ids)])

    @invariant()
    def every_dependency_of_a_bumped_job_is_bumped(self) -> None:
        for job in self.jobs.values():
            if job.bumped:
                for dep in job.depends_on:
                    assert self.jobs[dep].bumped, f"{job.id} is bumped but {dep} is not"

    @invariant()
    def every_pulled_job_belongs_to_a_named_bump_that_needs_it(self) -> None:
        for job in self.jobs.values():
            if job.bumped and not job.named:
                assert job.bump_origin is not None
                owner = self.jobs[job.bump_origin]
                assert owner.named, f"{job.id} belongs to {owner.id}, which is not named"
                assert job.id in _reach(self.jobs, owner.id)

    @invariant()
    def unbumping_every_named_job_clears_the_queue(self) -> None:
        saved = dict(self.jobs)
        progress = True
        while progress:
            progress = False
            for job in sorted(self.jobs.values(), key=lambda j: j.id):
                if job.named and self._unbump(job.id):
                    progress = True
        left = [job.id for job in self.jobs.values() if job.bumped]
        self.jobs = saved
        assert left == [], f"still bumped after every named job went back: {left}"


def _reach(jobs: Mapping[UUID, QueuedJob], root: UUID) -> set[UUID]:
    seen: set[UUID] = set()
    stack = [root]
    while stack:
        job_id = stack.pop()
        if job_id not in seen:
            seen.add(job_id)
            stack.extend(jobs[job_id].depends_on)
    return seen


TestQueueMachine = QueueMachine.TestCase
TestQueueMachine.settings = settings(max_examples=150, stateful_step_count=30, deadline=None)
