# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An item that builds on another waits for it, before any engine is chosen."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from vibey.application.build_dependency_wait import (
    DEFAULT_DEPENDENCY_WAIT,
    DeferringHandler,
    DependencyWait,
    unintegrated_dependencies,
)
from vibey.application.dto import JobRecord
from vibey.application.worker import Defer
from vibey.domain.job import JobState


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def _integrated(project: UUID, item: str, state: JobState) -> JobRecord:
    return replace(make_job(project, state=state), kind="build.integrate", work_item_id=item)


def _dependent(project: UUID, depends_on: object) -> JobRecord:
    return replace(
        make_job(project),
        work_item_id="c8",
        payload={"depends_on_items": depends_on},
    )


def test_the_default_poll_is_five_seconds() -> None:
    assert timedelta(seconds=5) == DEFAULT_DEPENDENCY_WAIT


async def test_only_dependencies_without_a_succeeded_integrate_are_unintegrated() -> None:
    project = uuid4()
    jobs = FakeJobRepository(
        [
            _integrated(project, "ws", JobState.SUCCEEDED),
            _integrated(project, "c7", JobState.READY),
        ]
    )

    assert await unintegrated_dependencies(jobs, _dependent(project, ["ws", "c7", "c9"])) == (
        "c7",
        "c9",
    )


@pytest.mark.parametrize("depends_on", [None, "ws", [], 3])
async def test_a_job_without_a_list_of_dependencies_waits_for_nothing(depends_on: object) -> None:
    project = uuid4()

    assert (
        await unintegrated_dependencies(FakeJobRepository(), _dependent(project, depends_on)) == ()
    )


async def test_a_waiting_job_gets_a_defer_that_is_not_an_engine_signal() -> None:
    project = uuid4()
    waiter = DependencyWait(jobs=FakeJobRepository(), clock=FixedClock(), wait=timedelta(seconds=9))

    deferral = await waiter.deferral(_dependent(project, ["ws"]))

    assert isinstance(deferral, Defer)
    assert deferral.capacity is False
    assert deferral.retry_at == FixedClock().now() + timedelta(seconds=9)
    assert deferral.detail == "waiting for ws to be integrated, so this item builds on their code"


async def test_a_job_whose_dependencies_are_integrated_does_not_wait() -> None:
    project = uuid4()
    jobs = FakeJobRepository([_integrated(project, "ws", JobState.SUCCEEDED)])

    assert (
        await DependencyWait(jobs=jobs, clock=FixedClock()).deferral(_dependent(project, ["ws"]))
        is None
    )


async def test_the_deferring_handler_returns_its_defer_and_nothing_else() -> None:
    deferral = Defer(retry_at=FixedClock().now(), detail="waiting")

    assert await DeferringHandler(deferral).handle(make_job(uuid4())) is deferral
