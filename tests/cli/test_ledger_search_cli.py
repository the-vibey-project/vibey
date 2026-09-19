# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey ledger search`, end to end against real Postgres."""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.bootstrap import build_app, database_url
from vibey.cli.interfaces import (
    LedgerSearchCommandInterface,
    LedgerSearchPresenterInterface,
    TimeBoundParserInterface,
)
from vibey.cli.ledger_search import (
    LEDGER_SEARCH,
    PRESENTER,
    TIME_BOUNDS,
    LedgerSearchPresenter,
    TimeBoundParser,
)
from vibey.cli.main import app
from vibey.domain.engine import EngineId
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    Provenance,
    UnrecognizedEventKind,
    digest_event,
)
from vibey.domain.ledger_query import InvalidLedgerQuery, LedgerSearchResult
from vibey.domain.phase import Phase
from vibey.infrastructure.engines.tailer import LedgerEventDraft

pytestmark = pytest.mark.integration
# See tests/cli/test_operational_commands.py: CI's GITHUB_ACTIONS makes typer
# embed ANSI codes in help and errors; plain substring checks need it off.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
async def _use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    url = os.environ.get(
        "VIBEY_TEST_DATABASE_URL",
        f"postgresql://{os.environ.get('USER', 'postgres')}@localhost:5432/vibey_test",
    )
    monkeypatch.setenv("VIBEY_PG_URL", url)
    conn = await asyncpg.connect(database_url())
    await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
    await conn.execute("CREATE SCHEMA IF NOT EXISTS public")
    await conn.close()


def _draft(project_id: UUID, minute: int, **overrides: object) -> LedgerEventDraft:
    payload = overrides.pop("payload", {"minute": minute})
    fields: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.INTAKE,
        "kind": EventKind.QUESTION_ASKED,
        "engine_id": None,
        "job_id": None,
        "causation_id": None,
        "correlation_id": project_id,
        "provenance": Provenance.TRUSTED,
        "produced_at": T0 + timedelta(minutes=minute),
        "payload": payload,
        "digest": digest_event(payload),  # type: ignore[arg-type]
    }
    fields.update(overrides)
    return LedgerEventDraft(**fields)  # type: ignore[arg-type]


async def _seed(tmp_path: Path, name: str = "search-proj") -> tuple[UUID, list[LedgerEvent]]:
    async with build_app() as resources:
        project = await resources.projects.create(
            name, tmp_path, max_cycles=5, config={"project": {"name": name}}
        )
        pid = project.project_id
        drafts = [
            _draft(pid, 0, payload={"question_id": "q1", "text": "What is the goal?"}),
            _draft(pid, 1, kind=EventKind.ANSWER_GIVEN, payload={"question_id": "q1"}),
            _draft(
                pid,
                2,
                phase=Phase.BUILD,
                kind=EventKind.FINDING_RAISED,
                engine_id=EngineId.CODEXLOOP,
                provenance=Provenance.AGENT,
                payload={"finding_id": "f1", "summary": "flaky test"},
            ),
        ]
        events = [await resources.ledger.append(draft) for draft in drafts]
        return pid, events


def _search(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["ledger", "search", *args])
    return result.exit_code, result.output


# -- the happy paths --------------------------------------------------------


def test_no_criteria_lists_the_latest_events_oldest_first(tmp_path: Path) -> None:
    pid, events = asyncio.run(_seed(tmp_path))
    code, out = _search(str(pid))

    assert code == 0, out
    lines = out.strip().splitlines()
    assert lines[0].startswith("#1 ")
    assert "[INTAKE] QuestionAsked" in lines[0]
    assert f"id={events[0].event_id}" in lines[0]
    assert f"digest={events[0].digest[:12]}" in lines[0]
    assert events[0].digest not in lines[0]
    assert "[BUILD] FindingRaised [codexloop]" in lines[2]
    assert lines[-1] == "3 matching events"


def test_the_latest_project_is_searched_when_none_is_named(tmp_path: Path) -> None:
    asyncio.run(_seed(tmp_path))
    code, out = _search("--kind", "findingraised")
    assert code == 0, out
    assert "FindingRaised" in out
    assert out.strip().endswith("1 matching event")


def test_every_criterion_reaches_the_search(tmp_path: Path) -> None:
    pid, events = asyncio.run(_seed(tmp_path))

    assert "#2 " in _search(str(pid), "--id", str(events[1].event_id))[1]
    by_digest = _search(str(pid), "--digest", events[2].digest.upper())[1]
    assert "#3 " in by_digest
    assert "1 matching event" in by_digest
    assert "#3 " in _search(str(pid), "--actor", "codexloop")[1]
    assert "2 matching events" in _search(str(pid), "--actor", "vibey")[1]
    assert "2 matching events" in _search(str(pid), "--actor", "Trusted")[1]
    assert "#1 " in _search(str(pid), "--text", "GOAL")[1]
    both = _search(str(pid), "--kind", "QuestionAsked", "--kind", "ANSWER_GIVEN")[1]
    assert "2 matching events" in both


def test_a_time_window_reads_iso_8601_with_or_without_a_zone(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path))

    naive = _search(str(pid), "--since", "2026-09-18T12:01:00", "--until", "2026-09-18T12:02:00")
    assert naive[0] == 0, naive[1]
    assert "#2 " in naive[1]
    assert "1 matching event" in naive[1]

    # 14:02 in UTC+2 is 12:02 UTC: only the third event is at or after it.
    zoned = _search(str(pid), "--since", "2026-09-18T14:02:00+02:00")
    assert "#3 " in zoned[1]
    assert "1 matching event" in zoned[1]


def test_the_limit_says_when_older_matches_were_left_out(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path))
    code, out = _search(str(pid), "--limit", "2")
    assert code == 0, out
    assert "#1 " not in out
    assert "#2 " in out
    assert "#3 " in out
    assert "older matches were left out" in out


def test_no_match_says_so(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path))
    code, out = _search(str(pid), "--text", "nowhere to be found")
    assert code == 0, out
    assert out.strip() == "no events match"


def test_json_carries_every_field_of_every_event(tmp_path: Path) -> None:
    pid, events = asyncio.run(_seed(tmp_path))
    code, out = _search(str(pid), "--json", "--limit", "2")

    assert code == 0, out
    document = json.loads(out)
    assert document["project_id"] == str(pid)
    assert document["truncated"] is True
    assert [record["seq"] for record in document["events"]] == [2, 3]
    finding = document["events"][1]
    assert finding == {
        "event_id": str(events[2].event_id),
        "project_id": str(pid),
        "seq": 3,
        "cycle": 1,
        "phase": "build",
        "kind": "FindingRaised",
        "engine_id": "codexloop",
        "job_id": None,
        "causation_id": None,
        "correlation_id": str(pid),
        "provenance": "agent",
        "produced_at": events[2].produced_at.isoformat(),
        "digest": events[2].digest,
        "payload": {"finding_id": "f1", "summary": "flaky test"},
    }
    assert document["events"][0]["engine_id"] is None


# -- a kind a newer vibey wrote (vibey#275) ----------------------------------


async def _seed_with_a_newer_kind(tmp_path: Path) -> UUID:
    pid, _ = await _seed(tmp_path)
    payload = {"transcript_ref": "runs/1/t.jsonl"}
    async with build_app() as resources, resources.ledger._pool.acquire() as conn:
        # A newer vibey's appender, through the same SQL function.
        await conn.execute(
            "SELECT append_event($1, 1, 'build', 'FutureKindX', 'claudeloop', NULL, NULL, "
            "$1, 'agent', $2, $3::jsonb, $4)",
            pid,
            T0 + timedelta(minutes=3),
            json.dumps(payload),
            digest_event(payload),
        )
    return pid


def test_the_ledger_stays_searchable_with_a_kind_this_vibey_does_not_know(
    tmp_path: Path,
) -> None:
    pid = asyncio.run(_seed_with_a_newer_kind(tmp_path))

    code, out = _search(str(pid))
    assert code == 0, out
    assert "[BUILD] FutureKindX [claudeloop]" in out
    assert out.strip().endswith("4 matching events")


def test_a_kind_this_vibey_does_not_know_is_found_by_its_exact_text(tmp_path: Path) -> None:
    pid = asyncio.run(_seed_with_a_newer_kind(tmp_path))

    result = runner.invoke(app, ["ledger", "search", str(pid), "--kind", "FutureKindX"])
    assert result.exit_code == 0, result.output
    assert "#4 " in result.stdout
    assert result.stdout.strip().endswith("1 matching event")
    # A typo would find nothing too, so the CLI says it matched literally --
    # on stderr, out of the way of the result.
    assert "'FutureKindX' is not an event kind this vibey knows" in result.stderr
    assert "not an event kind" not in result.stdout


def test_json_stays_one_document_when_a_kind_is_matched_literally(tmp_path: Path) -> None:
    pid = asyncio.run(_seed_with_a_newer_kind(tmp_path))

    result = runner.invoke(app, ["ledger", "search", str(pid), "--kind", "FutureKindX", "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert [record["kind"] for record in document["events"]] == ["FutureKindX"]
    assert document["events"][0]["payload"] == {"transcript_ref": "runs/1/t.jsonl"}


def test_the_presenter_notes_only_the_kinds_it_matched_literally() -> None:
    notes = LedgerSearchPresenter().kind_notes(
        [UnrecognizedEventKind("Zed"), EventKind.FINDING_RAISED, UnrecognizedEventKind("Alpha")]
    )
    assert [note.split("'")[1] for note in notes] == ["Alpha", "Zed"]
    assert LedgerSearchPresenter().kind_notes([EventKind.FINDING_RAISED]) == []


# -- nothing to search ------------------------------------------------------


def test_no_projects_exits_1() -> None:
    code, out = _search()
    assert code == 1
    assert "no projects found" in out


def test_an_unknown_project_exits_1(tmp_path: Path) -> None:
    asyncio.run(_seed(tmp_path))
    stranger = uuid4()
    code, out = _search(str(stranger))
    assert code == 1
    assert f"unknown project {stranger}" in out


# -- usage errors, before any connection ------------------------------------


@pytest.mark.parametrize(
    ("args", "fragment"),
    [
        (["--actor", "mallory"], "unknown actor 'mallory'"),
        (["--kind", " "], "unknown event kind ' '"),
        (["--digest", "abc123"], "full 64-character hex SHA-256"),
        (["--since", "yesterday"], "'yesterday' is not an ISO-8601"),
        (["--until", "2026-13-01"], "'2026-13-01' is not an ISO-8601"),
        (["--since", "2026-09-18", "--until", "2026-09-17"], "the window is empty"),
        (["--text", ""], "text must not be empty"),
    ],
    ids=["actor", "kind", "digest", "since", "until", "window", "text"],
)
def test_bad_input_is_a_usage_error(args: list[str], fragment: str) -> None:
    code, out = _search(*args)
    assert code == 2, out
    assert fragment in " ".join(out.split())


def test_a_limit_below_one_is_refused_by_typer() -> None:
    code, _ = _search("--limit", "0")
    assert code == 2


def test_search_is_listed_under_ledger() -> None:
    result = runner.invoke(app, ["ledger", "--help"])
    assert result.exit_code == 0
    assert "search" in result.output


# -- the pieces, without a database -----------------------------------------


def test_a_bound_without_a_zone_is_read_in_the_assumed_zone() -> None:
    plus_five = timezone(timedelta(hours=5))
    assert TimeBoundParser(assume=plus_five).parse("2026-09-18").utcoffset() == timedelta(hours=5)
    assert TimeBoundParser().parse(" 2026-09-18T12:00:00Z ") == T0
    with pytest.raises(InvalidLedgerQuery):
        TimeBoundParser().parse("soon")


def test_the_digest_width_is_configurable() -> None:
    event = LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=Phase.BUILD,
        seq=1,
        kind=EventKind.TURN_COMPLETED,
        engine_id=None,
        job_id=uuid4(),
        causation_id=uuid4(),
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=T0,
        payload={},
        digest=digest_event({}),
    )
    result = LedgerSearchResult(events=(event,), truncated=False)
    line = LedgerSearchPresenter(digest_width=4).human(result)[0]
    assert line.endswith(f"digest={event.digest[:4]}")
    record = json.loads(LedgerSearchPresenter().machine(event.project_id, result))["events"][0]
    assert record["job_id"] == str(event.job_id)
    assert record["causation_id"] == str(event.causation_id)


def test_the_classes_satisfy_their_declared_seams() -> None:
    assert isinstance(LEDGER_SEARCH, LedgerSearchCommandInterface)
    assert isinstance(PRESENTER, LedgerSearchPresenterInterface)
    assert isinstance(TIME_BOUNDS, TimeBoundParserInterface)
