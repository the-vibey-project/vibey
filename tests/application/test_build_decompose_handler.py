# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from vibey.application.build_decompose_handler import BuildDecomposeHandler
from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.worker import Failure, Success
from vibey.domain.effort import Effort
from vibey.domain.job import FailureClass, idempotency_key
from vibey.domain.phase import Phase
from vibey.domain.plan import VerificationSpec, WorkItem
from vibey.domain.spec import AcceptanceCriterion, DesignSpec


def spec() -> DesignSpec:
    return DesignSpec(
        "Ship",
        (),
        (),
        (
            AcceptanceCriterion("AC-1", "given", "when", "then", "fit"),
            AcceptanceCriterion("AC-2", "given", "when", "then", "fit"),
        ),
        (),
        "one path",
    )


def _item(item_id: str, **overrides: object) -> WorkItem:
    defaults: dict[str, object] = {
        "item_id": item_id,
        "title": f"do {item_id}",
        "acceptance_ids": (),
        "depends_on": (),
        "est_effort": Effort.LOW,
        "files_touched_hint": (),
        "verification": VerificationSpec(commands=("pytest",), criteria_checked=()),
    }
    defaults.update(overrides)
    return WorkItem(**defaults)  # type: ignore[arg-type]


class Specs:
    def __init__(self, value: DesignSpec | None) -> None:
        self.value = value

    async def load(self, project_id, cycle):  # type: ignore[no-untyped-def]
        return self.value


class Decomposer:
    def __init__(self, items: tuple[WorkItem, ...]) -> None:
        self.items = items
        self.calls = 0

    async def decompose(self, spec):  # type: ignore[no-untyped-def]
        self.calls += 1
        return self.items


class DyingJobRepository(FakeJobRepository):
    """The worker dies part-way through writing the fan-out. The batch is one
    transaction, so dying inside it commits nothing."""

    async def enqueue_batch(self, requests: Sequence[EnqueueRequest]) -> tuple[JobRecord, ...]:
        raise ConnectionResetError("worker died mid-batch")


def _fan_out(jobs: FakeJobRepository) -> list[JobRecord]:
    return [record for record in jobs._jobs.values() if record.kind == "build.implement"]


async def test_decompose_fans_out_build_implement_jobs_in_dependency_order() -> None:
    job = replace(make_job(uuid4()), kind="build.decompose")
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
    )
    jobs = FakeJobRepository()
    handler = BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    skeleton_job = await jobs.claim(job.project_id, owner="w", lease=timedelta(seconds=5))
    assert skeleton_job is not None
    assert skeleton_job.work_item_id == "skeleton"
    assert skeleton_job.kind == "build.implement"
    await jobs.ack(skeleton_job.id, owner="w")
    item_2_job = await jobs.claim(job.project_id, owner="w", lease=timedelta(seconds=5))
    assert item_2_job is not None
    assert item_2_job.work_item_id == "item-2"


async def test_decompose_rejects_wrong_kind_and_missing_spec() -> None:
    handler = BuildDecomposeHandler(
        specs=Specs(None), decomposer=Decomposer(()), jobs=FakeJobRepository()
    )
    assert await handler.handle(make_job(uuid4())) == Failure(
        FailureClass.VIBEY, "expected build.decompose job"
    )
    job = replace(make_job(uuid4()), kind="build.decompose")
    outcome = await handler.handle(job)
    assert outcome == Failure(FailureClass.WORK, "no accepted design spec exists")


async def test_decompose_rejects_empty_and_unmapped_decompositions() -> None:
    job = replace(make_job(uuid4()), kind="build.decompose")

    empty = BuildDecomposeHandler(
        specs=Specs(spec()), decomposer=Decomposer(()), jobs=FakeJobRepository()
    )
    assert await empty.handle(job) == Failure(
        FailureClass.WORK, "decomposition produced no work items"
    )

    unmapped_items = (_item("skeleton", acceptance_ids=("AC-1",)),)
    unmapped = BuildDecomposeHandler(
        specs=Specs(spec()), decomposer=Decomposer(unmapped_items), jobs=FakeJobRepository()
    )
    outcome = await unmapped.handle(job)
    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK
    assert "AC-2" in outcome.detail


async def test_a_forward_dependency_plan_is_enqueued_whole_in_dependency_order() -> None:
    """A producer that lists a dependent before its dependency no longer fails
    half-enqueued (#265): the plan is sound, so it is put in order and fanned
    out in one batch, with every dependency edge in place."""
    job = replace(make_job(uuid4()), kind="build.decompose")
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("item-3",)),
        _item("item-3", acceptance_ids=(), depends_on=("skeleton",)),
    )
    jobs = FakeJobRepository()
    handler = BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    outcome = await handler.handle(job)

    assert outcome == Success({"work_items": 3})
    assert jobs.calls == ["enqueue_batch"]
    by_item = {record.work_item_id: record for record in _fan_out(jobs)}
    assert list(by_item) == ["skeleton", "item-3", "item-2"]
    assert jobs.dependencies[by_item["skeleton"].id] == ()
    assert jobs.dependencies[by_item["item-3"].id] == (by_item["skeleton"].id,)
    assert jobs.dependencies[by_item["item-2"].id] == (by_item["item-3"].id,)
    for item_id, record in by_item.items():
        assert record.idempotency_key == idempotency_key(
            job.project_id, job.cycle, "build.implement", item_id
        )


async def test_a_cyclic_plan_enqueues_nothing_and_names_the_cycle() -> None:
    job = replace(make_job(uuid4()), kind="build.decompose")
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("item-3",)),
        _item("item-3", depends_on=("item-2",)),
    )
    jobs = FakeJobRepository()
    handler = BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    outcome = await handler.handle(job)

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK
    assert "dependency cycle: items 'item-2', 'item-3'" in outcome.detail
    assert _fan_out(jobs) == []
    assert "enqueue_batch" not in jobs.calls


async def test_a_bad_last_item_enqueues_nothing_of_the_good_ones_before_it() -> None:
    """The old fan-out committed every item ahead of the one it choked on;
    the whole plan is judged first now, and every violation is named."""
    job = replace(make_job(uuid4()), kind="build.decompose")
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
        _item("item-3", depends_on=("ghost", "phantom")),
    )
    jobs = FakeJobRepository()
    handler = BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    outcome = await handler.handle(job)

    assert outcome == Failure(
        FailureClass.WORK,
        "item 'item-3' depends on unknown item 'ghost'; "
        "item 'item-3' depends on unknown item 'phantom'",
    )
    assert _fan_out(jobs) == []


async def test_a_crash_mid_batch_then_a_replay_makes_exactly_one_job_per_item() -> None:
    job = replace(make_job(uuid4()), kind="build.decompose")
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
        _item("item-3", depends_on=("item-2",)),
    )
    dying = DyingJobRepository()
    with pytest.raises(ConnectionResetError):
        await BuildDecomposeHandler(
            specs=Specs(spec()), decomposer=Decomposer(items), jobs=dying
        ).handle(job)
    assert _fan_out(dying) == []

    # The lease expires; the replay runs against the same, untouched queue.
    jobs = FakeJobRepository(list(dying._jobs.values()))
    outcome = await BuildDecomposeHandler(
        specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs
    ).handle(job)

    assert outcome == Success({"work_items": 3})
    assert sorted(record.work_item_id or "" for record in _fan_out(jobs)) == [
        "item-2",
        "item-3",
        "skeleton",
    ]


async def test_a_replay_after_the_fan_out_committed_never_decomposes_again() -> None:
    """The worker died between the batch's commit and the ack. The producer is
    a model: asked again it may answer with a different plan, and enqueueing
    that beside the first would orphan half of both. The replay returns the
    committed fan-out instead."""
    job = replace(make_job(uuid4()), kind="build.decompose")
    first_plan = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
    )
    jobs = FakeJobRepository()
    await BuildDecomposeHandler(
        specs=Specs(spec()), decomposer=Decomposer(first_plan), jobs=jobs
    ).handle(job)

    second_plan = (_item("different", acceptance_ids=("AC-1", "AC-2")),)
    second = Decomposer(second_plan)
    outcome = await BuildDecomposeHandler(specs=Specs(spec()), decomposer=second, jobs=jobs).handle(
        job
    )

    assert outcome == Success({"work_items": 2, "replayed": True})
    assert second.calls == 0
    assert sorted(record.work_item_id or "" for record in _fan_out(jobs)) == [
        "item-2",
        "skeleton",
    ]


async def test_follow_ups_of_the_cycle_are_not_mistaken_for_its_fan_out() -> None:
    """A wind-down follow-up or verify repair is a build.implement of the same
    cycle with a key of its own; only the fan-out's own keys mean 'already
    decomposed'. A job with no work item is not one either."""
    job = replace(make_job(uuid4()), kind="build.decompose")
    jobs = FakeJobRepository()
    await jobs.enqueue(
        EnqueueRequest(
            project_id=job.project_id,
            cycle=job.cycle,
            phase=Phase.BUILD,
            kind="build.implement",
            idempotency_key=idempotency_key(
                job.project_id, job.cycle, "build.implement", "skeleton:wind-down:1"
            ),
            work_item_id="skeleton",
        )
    )
    await jobs.enqueue(
        EnqueueRequest(
            project_id=job.project_id,
            cycle=job.cycle,
            phase=Phase.BUILD,
            kind="build.implement",
            idempotency_key="no-work-item",
        )
    )
    items = (_item("skeleton", acceptance_ids=("AC-1", "AC-2")),)
    decomposer = Decomposer(items)

    outcome = await BuildDecomposeHandler(
        specs=Specs(spec()), decomposer=decomposer, jobs=jobs
    ).handle(job)

    assert outcome == Success({"work_items": 1})
    assert decomposer.calls == 1


async def test_build_plan_kind_is_the_fast_loopback_spelling() -> None:
    """review.triage's fast loop-back enqueues 'build.plan'; the decompose
    handler accepts it as the same work."""
    job = replace(make_job(uuid4()), kind="build.plan")
    items = (_item("skeleton", acceptance_ids=("AC-1", "AC-2")),)
    jobs = FakeJobRepository()
    handler = BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert any(j.kind == "build.implement" for j in jobs._jobs.values())


async def test_fan_out_stamps_the_integration_base_ref_on_every_item() -> None:
    """Item branches stack on integrated code when any exists -- every
    item branching from the empty base rewrote the same module in
    parallel and guaranteed add/add merge conflicts, live."""
    from vibey.domain.worktree import branch_name

    job = replace(make_job(uuid4()), kind="build.decompose")
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
    )
    jobs = FakeJobRepository()
    handler = BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    records = list(jobs._jobs.values())
    assert len(records) == 2
    for record in records:
        assert record.payload["base_ref"] == branch_name(record.cycle, "integration")
