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
from vibey.domain.acp.session_log import AcpSessionLimitReached, SessionEventConflict
from vibey.infrastructure.db.acp_session_repository import PostgresAcpSessionRepository

S1 = "00000000-0000-4000-8000-000000000001"
S2 = "00000000-0000-4000-8000-000000000002"
REFUSED = "append-only"

LIMIT = 1000
"""A cap no test here reaches, except where a test says otherwise."""


def _sid(n: int) -> str:
    return f"00000000-0000-4000-8000-{n:012d}"


async def test_the_repository_meets_its_declared_seam(migrated_pool: asyncpg.Pool) -> None:
    assert isinstance(PostgresAcpSessionRepository(migrated_pool), AcpSessionRepositoryInterface)


async def test_create_is_idempotent_and_owner_names_creator_and_folder(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    assert await repo.owner(S1) is None
    await repo.create(S1, "/work/a", "agent", limit=LIMIT)
    await repo.create(S1, "/work/other", "device", limit=LIMIT)  # a second create changes nothing
    assert await repo.owner(S1) == ("agent", "/work/a")


async def test_append_is_idempotent_for_an_identical_replay(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    payload = {"text": "hi", "nested": {"b": 2, "a": 1}}
    assert await repo.append(S1, 1, "user_message", payload, limit=LIMIT) is True
    # The same event again, its keys in another order: answered as stored, written once.
    assert await repo.append(
        S1, 1, "user_message", {"nested": {"a": 1, "b": 2}, "text": "hi"}, limit=LIMIT
    )
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
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    await repo.append(S1, 1, "user_message", {"text": "hi"}, limit=LIMIT)
    with pytest.raises(SessionEventConflict, match="seq 1"):
        await repo.append(S1, 1, kind, payload, limit=LIMIT)
    assert [dict(e.payload) for e in await repo.events_after(S1, 0, 10)] == [{"text": "hi"}]


async def test_a_concurrent_identical_append_is_answered_as_stored(
    migrated_pool: asyncpg.Pool,
) -> None:
    """The second statement sees a row the first statement's snapshot could not."""
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    held = await migrated_pool.acquire()
    try:
        transaction = held.transaction()
        await transaction.start()
        await held.execute(
            "INSERT INTO acp_session_event (session_id, seq, kind, payload) "
            "VALUES ($1, 1, 'plan', '{\"entries\": []}')",
            S1,
        )
        racing = asyncio.create_task(repo.append(S1, 1, "plan", {"entries": []}, limit=LIMIT))
        # Wait, without the real clock, until the racing insert waits on the held row.
        async with migrated_pool.acquire() as watcher:
            while not racing.done() and not await watcher.fetchval(
                "SELECT count(*) > 0 FROM pg_stat_activity "
                "WHERE wait_event_type = 'Lock' AND datname = current_database()"
            ):
                await asyncio.sleep(0)
        assert not racing.done()  # it waits on the held row, as a concurrent append does
        await transaction.commit()
        assert await racing is True
    finally:
        await migrated_pool.release(held)


async def test_an_event_needs_its_session_and_a_known_kind(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await repo.append(S1, 1, "plan", {}, limit=LIMIT)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    with pytest.raises(asyncpg.CheckViolationError):
        await repo.append(S1, 1, "request_permission", {}, limit=LIMIT)
    with pytest.raises(asyncpg.CheckViolationError):
        await repo.append(S1, 0, "plan", {}, limit=LIMIT)


async def test_events_after_reads_in_seq_order_from_the_watermark(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    for seq in (3, 1, 2, 4):
        await repo.append(S1, seq, "agent_message", {"text": str(seq)}, limit=LIMIT)
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
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    await repo.append(S1, 1, "user_message", {"text": "hi"}, limit=LIMIT)
    async with owner_pool.acquire() as conn:
        with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
            await conn.execute(statement.format(t=table))
        assert await conn.fetchval("SELECT count(*) FROM acp_session_event") == 1


async def test_even_the_owner_cannot_rewrite_an_event(owner_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(owner_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    await repo.append(S1, 1, "user_message", {"text": "hi"}, limit=LIMIT)
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
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    await repo.create(S2, "/work", "agent", limit=LIMIT)
    await repo.append(S1, 1, "title", {"title": "first"}, limit=LIMIT)
    await repo.append(S1, 2, "title", {"title": "second"}, limit=LIMIT)
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
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    (record,) = await repo.list("agent", cwd=None, cursor=None, limit=10)
    assert record.title is None and record.closed is False
    assert record.updated_at.tzinfo is not None


async def test_list_is_scoped_to_the_creator(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work/a", "agent", limit=LIMIT)
    await repo.create(S2, "/work/b", "device", limit=LIMIT)
    await repo.create(_sid(3), "/work/b", "agent", limit=LIMIT)
    every = await repo.list("agent", cwd=None, cursor=None, limit=9)
    assert {r.session_id for r in every} == {S1, _sid(3)}
    mine = await repo.list("agent", cwd="/work/b", cursor=None, limit=9)
    assert [r.session_id for r in mine] == [_sid(3)]
    assert [r.session_id for r in await repo.list("device", cwd=None, cursor=None, limit=9)] == [S2]
    assert await repo.list("nobody", cwd=None, cursor=None, limit=9) == ()


async def test_create_reports_whether_it_kept_the_session_and_stops_at_the_cap(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    assert await repo.create(S1, "/work", "agent", limit=1) is True
    assert await repo.create(S1, "/work", "agent", limit=1) is False  # already kept
    assert await repo.create(S2, "/work", "agent", limit=1) is False  # the cap
    assert await repo.create(S2, "/work", "device", limit=1) is True  # each principal's own
    assert await repo.owner(S2) == ("device", "/work")


async def test_past_the_event_cap_an_append_is_refused_and_nothing_kept_changes(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    await repo.append(S1, 1, "user_message", {"text": "a"}, limit=2)
    await repo.append(S1, 2, "agent_message", {"text": "b"}, limit=2)
    with pytest.raises(AcpSessionLimitReached, match="session_events_max"):
        await repo.append(S1, 3, "closed", {}, limit=2)
    # A resend of a kept event is still answered as stored, and a different one at a kept seq
    # is still a conflict, never a cap.
    assert await repo.append(S1, 2, "agent_message", {"text": "b"}, limit=2) is True
    with pytest.raises(SessionEventConflict):
        await repo.append(S1, 2, "agent_message", {"text": "c"}, limit=2)
    assert [(e.seq, dict(e.payload)) for e in await repo.events_after(S1, 0, 10)] == [
        (1, {"text": "a"}),
        (2, {"text": "b"}),
    ]


async def test_the_event_cap_is_on_the_seq_so_it_costs_nothing_however_long_the_log(
    migrated_pool: asyncpg.Pool,
) -> None:
    """A seq past the cap is refused even when the log holds one event: the cap bounds the
    primary key, so it never counts the log."""
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    await repo.append(S1, 1, "user_message", {"text": "a"}, limit=5)
    with pytest.raises(AcpSessionLimitReached):
        await repo.append(S1, 6, "user_message", {"text": "b"}, limit=5)
    assert await repo.append(S1, 5, "user_message", {"text": "c"}, limit=5) is True


async def test_a_summary_reads_the_newest_seq_and_the_newest_of_each_state(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    empty = await repo.summary(S1)
    assert (empty.newest_seq, empty.mode, empty.attach, empty.title) == (0, None, None, None)
    for seq, kind, payload in (
        (1, "title", {"title": "first"}),
        (2, "mode", {"modeId": "observe"}),
        (3, "attach", {"projectId": "p1"}),
        (4, "mode", {"modeId": "drive"}),
        (5, "attach", {"projectId": "p2"}),
        (6, "user_message", {"text": "x"}),
    ):
        await repo.append(S1, seq, kind, payload, limit=LIMIT)
    summary = await repo.summary(S1)
    assert summary.newest_seq == 6
    assert dict(summary.mode or {}) == {"modeId": "drive"}
    assert dict(summary.attach or {}) == {"projectId": "p2"}
    assert dict(summary.title or {}) == {"title": "first"}


async def test_list_reads_each_sessions_newest_event_by_its_seq(
    migrated_pool: asyncpg.Pool, owner_pool: asyncpg.Pool
) -> None:
    """`updated_at` is the newest event's `recorded_at`: the event with the highest seq."""
    repo = PostgresAcpSessionRepository(migrated_pool)
    await repo.create(S1, "/work", "agent", limit=LIMIT)
    stamp = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
    async with owner_pool.acquire() as conn:
        for seq, kind, when in ((1, "user_message", stamp), (2, "closed", stamp + timedelta(1))):
            await conn.execute(
                "INSERT INTO acp_session_event (session_id, seq, kind, payload, recorded_at) "
                "VALUES ($1, $2, $3, '{}', $4)",
                S1,
                seq,
                kind,
                when,
            )
    (record,) = await repo.list("agent", cwd=None, cursor=None, limit=5)
    assert record.updated_at == stamp + timedelta(1) and record.closed is True
