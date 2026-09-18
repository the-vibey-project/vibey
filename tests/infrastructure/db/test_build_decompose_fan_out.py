# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""build.decompose's fan-out against real Postgres (#265): a worker that dies
part-way through writing the plan leaves nothing behind, the replay writes
exactly one job per item, and a replay after the commit never asks the
producer for a second plan."""

from collections.abc import Mapping
from datetime import timedelta
from uuid import UUID

import asyncpg
import pytest

from vibey.application.build_decompose_handler import BuildDecomposeHandler
from vibey.application.dto import EnqueueRequest, JobRecord
from vibey.application.worker import Success
from vibey.domain.effort import Effort
from vibey.domain.job import idempotency_key
from vibey.domain.phase import Phase
from vibey.domain.plan import VerificationSpec, WorkItem
from vibey.domain.spec import AcceptanceCriterion, DesignSpec
from vibey.infrastructure.db.job_repository import PostgresJobRepository

LEASE = timedelta(seconds=30)

SPEC = DesignSpec(
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


def _item(
    item_id: str, *, acceptance_ids: tuple[str, ...] = (), depends_on: tuple[str, ...] = ()
) -> WorkItem:
    return WorkItem(
        item_id=item_id,
        title=f"do {item_id}",
        acceptance_ids=acceptance_ids,
        depends_on=depends_on,
        est_effort=Effort.LOW,
        files_touched_hint=(),
        verification=VerificationSpec(commands=("true",), criteria_checked=acceptance_ids),
    )


# Listed out of dependency order on purpose: item-2 names item-3, which comes
# after it. The handler orders the plan; the batch never sees it this way.
PLAN = (
    _item("skeleton", acceptance_ids=("AC-1",)),
    _item("item-2", acceptance_ids=("AC-2",), depends_on=("item-3",)),
    _item("item-3", depends_on=("skeleton",)),
)


class Specs:
    async def load(self, project_id: UUID, cycle: int) -> DesignSpec:
        return SPEC


class Decomposer:
    def __init__(self, items: tuple[WorkItem, ...]) -> None:
        self.items = items
        self.calls = 0

    async def decompose(self, spec: DesignSpec) -> tuple[WorkItem, ...]:
        self.calls += 1
        return self.items


class DyingJobRepository(PostgresJobRepository):
    """The worker dies writing the Nth request of a batch: the rows before it
    are already inside the transaction when the connection goes."""

    def __init__(self, pool: asyncpg.Pool, *, dies_at: int) -> None:
        super().__init__(pool)
        self._dies_at = dies_at
        self._writes = 0

    async def _enqueue_on(
        self,
        conn: asyncpg.Connection,
        request: EnqueueRequest,
        enqueued: Mapping[tuple[UUID, str], UUID],
    ) -> JobRecord:
        self._writes += 1
        if self._writes == self._dies_at:
            raise ConnectionResetError("worker died mid-fan-out")
        return await super()._enqueue_on(conn, request, enqueued)


async def _claimed_decompose_job(repo: PostgresJobRepository, project_id: UUID) -> JobRecord:
    await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            kind="build.decompose",
            idempotency_key=idempotency_key(project_id, 1, "build.decompose", "entry"),
        )
    )
    job = await repo.claim(project_id, owner="worker-1", lease=LEASE)
    assert job is not None and job.kind == "build.decompose"
    return job


async def _edges(pool: asyncpg.Pool, project_id: UUID) -> set[tuple[str, str]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT j.work_item_id AS job, p.work_item_id AS waits_for
            FROM job_dependency d
            JOIN job j ON j.id = d.job_id
            JOIN job p ON p.id = d.depends_on_job_id
            WHERE j.project_id = $1
            """,
            project_id,
        )
    return {(row["job"], row["waits_for"]) for row in rows}


async def test_a_worker_dying_mid_fan_out_leaves_nothing_and_the_replay_one_job_per_item(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await _claimed_decompose_job(repo, project_id)

    dying = DyingJobRepository(migrated_pool, dies_at=3)
    first_attempt = BuildDecomposeHandler(specs=Specs(), decomposer=Decomposer(PLAN), jobs=dying)
    with pytest.raises(ConnectionResetError):
        await first_attempt.handle(job)
    assert await repo.list_for_cycle(project_id, cycle=1, kind="build.implement") == ()

    replay = BuildDecomposeHandler(specs=Specs(), decomposer=Decomposer(PLAN), jobs=repo)
    outcome = await replay.handle(job)

    assert outcome == Success({"work_items": 3})
    fan_out = await repo.list_for_cycle(project_id, cycle=1, kind="build.implement")
    assert sorted(record.work_item_id or "" for record in fan_out) == [
        "item-2",
        "item-3",
        "skeleton",
    ]
    assert await _edges(migrated_pool, project_id) == {
        ("item-3", "skeleton"),
        ("item-2", "item-3"),
    }


async def test_a_replay_after_the_commit_keeps_the_committed_plan(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await _claimed_decompose_job(repo, project_id)
    await BuildDecomposeHandler(specs=Specs(), decomposer=Decomposer(PLAN), jobs=repo).handle(job)

    # The worker died after the commit, before the ack. Asked again, the
    # producer would answer differently -- so it is not asked.
    different = Decomposer((_item("other", acceptance_ids=("AC-1", "AC-2")),))
    replay = BuildDecomposeHandler(specs=Specs(), decomposer=different, jobs=repo)
    outcome = await replay.handle(job)

    assert outcome == Success({"work_items": 3, "replayed": True})
    assert different.calls == 0
    fan_out = await repo.list_for_cycle(project_id, cycle=1, kind="build.implement")
    assert len(fan_out) == 3
    assert "other" not in {record.work_item_id for record in fan_out}
