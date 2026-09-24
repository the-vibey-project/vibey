# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Changing a project's caps against real PostgreSQL, as the application role.

The store runs under `migrated_pool` -- the restricted role production connects as
(ADR-0055) -- so the privileges it needs are the declared ones: `SELECT` and `UPDATE` on
`project`, `INSERT` on the ledger. Each change writes the config and appends one
`BudgetCapChanged` event per changed cap in ONE transaction; a replay writes nothing;
two changes to one project serialise on its row; and the ledger is only ever appended to.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.domain.budget_caps import CAP_CHANGE_PLANNER, CapChange, CapField
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.ledger import EventKind
from vibey.infrastructure.db.interfaces import (
    BudgetCapDraftBuilderInterface,
    PostgresProjectBudgetStoreInterface,
)
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.db.project_budget_store import (
    _LOCK_PROJECT,
    BUDGET_CAP_DRAFTS,
    PostgresProjectBudgetStore,
)
from vibey.infrastructure.db.project_repository import PostgresProjectRepository
from vibey.infrastructure.engines.loop_events import LOOP_EVENT_MAP
from vibey.infrastructure.engines.tailer import LedgerEventDraft

AT = datetime(2026, 9, 24, 19, 2, tzinfo=UTC)
DOLLARS = CapField.MAX_CYCLE_DOLLARS
TURNS = CapField.MAX_CYCLE_TURNS


async def _row(pool: asyncpg.Pool, project_id: UUID) -> asyncpg.Record:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT config, phase::text AS phase, cycle, updated_at FROM project WHERE id = $1",
            project_id,
        )
    assert row is not None
    return row


async def _config(pool: asyncpg.Pool, project_id: UUID) -> dict[str, object]:
    return dict(json.loads((await _row(pool, project_id))["config"]))


async def _events(pool: asyncpg.Pool, project_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "SELECT seq, cycle, phase::text AS phase, engine_id, job_id, "
                "provenance::text AS provenance, produced_at, payload FROM event "
                "WHERE project_id = $1 AND kind = 'BudgetCapChanged' ORDER BY seq",
                project_id,
            )
        )


async def _set_config(pool: asyncpg.Pool, project_id: UUID, config: dict[str, object]) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE project SET config = $2::jsonb WHERE id = $1", project_id, json.dumps(config)
        )


def test_the_store_and_its_draft_builder_satisfy_their_seams() -> None:
    assert isinstance(BUDGET_CAP_DRAFTS, BudgetCapDraftBuilderInterface)
    assert isinstance(PostgresProjectBudgetStore(pool=None), PostgresProjectBudgetStoreInterface)  # type: ignore[arg-type]


def test_no_engine_event_is_ever_translated_into_a_cap_change() -> None:
    """Only vibey's own command writes the kind: no loop's event type maps onto it."""
    for engine_map in LOOP_EVENT_MAP.values():
        assert EventKind.BUDGET_CAP_CHANGED not in engine_map.values()


async def test_setting_a_cap_writes_the_config_and_its_event_in_one_step(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _set_config(migrated_pool, project_id, {"project": {"name": "demo"}})
    before = await _row(migrated_pool, project_id)
    store = PostgresProjectBudgetStore(migrated_pool)

    outcome = await store.apply(
        project_id,
        CAP_CHANGE_PLANNER.setting(max_dollars=15),
        by="vibey-vscode",
        account="adam",
        at=AT,
    )

    assert outcome.changes == (CapChange(DOLLARS, None, 15.0),)
    assert outcome.project.config == {"project": {"name": "demo"}, "max_cycle_dollars": 15.0}
    assert await _config(migrated_pool, project_id) == outcome.project.config
    assert (await _row(migrated_pool, project_id))["updated_at"] > before["updated_at"]
    (event,) = await _events(migrated_pool, project_id)
    assert json.loads(event["payload"]) == {
        "field": "max_cycle_dollars",
        "old": None,
        "new": 15.0,
        "by": "vibey-vscode",
        "account": "adam",
    }
    assert (event["phase"], event["cycle"]) == (before["phase"], before["cycle"])
    assert (event["engine_id"], event["job_id"], event["provenance"]) == (None, None, "trusted")
    assert event["produced_at"] == AT


async def test_both_caps_are_two_events_dollars_first_in_one_transaction(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _set_config(migrated_pool, project_id, {"max_cycle_turns": 40})

    outcome = await PostgresProjectBudgetStore(migrated_pool).apply(
        project_id,
        CAP_CHANGE_PLANNER.setting(max_turns=200, max_dollars=2.5),
        by="adam",
        account="adam",
        at=AT,
    )

    assert outcome.changes == (CapChange(DOLLARS, None, 2.5), CapChange(TURNS, 40, 200))
    assert await _config(migrated_pool, project_id) == {
        "max_cycle_dollars": 2.5,
        "max_cycle_turns": 200,
    }
    events = [json.loads(e["payload"]) for e in await _events(migrated_pool, project_id)]
    assert [(e["field"], e["old"], e["new"]) for e in events] == [
        ("max_cycle_dollars", None, 2.5),
        ("max_cycle_turns", 40, 200),
    ]


async def test_a_replayed_change_writes_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresProjectBudgetStore(migrated_pool)
    request = CAP_CHANGE_PLANNER.setting(max_dollars=15, max_turns=40)
    await store.apply(project_id, request, by="adam", account="adam", at=AT)
    settled = await _row(migrated_pool, project_id)

    replay = await store.apply(project_id, request, by="adam", account="adam", at=AT)

    assert replay.changes == ()
    assert await _row(migrated_pool, project_id) == settled
    assert len(await _events(migrated_pool, project_id)) == 2


async def test_clearing_removes_the_key_so_the_project_is_as_if_never_capped(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _set_config(
        migrated_pool, project_id, {"max_cycle_dollars": 15.0, "max_cycle_turns": 40, "x": 1}
    )
    store = PostgresProjectBudgetStore(migrated_pool)

    outcome = await store.apply(
        project_id, CAP_CHANGE_PLANNER.clearing([DOLLARS]), by="adam", account="adam", at=AT
    )
    nothing = await store.apply(
        project_id, CAP_CHANGE_PLANNER.clearing([DOLLARS]), by="adam", account="adam", at=AT
    )

    assert outcome.changes == (CapChange(DOLLARS, 15.0, None),)
    assert nothing.changes == ()
    assert await _config(migrated_pool, project_id) == {"max_cycle_turns": 40, "x": 1}
    (event,) = await _events(migrated_pool, project_id)
    assert json.loads(event["payload"])["new"] is None


async def test_an_unknown_project_is_refused_and_nothing_is_written(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    missing = uuid4()

    with pytest.raises(UnknownProject, match=str(missing)):
        await PostgresProjectBudgetStore(migrated_pool).apply(
            missing, CAP_CHANGE_PLANNER.setting(max_dollars=1), by="a", account="a", at=AT
        )

    assert await _events(migrated_pool, missing) == []


async def test_a_project_in_a_phase_this_vibey_does_not_know_is_left_untouched(
    migrated_pool: asyncpg.Pool, project_id: UUID, owner_pool: asyncpg.Pool
) -> None:
    # Widening an enum is the owner's act (ADR-0055); the row is the application's.
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'hyperdrive'")
    async with migrated_pool.acquire() as conn:
        await conn.execute("UPDATE project SET phase = 'hyperdrive' WHERE id = $1", project_id)
    before = await _row(migrated_pool, project_id)

    with pytest.raises(WrongPhase, match="'hyperdrive'"):
        await PostgresProjectBudgetStore(migrated_pool).apply(
            project_id, CAP_CHANGE_PLANNER.setting(max_dollars=1), by="a", account="a", at=AT
        )

    assert await _row(migrated_pool, project_id) == before
    assert await _events(migrated_pool, project_id) == []


async def test_a_change_whose_event_cannot_be_appended_leaves_the_caps_as_they_were(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The config is never changed without its record: a failed append rolls it back."""

    class _Failing:
        async def append(self, conn: object, draft: LedgerEventDraft) -> object:
            raise RuntimeError("the ledger is unreachable")

    await _set_config(migrated_pool, project_id, {"max_cycle_dollars": 15.0})
    before = await _row(migrated_pool, project_id)
    store = PostgresProjectBudgetStore(migrated_pool, appender=_Failing())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="unreachable"):
        await store.apply(
            project_id, CAP_CHANGE_PLANNER.clearing(CapField), by="a", account="a", at=AT
        )

    assert await _row(migrated_pool, project_id) == before
    assert await _events(migrated_pool, project_id) == []


async def test_changes_to_one_project_serialise_and_each_records_what_it_replaced(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    stores = [PostgresProjectBudgetStore(migrated_pool) for _ in range(6)]

    outcomes = await asyncio.gather(
        *(
            store.apply(
                project_id,
                CAP_CHANGE_PLANNER.setting(max_dollars=10 + n),
                by=f"writer-{n}",
                account="adam",
                at=AT + timedelta(seconds=n),
            )
            for n, store in enumerate(stores)
        )
    )

    events = [json.loads(e["payload"]) for e in await _events(migrated_pool, project_id)]
    assert len(events) == len(outcomes) == 6
    # Each change's `old` is the value the change before it left: no lost update.
    assert [e["old"] for e in events] == [None, *(e["new"] for e in events[:-1])]
    assert await _config(migrated_pool, project_id) == {"max_cycle_dollars": events[-1]["new"]}


async def test_the_row_lock_never_holds_up_the_ledger_or_the_queue(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """`FOR NO KEY UPDATE`: an event appended for the project while a cap change holds
    its row is not blocked by the lock -- a worker keeps writing its ledger."""
    ledger = PostgresLedgerRepository(migrated_pool)
    async with migrated_pool.acquire() as conn, conn.transaction():
        await conn.fetchrow(_LOCK_PROJECT, project_id)
        draft = BUDGET_CAP_DRAFTS.build(
            (await PostgresProjectRepository(migrated_pool).get(project_id)),  # type: ignore[arg-type]
            CapChange(TURNS, None, 5),
            by="elsewhere",
            account="adam",
            at=AT,
        )
        appended = await asyncio.wait_for(ledger.append(draft), timeout=10)

    assert appended.kind is EventKind.BUDGET_CAP_CHANGED


async def test_every_project_is_listed_newest_first_then_by_id(
    migrated_pool: asyncpg.Pool,
) -> None:
    async with migrated_pool.acquire() as conn:
        same = datetime(2026, 9, 1, tzinfo=UTC)
        ids = [
            await conn.fetchval(
                "INSERT INTO project (name, repo_path, config, created_at) "
                "VALUES ($1, $2, '{}'::jsonb, $3) RETURNING id",
                name,
                f"/tmp/{name}",
                created,
            )
            for name, created in (
                ("old", same - timedelta(days=1)),
                ("twin-a", same),
                ("twin-b", same),
                ("new", same + timedelta(days=1)),
            )
        ]

    listed = await PostgresProjectRepository(migrated_pool).list_all()

    twins = sorted(ids[1:3], reverse=True)
    assert [p.project_id for p in listed] == [ids[3], *twins, ids[0]]
