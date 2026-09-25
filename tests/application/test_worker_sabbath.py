# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sub-doctrine 8.i in the worker: no lease is claimed from sundown Friday to sundown
Saturday; the job waits where the queue put it, and the first poll after claims it."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey.application.interfaces import Outcome, Success
from vibey.application.worker import WorkerLoop
from vibey.domain.job import JobState
from vibey.domain.sabbath import RestWindow

PROJECT_ID = uuid4()
REST = RestWindow(
    datetime(2026, 9, 25, 23, 23, tzinfo=UTC),
    datetime(2026, 9, 26, 23, 22, tzinfo=UTC),
    True,
    "computed sundown",
)


class _Gate:
    def __init__(self) -> None:
        self.held: RestWindow | None = REST

    def hold(self) -> RestWindow | None:
        return self.held


class _Log:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> "_Log":
        return self

    def debug(self, event: str, **kwargs: Any) -> None: ...

    def info(self, event: str, **kwargs: Any) -> None:
        self.events.append((event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None: ...

    def error(self, event: str, **kwargs: Any) -> None: ...


class _Handler:
    async def handle(self, job: Any) -> Outcome:
        return Success()


async def test_a_resting_worker_claims_nothing_and_resumes_after_the_window() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gate = _Gate()
    log = _Log()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_Handler(),
        owner="w1",
        logger=log,
        sabbath=gate,
    )

    assert await loop.run_once(PROJECT_ID) is False
    assert await loop.run_once(PROJECT_ID) is False
    record = await jobs.get(job.id)
    assert record is not None and record.state is JobState.READY
    assert [event for event, _ in log.events] == ["sabbath.resting"]
    assert log.events[0][1]["resumes"] == REST.resumes.isoformat()

    gate.held = None
    assert await loop.run_once(PROJECT_ID) is True
    assert [event for event, _ in log.events] == ["sabbath.resting", "sabbath.ended"]
    record = await jobs.get(job.id)
    assert record is not None and record.state is JobState.SUCCEEDED
    assert await loop.run_once(PROJECT_ID) is False
    assert len(log.events) == 2
