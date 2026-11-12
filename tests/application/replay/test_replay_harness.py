# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The replay assertion itself is held to account: it passes a handler whose replay is
harmless and fails one whose replay is not, even when a COUNT would not notice."""

from dataclasses import replace
from uuid import uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from tests.application.replay.harness import (
    ReplayCase,
    ReplayRig,
    assert_replay_is_idempotent,
    jobs_content,
)
from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.worker import Success
from vibey.domain.job import idempotency_key
from vibey.domain.phase import Phase


class _ToyHandler:
    """Enqueues a follow-up. ``idempotent`` keys it by the job (a replay finds the row);
    otherwise it keys it by a fresh uuid, so every delivery adds a row."""

    def __init__(self, jobs: FakeJobRepository, *, idempotent: bool) -> None:
        self._jobs = jobs
        self._idempotent = idempotent

    async def handle(self, job: JobRecord) -> Success:
        key = (
            idempotency_key(job.project_id, job.cycle, "toy.follow", str(job.id))
            if self._idempotent
            else f"toy-{uuid4()}"
        )
        await self._jobs.enqueue(
            EnqueueRequest(
                project_id=job.project_id,
                cycle=job.cycle,
                phase=Phase.BUILD,
                kind="toy.follow",
                idempotency_key=key,
            )
        )
        return Success({})


class _ToyRewriter:
    """Always leaves exactly one follow-up row (the COUNT never changes) but rewrites its
    payload on every delivery: only a content comparison sees it."""

    def __init__(self, jobs: FakeJobRepository) -> None:
        self._jobs = jobs
        self._deliveries = 0

    async def handle(self, job: JobRecord) -> Success:
        self._deliveries += 1
        existing = [row for row in self._jobs._jobs.values() if row.kind == "toy.follow"]
        if existing:
            self._jobs._jobs[existing[0].id] = replace(
                existing[0], payload={"delivery": self._deliveries}
            )
        else:
            row = await self._jobs.enqueue(
                EnqueueRequest(
                    project_id=job.project_id,
                    cycle=job.cycle,
                    phase=Phase.BUILD,
                    kind="toy.follow",
                    idempotency_key="toy-one",
                    payload={"delivery": self._deliveries},
                )
            )
            assert row.kind == "toy.follow"
        return Success({})


def _case(make_handler) -> ReplayCase:  # type: ignore[no-untyped-def]
    def build() -> ReplayRig:
        jobs = FakeJobRepository()
        job = replace(make_job(uuid4()), kind="toy.in")
        jobs.seed_leased(job)
        return ReplayRig(
            handler=make_handler(jobs),
            job=job,
            snapshot=lambda: {"jobs": jobs_content(jobs)},
            redeliver=lambda: make_handler(jobs),
        )

    return ReplayCase(name="toy", kind="toy", build=build)


async def test_an_idempotent_handler_passes() -> None:
    await assert_replay_is_idempotent(_case(lambda jobs: _ToyHandler(jobs, idempotent=True)))


async def test_a_handler_that_adds_a_row_per_delivery_fails() -> None:
    with pytest.raises(AssertionError, match="a redelivery changed"):
        await assert_replay_is_idempotent(_case(lambda jobs: _ToyHandler(jobs, idempotent=False)))


async def test_a_handler_that_rewrites_a_row_fails_even_though_the_count_is_equal() -> None:
    # One row after the first delivery and one after the second: a count comparison passes.
    shared: dict[str, _ToyRewriter] = {}

    def handler(jobs: FakeJobRepository) -> _ToyRewriter:
        # A new instance over the same persisted rows, as a redelivery is; its delivery
        # counter continues so the second write differs from the first.
        previous = shared.get("h")
        instance = _ToyRewriter(jobs)
        instance._deliveries = previous._deliveries if previous else 0
        shared["h"] = instance
        return instance

    with pytest.raises(AssertionError, match="payload"):
        await assert_replay_is_idempotent(_case(handler))
