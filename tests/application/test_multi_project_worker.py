# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One worker for every project (#1189): each project's jobs through that project's loops."""

import asyncio
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID, uuid4

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey.application.dto import JobRecord
from vibey.application.interfaces.worker_interface import (
    MultiProjectWorkerInterface,
    WorkerLoopInterface,
)
from vibey.application.multi_project_worker import MultiProjectWorker
from vibey.application.worker import Outcome, Success, WorkerLoop
from vibey.domain.job import JobState


class _Recording:
    def __init__(self) -> None:
        self.handled: list[JobRecord] = []

    async def handle(self, job: JobRecord) -> Outcome:
        self.handled.append(job)
        return Success()


class _Logger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def bind(self, **kwargs: object) -> "_Logger":
        return self

    def debug(self, event: str, **kwargs: object) -> None:
        self.events.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: object) -> None:
        self.events.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: object) -> None:
        self.events.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: object) -> None:
        self.events.append(("error", event, kwargs))


class _Builder:
    """Builds real `WorkerLoop`s over the shared fake queue, one handler per project."""

    def __init__(self, jobs: FakeJobRepository, *, slots: int = 1) -> None:
        self._jobs = jobs
        self._slots = slots
        self.handlers: dict[UUID, _Recording] = {}
        self.built: list[UUID] = []

    async def __call__(self, project_id: UUID) -> Sequence[WorkerLoopInterface] | None:
        self.built.append(project_id)
        await asyncio.sleep(0)  # a real build awaits the preflight; let others interleave
        handler = self.handlers.setdefault(project_id, _Recording())
        return [
            WorkerLoop(
                jobs=self._jobs,
                gates=FakeHumanGateRepository(),
                handler=handler,
                owner=f"worker-{project_id}-{slot}",
                lease=timedelta(seconds=30),
            )
            for slot in range(self._slots)
        ]


def _worker(
    jobs: FakeJobRepository, builder: object, logger: _Logger | None = None
) -> MultiProjectWorker:
    return MultiProjectWorker(jobs=jobs, loops_for=builder, logger=logger)  # type: ignore[arg-type]


def test_it_is_the_interface_it_declares() -> None:
    worker = _worker(FakeJobRepository(), _Builder(FakeJobRepository()))
    assert isinstance(worker, MultiProjectWorkerInterface)


async def test_nothing_claimable_anywhere_runs_nothing() -> None:
    jobs = FakeJobRepository()
    builder = _Builder(jobs)
    worker = _worker(jobs, builder)

    assert await worker.run_once() is False
    assert builder.built == []
    assert worker.last_served is None


async def test_every_project_is_served_each_through_its_own_loop() -> None:
    first, second = uuid4(), uuid4()
    jobs = FakeJobRepository([make_job(first), make_job(second)])
    builder = _Builder(jobs)
    worker = _worker(jobs, builder)

    assert await worker.run_once() is True
    assert await worker.run_once() is True
    assert await worker.run_once() is False

    assert [job.project_id for job in builder.handlers[first].handled] == [first]
    assert [job.project_id for job in builder.handlers[second].handled] == [second]
    assert worker.last_served == second


async def test_a_project_is_built_once_however_many_loops_meet_it() -> None:
    project = uuid4()
    jobs = FakeJobRepository([make_job(project), make_job(project)])
    builder = _Builder(jobs, slots=2)
    worker = _worker(jobs, builder)

    results = await asyncio.gather(worker.run_once(0), worker.run_once(1))

    assert results == [True, True]
    assert builder.built == [project]
    assert len(builder.handlers[project].handled) == 2


async def test_a_project_whose_loops_cannot_be_built_is_refused_and_the_rest_are_served() -> None:
    broken, healthy = uuid4(), uuid4()
    jobs = FakeJobRepository([make_job(broken), make_job(healthy)])
    builder = _Builder(jobs)
    logger = _Logger()

    async def loops_for(project_id: UUID) -> Sequence[WorkerLoopInterface] | None:
        if project_id == broken:
            raise ValueError("forbidden engine_environment")
        return await builder(project_id)

    worker = _worker(jobs, loops_for, logger)

    assert await worker.run_once() is True
    assert await worker.run_once() is False
    assert worker.last_served == healthy
    assert ("error", "worker.project_refused") in {(lvl, ev) for lvl, ev, _ in logger.events}
    # Refused once, for the life of the worker: never rebuilt on the next poll.
    assert builder.built == [healthy]


async def test_a_project_the_builder_declines_is_skipped_quietly_after_one_warning() -> None:
    declined, served = uuid4(), uuid4()
    jobs = FakeJobRepository([make_job(declined), make_job(served)])
    builder = _Builder(jobs)
    logger = _Logger()
    calls: list[UUID] = []

    async def loops_for(project_id: UUID) -> Sequence[WorkerLoopInterface] | None:
        calls.append(project_id)
        if project_id == declined:
            return None
        return await builder(project_id)

    worker = _worker(jobs, loops_for, logger)
    assert await worker.run_once() is True
    assert await worker.run_once() is False
    assert calls.count(declined) == 1
    warnings = [ev for lvl, ev, _ in logger.events if lvl == "warning"]
    assert warnings == ["worker.project_refused"]


async def test_a_project_drained_by_another_worker_is_passed_over() -> None:
    """The listing is a snapshot; the claim decides. A project whose work another worker
    took in between claims nothing, and the next project is tried."""
    raced, next_up = uuid4(), uuid4()
    raced_job = make_job(raced)
    jobs = FakeJobRepository([raced_job, make_job(next_up)])
    builder = _Builder(jobs)
    worker = _worker(jobs, builder)

    listed = await jobs.claimable_projects()
    jobs._jobs[raced_job.id] = make_job(raced, state=JobState.LEASED)

    async def stale_listing() -> tuple[UUID, ...]:
        return listed

    jobs.claimable_projects = stale_listing  # type: ignore[method-assign]

    assert await worker.run_once() is True
    assert worker.last_served == next_up
