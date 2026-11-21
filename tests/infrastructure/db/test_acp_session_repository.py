# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ACP sessions and their logs in PostgreSQL (SP-ACP Task 6, migration 0023).

Run as the application role (`migrated_pool`), the grants production runs under, so a query
that needs an undeclared privilege fails here; the owner is used only to set up state the
application never writes itself (shared timestamps) and to show the triggers refuse even it.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
import pytest

from vibey.application.acp.interfaces.acp_session_repository_interface import (
    AcpSessionRepositoryInterface,
)
from vibey.domain.acp.session_log import SessionEventConflict
from vibey.infrastructure.db.acp_session_repository import PostgresAcpSessionRepository

S1 = "00000000-0000-4000-8000-000000000001"
S2 = "00000000-0000-4000-8000-000000000002"
REFUSED = "append-only"


def _sid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


async def test_the_repository_meets_its_declared_seam(migrated_pool: asyncpg.Pool) -> None:
    assert isinstance(PostgresAcpSessionRepository(migrated_pool), AcpSessionRepositoryInterface)


async def test_create_is_idempotent_and_owner_names_creator_and_folder(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    assert await repo.owner(S1) is None
    await repo.create(S1, "/work/a", "agent")
    await repo.create(S1, "/work/other", "device")  # a second create changes nothing
    assert await repo.owner(S1) == ("agent", "/work/a")


async def test_append_is_idempotent_for_an_identical_replay(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent")
    payload = {"text": "hi", "nested": {"b": 2, "a": 1}}
    assert await repo.append(S1, 1, "user_message", payload) is True
    # The same event again, its keys in another order: answered as stored, written once.
    assert await repo.append(S1, 1, "user_message", {"nested": {"a": 1, "b": 2}, "text": "hi"})
    events = await repo.events_after(S1, 0, 10)
    assert [(e.seq, e.kind, dict(e.payload)) for e in events] == [(1, "user_message", payload)]


@pytest.mark.parametrize(
    ("kind", "payload"),
    [("user_message", {"text": "other"}), ("agent_message", {"text": "hi"})],
)
async def test_append_conflicting_payload_raises(
    migrated_pool: asyncpg.Pool, kind: str, payload: dict[str, str]
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent")
    await repo.append(S1, 1, "user_message", {"text": "hi"})
    with pytest.raises(SessionEventConflict, match="seq 1"):
        await repo.append(S1, 1, kind, payload)
    assert [dict(e.payload) for e in await repo.events_after(S1, 0, 10)] == [{"text": "hi"}]


async def test_a_concurrent_identical_append_is_answered_as_stored(
    migrated_pool: asyncpg.Pool,
) -> None:
    """The second statement sees a row the first statement's snapshot could not."""
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent")
    held = await migrated_pool.acquire()
    try:
        transaction = held.transaction()
        await transaction.start()
        await held.execute(
            "INSERT INTO acp_session_event (session_id, seq, kind, payload) "
            "VALUES ($1, 1, 'plan', '{\"entries\": []}')",
            S1,
        )
        racing = asyncio.create_task(repo.append(S1, 1, "plan", {"entries": []}))
        await asyncio.sleep(0.2)  # the racing insert now waits on the held row
        await transaction.commit()
        assert await racing is True
    finally:
        await migrated_pool.release(held)


async def test_an_event_needs_its_session_and_a_known_kind(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await repo.append(S1, 1, "plan", {})
    await repo.create(S1, "/work", "agent")
    with pytest.raises(asyncpg.CheckViolationError):
        await repo.append(S1, 1, "request_permission", {})
    with pytest.raises(asyncpg.CheckViolationError):
        await repo.append(S1, 0, "plan", {})


async def test_events_after_reads_in_seq_order_from_the_watermark(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent")
    for seq in (3, 1, 2, 4):
        await repo.append(S1, seq, "agent_message", {"text": str(seq)})
    assert [e.seq for e in await repo.events_after(S1, 1, 2)] == [2, 3]
    assert [e.seq for e in await repo.events_after(S1, 0, 10)] == [1, 2, 3, 4]
    assert await repo.events_after(S2, 0, 10) == ()


@pytest.mark.parametrize("table", ["acp_session", "acp_session_event"])
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE {t} SET session_id = session_id",
        "DELETE FROM {t}",
        "TRUNCATE {t} CASCADE",
    ],
)
async def test_update_and_delete_are_refused_by_the_database(
    owner_pool: asyncpg.Pool, table: str, statement: str
) -> None:
    repo = PostgresAcpSessionRepository(owner_pool)
    await repo.create(S1, "/work", "agent")
    await repo.append(S1, 1, "user_message", {"text": "hi"})
    async with owner_pool.acquire() as conn:
        with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
            await conn.execute(statement.format(t=table))
        assert await conn.fetchval("SELECT count(*) FROM acp_session_event") == 1


async def test_even_the_owner_cannot_rewrite_an_event(owner_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(owner_pool)
    await repo.create(S1, "/work", "agent")
    await repo.append(S1, 1, "user_message", {"text": "hi"})
    async with owner_pool.acquire() as conn:
        with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
            await conn.execute("UPDATE acp_session_event SET kind = 'plan'")


async def _sessions_sharing_one_instant(owner_pool: asyncpg.Pool, count: int) -> datetime:
    """`count` sessions whose newest events were all recorded at one instant."""
    instant = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    async with owner_pool.acquire() as conn:
        for n in range(1, count + 1):
            await conn.execute(
                "INSERT INTO acp_session (session_id, cwd, created_by, created_at) "
                "VALUES ($1, '/work', 'agent', $2)",
                _sid(n),
                instant - timedelta(days=1),
            )
            await conn.execute(
                "INSERT INTO acp_session_event (session_id, seq, kind, payload, recorded_at) "
                "VALUES ($1, 1, 'user_message', '{}', $2)",
                _sid(n),
                instant - timedelta(hours=1),
            )
            await conn.execute(
                "INSERT INTO acp_session_event (session_id, seq, kind, payload, recorded_at) "
                "VALUES ($1, 2, 'agent_message', '{}', $2)",
                _sid(n),
                instant,
            )
    return instant


async def test_list_pages_by_keyset_with_no_gap_or_repeat_under_equal_timestamps(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool
) -> None:
    instant = await _sessions_sharing_one_instant(owner_pool, 25)
    repo = PostgresAcpSessionRepository(migrated_pool)
    seen: list[str] = []
    cursor: tuple[datetime, str] | None = None
    pages = 0
    while True:
        page = await repo.list("agent", cwd=None, cursor=cursor, limit=10)
        pages += 1
        seen += [record.session_id for record in page]
        assert all(record.updated_at == instant for record in page)
        if len(page) < 10:
            break
        cursor = (page[-1].updated_at, page[-1].session_id)
    assert pages == 3
    assert len(seen) == len(set(seen)) == 25
    assert seen == sorted(seen, reverse=True)


async def test_list_is_newest_first_by_the_newest_event_and_says_title_and_close(
    migrated_pool: asyncpg.Pool, owner_pool: asyncpg.Pool
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent")
    await repo.create(S2, "/work", "agent")
    await repo.append(S1, 1, "title", {"title": "first"})
    await repo.append(S1, 2, "title", {"title": "second"})
    async with owner_pool.acquire() as conn:
        # S2 is older than S1's newest event, though it was created after S1.
        await conn.execute(
            "INSERT INTO acp_session_event (session_id, seq, kind, payload, recorded_at) "
            "VALUES ($1, 1, 'closed', '{}', now() - interval '1 day')",
            S2,
        )
    listed = await repo.list("agent", cwd=None, cursor=None, limit=10)
    assert [(r.session_id, r.title, r.closed) for r in listed] == [
        (S1, "second", False),
        (S2, None, True),
    ]


async def test_a_session_with_no_event_is_listed_by_when_it_was_created(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent")
    (record,) = await repo.list("agent", cwd=None, cursor=None, limit=10)
    assert record.title is None and record.closed is False
    assert record.updated_at.tzinfo is not None


async def test_list_is_scoped_to_the_creator(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work/a", "agent")
    await repo.create(S2, "/work/b", "device")
    await repo.create(_sid(3), "/work/b", "agent")
    every = await repo.list("agent", cwd=None, cursor=None, limit=9)
    assert {r.session_id for r in every} == {S1, _sid(3)}
    mine = await repo.list("agent", cwd="/work/b", cursor=None, limit=9)
    assert [r.session_id for r in mine] == [_sid(3)]
    assert [r.session_id for r in await repo.list("device", cwd=None, cursor=None, limit=9)] == [S2]
    assert await repo.list("nobody", cwd=None, cursor=None, limit=9) == ()
