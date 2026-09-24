# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority: who may move a job ahead, and what moves with it (ADR-0054)."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.errors import DependencyCycle, NotReorderable, VibeyError
from vibey.domain.interfaces.queue_priority_interface import (
    BumpPlannerInterface,
    ClaimOrderInterface,
    PriorityGrantInterface,
    UnbumpPlannerInterface,
)
from vibey.domain.job import JobState, UnrecognizedJobState
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import (
    BUMP_PLANNER,
    CLAIM_ORDER,
    MOVABLE_STATES,
    OPERATOR_SOURCE,
    UNBUMP_PLANNER,
    BumpPlanner,
    ClaimOrder,
    MovedJob,
    PriorityAction,
    PriorityChange,
    PriorityGrant,
    PriorityRefusal,
    QueuedJob,
    UnbumpPlanner,
)

T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _id(n: int) -> UUID:
    return UUID(int=n)


def _job(
    n: int,
    *,
    state: JobState | UnrecognizedJobState = JobState.READY,
    bump_seq: int | None = None,
    priority: int = 0,
    after: int = 0,
    deps: tuple[int, ...] = (),
) -> QueuedJob:
    return QueuedJob(
        id=_id(n),
        state=state,
        priority=priority,
        run_after=T0 + timedelta(seconds=after),
        bump_seq=bump_seq,
        depends_on=tuple(_id(d) for d in deps),
    )


def _index(*jobs: QueuedJob) -> Mapping[UUID, QueuedJob]:
    return {job.id: job for job in jobs}


# -- the module's shared instances satisfy their declared seams ---------------


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(CLAIM_ORDER, ClaimOrderInterface)
    assert isinstance(BUMP_PLANNER, BumpPlannerInterface)
    assert isinstance(UNBUMP_PLANNER, UnbumpPlannerInterface)
    assert isinstance(PriorityGrant(), PriorityGrantInterface)


# -- who may reorder the queue -------------------------------------------------


def test_the_operator_is_always_admitted_and_nobody_else_by_default() -> None:
    grant = PriorityGrant()
    assert grant.admits(OPERATOR_SOURCE)
    assert not grant.admits("github-label")
    assert not grant.admits("")
    assert grant.declared == frozenset()


def test_a_declared_source_is_admitted_and_an_undeclared_one_is_not() -> None:
    grant = PriorityGrant(("storm", "nightly"))
    assert grant.admits("storm")
    assert grant.admits("nightly")
    assert not grant.admits("Storm"), "a source is matched exactly, never by case folding"
    assert not grant.admits("issue-comment")
    assert grant.declared == frozenset({"storm", "nightly"})


def test_a_refusal_names_the_source_and_where_it_would_have_to_be_declared() -> None:
    reason = PriorityGrant(("storm",)).refusal("github-label")
    assert "'github-label'" in reason
    assert "[queue.priority] sources" in reason
    assert "operator" in reason


# -- claim order ---------------------------------------------------------------


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


# -- bumping ---------------------------------------------------------------------


def test_bumping_a_lone_job_moves_just_that_job() -> None:
    plan = BUMP_PLANNER.plan(_id(1), _index(_job(1)))
    assert plan.target == _id(1)
    assert plan.moved == (_id(1),)
    assert plan.kept == ()
    assert plan.blocked_by == ()


def test_bumping_pulls_unfinished_dependencies_forward_first_and_transitively() -> None:
    # 3 needs 2, 2 needs 1; 4 is a finished dependency of 3 and stays put.
    jobs = _index(
        _job(1),
        _job(2, deps=(1,)),
        _job(4, state=JobState.SUCCEEDED),
        _job(3, deps=(2, 4)),
    )
    plan = BUMP_PLANNER.plan(_id(3), jobs)
    assert plan.moved == (_id(1), _id(2), _id(3))
    assert plan.blocked_by == ()


def test_pulled_dependencies_keep_their_relative_claim_order() -> None:
    # Target 9 needs 1, 2 and 3; none depends on another. Their current claim
    # order (priority, then run_after) is 3, 1, 2, and the bump keeps it.
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


def test_a_running_dependency_is_pulled_forward_so_a_retry_keeps_its_place() -> None:
    jobs = _index(_job(1, state=JobState.LEASED), _job(2, deps=(1,)))
    assert BUMP_PLANNER.plan(_id(2), jobs).moved == (_id(1), _id(2))


def test_parked_dependencies_are_pulled_forward_too() -> None:
    jobs = _index(
        _job(1, state=JobState.AWAITING_HUMAN),
        _job(2, state=JobState.AWAITING_CAPACITY),
        _job(3, deps=(1, 2)),
    )
    assert set(BUMP_PLANNER.plan(_id(3), jobs).moved) == {_id(1), _id(2), _id(3)}


def test_already_bumped_jobs_keep_their_place_and_are_reported_as_kept() -> None:
    jobs = _index(_job(1, bump_seq=4), _job(2, deps=(1,)))
    plan = BUMP_PLANNER.plan(_id(2), jobs)
    assert plan.moved == (_id(2),)
    assert plan.kept == (_id(1),)


def test_bumping_an_already_bumped_job_again_moves_nothing() -> None:
    plan = BUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=3)))
    assert plan.moved == ()
    assert plan.kept == (_id(1),)


def test_a_dependency_that_can_never_run_is_reported_not_moved() -> None:
    jobs = _index(
        _job(1, state=JobState.FAILED),
        _job(2, state=JobState.CANCELLED),
        _job(3, state=UnrecognizedJobState("quarantined")),
        _job(4, deps=(1, 2, 3, 1)),
    )
    plan = BUMP_PLANNER.plan(_id(4), jobs)
    assert plan.moved == (_id(4),)
    assert plan.blocked_by == (_id(1), _id(2), _id(3))


@pytest.mark.parametrize(
    "state",
    [
        JobState.SUCCEEDED,
        JobState.FAILED,
        JobState.CANCELLED,
        UnrecognizedJobState("quarantined"),
    ],
)
def test_a_finished_or_unknown_target_cannot_be_bumped(
    state: JobState | UnrecognizedJobState,
) -> None:
    with pytest.raises(NotReorderable) as caught:
        BUMP_PLANNER.plan(_id(1), _index(_job(1, state=state)))
    assert caught.value.job_id == _id(1)
    assert state.value in str(caught.value)
    assert isinstance(caught.value, VibeyError)


def test_a_job_missing_from_the_snapshot_is_a_caller_bug() -> None:
    with pytest.raises(LookupError, match="not in the snapshot"):
        BUMP_PLANNER.plan(_id(1), _index(_job(2)))
    with pytest.raises(LookupError, match="not in the snapshot"):
        BUMP_PLANNER.plan(_id(2), _index(_job(2, deps=(1,))))


def test_a_dependency_cycle_is_refused_rather_than_ordered_arbitrarily() -> None:
    jobs = _index(_job(1, deps=(2,)), _job(2, deps=(1,)), _job(3, deps=(1,)))
    with pytest.raises(DependencyCycle) as caught:
        BumpPlanner().plan(_id(3), jobs)
    assert set(caught.value.job_ids) == {_id(1), _id(2)}


# -- un-bumping ------------------------------------------------------------------


def test_unbumping_returns_just_that_job_to_normal_order() -> None:
    plan = UNBUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=3)))
    assert plan.target == _id(1)
    assert plan.moved == (_id(1),)


def test_unbumping_a_job_that_is_not_bumped_moves_nothing() -> None:
    assert UNBUMP_PLANNER.plan(_id(1), _index(_job(1))).moved == ()


def test_unbumping_a_dependency_sends_its_bumped_dependents_back_with_it() -> None:
    # 3 needs 2 needs 1, all bumped; 4 needs 1 but was never bumped; 5 needs 3
    # and already finished. Un-bumping 1 un-bumps 2 and 3: neither can run
    # before 1, so a bump on them would claim a place they cannot use.
    jobs = _index(
        _job(1, bump_seq=1),
        _job(2, bump_seq=2, deps=(1,)),
        _job(3, bump_seq=3, deps=(2,)),
        _job(4, deps=(1,)),
        _job(5, bump_seq=4, state=JobState.SUCCEEDED, deps=(3,)),
    )
    plan = UnbumpPlanner().plan(_id(1), jobs)
    assert plan.moved == (_id(1), _id(2), _id(3))


def test_unbumping_cascades_through_a_dependent_that_was_never_bumped() -> None:
    jobs = _index(
        _job(1, bump_seq=1),
        _job(2, deps=(1,)),
        _job(3, bump_seq=5, deps=(2,)),
        _job(4, bump_seq=6, deps=(2, 3)),
    )
    assert UNBUMP_PLANNER.plan(_id(1), jobs).moved == (_id(1), _id(3), _id(4))


def test_a_dependent_in_a_state_this_vibey_does_not_know_is_left_alone() -> None:
    jobs = _index(
        _job(1, bump_seq=1),
        _job(2, bump_seq=2, state=UnrecognizedJobState("quarantined"), deps=(1,)),
    )
    assert UNBUMP_PLANNER.plan(_id(1), jobs).moved == (_id(1),)


def test_a_finished_target_cannot_be_unbumped() -> None:
    with pytest.raises(NotReorderable):
        UNBUMP_PLANNER.plan(_id(1), _index(_job(1, bump_seq=2, state=JobState.SUCCEEDED)))
    with pytest.raises(LookupError):
        UNBUMP_PLANNER.plan(_id(1), _index())


# -- the records a change leaves behind ------------------------------------------


def test_a_change_reports_whether_anything_moved() -> None:
    moved = PriorityChange(
        action=PriorityAction.BUMP,
        source=OPERATOR_SOURCE,
        target=_id(1),
        moved=(MovedJob(job_id=_id(1), bump_seq=7, previous=None),),
    )
    assert moved.changed
    still = PriorityChange(
        action=PriorityAction.UNBUMP, source="storm", target=_id(1), moved=(), kept=(_id(1),)
    )
    assert not still.changed
    assert still.blocked_by == ()


def test_a_refusal_carries_what_the_ledger_needs() -> None:
    refusal = PriorityRefusal(
        project_id=_id(10),
        cycle=2,
        phase=Phase.BUILD,
        job_id=None,
        action=PriorityAction.ENQUEUE,
        source="github-label",
        reason="not declared",
    )
    assert refusal.job_id is None
    assert refusal.action.value == "enqueue"
    assert set(MOVABLE_STATES) == {
        JobState.READY,
        JobState.LEASED,
        JobState.AWAITING_HUMAN,
        JobState.AWAITING_CAPACITY,
    }


# -- properties --------------------------------------------------------------------

_STATES = st.sampled_from(
    [
        JobState.READY,
        JobState.READY,
        JobState.LEASED,
        JobState.AWAITING_HUMAN,
        JobState.SUCCEEDED,
        JobState.FAILED,
    ]
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
    assert target in order
    position = {job_id: index for index, job_id in enumerate(plan.moved)}
    for job_id in plan.moved:
        for dep in jobs[job_id].depends_on:
            if dep in position:
                assert position[dep] < position[job_id]
    for job_id in order:
        assert jobs[job_id].state in MOVABLE_STATES
    for job_id in plan.blocked_by:
        assert jobs[job_id].state not in MOVABLE_STATES
        assert jobs[job_id].state is not JobState.SUCCEEDED


@given(_dag())
def test_an_unbump_only_ever_clears_bumped_unfinished_jobs(
    case: tuple[Mapping[UUID, QueuedJob], UUID],
) -> None:
    jobs, _ = case
    first = _id(1)
    if jobs[first].state not in MOVABLE_STATES:
        with pytest.raises(NotReorderable):
            UNBUMP_PLANNER.plan(first, jobs)
        return
    plan = UNBUMP_PLANNER.plan(first, jobs)
    for job_id in plan.moved:
        assert jobs[job_id].bump_seq is not None
        assert jobs[job_id].state in MOVABLE_STATES


def test_every_value_satisfies_its_declared_interface() -> None:
    from vibey.domain.config import QueueConfig
    from vibey.domain.interfaces import (
        BumpPlanInterface,
        MovedJobInterface,
        PriorityChangeInterface,
        PriorityRefusalInterface,
        QueueConfigInterface,
        QueuedJobInterface,
        UnbumpPlanInterface,
    )
    from vibey.domain.queue_priority import BumpPlan, UnbumpPlan

    moved = MovedJob(job_id=_id(1), bump_seq=1, previous=None)
    assert isinstance(_job(1), QueuedJobInterface)
    assert isinstance(BumpPlan(target=_id(1), moved=()), BumpPlanInterface)
    assert isinstance(UnbumpPlan(target=_id(1), moved=()), UnbumpPlanInterface)
    assert isinstance(moved, MovedJobInterface)
    change = PriorityChange(
        action=PriorityAction.BUMP, source=OPERATOR_SOURCE, target=_id(1), moved=(moved,)
    )
    assert isinstance(change, PriorityChangeInterface)
    refusal = PriorityRefusal(
        project_id=_id(9),
        cycle=1,
        phase=Phase.BUILD,
        job_id=_id(1),
        action=PriorityAction.BUMP,
        source="x",
        reason="y",
    )
    assert isinstance(refusal, PriorityRefusalInterface)
    assert isinstance(QueueConfig(), QueueConfigInterface)


def test_the_priority_errors_say_what_happened() -> None:
    from vibey.domain.errors import PriorityRefused, UnknownJob

    unknown = UnknownJob(_id(5))
    assert unknown.job_id == _id(5)
    assert str(unknown) == f"unknown job {_id(5)}"
    refused = PriorityRefused("github-label", "not declared")
    assert refused.source == "github-label"
    assert refused.reason == "not declared"
    assert str(refused) == "refused: not declared"
    ring = DependencyCycle((_id(1), _id(2)))
    assert str(_id(2)) in str(ring)
