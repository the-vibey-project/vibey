# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey budget`, end to end against real PostgreSQL, as the application role.

Every test starts from an empty schema, migrated and granted as `vibey migrate` leaves
it, and runs the command as the restricted role production connects as (ADR-0055): a
query the command needs that the role was not granted fails here as `permission
denied`. The JSON is the contract the VS Code extension builds against, so its shape is
pinned key by key.
"""

import asyncio
import dataclasses
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import HumanGateRequest
from vibey.application.interfaces import ProjectBudgetServiceInterface, ProjectBudgetStore
from vibey.bootstrap import AppResources, build_app, migrations_dir
from vibey.cli.budget import BUDGET, BUDGET_PRESENTER
from vibey.cli.interfaces.budget_interface import BudgetCommandInterface, BudgetPresenterInterface
from vibey.cli.main import app
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.project_budget_store import PostgresProjectBudgetStore
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.queue_priority_grant import ProcessCaller

pytestmark = pytest.mark.integration
# CI's GITHUB_ACTIONS makes typer embed ANSI codes; plain substring checks need them off.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
ROLES = TestDatabaseRoles.from_environ(os.environ)
ACCOUNT = ProcessCaller().current().name
KEYS = ["project_id", "name", "cycle", "caps", "spend", "exhausted", "history"]


def _owner() -> str:
    return os.environ["VIBEY_TEST_DATABASE_URL"]


@pytest.fixture(autouse=True)
def _an_empty_schema_the_application_role_runs_on(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fresh() -> None:
        conn = await asyncpg.connect(_owner())
        try:
            await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            await conn.execute("CREATE SCHEMA public")
        finally:
            await conn.close()
        # Dropping `public` dropped the application role's grants with it: put the
        # schema back as `vibey migrate` leaves it before the role touches it.
        await ROLES.restore(_owner(), migrations_dir())

    asyncio.run(fresh())
    monkeypatch.setenv("VIBEY_PG_URL", ROLES.app_dsn(_owner()))


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["budget", *args])
    return result.exit_code, result.output


def _json(*args: str) -> object:
    code, out = _run(*args)
    assert code == 0, out
    return json.loads(out)


async def _create(
    repo: Path, name: str, config: dict[str, object] | None = None, *, spend: float = 0.0
) -> UUID:
    async with build_app() as resources:
        project = await resources.projects.create(name, repo, max_cycles=3, config=config or {})
        if spend:
            for kind, payload in (
                (EventKind.TURN_COMPLETED, {"cost_usd": spend - 0.71}),
                (EventKind.BUDGET_SPENT, {"dollars": 0.71, "turns": 2}),
            ):
                await resources.ledger.append(
                    LedgerEventDraft(
                        project_id=project.project_id,
                        cycle=project.cycle,
                        phase=Phase.BUILD,
                        kind=kind,
                        engine_id=EngineId.CLAUDELOOP,
                        job_id=None,
                        causation_id=None,
                        correlation_id=project.project_id,
                        provenance=Provenance.AGENT,
                        produced_at=datetime.now(UTC),
                        payload=dict(payload),
                        digest=digest_event(dict(payload)),
                    )
                )
        return project.project_id


def _project(tmp_path: Path, name: str = "greeter", **kwargs: object) -> UUID:
    repo = tmp_path / name
    repo.mkdir(exist_ok=True)
    return asyncio.run(_create(repo, name, **kwargs))  # type: ignore[arg-type]


async def _changes(project_id: UUID) -> list[LedgerEvent]:
    async with build_app() as resources:
        return [
            e
            for e in await resources.ledger.all_for_project(project_id)
            if e.kind is EventKind.BUDGET_CAP_CHANGED
        ]


async def _config(project_id: UUID) -> dict[str, object]:
    async with build_app() as resources:
        project = await resources.projects.get(project_id)
        assert project is not None
        return dict(project.config)


# -- the command -------------------------------------------------------------------------


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(BUDGET, BudgetCommandInterface)
    assert isinstance(BUDGET_PRESENTER, BudgetPresenterInterface)


def test_app_resources_offer_no_way_to_write_a_budget_but_the_service() -> None:
    async def inspect() -> None:
        async with build_app() as resources:
            assert isinstance(resources.project_budgets, ProjectBudgetServiceInterface)
            for field in dataclasses.fields(AppResources):
                value = getattr(resources, field.name)
                assert not isinstance(value, ProjectBudgetStore), field.name
                assert not isinstance(value, PostgresProjectBudgetStore), field.name

    asyncio.run(inspect())


def test_budget_is_a_command_group_whose_bare_form_shows() -> None:
    top = runner.invoke(app, ["--help"])
    code, out = _run("--help")

    assert "budget" in top.output
    assert code == 0 and all(name in out for name in ("show", "set", "clear"))
    assert "With no subcommand, shows the latest project's budget" in " ".join(out.split())


def test_with_no_project_there_is_no_latest_but_a_listing_of_none_is_an_answer() -> None:
    for args in ((), ("--json",), ("set", "--max-cycle-dollars", "5"), ("clear", "--all")):
        code, out = _run(*args)
        assert (code, out.strip()) == (1, "no projects found; create one with `vibey new` first")

    assert _json("--all", "--json") == []
    code, out = _run("--all")
    assert code == 0
    assert "no projects yet; create one with `vibey new <name> --repo <path>`" in out


def test_an_unknown_project_exits_1_and_names_it(tmp_path: Path) -> None:
    _project(tmp_path)
    missing = str(uuid4())

    for args in (
        (missing,),
        ("set", missing, "--max-cycle-turns", "5"),
        ("clear", missing, "--turns"),
    ):
        code, out = _run(*args)
        assert (code, out.strip()) == (1, f"unknown project {missing}")


# -- showing -----------------------------------------------------------------------------


def test_the_json_is_the_contract_the_extension_reads(tmp_path: Path) -> None:
    pid = _project(tmp_path, config={"max_cycle_dollars": 15}, spend=3.21)

    document = _json(str(pid), "--json")

    assert isinstance(document, dict)
    assert list(document) == KEYS
    assert document["project_id"] == str(pid)
    assert (document["name"], document["cycle"]) == ("greeter", 1)
    assert document["caps"] == {"max_cycle_dollars": 15.0, "max_cycle_turns": None}
    assert list(document["spend"]) == ["dollars", "turns"]
    assert document["spend"]["dollars"] == pytest.approx(3.21)
    assert document["spend"]["turns"] == 3
    assert document["exhausted"] is False
    assert document["history"] == []


def test_the_text_is_one_short_plain_block(tmp_path: Path) -> None:
    pid = _project(tmp_path, config={"max_cycle_dollars": 15}, spend=3.21)

    code, out = _run()

    assert code == 0, out
    assert out.splitlines() == [
        f"greeter ({pid}), cycle 1",
        "  dollars: $3.21 spent this cycle; cap $15.00",
        "  turns:   3 spent this cycle; no cap",
        "  last change: none since the project was created",
    ]


def test_every_project_newest_first_in_both_forms(tmp_path: Path) -> None:
    older = _project(tmp_path, "older", config={"max_cycle_turns": 7})
    newer = _project(tmp_path, "newer")

    documents = _json("--all", "--json")
    code, out = _run("--all")

    assert isinstance(documents, list)
    assert [d["project_id"] for d in documents] == [str(newer), str(older)]
    assert all(list(d) == KEYS for d in documents)
    assert code == 0
    assert out.index(f"newer ({newer})") < out.index(f"older ({older})")
    assert "\n\nolder (" in out
    assert _json("--json")["project_id"] == str(newer)  # type: ignore[index]


def test_a_project_id_and_all_together_are_a_usage_error(tmp_path: Path) -> None:
    pid = _project(tmp_path)

    code, out = _run(str(pid), "--all")

    assert code == 2
    assert "name a PROJECT_ID or give --all, not both" in out


# -- changing ----------------------------------------------------------------------------


def test_set_changes_the_config_records_each_cap_and_the_history_reads_it_back(
    tmp_path: Path,
) -> None:
    pid = _project(tmp_path, config={"project": {"name": "greeter"}})

    code, out = _run("set", str(pid), "--max-cycle-dollars", "15", "--max-cycle-turns", "200")

    assert code == 0, out
    assert out.splitlines()[:3] == [
        f"Changed by {ACCOUNT}:",
        "  dollar cap: none -> $15.00",
        "  turn cap: none -> 200",
    ]
    assert asyncio.run(_config(pid)) == {
        "project": {"name": "greeter"},
        "max_cycle_dollars": 15.0,
        "max_cycle_turns": 200,
    }
    document = _json(str(pid), "--json")
    assert isinstance(document, dict)
    assert document["caps"] == {"max_cycle_dollars": 15.0, "max_cycle_turns": 200}
    history = document["history"]
    assert [(h["by"], h["field"], h["old"], h["new"]) for h in history] == [
        (ACCOUNT, "max_cycle_dollars", None, 15.0),
        (ACCOUNT, "max_cycle_turns", None, 200),
    ]
    assert all(list(h) == ["at", "by", "field", "old", "new"] for h in history)
    assert all(datetime.fromisoformat(h["at"]).tzinfo is not None for h in history)


def test_by_is_a_label_for_the_record_and_the_account_stays_beside_it(tmp_path: Path) -> None:
    pid = _project(tmp_path)

    code, out = _run("set", "--max-cycle-turns", "40", "--by", "vibey-vscode")

    assert code == 0, out
    assert out.startswith("Changed by vibey-vscode:")
    (event,) = asyncio.run(_changes(pid))
    assert event.provenance is Provenance.TRUSTED
    assert (event.payload["by"], event.payload["account"]) == ("vibey-vscode", ACCOUNT)
    history = _json("--json")["history"]  # type: ignore[index]
    assert [h["by"] for h in history] == ["vibey-vscode"]


def test_a_cap_at_or_below_the_spend_is_allowed_and_the_command_says_what_follows(
    tmp_path: Path,
) -> None:
    pid = _project(tmp_path, spend=3.21)

    code, out = _run("set", "--max-cycle-dollars", "2")

    assert code == 0, out
    assert (
        "  The dollar cap is reached: the next BUILD session will park a budget_exhausted gate."
        in out.splitlines()
    )
    assert _json(str(pid), "--json")["exhausted"] is True  # type: ignore[index]


def test_clear_leaves_the_project_uncapped_as_if_never_set(tmp_path: Path) -> None:
    pid = _project(tmp_path, config={"max_cycle_dollars": 15.0, "max_cycle_turns": 40, "x": 1})

    code, out = _run("clear", "--dollars")
    assert code == 0, out
    assert "  dollar cap: $15.00 -> none" in out.splitlines()
    assert asyncio.run(_config(pid)) == {"max_cycle_turns": 40, "x": 1}

    code, out = _run("clear", str(pid), "--all", "--by", "vibey-vscode")
    assert code == 0, out
    assert "  turn cap: 40 -> none" in out.splitlines()
    assert asyncio.run(_config(pid)) == {"x": 1}

    history = _json("--json")["history"]  # type: ignore[index]
    assert [(h["field"], h["old"], h["new"]) for h in history] == [
        ("max_cycle_dollars", 15.0, None),
        ("max_cycle_turns", 40, None),
    ]


def test_a_change_that_changes_nothing_records_nothing(tmp_path: Path) -> None:
    pid = _project(tmp_path, config={"max_cycle_dollars": 15.0})

    for args in (("set", "--max-cycle-dollars", "15"), ("clear", "--turns")):
        code, out = _run(*args)
        assert code == 0, out
        assert out.startswith("Nothing changed: the caps were already as asked.")

    assert asyncio.run(_changes(pid)) == []


@pytest.mark.parametrize(
    "args",
    [
        ("set",),
        ("set", "--max-cycle-dollars", "0"),
        ("set", "--max-cycle-dollars", "-1"),
        ("set", "--max-cycle-dollars", "nan"),
        ("set", "--max-cycle-dollars", "inf"),
        ("set", "--max-cycle-dollars", "ten"),
        ("set", "--max-cycle-turns", "0"),
        ("set", "--max-cycle-turns", "2.5"),
        ("set", "--max-cycle-turns", "5", "--by", ""),
        ("set", "--max-cycle-turns", "5", "--by", "two\nlines"),
        ("clear",),
        ("clear", "--turns", "--by", " "),
    ],
    ids=[
        "set-nothing",
        "zero-dollars",
        "negative-dollars",
        "nan",
        "inf",
        "not-a-number",
        "zero-turns",
        "fractional-turns",
        "empty-label",
        "two-line-label",
        "clear-nothing",
        "blank-label",
    ],
)
def test_a_change_vibey_would_refuse_is_a_usage_error_that_changes_nothing(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    pid = _project(tmp_path, config={"max_cycle_turns": 40})

    code, _ = _run(*args)

    assert code == 2
    assert asyncio.run(_config(pid)) == {"max_cycle_turns": 40}
    assert asyncio.run(_changes(pid)) == []


def test_a_job_parked_on_a_budget_gate_is_named_with_the_answer_that_resumes_it(
    tmp_path: Path,
) -> None:
    pid = _project(tmp_path, config={"max_cycle_dollars": 2.0}, spend=3.21)

    async def park() -> UUID:
        async with build_app() as resources:
            gate = await resources.gates.raise_gate(
                pid, None, HumanGateRequest(kind="budget_exhausted", prompt="grant more?")
            )
            return gate.gate_id

    gate_id = asyncio.run(park())

    code, out = _run("set", "--max-cycle-dollars", "50")

    assert code == 0, out
    assert out.splitlines()[-2:] == [
        "1 job is still parked on a budget_exhausted gate. A changed cap applies once the "
        "gate is answered:",
        f"  vibey answer {gate_id} --raw '{{}}'",
    ]


@pytest.mark.parametrize("billing", [False, True], ids=["public", "billing"])
def test_the_ledger_export_withholds_every_cap_change_and_counts_it(
    tmp_path: Path, billing: bool
) -> None:
    """The publication policy's decision, end to end: neither the public shard nor the
    operator's billing shard carries a cap change, and each says it left one out."""
    pid = _project(tmp_path)
    assert _run("set", "--max-cycle-dollars", "15", "--by", "vibey-vscode")[0] == 0
    shard = tmp_path / "shard.jsonl"

    result = runner.invoke(
        app,
        ["ledger", "export", str(pid), "--out", str(shard), *(["--billing"] if billing else [])],
    )

    assert result.exit_code == 0, result.output
    assert (
        "1 event withheld by policy (0 untrusted provenance, 0 engine chatter, "
        "1 kind not allowlisted)" in result.output
    )
    lines = [json.loads(line) for line in shard.read_text().splitlines() if line.strip()]
    assert not [line for line in lines if line.get("kind") == "BudgetCapChanged"]
    assert "vibey-vscode" not in shard.read_text()


def test_vibey_cost_reports_the_cap_budget_set_wrote(tmp_path: Path) -> None:
    _project(tmp_path, spend=3.21)
    assert _run("set", "--max-cycle-dollars", "3")[0] == 0

    result = runner.invoke(app, ["cost"])

    assert result.exit_code == 0, result.output
    assert "Cycle spend:      $3.21 (3 turns)" in result.output
    assert "Cycle dollar cap: $3.00" in result.output
    assert "Cycle turn cap:   none" in result.output
    assert "Cap reached: the next BUILD session parks a budget_exhausted gate." in result.output


def test_a_project_in_a_phase_this_vibey_does_not_know_is_shown_but_not_changed(
    tmp_path: Path,
) -> None:
    pid = _project(tmp_path, config={"max_cycle_turns": 40})

    async def widen() -> None:
        # Widening an enum is the owner's act (ADR-0055).
        conn = await asyncpg.connect(_owner())
        try:
            await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'hyperdrive'")
            await conn.execute("UPDATE project SET phase = 'hyperdrive' WHERE id = $1", pid)
        finally:
            await conn.close()

    asyncio.run(widen())

    assert _json(str(pid), "--json")["caps"] == {  # type: ignore[index]
        "max_cycle_dollars": None,
        "max_cycle_turns": 40,
    }
    result = runner.invoke(app, ["budget", "set", str(pid), "--max-cycle-turns", "5"])
    assert result.exit_code == 3
    assert "which this vibey does not know" in result.output
    assert asyncio.run(_config(pid)) == {"max_cycle_turns": 40}
