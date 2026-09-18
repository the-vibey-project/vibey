# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`LedgerSearch` over real Postgres: every criterion in SQL, every value bound."""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.interfaces import LedgerSearch
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_query import (
    SELF_ACTOR,
    Actor,
    ActorScope,
    LedgerQuery,
)
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import (
    EventRowMapperInterface,
    LedgerSearchCompilerInterface,
    SearchStatementInterface,
)
from vibey.infrastructure.db.ledger_repository import EVENT_ROWS, PostgresLedgerRepository
from vibey.infrastructure.db.ledger_search_repository import (
    LEDGER_SEARCH_SQL,
    LedgerSearchCompiler,
    PostgresLedgerSearchRepository,
)
from vibey.infrastructure.engines.tailer import LedgerEventDraft

T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _draft(
    project_id: UUID,
    *,
    at: int,
    kind: EventKind = EventKind.TURN_COMPLETED,
    engine_id: EngineId | None = EngineId.CLAUDELOOP,
    provenance: Provenance = Provenance.AGENT,
    payload: Mapping[str, object] | None = None,
) -> LedgerEventDraft:
    body = dict(payload) if payload is not None else {"minute": at}
    return LedgerEventDraft(
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        kind=kind,
        engine_id=engine_id,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,
        provenance=provenance,
        produced_at=T0 + timedelta(minutes=at),
        payload=body,
        digest=digest_event(body),
    )


async def _seed(pool: asyncpg.Pool, project_id: UUID) -> list[LedgerEvent]:
    """Six events, one per minute from T0, each distinguishable on one axis."""
    ledger = PostgresLedgerRepository(pool)
    drafts = [
        _draft(project_id, at=0, kind=EventKind.QUESTION_ASKED, engine_id=None,
               provenance=Provenance.TRUSTED, payload={"text": "What is the GOAL?"}),
        _draft(project_id, at=1, kind=EventKind.ANSWER_GIVEN, engine_id=None,
               provenance=Provenance.TRUSTED, payload={}),
        _draft(project_id, at=2, engine_id=EngineId.CODEXLOOP, payload={"note": "100% done"}),
        _draft(project_id, at=3, payload={"note": "1000 done"}),
        _draft(project_id, at=4, kind=EventKind.FINDING_RAISED, provenance=Provenance.UNTRUSTED,
               payload={}),
        _draft(project_id, at=5, kind=EventKind.FINDING_RESOLVED, payload={"path": "a_b\\c"}),
    ]  # fmt: skip
    return [await ledger.append(draft) for draft in drafts]


async def _seqs(pool: asyncpg.Pool, project_id: UUID, query: LedgerQuery) -> list[int]:
    result = await PostgresLedgerSearchRepository(pool).search(project_id, query)
    return [event.seq for event in result.events]


# -- the compiler, without a database --------------------------------------


def test_no_criteria_is_the_project_newest_first() -> None:
    project_id = uuid4()
    statement = LedgerSearchCompiler().compile(project_id, LedgerQuery(), fetch=51)
    assert statement.sql == "SELECT * FROM event WHERE project_id = $1 ORDER BY seq DESC LIMIT $2"
    assert statement.args == (project_id, 51)


def test_every_criterion_is_a_placeholder_and_every_value_an_argument() -> None:
    project_id, event_id = uuid4(), uuid4()
    digest = digest_event({})
    query = LedgerQuery(
        event_id=event_id,
        digest=digest,
        actor=Actor(ActorScope.ENGINE, "codexloop"),
        since=T0,
        until=T0 + timedelta(hours=1),
        kinds=frozenset({EventKind.FINDING_RESOLVED, EventKind.FINDING_RAISED}),
        text="50%",
        limit=3,
    )
    statement = LedgerSearchCompiler().compile(project_id, query, fetch=4)

    assert statement.sql == (
        "SELECT * FROM event WHERE project_id = $1 AND event_id = $2 AND digest = $3"
        " AND engine_id = $4 AND produced_at >= $5 AND produced_at < $6"
        " AND kind = ANY($7::text[]) AND payload::text ILIKE $8 ESCAPE '\\'"
        " ORDER BY seq DESC LIMIT $9"
    )
    assert statement.args == (
        project_id,
        event_id,
        digest,
        "codexloop",
        T0,
        T0 + timedelta(hours=1),
        ["FindingRaised", "FindingResolved"],
        "%50\\%%",
        4,
    )


_ACTOR_CLAUSES = {
    ActorScope.ENGINE: ("engine_id = $2", ("x",)),
    ActorScope.PROVENANCE: ("provenance = $2::provenance", ("x",)),
    ActorScope.SELF: ("engine_id IS NULL", ()),
}


@pytest.mark.parametrize("scope", list(ActorScope))
def test_every_actor_scope_has_its_own_clause(scope: ActorScope) -> None:
    """A scope added to the domain without a clause here fails with KeyError --
    the compiler would otherwise read it as a provenance."""
    clause, bound = _ACTOR_CLAUSES[scope]
    project_id = uuid4()
    query = LedgerQuery(actor=Actor(scope, "x"))
    statement = LedgerSearchCompiler().compile(project_id, query, fetch=2)
    assert f"WHERE project_id = $1 AND {clause} ORDER BY" in statement.sql
    assert statement.args == (project_id, *bound, 2)


@pytest.mark.parametrize(
    ("needle", "pattern"),
    [
        ("plain", "%plain%"),
        ("50%", "%50\\%%"),
        ("a_b", "%a\\_b%"),
        ("back\\slash", "%back\\\\slash%"),
    ],
)
def test_the_needle_is_matched_literally(needle: str, pattern: str) -> None:
    assert LedgerSearchCompiler.contains_pattern(needle) == pattern


def test_nothing_a_searcher_types_reaches_the_sql_text() -> None:
    hostile = "'; DROP TABLE event; --"
    statement = LedgerSearchCompiler().compile(uuid4(), LedgerQuery(text=hostile), fetch=2)
    assert hostile not in statement.sql
    assert "DROP" not in statement.sql
    assert f"%{hostile}%" in statement.args


def test_the_seams_are_satisfied() -> None:
    statement = LEDGER_SEARCH_SQL.compile(uuid4(), LedgerQuery(), fetch=1)
    assert isinstance(LEDGER_SEARCH_SQL, LedgerSearchCompilerInterface)
    assert isinstance(statement, SearchStatementInterface)
    assert isinstance(EVENT_ROWS, EventRowMapperInterface)


# -- against Postgres -------------------------------------------------------


async def test_the_repository_is_the_application_port(migrated_pool: asyncpg.Pool) -> None:
    assert isinstance(PostgresLedgerSearchRepository(migrated_pool), LedgerSearch)


async def test_no_criteria_returns_the_latest_events_oldest_first(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    events = await _seed(migrated_pool, project_id)
    result = await PostgresLedgerSearchRepository(migrated_pool).search(project_id, LedgerQuery())

    assert result.events == tuple(events)
    assert result.truncated is False


async def test_the_limit_keeps_the_latest_and_says_older_ones_were_cut(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _seed(migrated_pool, project_id)
    repo = PostgresLedgerSearchRepository(migrated_pool)

    cut = await repo.search(project_id, LedgerQuery(limit=2))
    exact = await repo.search(project_id, LedgerQuery(limit=6))

    assert [e.seq for e in cut.events] == [5, 6]
    assert cut.truncated is True
    assert len(exact.events) == 6
    assert exact.truncated is False


async def test_by_record_id(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    events = await _seed(migrated_pool, project_id)
    assert await _seqs(migrated_pool, project_id, LedgerQuery(event_id=events[3].event_id)) == [4]
    assert await _seqs(migrated_pool, project_id, LedgerQuery(event_id=uuid4())) == []


async def test_a_digest_matches_every_record_with_that_payload(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _seed(migrated_pool, project_id)
    empty = LedgerQuery(digest=digest_event({}))
    assert await _seqs(migrated_pool, project_id, empty) == [2, 5]


@pytest.mark.parametrize(
    ("actor", "seqs"),
    [
        (Actor(ActorScope.ENGINE, "claudeloop"), [4, 5, 6]),
        (Actor(ActorScope.ENGINE, "codexloop"), [3]),
        (Actor(ActorScope.SELF, SELF_ACTOR), [1, 2]),
        (Actor(ActorScope.PROVENANCE, "trusted"), [1, 2]),
        (Actor(ActorScope.PROVENANCE, "untrusted"), [5]),
    ],
)
async def test_by_actor(
    migrated_pool: asyncpg.Pool, project_id: UUID, actor: Actor, seqs: list[int]
) -> None:
    await _seed(migrated_pool, project_id)
    assert await _seqs(migrated_pool, project_id, LedgerQuery(actor=actor)) == seqs


async def test_the_time_window_is_half_open(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    await _seed(migrated_pool, project_id)
    window = LedgerQuery(since=T0 + timedelta(minutes=1), until=T0 + timedelta(minutes=3))
    assert await _seqs(migrated_pool, project_id, window) == [2, 3]
    assert await _seqs(migrated_pool, project_id, LedgerQuery(since=T0 + timedelta(minutes=5))) == [
        6
    ]
    assert await _seqs(migrated_pool, project_id, LedgerQuery(until=T0 + timedelta(minutes=1))) == [
        1
    ]


async def test_any_of_several_kinds(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    await _seed(migrated_pool, project_id)
    findings = LedgerQuery(kinds=frozenset({EventKind.FINDING_RAISED, EventKind.FINDING_RESOLVED}))
    assert await _seqs(migrated_pool, project_id, findings) == [5, 6]


async def test_text_is_case_insensitive(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    await _seed(migrated_pool, project_id)
    assert await _seqs(migrated_pool, project_id, LedgerQuery(text="goal")) == [1]
    assert await _seqs(migrated_pool, project_id, LedgerQuery(text="nowhere")) == []


async def test_wildcards_in_the_text_are_literal(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _seed(migrated_pool, project_id)
    # Unescaped, "100%" would also match "1000 done", and "a_b" any "a?b".
    assert await _seqs(migrated_pool, project_id, LedgerQuery(text="100%")) == [3]
    assert await _seqs(migrated_pool, project_id, LedgerQuery(text="a_b")) == [6]


async def test_a_hostile_needle_is_just_text(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    await _seed(migrated_pool, project_id)
    hostile = LedgerQuery(text="'); DELETE FROM project; --")
    assert await _seqs(migrated_pool, project_id, hostile) == []
    assert len(await _seqs(migrated_pool, project_id, LedgerQuery())) == 6


async def test_criteria_combine_with_and(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    await _seed(migrated_pool, project_id)
    query = LedgerQuery(actor=Actor(ActorScope.ENGINE, "claudeloop"), text="done")
    assert await _seqs(migrated_pool, project_id, query) == [4]


async def test_a_search_never_crosses_into_another_project(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _seed(migrated_pool, project_id)
    async with migrated_pool.acquire() as conn:
        other = await conn.fetchval(
            "INSERT INTO project (name, repo_path, config) "
            "VALUES ('other', '/tmp/other', '{}'::jsonb) RETURNING id"
        )
    other_id = UUID(str(other))
    await _seed(migrated_pool, other_id)

    everything = await PostgresLedgerSearchRepository(migrated_pool).search(
        project_id, LedgerQuery(digest=digest_event({}))
    )
    assert {e.project_id for e in everything.events} == {project_id}


async def test_the_search_indexes_exist(migrated_pool: asyncpg.Pool) -> None:
    async with migrated_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'event'"
        )
    definitions = {row["indexname"]: row["indexdef"] for row in rows}
    assert "(digest)" in definitions["event_digest"]
    assert "(project_id, produced_at)" in definitions["event_project_produced_at"]
    assert "(project_id, engine_id, seq)" in definitions["event_project_engine"]


async def test_a_substituted_compiler_and_row_mapper_are_used(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    events = await _seed(migrated_pool, project_id)
    seen: list[str] = []

    class _Rows:
        def to_event(self, row: asyncpg.Record) -> LedgerEvent:
            seen.append(str(row["event_id"]))
            return EVENT_ROWS.to_event(row)

    class _OnlyTheFirst:
        def compile(
            self, project_id: UUID, query: LedgerQuery, *, fetch: int
        ) -> SearchStatementInterface:
            return LedgerSearchCompiler().compile(
                project_id, LedgerQuery(event_id=events[0].event_id), fetch=fetch
            )

    repo = PostgresLedgerSearchRepository(migrated_pool, compiler=_OnlyTheFirst(), rows=_Rows())
    result = await repo.search(project_id, LedgerQuery())

    assert [e.seq for e in result.events] == [1]
    assert seen == [str(events[0].event_id)]
