# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey ledger export` against real Postgres, and `vibey ledger site` with none."""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.application.ledger_publication import (
    LedgerShard,
    LedgerSitePlan,
    ShardHeader,
    ShardHolding,
)
from vibey.bootstrap import AppResources, build_app, database_url
from vibey.cli.interfaces import (
    LedgerExportCommandInterface,
    LedgerSiteCommandInterface,
    PublicationPresenterInterface,
)
from vibey.cli.ledger_publication import (
    LEDGER_EXPORT,
    LEDGER_SITE,
    PRESENTER,
    LedgerExportCommand,
)
from vibey.cli.main import app
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.phase import Phase
from vibey.domain.publication_policy import TrimCounts, WithheldReason
from vibey.infrastructure.engines.tailer import LedgerEventDraft

# See tests/cli/test_operational_commands.py: CI's GITHUB_ACTIONS makes typer
# embed ANSI codes in help and errors; plain substring checks need it off.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000006")


@pytest.fixture
async def database(monkeypatch: pytest.MonkeyPatch) -> None:
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
    payload = overrides.pop("payload", {"decision_id": f"d{minute}", "title": "use Postgres"})
    fields: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.DESIGN,
        "kind": EventKind.DECISION_RECORDED,
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


async def _seed(repo: Path) -> tuple[UUID, tuple[LedgerEvent, ...]]:
    async with build_app() as resources:
        project = await resources.projects.create(
            "greeter", repo, max_cycles=5, config={"project": {"name": "greeter"}}
        )
        pid = project.project_id
        drafts = [
            _draft(pid, 0, payload={"decision_id": "d1", "title": f"work in {repo}"}),
            _draft(
                pid,
                1,
                kind=EventKind.TURN_COMPLETED,
                engine_id=EngineId.CLAUDELOOP,
                provenance=Provenance.AGENT,
                payload={"text": "model output nobody should read"},
            ),
            _draft(
                pid,
                2,
                kind=EventKind.FINDING_RAISED,
                payload={"finding_id": "f1", "text": "<script>x</script>", "author": "a@b.io"},
            ),
        ]
        for draft in drafts:
            await resources.ledger.append(draft)
        return pid, await resources.ledger.all_for_project(pid)


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["ledger", *args])
    return result.exit_code, result.output


def test_the_commands_satisfy_their_seams() -> None:
    assert isinstance(LEDGER_EXPORT, LedgerExportCommandInterface)
    assert isinstance(LEDGER_SITE, LedgerSiteCommandInterface)
    assert isinstance(PRESENTER, PublicationPresenterInterface)


# -- export, then site ------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.usefixtures("database")
def test_export_then_site_publishes_the_policys_projection(tmp_path: Path) -> None:
    repo = tmp_path / "private-checkout"
    pid, events = asyncio.run(_seed(repo))
    shard = tmp_path / "ledger" / "greeter.jsonl"

    code, out = _run("export", str(pid), "--out", str(shard))

    assert code == 0, out
    lines = out.strip().splitlines()
    assert lines[0] == f"exported 2 of 3 ledger event(s) of project greeter ({pid}) to {shard}"
    assert lines[1] == (
        "1 event withheld by policy (0 untrusted provenance, 1 engine chatter, "
        "0 kind not allowlisted)"
    )
    assert lines[2] == (
        "from published records: 1 field(s) withheld, 1 absolute path(s) and 0 email "
        "address(es) stripped, 0 record(s) with a credential redacted"
    )
    head = LEDGER_CHAIN.verify(pid, events).head
    assert lines[3] == f"chain head {head} at seq 3, verified"

    site = tmp_path / "site"
    code, out = _run("site", "--from", str(shard), "--out", str(site), "--json-only")

    assert code == 0, out
    assert out.startswith(
        f"built the JSON surface of project greeter ({pid}) in {site}: 2 record document(s)"
    )
    manifest = json.loads((site / "manifest.json").read_text())
    assert manifest["chain"]["head"] == head
    assert manifest["statement"] == "1 event withheld by policy"
    served = "".join(p.read_text() for p in site.rglob("*.json"))
    for leaked in (str(repo), "model output", "a@b.io"):
        assert leaked not in shard.read_text() + served
    assert "<script>" not in served


@pytest.mark.integration
@pytest.mark.usefixtures("database")
def test_export_of_an_unknown_project_exits_1(tmp_path: Path) -> None:
    missing = uuid4()
    code, out = _run("export", str(missing), "--out", str(tmp_path / "x.jsonl"))
    assert code == 1
    assert out.strip() == f"unknown project {missing}"
    assert not (tmp_path / "x.jsonl").exists()


def test_export_needs_an_out_file() -> None:
    code, out = _run("export", str(uuid4()))
    assert code == 2
    assert "--out" in out


# -- site needs no database ------------------------------------------------------------


def _shard_file(tmp_path: Path) -> Path:
    # Built without Postgres: the export command with a stand-in app, then read back.
    events = (
        LedgerEvent(
            event_id=UUID(int=1),
            project_id=PROJECT,
            cycle=1,
            phase=Phase.DESIGN,
            seq=1,
            kind=EventKind.DECISION_RECORDED,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=PROJECT,
            provenance=Provenance.TRUSTED,
            produced_at=T0,
            payload={"title": "t"},
            digest=digest_event({"title": "t"}),
        ),
    )

    class _Projects:
        async def get(self, project_id: UUID) -> object:
            return type("Project", (), {"project_id": project_id, "name": "offline"})()

    class _Ledger:
        async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
            return events

    @asynccontextmanager
    async def _app() -> AsyncIterator[AppResources]:
        yield type("Resources", (), {"projects": _Projects(), "ledger": _Ledger()})()  # type: ignore[misc]

    path = tmp_path / "offline.jsonl"
    asyncio.run(LedgerExportCommand(open_app=_app).run(PROJECT, path))
    return path


def test_site_builds_from_a_shard_file_alone(tmp_path: Path) -> None:
    shard = _shard_file(tmp_path)
    site = tmp_path / "site"

    code, out = _run("site", "--from", str(shard), "--out", str(site), "--json-only")

    assert code == 0, out
    assert sorted(p.relative_to(site).as_posix() for p in site.rglob("*.json")) == [
        "index.json",
        "manifest.json",
        f"records/{UUID(int=1)}.json",
    ]
    assert "0 events withheld by policy" in out


def test_site_without_json_only_is_a_usage_error(tmp_path: Path) -> None:
    shard = _shard_file(tmp_path)
    code, out = _run("site", "--from", str(shard), "--out", str(tmp_path / "site"))
    assert code == 2
    assert "pass --json-only" in out
    assert not (tmp_path / "site").exists()


def test_site_from_a_missing_file_is_a_usage_error(tmp_path: Path) -> None:
    code, out = _run(
        "site", "--from", str(tmp_path / "absent.jsonl"), "--out", str(tmp_path), "--json-only"
    )
    assert code == 2
    # typer draws the error in a box and wraps it; read the words, not the lines.
    assert "does not exist" in " ".join(out.replace("│", " ").split())


def test_site_from_a_file_that_is_not_a_shard_exits_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json\n")
    code, out = _run("site", "--from", str(bad), "--out", str(tmp_path / "s"), "--json-only")
    assert code == 1
    assert out.strip() == f"invalid shard {bad}: line 1: not JSON: Expecting value"


# -- the presenter ------------------------------------------------------------------------


def _header(**changes: object) -> ShardHeader:
    fields: dict[str, object] = {
        "format": "vibey-ledger-shard/v1",
        "project_id": PROJECT,
        "project_name": "greeter",
        "holds": ShardHolding.FULL,
        "tier": "standard (untiered)",
        "ledger_first_seq": 1,
        "ledger_last_seq": 9,
        "ledger_event_count": 9,
        "chain_scheme": "vibey-ledger-chain/v1",
        "chain_head": "ab" * 32,
        "chain_findings": 0,
        "policy_scheme": "vibey-publication-policy/v1",
        "policy_fingerprint": "cd" * 32,
        "published_count": 4,
        "published_digest_range": "ef" * 32,
        "withheld": MappingProxyType(
            {
                WithheldReason.UNTRUSTED_PROVENANCE: 2,
                WithheldReason.ENGINE_CHATTER: 2,
                WithheldReason.KIND_NOT_ALLOWLISTED: 1,
            }
        ),
        "trimmed": TrimCounts(fields=3, paths=2, emails=1, credentials=1),
        "trims": MappingProxyType({}),
    }
    fields.update(changes)
    return ShardHeader(**fields)  # type: ignore[arg-type]


def test_the_presenter_counts_every_reason_and_every_trim() -> None:
    lines = PRESENTER.exported(LedgerShard(header=_header(), records=()), Path("s.jsonl"))
    assert lines == [
        f"exported 4 of 9 ledger event(s) of project greeter ({PROJECT}) to s.jsonl",
        "5 events withheld by policy (2 untrusted provenance, 2 engine chatter, "
        "1 kind not allowlisted)",
        "from published records: 3 field(s) withheld, 2 absolute path(s) and 1 email "
        "address(es) stripped, 1 record(s) with a credential redacted",
        f"chain head {'ab' * 32} at seq 9, verified",
    ]


def test_the_presenter_says_when_the_chain_walk_disagreed() -> None:
    shard = LedgerShard(header=_header(chain_findings=2), records=())
    assert PRESENTER.exported(shard, Path("s"))[-1] == (
        f"chain head {'ab' * 32} at seq 9: the ledger's chain walk found 2 disagreement(s), "
        "so the head is published unverified"
    )


def test_the_presenter_says_an_empty_ledger_is_anchored_at_genesis() -> None:
    header = _header(ledger_first_seq=None, ledger_last_seq=None, ledger_event_count=0)
    shard = LedgerShard(header=header, records=())
    assert PRESENTER.exported(shard, Path("s"))[-1] == (
        f"chain head {'ab' * 32} at genesis (the ledger is empty), verified"
    )


def test_the_presenter_describes_a_built_site() -> None:
    plan = LedgerSitePlan(
        shard=LedgerShard(header=_header(), records=()), documents=MappingProxyType({})
    )
    assert PRESENTER.built(plan, Path("site"))[0] == (
        f"built the JSON surface of project greeter ({PROJECT}) in site: 4 record "
        "document(s), an index and a manifest"
    )
