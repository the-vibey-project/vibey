# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg

from vibey.application.design import DesignEvent
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, Provenance, UnrecognizedEventKind, digest_event
from vibey.infrastructure.db.design_ledger import PostgresDesignLedger
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository


async def test_design_events_round_trip_through_real_append_only_ledger(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    ledger = PostgresDesignLedger(PostgresLedgerRepository(migrated_pool))
    job_id = uuid4()
    event = DesignEvent(
        EventKind.QUESTION_ASKED,
        Provenance.AGENT,
        datetime(2026, 8, 14, tzinfo=UTC),
        {
            "item_id": "q-1",
            "text": "Who uses it?",
            "default": "A developer",
            "blocking": True,
            "stage": "context_free",
        },
    )
    await ledger.append(project_id, 1, job_id, EngineId.CLAUDELOOP, event)

    replayed = await ledger.all_for_project(project_id)
    assert replayed == (event,)


async def test_a_design_kind_this_vibey_does_not_know_is_left_out_of_the_design_view(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """vibey#275: no design handler can act on a newer vibey's kind, and a
    `DesignEvent` only ever carries a kind vibey can write. The row stays in
    the ledger itself."""
    repository = PostgresLedgerRepository(migrated_pool)
    ledger = PostgresDesignLedger(repository)
    at = datetime(2026, 8, 14, tzinfo=UTC)
    known = DesignEvent(EventKind.QUESTION_ASKED, Provenance.AGENT, at, {"item_id": "q-1"})
    await ledger.append(project_id, 1, uuid4(), None, known)
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            "SELECT append_event($1, 1, 'design', 'DesignSketched', NULL, NULL, NULL, $1, "
            "'agent', $2, '{}'::jsonb, $3)",
            project_id,
            at,
            digest_event({}),
        )

    assert await ledger.all_for_project(project_id) == (known,)
    everything = await repository.all_for_project(project_id)
    assert [e.kind for e in everything] == [
        EventKind.QUESTION_ASKED,
        UnrecognizedEventKind("DesignSketched"),
    ]
