# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.domain.ledger import (
    EventKind,
    Provenance,
    UnrecognizedEventKind,
    digest_event,
    digest_range,
)
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _draft(project_id: UUID, **overrides: object) -> LedgerEventDraft:
    payload = {"prompt_digest": "abc"}
    defaults: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": EventKind.TURN_REQUESTED,
        "engine_id": None,
        "job_id": None,
        "causation_id": None,
        "correlation_id": uuid4(),
        "provenance": Provenance.AGENT,
        "produced_at": NOW,
        "payload": payload,
        "digest": digest_event(payload),
    }
    defaults.update(overrides)
    return LedgerEventDraft(**defaults)  # type: ignore[arg-type]


async def test_append_assigns_seq_starting_at_one(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresLedgerRepository(migrated_pool)

    event = await repo.append(_draft(project_id))

    assert event.seq == 1
    assert event.project_id == project_id
    assert event.produced_at == NOW


async def test_append_seq_increments_sequentially(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresLedgerRepository(migrated_pool)

    e1 = await repo.append(_draft(project_id))
    e2 = await repo.append(_draft(project_id))
    e3 = await repo.append(_draft(project_id))

    assert [e1.seq, e2.seq, e3.seq] == [1, 2, 3]


async def test_seq_is_scoped_per_project(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresLedgerRepository(migrated_pool)
    async with migrated_pool.acquire() as conn:
        p1 = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) "
            "VALUES ('a','/a','{}'::jsonb) RETURNING id"
        )
        p2 = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) "
            "VALUES ('b','/b','{}'::jsonb) RETURNING id"
        )

    e1 = await repo.append(_draft(UUID(str(p1))))
    e2 = await repo.append(_draft(UUID(str(p2))))

    assert e1.seq == 1
    assert e2.seq == 1


async def test_range_returns_events_in_seq_order(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresLedgerRepository(migrated_pool)
    for _ in range(5):
        await repo.append(_draft(project_id))

    events = await repo.range(project_id, from_seq=2, to_seq=4)

    assert [e.seq for e in events] == [2, 3, 4]


async def test_latest_seq_reflects_appends(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    repo = PostgresLedgerRepository(migrated_pool)
    assert await repo.latest_seq(project_id) == 0

    await repo.append(_draft(project_id))
    await repo.append(_draft(project_id))

    assert await repo.latest_seq(project_id) == 2


async def test_planted_secret_never_reaches_the_column(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresLedgerRepository(migrated_pool)
    planted = "sk-" + "z" * 20
    draft = _draft(project_id, payload={"summary": f"logged in with {planted}"})

    event = await repo.append(draft)

    assert planted not in str(event.payload)
    async with migrated_pool.acquire() as conn:
        raw = await conn.fetchval(
            "SELECT payload::text FROM event WHERE event_id = $1", event.event_id
        )
    assert planted not in raw


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE event SET kind = 'PhaseTransitioned' WHERE event_id = $1",
        "DELETE FROM event WHERE event_id = $1",
    ],
)
async def test_a_rewrite_of_an_event_is_refused_even_for_the_owner(
    migrated_pool: asyncpg.Pool, owner_pool: asyncpg.Pool, project_id: UUID, statement: str
) -> None:
    """It used to be a silent no-op (a `DO INSTEAD NOTHING` rule). Now it is refused
    loudly, by a trigger, for every role (ADR-0055)."""
    repo = PostgresLedgerRepository(migrated_pool)
    event = await repo.append(_draft(project_id))

    async with owner_pool.acquire() as conn:
        with pytest.raises(asyncpg.InsufficientPrivilegeError, match="append-only"):
            await conn.execute(statement, event.event_id)
        row = await conn.fetchrow("SELECT kind FROM event WHERE event_id = $1", event.event_id)

    assert row is not None
    assert row["kind"] == EventKind.TURN_REQUESTED.value


async def test_to_drafts_round_trips_persisted_events(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    from vibey.infrastructure.db.ledger_repository import to_drafts

    repo = PostgresLedgerRepository(migrated_pool)
    await repo.append(_draft(project_id))
    await repo.append(_draft(project_id, kind=EventKind.SESSION_SEEDED))

    events = await repo.all_for_project(project_id)
    drafts = to_drafts(events)

    assert len(drafts) == 2
    assert drafts[0].project_id == project_id
    assert drafts[0].kind == EventKind.TURN_REQUESTED
    assert drafts[1].kind == EventKind.SESSION_SEEDED


async def test_append_raises_lookup_error_when_fetchrow_returns_none() -> None:
    class _NullConn:
        async def fetchval(self, *a: object, **kw: object) -> int:
            return 42

        async def fetchrow(self, *a: object, **kw: object) -> None:
            return None

        def transaction(self) -> "_NullTx":
            return _NullTx()

    class _NullTx:
        async def __aenter__(self) -> "_NullTx":
            return self

        async def __aexit__(self, *a: object) -> None:
            pass

    class _NullPool:
        def acquire(self) -> "_NullPool":
            return self

        async def __aenter__(self) -> _NullConn:
            return _NullConn()

        async def __aexit__(self, *a: object) -> None:
            pass

    from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository

    repo = PostgresLedgerRepository(_NullPool())  # type: ignore[arg-type]
    with pytest.raises(LookupError, match="append_event returned seq 42"):
        await repo.append(_draft(uuid4()))


@pytest.mark.slow
async def test_concurrent_appends_are_gapless_and_have_no_duplicates(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """4.1's concurrency test: 100 parallel appends produce exactly the
    sequence 1..100 with no gaps and no duplicates."""
    repo = PostgresLedgerRepository(migrated_pool)

    results = await asyncio.gather(*(repo.append(_draft(project_id)) for _ in range(100)))

    seqs = sorted(e.seq for e in results)
    assert seqs == list(range(1, 101))


# -- a kind a newer vibey wrote (vibey#275) ----------------------------------


async def _append_as_a_newer_vibey(
    pool: asyncpg.Pool, project_id: UUID, kind: str, payload: dict[str, object]
) -> int:
    """What a newer vibey's appender does, through the same SQL function -- the
    one way a row this vibey has no `EventKind` for can reach the table."""
    import json

    async with pool.acquire() as conn:
        seq = await conn.fetchval(
            "SELECT append_event($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb, $12)",
            project_id,
            1,
            Phase.BUILD.value,
            kind,
            "claudeloop",
            None,
            None,
            project_id,
            Provenance.AGENT.value,
            NOW,
            json.dumps(payload),
            digest_event(payload),
        )
    assert isinstance(seq, int)
    return seq


async def test_a_row_of_a_kind_this_vibey_does_not_know_reads_back_intact(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The rolling-upgrade crash: `EventKind("FutureKindX")` used to raise, so
    one newer row made the whole project ledger unreadable to this worker."""
    repo = PostgresLedgerRepository(migrated_pool)
    before = await repo.append(_draft(project_id))
    payload = {"transcript_ref": "runs/1/t.jsonl", "tokens": 1234}
    seq = await _append_as_a_newer_vibey(migrated_pool, project_id, "FutureKindX", payload)
    after = await repo.append(_draft(project_id, kind=EventKind.SESSION_SEEDED))

    events = await repo.all_for_project(project_id)

    assert [e.seq for e in events] == [before.seq, seq, after.seq]
    stranger = events[1]
    assert stranger.kind == UnrecognizedEventKind("FutureKindX")
    assert stranger.payload == payload
    assert stranger.digest == digest_event(payload)
    assert stranger.phase is Phase.BUILD
    assert stranger.engine_id is not None
    assert stranger.engine_id.value == "claudeloop"
    assert stranger.correlation_id == project_id
    assert stranger.produced_at == NOW
    # A window over it reads it too, and folds to the digest of the full read.
    window = await repo.range(project_id, from_seq=1, to_seq=3)
    assert window == events
    assert digest_range(window) == digest_range(events)
    assert await repo.latest_seq(project_id) == 3


async def test_to_drafts_refuses_to_re_append_a_kind_this_vibey_does_not_know(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Writers stay strict: vibey reads a newer kind but never writes one."""
    from vibey.infrastructure.db.ledger_repository import to_drafts

    repo = PostgresLedgerRepository(migrated_pool)
    await _append_as_a_newer_vibey(migrated_pool, project_id, "FutureKindX", {})

    events = await repo.all_for_project(project_id)

    with pytest.raises(ValueError, match="'FutureKindX', which this vibey does not know"):
        to_drafts(events)
