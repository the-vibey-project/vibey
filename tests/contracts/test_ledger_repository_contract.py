# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contract test: InMemoryLedgerRepository behaves like PostgresLedgerRepository.

ONE body runs against the in-memory ledger and the real repository, so a fake that
drifts from the SQL fails here instead of letting a false-green through every test
that stands on it. Where the two disagree the fake is made faithful (it is the
reference only because it is the one that can be wrong). Each test names the source
of its expectation in a comment:

- ``ledger_repository.py``: ``ConnectionEventAppender.append`` (redact, digest the
  redacted payload, ``json.dumps`` it, call ``append_event``, read the row back) and
  the three readers' SQL;
- ``migrations/0002_event.sql`` / ``0009`` / ``0013``: ``append_event`` claims the
  next seq from the per-project ``event_seq`` counter in the same transaction as the
  insert; ``event_id`` is ``gen_random_uuid()``; ``produced_at`` is the draft's;
- ``migrations/0016`` / ``0017`` and ``infrastructure/db/ledger_guard.py``: the
  append-only guard (ADR-0055);
- ``domain/ledger_chain.py``: the derived hash chain; ``domain/ledger.py``:
  ``digest_event`` and ``open_items`` (a correction is a new event naming the one it
  supersedes; CLAUDE.md: "Corrections are new events that supersede prior ones").
"""

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from enum import IntEnum
from uuid import UUID, uuid4

import asyncpg
import pytest

from tests.db_roles import TestDatabaseRoles
from tests.fakes.ledger_repository import InMemoryLedgerRepository, LedgerRepository
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event, open_items
from vibey.domain.ledger_chain import LedgerChain
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.interfaces.class_contracts import PostgresLedgerRepositoryInterface
from vibey.infrastructure.ledger.redact import REDACTED

ROLES = TestDatabaseRoles.from_environ(os.environ)
AT = datetime(2026, 11, 11, 9, 30, 15, 123456, tzinfo=UTC)
LEDGER_METHODS = frozenset({"append", "range", "all_for_project", "latest_seq"})


class Level(IntEnum):
    HIGH = 3


@dataclass
class Ledger:
    """One repository plus the one setup move its interface lacks: a project to write
    to. ``event.project_id`` references ``project(id)`` (0002), so PostgreSQL needs a
    row; the fake keeps the same table as its ``projects`` set."""

    repo: LedgerRepository
    new_project: "NewProject"


class NewProject:
    def __init__(self, table: asyncpg.Pool | InMemoryLedgerRepository) -> None:
        self._table = table

    async def __call__(self) -> UUID:
        if isinstance(self._table, InMemoryLedgerRepository):
            project = uuid4()
            self._table.projects.add(project)
            return project
        name = f"ledger-contract-{uuid4()}"
        pid = await self._table.fetchval(
            "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) "
            "RETURNING id",
            name,
            f"/tmp/{name}",
        )
        return UUID(str(pid))


@pytest.fixture(params=["fake", "postgres"])
def ledger(request: pytest.FixtureRequest) -> Ledger:
    if request.param == "fake":
        fake = InMemoryLedgerRepository()
        return Ledger(fake, NewProject(fake))
    pool: asyncpg.Pool = request.getfixturevalue("migrated_pool")
    return Ledger(PostgresLedgerRepository(pool), NewProject(pool))


def draft(
    project_id: UUID,
    payload: dict[str, object] | None = None,
    *,
    kind: EventKind = EventKind.TURN_REQUESTED,
    produced_at: datetime = AT,
    **overrides: object,
) -> LedgerEventDraft:
    """A draft as a caller builds one: the digest over the payload it hands in."""
    body: dict[str, object] = {"n": 1} if payload is None else payload
    values: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": kind,
        "engine_id": None,
        "job_id": None,
        "causation_id": None,
        "correlation_id": UUID(int=7),
        "provenance": Provenance.AGENT,
        "produced_at": produced_at,
        "payload": body,
        "digest": digest_event(body),
    }
    values.update(overrides)
    return LedgerEventDraft(**values)  # type: ignore[arg-type]


async def append_n(ledger: Ledger, project_id: UUID, n: int) -> list[LedgerEvent]:
    return [await ledger.repo.append(draft(project_id, {"n": i})) for i in range(n)]


# --- the shape: append is the only write ----------------------------------------------


def test_the_repository_is_the_declared_interface_and_only_appends(ledger: Ledger) -> None:
    # class_contracts.py PostgresLedgerRepositoryInterface: append, range, all_for_project,
    # latest_seq -- and nothing that could rewrite or remove an event (CLAUDE.md: "The
    # ledger is append-only. No updates, no deletes.").
    assert isinstance(ledger.repo, PostgresLedgerRepositoryInterface)
    public = {
        name
        for name in dir(ledger.repo)
        if not name.startswith("_") and callable(getattr(ledger.repo, name))
    }
    assert public == LEDGER_METHODS


@pytest.mark.parametrize("table", ["event", "event_partitioned_0013_default"])
@pytest.mark.parametrize(
    "statement",
    ["UPDATE {t} SET digest = 'forged'", "DELETE FROM {t}", "TRUNCATE {t}"],
)
async def test_the_application_role_cannot_rewrite_the_ledger(
    migrated_pool: asyncpg.Pool, project_id: UUID, table: str, statement: str
) -> None:
    # 0016/0017 + ledger_guard.py, as tests/infrastructure/db/test_ledger_guard.py holds
    # them: the application role holds no UPDATE, DELETE or TRUNCATE on the ledger
    # ("permission denied"). When the suite runs as one role the application IS the
    # owner, and the guard's triggers refuse instead -- the same error class either way,
    # so this test holds in both set-ups and never skips.
    repo = PostgresLedgerRepository(migrated_pool)
    await repo.append(draft(project_id))
    before = await repo.all_for_project(project_id)
    refusal = "permission denied" if ROLES.split else "the ledger is append-only"
    async with migrated_pool.acquire() as conn:
        with pytest.raises(asyncpg.InsufficientPrivilegeError, match=refusal):
            await conn.execute(statement.format(t=table))
    assert await repo.all_for_project(project_id) == before


async def test_a_returned_event_cannot_change_the_ledger(ledger: Ledger) -> None:
    # ledger_repository.py: every read builds a fresh LedgerEvent from the row
    # (`json.loads(row["payload"])`), so whatever a caller does to a returned payload,
    # the stored event is untouched. The same holds for the draft handed to append.
    project = await ledger.new_project()
    body: dict[str, object] = {"n": 1, "items": [1, 2]}
    sent = draft(project, body)
    appended = await ledger.repo.append(sent)
    body["n"] = 99
    assert isinstance(appended.payload, dict)
    appended.payload["n"] = 98
    (read,) = await ledger.repo.all_for_project(project)
    assert isinstance(read.payload, dict)
    read.payload["items"] = []
    assert (await ledger.repo.all_for_project(project))[0].payload == {"n": 1, "items": [1, 2]}


# --- seq --------------------------------------------------------------------------------


async def test_seq_starts_at_one_and_is_contiguous_per_project(ledger: Ledger) -> None:
    # append_event: the per-project `event_seq` counter starts the project at 1
    # (`VALUES (p_project_id, 2) ... RETURNING next_seq - 1`) and adds one per append.
    project = await ledger.new_project()
    events = await append_n(ledger, project, 4)
    assert [e.seq for e in events] == [1, 2, 3, 4]


async def test_seq_is_independent_across_projects(ledger: Ledger) -> None:
    # append_event: `event_seq` is keyed by project_id, so interleaved appends to two
    # projects each count from 1 on their own.
    first, second = await ledger.new_project(), await ledger.new_project()
    seqs = [
        (await ledger.repo.append(draft(project, {"i": i}))).seq
        for i, project in enumerate([first, second, first, first, second])
    ]
    assert seqs == [1, 1, 2, 3, 2]
    assert [e.seq for e in await ledger.repo.all_for_project(first)] == [1, 2, 3]
    assert [e.seq for e in await ledger.repo.all_for_project(second)] == [1, 2]
    # latest_seq: `max(seq) ... WHERE project_id = $1` -- this project's, not the table's.
    assert (await ledger.repo.latest_seq(first), await ledger.repo.latest_seq(second)) == (3, 2)


async def test_a_payload_json_cannot_carry_is_refused_and_claims_no_seq(ledger: Ledger) -> None:
    # ConnectionEventAppender.append: `json.dumps(redacted_payload)` is evaluated as an
    # argument before `append_event` runs, so the TypeError comes before any seq is
    # claimed; the next append still gets 1. (digest_event uses `default=str` and would
    # have accepted it -- the refusal is json.dumps', not the digest's.)
    project = await ledger.new_project()
    with pytest.raises(TypeError):
        await ledger.repo.append(draft(project, {"x": object()}))
    assert await ledger.repo.latest_seq(project) == 0
    assert (await ledger.repo.append(draft(project))).seq == 1


async def test_an_append_to_a_project_that_does_not_exist_is_refused(ledger: Ledger) -> None:
    # 0002: `event_seq.project_id REFERENCES project(id)` -- append_event's first insert
    # (into event_seq) is refused, and the transaction claims no seq. Probed 2026-11-11:
    # ForeignKeyViolationError, `violates foreign key constraint "event_seq_project_id_fkey"`.
    stranger = uuid4()
    with pytest.raises(asyncpg.ForeignKeyViolationError, match="event_seq_project_id_fkey"):
        await ledger.repo.append(draft(stranger))
    assert await ledger.repo.latest_seq(stranger) == 0
    assert await ledger.repo.all_for_project(stranger) == ()


@pytest.mark.parametrize(
    "payload",
    [{"s": "a\x00b"}, {"nested": ["ok", {"k": "\x00"}]}, {"key\x00": 1}],
    ids=["value", "nested", "key"],
)
async def test_a_nul_character_is_refused_and_claims_no_seq(
    ledger: Ledger, payload: dict[str, object]
) -> None:
    # jsonb cannot hold U+0000 (`text` cannot): psql `select '{"a\u0000": 1}'::jsonb` and
    # the append itself (probed 2026-11-11) fail with "unsupported Unicode escape
    # sequence", SQLSTATE 22P05, asyncpg.UntranslatableCharacterError.
    project = await ledger.new_project()
    with pytest.raises(asyncpg.UntranslatableCharacterError, match="unsupported Unicode escape"):
        await ledger.repo.append(draft(project, payload))
    assert await ledger.repo.latest_seq(project) == 0
    assert (await ledger.repo.append(draft(project))).seq == 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
async def test_a_non_finite_number_is_refused_and_claims_no_seq(
    ledger: Ledger, value: float
) -> None:
    # json.dumps writes NaN / Infinity / -Infinity, which JSON (and so jsonb) has no token
    # for: "invalid input syntax for type json", SQLSTATE 22P02,
    # asyncpg.InvalidTextRepresentationError (probed 2026-11-11).
    project = await ledger.new_project()
    with pytest.raises(asyncpg.InvalidTextRepresentationError, match="type json"):
        await ledger.repo.append(draft(project, {"x": value}))
    assert await ledger.repo.latest_seq(project) == 0
    assert (await ledger.repo.append(draft(project))).seq == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="jsonb rewrites 1e+16 / -0.0 after the repository digested Python's rendering, "
    "so the stored digest no longer matches the stored payload; see the follow-up issue",
)
@pytest.mark.parametrize("value", [1e16, 1e20, -0.0], ids=["1e16", "1e20", "minus-zero"])
async def test_a_float_jsonb_rewrites_still_verifies_in_postgres(
    migrated_pool: asyncpg.Pool, project_id: UUID, value: float
) -> None:
    # ConnectionEventAppender.append digests `redacted_payload` as Python renders it
    # (`json.dumps(1e16)` is `1e+16`, of -0.0 is `-0.0`), but jsonb stores and returns
    # 10000000000000000 (an int, once json.loads reads it) and 0.0. The stored digest is then
    # not the digest of the stored payload, and LedgerChain.verify reports
    # DIGEST_MISMATCH on the real ledger. PostgreSQL only: the fake keeps the float, which
    # is what the ledger promises. Flips loudly (strict) the day the repository is fixed.
    repo = PostgresLedgerRepository(migrated_pool)
    await repo.append(draft(project_id, {"x": value}))
    events = await repo.all_for_project(project_id)
    verified = LedgerChain().verify(project_id, events)
    assert verified.ok, verified.findings


# --- what an event holds ------------------------------------------------------------------


async def test_append_returns_exactly_what_the_readers_return(ledger: Ledger) -> None:
    # ConnectionEventAppender.append reads the row back (`SELECT * FROM event WHERE
    # project_id = $1 AND seq = $2`) and maps it with the same EVENT_ROWS the readers use.
    project = await ledger.new_project()
    job, cause = uuid4(), uuid4()
    appended = await ledger.repo.append(
        draft(
            project,
            {"path": "a.py", "lines": [1, 2], "nested": {"ok": True, "none": None}},
            kind=EventKind.FILE_EDITED,
            cycle=3,
            phase=Phase.REVIEW,
            engine_id=EngineId.CLAUDELOOP,
            job_id=job,
            causation_id=cause,
            provenance=Provenance.TRUSTED,
        )
    )
    assert (await ledger.repo.all_for_project(project)) == (appended,)
    assert (await ledger.repo.range(project, from_seq=1, to_seq=1)) == (appended,)
    assert (appended.cycle, appended.phase, appended.kind) == (
        3,
        Phase.REVIEW,
        EventKind.FILE_EDITED,
    )
    assert (appended.engine_id, appended.job_id, appended.causation_id) == (
        EngineId.CLAUDELOOP,
        job,
        cause,
    )
    assert appended.provenance is Provenance.TRUSTED
    assert appended.payload == {
        "path": "a.py",
        "lines": [1, 2],
        "nested": {"ok": True, "none": None},
    }
    # 0002: `event_id uuid ... DEFAULT gen_random_uuid()` -- minted per event.
    other = await ledger.repo.append(draft(project))
    assert other.event_id != appended.event_id


async def test_the_stored_digest_is_the_redacted_payloads_never_the_drafts(
    ledger: Ledger,
) -> None:
    # ConnectionEventAppender.append: "the digest is recomputed over what actually lands
    # in the column -- never over the pre-redaction payload the caller built the draft
    # from" (redact.py: a sensitive key name, or a vendor-shaped secret in any string).
    project = await ledger.new_project()
    secret = "sk-" + "A" * 24
    sent = draft(project, {"api_key": "hunter2", "note": f"key {secret}", "n": 1})
    event = await ledger.repo.append(sent)
    assert event.payload == {"api_key": REDACTED, "note": f"key {REDACTED}", "n": 1}
    assert event.digest == digest_event(event.payload)
    assert event.digest != sent.digest


async def test_a_tuple_in_the_payload_comes_back_as_a_list(ledger: Ledger) -> None:
    # redact.py `_redact_value`: a list or tuple is rebuilt as a list; jsonb has no tuple.
    project = await ledger.new_project()
    event = await ledger.repo.append(draft(project, {"pair": (1, "two")}))
    assert event.payload == {"pair": [1, "two"]}


async def test_the_payload_comes_back_as_plain_json_values(ledger: Ledger) -> None:
    # ConnectionEventAppender.append stores `json.dumps(redacted_payload)` in a jsonb
    # column and EventRowMapper reads it back with `json.loads`: an int-valued enum the
    # caller put in comes back as the plain int, so `payload[...] is Level.HIGH` is False.
    project = await ledger.new_project()
    event = await ledger.repo.append(draft(project, {"level": Level.HIGH}))
    (read,) = await ledger.repo.all_for_project(project)
    for got in (event, read):
        assert got.payload == {"level": 3}
        assert type(got.payload["level"]) is int


async def test_produced_at_is_the_drafts_instant_returned_in_utc(ledger: Ledger) -> None:
    # 0009: the 12-argument append_event stores `p_produced_at`, never insertion time;
    # asyncpg decodes timestamptz as an aware UTC datetime.
    project = await ledger.new_project()
    india = timezone(timedelta(hours=5, minutes=30))
    sent = AT.astimezone(india)
    event = await ledger.repo.append(draft(project, produced_at=sent))
    assert event.produced_at == AT
    assert event.produced_at.utcoffset() == timedelta(0)
    assert event.produced_at.isoformat() == AT.isoformat()


async def test_a_naive_produced_at_is_read_as_this_hosts_local_time(ledger: Ledger) -> None:
    # asyncpg encodes a naive datetime bound to a timestamptz parameter as the host's
    # local time (Python's `astimezone()` of a naive instant), whatever the session's
    # TimeZone; probed 2026-11-11 under TZ=UTC and the host's EST.
    project = await ledger.new_project()
    naive = datetime(2026, 1, 1, 12, 0, 0, 123456)
    event = await ledger.repo.append(draft(project, produced_at=naive))
    assert event.produced_at == naive.astimezone(UTC)
    assert event.produced_at.tzinfo == UTC


# --- the readers --------------------------------------------------------------------------


async def test_range_is_the_inclusive_slice_of_all_for_project(ledger: Ledger) -> None:
    # range: `seq BETWEEN $2 AND $3 ORDER BY seq` -- inclusive at both ends, empty when
    # the bounds are reversed or miss the ledger.
    project = await ledger.new_project()
    await append_n(ledger, project, 5)
    everything = await ledger.repo.all_for_project(project)
    for low in range(-1, 8):
        for high in range(-1, 8):
            got = await ledger.repo.range(project, from_seq=low, to_seq=high)
            assert got == tuple(e for e in everything if low <= e.seq <= high), (low, high)


async def test_latest_seq_is_the_number_of_events(ledger: Ledger) -> None:
    # latest_seq: `max(seq)`, and 0 when the project has none.
    project = await ledger.new_project()
    assert await ledger.repo.latest_seq(project) == 0
    assert await ledger.repo.all_for_project(project) == ()
    assert await ledger.repo.range(project, from_seq=1, to_seq=10) == ()
    for n in range(1, 4):
        await ledger.repo.append(draft(project))
        assert (
            await ledger.repo.latest_seq(project)
            == n
            == len(await ledger.repo.all_for_project(project))
        )


async def test_a_project_never_written_reads_as_empty(ledger: Ledger) -> None:
    # Every reader filters `WHERE project_id = $1`; nothing matches an unknown id.
    stranger = uuid4()
    assert await ledger.repo.all_for_project(stranger) == ()
    assert await ledger.repo.range(stranger, from_seq=0, to_seq=99) == ()
    assert await ledger.repo.latest_seq(stranger) == 0


# --- the chain and corrections ------------------------------------------------------------


async def test_the_hash_chain_verifies_over_all_for_project(ledger: Ledger) -> None:
    # ledger_chain.py LedgerChain.verify: contiguous seqs from 1, every digest the digest
    # of its payload -- no findings, one link per event.
    project = await ledger.new_project()
    await append_n(ledger, project, 3)
    await ledger.repo.append(draft(project, {"token": "x"}))
    events = await ledger.repo.all_for_project(project)
    verified = LedgerChain().verify(project, events)
    assert verified.ok, verified.findings
    assert [link.seq for link in verified.links] == [1, 2, 3, 4]
    # A window verifies too, anchored on the link before it (ledger_chain.py docstring).
    window = await ledger.repo.range(project, from_seq=3, to_seq=4)
    tail = LedgerChain().verify(project, window, prev_link=verified.links[1].link)
    assert tail.ok and tail.head == verified.head


async def test_a_correction_supersedes_without_mutating_the_original(ledger: Ledger) -> None:
    # CLAUDE.md: "Corrections are new events that supersede prior ones." ledger.py
    # open_items: a DecisionRecorded naming `supersedes` closes the decision it names.
    project = await ledger.new_project()
    original = await ledger.repo.append(
        draft(
            project, {"decision_id": "d1", "text": "use SQLite"}, kind=EventKind.DECISION_RECORDED
        )
    )
    correction = await ledger.repo.append(
        draft(
            project,
            {"decision_id": "d2", "text": "use PostgreSQL", "supersedes": "d1"},
            kind=EventKind.DECISION_RECORDED,
            causation_id=original.event_id,
        )
    )
    events = await ledger.repo.all_for_project(project)
    assert events == (original, correction)
    assert open_items(events, EventKind.DECISION_RECORDED) == ("d2",)
    assert LedgerChain().verify(project, events).ok
