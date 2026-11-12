# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How many SQL statements each hot-path operation costs, held to a budget that can only fall.

`query_budgets.toml` records what each operation sends today. The check is
two-sided: a higher count fails (a new round trip needs a written reason in the
commit), and a lower count fails too, so the budget follows every saving down
and a later regression cannot hide inside the slack.
"""

import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest

from tests.infrastructure.db.query_counter import QueryCounter, QueryLog
from vibey.application.dto import EnqueueRequest
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft

BUDGETS = tomllib.loads((Path(__file__).parent / "query_budgets.toml").read_text())
LEASE = timedelta(seconds=30)


def check_budget(operation: str, log: QueryLog) -> None:
    budget = BUDGETS[operation]
    assert isinstance(budget, int)
    listing = "\n".join(
        f"  {n}. {' '.join(s.split())[:110]}" for n, s in enumerate(log.statements, 1)
    )
    assert log.count <= budget, (
        f"{operation} sent {log.count} statements against a budget of {budget}. "
        f"Raise a budget only with a written reason in the commit.\n{listing}"
    )
    assert log.count >= budget, (
        f"{operation} sent {log.count} statements, fewer than its budget of {budget}. "
        f"The count fell: lower {operation} to {log.count} in query_budgets.toml so the "
        f"saving cannot be spent again.\n{listing}"
    )


def _draft(project_id: UUID) -> LedgerEventDraft:
    payload: dict[str, object] = {"prompt_digest": "abc"}
    return LedgerEventDraft(
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        kind=EventKind.TURN_REQUESTED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload=payload,
        digest=digest_event(payload),
    )


def _request(project_id: UUID, subject: str = "item-001") -> EnqueueRequest:
    return EnqueueRequest(
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        kind="build.implement",
        idempotency_key=f"key-{subject}",
        payload={"subject": subject},
    )


async def test_ledger_append_stays_within_its_query_budget(
    migrated_pool: asyncpg.Pool, project_id: UUID, query_counter: QueryCounter
) -> None:
    repo = PostgresLedgerRepository(migrated_pool)

    async with query_counter.count(migrated_pool) as log:
        await repo.append(_draft(project_id))

    check_budget("ledger_append", log)


async def test_job_enqueue_stays_within_its_query_budget(
    migrated_pool: asyncpg.Pool, project_id: UUID, query_counter: QueryCounter
) -> None:
    repo = PostgresJobRepository(migrated_pool)

    async with query_counter.count(migrated_pool) as log:
        await repo.enqueue(_request(project_id))

    check_budget("job_enqueue", log)


async def test_job_claim_stays_within_its_query_budget(
    migrated_pool: asyncpg.Pool, project_id: UUID, query_counter: QueryCounter
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    await repo.enqueue(_request(project_id))

    async with query_counter.count(migrated_pool) as log:
        claimed = await repo.claim(project_id, owner="worker-1", lease=LEASE)

    assert claimed is not None
    check_budget("job_claim", log)


async def test_job_ack_stays_within_its_query_budget(
    migrated_pool: asyncpg.Pool, project_id: UUID, query_counter: QueryCounter
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    job = await repo.enqueue(_request(project_id))
    await repo.claim(project_id, owner="worker-1", lease=LEASE)

    async with query_counter.count(migrated_pool) as log:
        acked = await repo.ack(job.id, owner="worker-1")

    assert acked is True
    check_budget("job_ack", log)


async def test_the_counter_counts_every_statement_in_the_block(
    migrated_pool: asyncpg.Pool, query_counter: QueryCounter
) -> None:
    async with query_counter.count(migrated_pool) as log:
        async with migrated_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        async with migrated_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

    assert log.count == 2
    assert log.statements == ["SELECT 1", "SELECT 1"]


async def test_the_counter_covers_connections_the_pool_opens_during_the_block(
    migrated_pool: asyncpg.Pool, query_counter: QueryCounter
) -> None:
    async with (
        query_counter.count(migrated_pool) as log,
        migrated_pool.acquire() as first,
        migrated_pool.acquire() as second,
    ):
        await first.fetchval("SELECT 1")
        await second.fetchval("SELECT 2")

    assert sorted(log.statements) == ["SELECT 1", "SELECT 2"]


async def test_the_counter_removes_its_logger_on_exit(
    migrated_pool: asyncpg.Pool, query_counter: QueryCounter
) -> None:
    async with query_counter.count(migrated_pool) as log:
        await migrated_pool.fetchval("SELECT 1")

    await migrated_pool.fetchval("SELECT 1")
    await migrated_pool.fetchval("SELECT 1")

    assert log.count == 1


def test_a_count_above_the_budget_fails_and_asks_for_a_written_reason() -> None:
    log = QueryLog(statements=["SELECT 1"] * (BUDGETS["job_ack"] + 1))

    with pytest.raises(AssertionError, match="written reason in the commit"):
        check_budget("job_ack", log)


def test_a_count_below_the_budget_fails_and_asks_for_the_budget_to_be_lowered() -> None:
    log = QueryLog(statements=["SELECT 1"] * (BUDGETS["ledger_append"] - 1))

    with pytest.raises(AssertionError, match="lower ledger_append to 3"):
        check_budget("ledger_append", log)
