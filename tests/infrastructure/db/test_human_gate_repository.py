# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.worker import Outcome, Park, WorkerLoop
from vibey.domain.job import JobState
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.job_repository import PostgresJobRepository

from .test_job_repository import LEASE, _request

RAISED = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


async def _other_project(owner: asyncpg.Pool) -> UUID:
    async with owner.acquire() as conn:
        pid = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) "
            "RETURNING id",
            "other",
            "/tmp/other",
        )
    return UUID(str(pid))


async def _gate_row(
    owner: asyncpg.Pool,
    project_id: UUID,
    *,
    gate_id: UUID,
    raised_at: datetime,
    answered: bool = False,
) -> None:
    """A gate with the id and raise time the test names, written as the owner: setting
    `raised_at` is fixture work, not something the application does."""
    async with owner.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO human_gate (gate_id, project_id, kind, prompt, raised_at,
                                    answer, answered_at, answered_by)
            VALUES ($1, $2, 'approval', 'proceed?', $3, $4::jsonb, $5, $6)
            """,
            gate_id,
            project_id,
            raised_at,
            '{"verdict": "accept"}' if answered else None,
            raised_at if answered else None,
            "adam" if answered else None,
        )


class _ParkingHandler:
    async def handle(self, job: JobRecord) -> Outcome:
        return Park(HumanGateRequest(kind="approval", prompt="proceed with deploy?"))


async def test_raise_and_answer_round_trip(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    jobs = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await jobs.enqueue(_request(project_id))
    claimed = await jobs.claim(project_id, owner="w1", lease=LEASE)
    assert claimed is not None
    assert await jobs.park(job.id, owner="w1")

    raised = await gates.raise_gate(
        project_id,
        job.id,
        HumanGateRequest(kind="approval", prompt="proceed?", options=("yes", "no")),
    )

    assert raised.answered_at is None
    assert raised.prompt == "proceed?"
    assert raised.options == ("yes", "no")

    answered = await gates.answer(raised.gate_id, answer={"choice": "yes"}, answered_by="adam")

    assert answered.answered_at is not None
    assert answered.answered_by == "adam"
    assert answered.answer == {"choice": "yes"}

    fetched = await gates.get(raised.gate_id)
    assert fetched is not None
    assert fetched.answer == {"choice": "yes"}
    requeued = await jobs.get(job.id)
    assert requeued is not None
    assert requeued.state is JobState.READY


async def test_answer_nonexistent_gate_raises_lookup_error(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    from uuid import uuid4

    gates = PostgresHumanGateRepository(migrated_pool)
    with pytest.raises(LookupError, match="expected a row"):
        await gates.answer(uuid4(), answer={"choice": "yes"}, answered_by="test")


async def test_answer_gate_with_no_job_id_skips_job_requeue(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    gates = PostgresHumanGateRepository(migrated_pool)

    raised = await gates.raise_gate(
        project_id,
        None,
        HumanGateRequest(kind="approval", prompt="proceed?"),
    )

    answered = await gates.answer(raised.gate_id, answer={"choice": "yes"}, answered_by="test")
    assert answered.answered_at is not None
    assert answered.answer == {"choice": "yes"}


async def test_parked_job_releases_lease_immediately_and_worker_is_free(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    jobs = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await jobs.enqueue(_request(project_id))
    other = await jobs.enqueue(_request(project_id, subject="other"))

    loop = WorkerLoop(jobs=jobs, gates=gates, handler=_ParkingHandler(), owner="w1", lease=LEASE)
    claimed = await loop.run_once(project_id)
    assert claimed is True

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN
    assert record.lease_owner is None
    assert record.lease_expires_at is None

    # The worker is free within one loop iteration -- it can immediately
    # claim the next ready job rather than waiting out any lease.
    next_claim = await jobs.claim(project_id, owner="w1", lease=LEASE)
    assert next_claim is not None
    assert next_claim.id == other.id


async def test_the_repository_satisfies_its_port(migrated_pool: asyncpg.Pool) -> None:
    assert isinstance(PostgresHumanGateRepository(migrated_pool), HumanGateRepository)


async def test_open_all_is_empty_when_nothing_waits(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    assert await PostgresHumanGateRepository(migrated_pool).open_all() == ()


async def test_open_all_lists_every_projects_unanswered_gates_oldest_first(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    other = await _other_project(owner_pool)
    newest, oldest, middle, answered = uuid4(), uuid4(), uuid4(), uuid4()
    await _gate_row(owner_pool, project_id, gate_id=newest, raised_at=RAISED + timedelta(minutes=2))
    await _gate_row(owner_pool, other, gate_id=oldest, raised_at=RAISED)
    await _gate_row(owner_pool, project_id, gate_id=middle, raised_at=RAISED + timedelta(minutes=1))
    # The oldest of all, but answered: it waits on no one.
    await _gate_row(
        owner_pool, other, gate_id=answered, raised_at=RAISED - timedelta(minutes=1), answered=True
    )

    listed = await PostgresHumanGateRepository(migrated_pool).open_all()

    assert [gate.gate_id for gate in listed] == [oldest, middle, newest]
    assert [gate.project_id for gate in listed] == [other, project_id, project_id]
    assert all(gate.answered_at is None and gate.answer is None for gate in listed)


async def test_open_all_breaks_a_raised_at_tie_by_gate_id(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    low, high = UUID(int=1), UUID(int=2)
    await _gate_row(owner_pool, project_id, gate_id=high, raised_at=RAISED)
    await _gate_row(owner_pool, project_id, gate_id=low, raised_at=RAISED)

    listed = await PostgresHumanGateRepository(migrated_pool).open_all()

    assert [gate.gate_id for gate in listed] == [low, high]


async def test_open_all_reads_every_field_a_raised_gate_carries(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    jobs = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await jobs.enqueue(_request(project_id))
    raised = await gates.raise_gate(
        project_id,
        job.id,
        HumanGateRequest(
            kind="choice",
            prompt="Deploy?",
            options=("local_only", "deploy"),
            default_answer="local_only",
            timeout_at=RAISED + timedelta(days=7),
        ),
    )

    assert await gates.open_all() == (raised,)
    assert await gates.open_all() == await gates.open_for_project(project_id)
