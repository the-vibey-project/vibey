# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.application.dto import EngineHealthRecord, EnqueueRequest
from vibey.bootstrap import build_app, database_url
from vibey.cli.main import app
from vibey.domain.circuit import CircuitState
from vibey.domain.engine import EngineId
from vibey.domain.job import idempotency_key
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.postgres import PostgresStatus

pytestmark = pytest.mark.integration
# Typer force-enables rich ANSI styling whenever GITHUB_ACTIONS is set
# (typer/rich_utils.py), which CI always has and a local shell never does.
# That embeds escape codes inside option names, breaking plain substring
# checks against --help output -- disable it the way Typer itself exposes.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


@pytest.fixture(autouse=True)
def _database_security_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests run as the schema's owner, and whether the local server accepts a
    password-less connection depends on the machine. ADR-0055's database checks are
    tested on their own (tests/cli/test_doctor_database.py); here they pass."""
    from vibey.infrastructure.cluster_preflight import ClusterCheck, DatabaseSecurityChecks

    async def passing(self: object, conn: object, dsn: str) -> tuple[ClusterCheck, ...]:
        return (
            ClusterCheck("ledger-guard", True, "stub"),
            ClusterCheck("local-auth", True, "stub"),
        )

    monkeypatch.setattr(DatabaseSecurityChecks, "run", passing)


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


async def _seed_status_project(tmp_path: Path) -> UUID:
    async with build_app() as resources:
        project = await resources.projects.create(
            "ops-status-proj",
            tmp_path,
            max_cycles=5,
            config={"project": {"name": "ops-status-proj"}},
        )
        health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
        await health_repo.upsert(
            EngineHealthRecord(
                project_id=project.project_id,
                engine_id=EngineId.CLAUDELOOP,
                installed=True,
                version="1.0.0",
                conformance_ok=True,
                conformance_at=datetime.now(UTC),
                auth_ok_at=datetime.now(UTC),
                circuit=CircuitState.CLOSED,
                capacity_state=None,
                resets_at=None,
                probe_next_at=None,
                probe_attempt=0,
                consecutive_fail=0,
                ewma_failure=0.0,
                cost_usd_cycle=1.50,
                selected_count=3,
            )
        )
        await resources.jobs.enqueue(
            EnqueueRequest(
                project_id=project.project_id,
                cycle=project.cycle,
                phase=Phase.INTAKE,
                kind="design.interview",
                idempotency_key=idempotency_key(
                    project.project_id, project.cycle, "design.interview", "1"
                ),
                requirement={},
            )
        )
        return project.project_id


def test_status_command_text_and_json(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_status_project(tmp_path))

    # Test text output
    res_text = runner.invoke(app, ["status", str(project_id)])
    assert res_text.exit_code == 0, res_text.output
    assert "ops-status-proj" in res_text.stdout
    assert "INTAKE" in res_text.stdout
    assert "claudeloop" in res_text.stdout

    # Test JSON output
    res_json = runner.invoke(app, ["status", "--json", str(project_id)])
    assert res_json.exit_code == 0, res_json.output
    payload = json.loads(res_json.stdout)
    assert payload["name"] == "ops-status-proj"
    assert payload["phase"] == "intake"
    assert payload["cycle"] == 1
    assert payload["queue_depth"]["ready"] == 1
    assert len(payload["circuits"]) == 1
    assert payload["circuits"][0]["engine_id"] == "claudeloop"


async def _seed_engines_project(tmp_path: Path) -> UUID:
    async with build_app() as resources:
        project = await resources.projects.create(
            "ops-engines-proj",
            tmp_path,
            max_cycles=5,
            config={"project": {"name": "ops-engines-proj"}},
        )
        health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
        await health_repo.upsert(
            EngineHealthRecord(
                project_id=project.project_id,
                engine_id=EngineId.CLAUDELOOP,
                installed=True,
                version="1.0.0",
                conformance_ok=True,
                conformance_at=datetime.now(UTC),
                auth_ok_at=datetime.now(UTC),
                circuit=CircuitState.CLOSED,
                capacity_state=None,
                resets_at=None,
                probe_next_at=None,
                probe_attempt=0,
                consecutive_fail=0,
                ewma_failure=0.0,
                cost_usd_cycle=2.00,
                selected_count=5,
            )
        )
        return project.project_id


def test_engines_command(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_engines_project(tmp_path))
    res = runner.invoke(app, ["engines", str(project_id)])
    assert res.exit_code == 0, res.output
    assert "claudeloop" in res.stdout
    assert "closed" in res.stdout
    assert "$2.00" in res.stdout


async def _seed_cost_project(tmp_path: Path, config: dict[str, object] | None = None) -> UUID:
    """A project whose spend is in the ledger -- $2.50 over one BUILD turn and
    $0.75 over one DESIGN turn -- while its engine_health row still says $0,
    the way it does in production today (issue #209)."""
    async with build_app() as resources:
        project = await resources.projects.create(
            "ops-cost-proj",
            tmp_path,
            max_cycles=5,
            config={"project": {"name": "ops-cost-proj"}, **(config or {})},
        )
        health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
        await health_repo.upsert(
            EngineHealthRecord(
                project_id=project.project_id,
                engine_id=EngineId.CLAUDELOOP,
                installed=True,
                version="1.0.0",
                conformance_ok=True,
                conformance_at=datetime.now(UTC),
                auth_ok_at=datetime.now(UTC),
                circuit=CircuitState.CLOSED,
                capacity_state=None,
                resets_at=None,
                probe_next_at=None,
                probe_attempt=0,
                consecutive_fail=0,
                ewma_failure=0.0,
                cost_usd_cycle=0.0,
                selected_count=4,
            )
        )
        spend = (
            (Phase.BUILD, EventKind.TURN_COMPLETED, {"verdict": "Done", "cost_usd": 2.5}),
            (Phase.DESIGN, EventKind.BUDGET_SPENT, {"dollars": 0.75, "turns": 1}),
        )
        for n, (phase, kind, payload) in enumerate(spend):
            await resources.ledger.append(
                LedgerEventDraft(
                    project_id=project.project_id,
                    cycle=project.cycle,
                    phase=phase,
                    kind=kind,
                    engine_id=None,
                    job_id=None,
                    causation_id=None,
                    correlation_id=project.project_id,
                    provenance=Provenance.TRUSTED,
                    produced_at=datetime.now(UTC),
                    payload=payload,
                    digest=f"cost-digest-{n}",
                )
            )
        return project.project_id


def test_cost_command_shows_the_enforced_caps_and_the_ledger_spend(tmp_path: Path) -> None:
    """The bug this guards (#210): `vibey cost` printed caps from a `budget`
    key nothing writes, so a project capped at $10 was shown "$40.00", and
    its spend came from engine_health, which is $0 in production."""
    project_id = asyncio.run(
        _seed_cost_project(tmp_path, {"max_cycle_dollars": 10.0, "max_cycle_turns": 50})
    )
    res = runner.invoke(app, ["cost", str(project_id)])
    assert res.exit_code == 0, res.output
    assert "Cycle spend:      $3.25 (2 turns)" in res.stdout
    assert "Cycle dollar cap: $10.00" in res.stdout
    assert "Cycle turn cap:   50" in res.stdout
    assert "Cap reached" not in res.stdout
    # Nothing enforces a lifetime cap, so none is printed.
    assert "Total Budget" not in res.stdout
    # The per-engine count is rotation selections, never labelled turns.
    assert "claudeloop: $0.00 (4 selections)" in res.stdout
    # The per-engine figure is metered BUILD spend that nothing resets (#209),
    # so it must not be labelled as this cycle's.
    assert "Per-engine (BUILD sessions, all cycles):" in res.stdout
    assert "current cycle" not in res.stdout


def test_cost_command_uncapped_ignores_the_legacy_budget_table(tmp_path: Path) -> None:
    project_id = asyncio.run(
        _seed_cost_project(
            tmp_path,
            {"budget": {"max_dollars_per_cycle": 40.0, "max_dollars_total": 250.0}},
        )
    )
    res = runner.invoke(app, ["cost", str(project_id)])
    assert res.exit_code == 0, res.output
    assert "Cycle dollar cap: none (uncapped)" in res.stdout
    assert "Cycle turn cap:   none" in res.stdout
    assert "$40.00" not in res.stdout
    assert "$250.00" not in res.stdout


def test_cost_command_says_when_the_cap_has_tripped(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_cost_project(tmp_path, {"max_cycle_dollars": 3}))
    res = runner.invoke(app, ["cost", str(project_id)])
    assert res.exit_code == 0, res.output
    assert "Cycle dollar cap: $3.00" in res.stdout
    assert "Cap reached: the next BUILD session parks a budget_exhausted gate." in res.stdout


async def _seed_ledger_project(tmp_path: Path) -> UUID:
    async with build_app() as resources:
        project = await resources.projects.create(
            "ops-ledger-proj",
            tmp_path,
            max_cycles=5,
            config={"project": {"name": "ops-ledger-proj"}},
        )
        await resources.ledger.append(
            LedgerEventDraft(
                project_id=project.project_id,
                cycle=project.cycle,
                phase=Phase.INTAKE,
                kind=EventKind.QUESTION_ASKED,
                engine_id=None,
                job_id=None,
                causation_id=None,
                correlation_id=project.project_id,
                provenance=Provenance.TRUSTED,
                produced_at=datetime.now(UTC),
                payload={"question_id": "q1", "text": "What is the goal?"},
                digest="test-digest-1",
            )
        )
        await resources.ledger.append(
            LedgerEventDraft(
                project_id=project.project_id,
                cycle=project.cycle,
                phase=Phase.INTAKE,
                kind=EventKind.ANSWER_GIVEN,
                engine_id=None,
                job_id=None,
                causation_id=None,
                correlation_id=project.project_id,
                provenance=Provenance.TRUSTED,
                produced_at=datetime.now(UTC),
                payload={"question_id": "q1", "answer": "Build a notes app"},
                digest="test-digest-2",
            )
        )
        return project.project_id


def test_ledger_show_command(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_ledger_project(tmp_path))
    res = runner.invoke(app, ["ledger", "show", str(project_id)])
    assert res.exit_code == 0, res.output
    assert "QuestionAsked" in res.stdout
    assert "AnswerGiven" in res.stdout
    assert "#1" in res.stdout
    assert "#2" in res.stdout


def test_watch_command_with_no_projects() -> None:
    """Watch command exits gracefully when no projects exist."""
    from unittest.mock import AsyncMock, patch

    # Mock the TUI app so it doesn't actually start
    with patch("vibey.tui.dashboard.VibeyDashboardApp") as mock_app:
        mock_app.return_value.run_async = AsyncMock()
        res = runner.invoke(app, ["watch"])
        assert res.exit_code == 1, res.output
        assert "no projects found" in res.output


def test_watch_command_with_unknown_project_id() -> None:
    """Watch command exits gracefully for unknown project ID."""
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    unknown_id = uuid4()
    with patch("vibey.tui.dashboard.VibeyDashboardApp") as mock_app:
        mock_app.return_value.run_async = AsyncMock()
        res = runner.invoke(app, ["watch", str(unknown_id)])
        assert res.exit_code == 1, res.output
        assert "unknown project" in res.output


# ── "use latest" paths ──────────────────────────────────────────────────────


def test_status_uses_latest_project_when_no_id_given(tmp_path: Path) -> None:
    asyncio.run(_seed_status_project(tmp_path))
    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0, res.output
    assert "ops-status-proj" in res.stdout


def test_status_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["status"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_engines_uses_latest_project_when_no_id_given(tmp_path: Path) -> None:
    asyncio.run(_seed_engines_project(tmp_path))
    res = runner.invoke(app, ["engines"])
    assert res.exit_code == 0, res.output
    assert "claudeloop" in res.stdout


def test_engines_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["engines"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_engines_with_no_engines_recorded(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("empty-eng", tmp_path, max_cycles=1, config={})
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["engines", str(pid)])
    assert res.exit_code == 0, res.output
    assert "no engines recorded" in res.output


def test_cost_uses_latest_project_when_no_id_given(tmp_path: Path) -> None:
    asyncio.run(_seed_cost_project(tmp_path))
    res = runner.invoke(app, ["cost"])
    assert res.exit_code == 0, res.output
    assert "ops-cost-proj" in res.stdout
    assert "Cycle dollar cap: none (uncapped)" in res.stdout


def test_cost_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["cost"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_cost_unknown_project_exits_with_error() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["cost", str(uuid4())])
    assert res.exit_code == 1
    assert "unknown project" in res.output


def test_ledger_no_subcommand_shows_help() -> None:
    res = runner.invoke(app, ["ledger"])
    assert res.exit_code == 0
    assert "show" in res.output.lower()


def test_ledger_show_uses_latest_project_when_no_id_given(tmp_path: Path) -> None:
    asyncio.run(_seed_ledger_project(tmp_path))
    res = runner.invoke(app, ["ledger", "show"])
    assert res.exit_code == 0, res.output
    assert "QuestionAsked" in res.stdout


def test_ledger_show_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["ledger", "show"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_ledger_show_with_phase_filter(tmp_path: Path) -> None:
    pid = asyncio.run(_seed_ledger_project(tmp_path))
    res = runner.invoke(app, ["ledger", "show", str(pid), "--phase", "intake"])
    assert res.exit_code == 0, res.output
    assert "INTAKE" in res.stdout


def test_ledger_show_with_kind_filter(tmp_path: Path) -> None:
    pid = asyncio.run(_seed_ledger_project(tmp_path))
    res = runner.invoke(app, ["ledger", "show", str(pid), "--kind", "QuestionAsked"])
    assert res.exit_code == 0, res.output
    assert "QuestionAsked" in res.stdout
    assert "AnswerGiven" not in res.stdout
    by_name = runner.invoke(app, ["ledger", "show", str(pid), "--kind", "answer_given"])
    assert "AnswerGiven" in by_name.stdout
    assert "QuestionAsked" not in by_name.stdout
    assert by_name.stderr == ""


async def _seed_ledger_project_with_a_newer_kind(tmp_path: Path) -> UUID:
    pid = await _seed_ledger_project(tmp_path)
    async with build_app() as resources, resources.ledger._pool.acquire() as conn:
        # A newer vibey's appender, through the same SQL function.
        await conn.execute(
            "SELECT append_event($1, 1, 'intake', 'FutureKindX', NULL, NULL, NULL, $1, "
            "'agent', now(), '{}'::jsonb, 'test-digest-3')",
            pid,
        )
    return pid


def test_ledger_show_reads_a_kind_this_vibey_does_not_know(tmp_path: Path) -> None:
    """vibey#275: one row a newer vibey wrote used to crash `ledger show`."""
    pid = asyncio.run(_seed_ledger_project_with_a_newer_kind(tmp_path))

    res = runner.invoke(app, ["ledger", "show", str(pid)])
    assert res.exit_code == 0, res.output
    assert "[INTAKE] FutureKindX" in res.stdout

    only = runner.invoke(app, ["ledger", "show", str(pid), "--kind", "FutureKindX"])
    assert only.exit_code == 0, only.output
    assert "#3" in only.stdout
    assert "QuestionAsked" not in only.stdout
    assert "'FutureKindX' is not an event kind this vibey knows" in only.stderr


def test_ledger_show_refuses_an_empty_kind_before_connecting() -> None:
    res = runner.invoke(app, ["ledger", "show", "--kind", " "])
    assert res.exit_code == 2
    assert "unknown event kind" in res.output


def test_status_with_no_engines_shows_no_engines_message(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("no-eng-proj", tmp_path, max_cycles=1, config={})
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["status", str(pid)])
    assert res.exit_code == 0, res.output
    assert "no engines recorded" in res.output


# ── deploy commands without project_id and with unknown project ─────────────


def test_deploy_status_uses_latest_project(tmp_path: Path) -> None:
    from tests.cli.test_deploy_cli import _seed_deploy_project

    asyncio.run(_seed_deploy_project(tmp_path))
    res = runner.invoke(app, ["deploy", "status"])
    assert res.exit_code == 0, res.output
    assert "deploy-cli-proj" in res.stdout


def test_deploy_status_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["deploy", "status"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_deploy_status_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["deploy", "status", str(uuid4())])
    assert res.exit_code == 1
    assert "unknown project" in res.output


def test_deploy_inspect_uses_latest_project(tmp_path: Path) -> None:
    from tests.cli.test_deploy_cli import _seed_deploy_project

    asyncio.run(_seed_deploy_project(tmp_path))
    res = runner.invoke(app, ["deploy", "inspect"])
    assert res.exit_code == 0, res.output
    assert "spec_id" in res.output


def test_deploy_inspect_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["deploy", "inspect"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_deploy_inspect_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["deploy", "inspect", str(uuid4())])
    assert res.exit_code == 1
    assert "unknown project" in res.output


def test_deploy_plan_uses_latest_project(tmp_path: Path) -> None:
    from tests.cli.test_deploy_cli import _seed_deploy_project

    asyncio.run(_seed_deploy_project(tmp_path))
    res = runner.invoke(app, ["deploy", "plan"])
    assert res.exit_code == 0, res.output
    assert "Plan Evaluation" in res.output


def test_deploy_plan_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["deploy", "plan"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_deploy_plan_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["deploy", "plan", str(uuid4())])
    assert res.exit_code == 1
    assert "unknown project" in res.output


def test_deploy_cancel_uses_latest_project(tmp_path: Path) -> None:
    from tests.cli.test_deploy_cli import _seed_deploy_project

    asyncio.run(_seed_deploy_project(tmp_path))
    res = runner.invoke(app, ["deploy", "cancel"])
    assert res.exit_code == 0, res.output
    assert "cancelled" in res.output.lower()


def test_deploy_cancel_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["deploy", "cancel"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_deploy_cancel_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["deploy", "cancel", str(uuid4())])
    assert res.exit_code == 1
    assert "unknown project" in res.output


def test_deploy_rollback_uses_latest_project(tmp_path: Path) -> None:
    from tests.cli.test_deploy_cli import _seed_deploy_project

    asyncio.run(_seed_deploy_project(tmp_path))
    res = runner.invoke(app, ["deploy", "rollback"])
    assert res.exit_code == 0, res.output
    assert "rollback" in res.output.lower()


def test_deploy_rollback_no_projects_exits_with_error() -> None:
    res = runner.invoke(app, ["deploy", "rollback"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_deploy_rollback_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["deploy", "rollback", str(uuid4())])
    assert res.exit_code == 1
    assert "unknown project" in res.output


# ── _work_once and _enqueue_design error paths ──────────────────────────────


def test_work_once_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["work", str(uuid4())])
    assert res.exit_code != 0


def test_work_once_unknown_provider(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("prov-test", tmp_path, max_cycles=1, config={})
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["work", str(pid), "--provider", "nonexistent"])
    assert res.exit_code != 0


def test_work_once_visual_phase_rejects_non_scripted_provider(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("vis-test", tmp_path, max_cycles=1, config={})
            await resources.projects.transition(
                p.project_id, expected=Phase.INTAKE, to=Phase.VISUAL_DESIGN
            )
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["work", str(pid), "--provider", "claudeloop"])
    assert res.exit_code != 0


def test_work_once_claudeloop_provider(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("cl-test", tmp_path, max_cycles=1, config={})
            await resources.projects.transition(
                p.project_id, expected=Phase.INTAKE, to=Phase.DESIGN
            )
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["work", str(pid), "--provider", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


def test_work_once_qwenloop_provider(tmp_path: Path) -> None:
    """--provider qwenloop (8.a's sovereign path) on the one-shot `work` command, with
    no VIBEY_EVIDENCE_DIR set — mirrors test_work_once_claudeloop_provider."""

    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create(
                "qwenloop-work-test", tmp_path, max_cycles=1, config={}
            )
            await resources.projects.transition(
                p.project_id, expected=Phase.INTAKE, to=Phase.DESIGN
            )
            return p.project_id

    pid = asyncio.run(seed())
    from unittest.mock import patch

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("VIBEY_EVIDENCE_DIR", None)
        res = runner.invoke(app, ["work", str(pid), "--provider", "qwenloop"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


def test_work_once_qwenloop_provider_picks_up_evidence_dir(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create(
                "qwenloop-work-evidence", tmp_path, max_cycles=1, config={}
            )
            await resources.projects.transition(
                p.project_id, expected=Phase.INTAKE, to=Phase.DESIGN
            )
            return p.project_id

    pid = asyncio.run(seed())
    from unittest.mock import patch

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    with patch.dict(os.environ, {"VIBEY_EVIDENCE_DIR": str(evidence_dir)}):
        res = runner.invoke(app, ["work", str(pid), "--provider", "qwenloop"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


def test_enqueue_design_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["design", "resume", str(uuid4())])
    assert res.exit_code != 0


def test_enqueue_design_wrong_phase(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("phase-test", tmp_path, max_cycles=1, config={})
            await resources.projects.transition(p.project_id, expected=Phase.INTAKE, to=Phase.BUILD)
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["design", "resume", str(pid)])
    assert res.exit_code != 0


def test_accept_design_unknown_project() -> None:
    from uuid import uuid4

    res = runner.invoke(app, ["design", "accept", str(uuid4())])
    assert res.exit_code != 0


def test_accept_design_with_spec_json(tmp_path: Path) -> None:
    import json as _json

    spec_json = tmp_path / "spec.json"
    spec_data = {
        "objective": "Ship",
        "constraints": [{"text": "Offline", "kind": "hard"}],
        "non_goals": [],
        "criteria": [
            {
                "criterion_id": "AC-1",
                "given": "input",
                "when": "run",
                "then": "output",
                "fit": "passes",
            }
        ],
        "nfrs": [],
        "walking_skeleton": "path",
    }
    spec_json.write_text(_json.dumps(spec_data))

    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create(
                "spec-accept", tmp_path / "repo", max_cycles=1, config={}
            )
            await resources.projects.transition(
                p.project_id, expected=Phase.INTAKE, to=Phase.DESIGN
            )
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["design", "accept", str(pid), "--spec-json", str(spec_json)])
    assert res.exit_code == 0, res.output
    assert "accepted design" in res.output


# ── watch command with real project ──────────────────────────────────────────


def test_watch_with_replay(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    pid = asyncio.run(_seed_ledger_project(tmp_path))
    with patch("vibey.tui.dashboard.VibeyReplayApp") as mock_replay:
        mock_replay.return_value.run_async = AsyncMock()
        res = runner.invoke(app, ["watch", str(pid), "--replay"])
        assert res.exit_code == 0, res.output
        mock_replay.assert_called_once()


def test_watch_with_latest_project(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    asyncio.run(_seed_status_project(tmp_path))
    with patch("vibey.tui.dashboard.VibeyDashboardApp") as mock_app_cls:
        mock_app_cls.return_value.run_async = AsyncMock()
        res = runner.invoke(app, ["watch"])
        assert res.exit_code == 0, res.output
        mock_app_cls.assert_called_once()


def test_watch_with_explicit_project(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    pid = asyncio.run(_seed_status_project(tmp_path))
    with patch("vibey.tui.dashboard.VibeyDashboardApp") as mock_app_cls:
        mock_app_cls.return_value.run_async = AsyncMock()
        res = runner.invoke(app, ["watch", str(pid)])
        assert res.exit_code == 0, res.output
        mock_app_cls.assert_called_once()


# ── deploy status/inspect branch coverage ────────────────────────────────────


def test_deploy_status_no_deployment_events(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("no-dep-ev", tmp_path, max_cycles=1, config={})
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["deploy", "status", str(pid)])
    assert res.exit_code == 0, res.output
    assert "(none)" in res.output


def test_deploy_status_event_without_endpoint(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("no-endpoint", tmp_path, max_cycles=1, config={})
            await resources.ledger.append(
                LedgerEventDraft(
                    project_id=p.project_id,
                    cycle=p.cycle,
                    phase=Phase.INTAKE,
                    kind=EventKind.ARTIFACT_PRODUCED,
                    engine_id=None,
                    job_id=None,
                    causation_id=None,
                    correlation_id=p.project_id,
                    provenance=Provenance.TRUSTED,
                    produced_at=datetime.now(UTC),
                    payload={
                        "artifact_type": "deployment_verification",
                        "outputs": {"status": "ok"},
                    },
                    digest="test",
                )
            )
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["deploy", "status", str(pid)])
    assert res.exit_code == 0, res.output
    assert "(none)" in res.output


def test_deploy_inspect_no_spec_events(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("no-spec-ev", tmp_path, max_cycles=1, config={})
            return p.project_id

    pid = asyncio.run(seed())
    res = runner.invoke(app, ["deploy", "inspect", str(pid)])
    assert res.exit_code == 0, res.output
    assert "default" in res.output


# ── doctor command ────────────────────────────────────────────────────────────


def test_doctor_basic_lists_all_engines() -> None:
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0, res.output
    assert "claudeloop" in res.output
    assert "postgresql" in res.output


def test_install_requires_an_explicit_postgres_target() -> None:
    res = runner.invoke(app, ["install"])

    assert res.exit_code == 2
    assert "install --postgres" in res.output


def test_install_postgres_reports_success() -> None:
    from unittest.mock import patch

    from vibey.infrastructure.postgres import PostgresInstallResult, PostgresVersion

    status = PostgresStatus(
        installed=True,
        running=True,
        supported=True,
        version=PostgresVersion(18, 4),
        detail="PostgreSQL 18.4 is accepting local connections",
    )
    result = PostgresInstallResult(
        ok=True, changed=True, detail="installed", status=status, commands=()
    )
    with patch("vibey.cli.main.PostgresLocalService") as service_cls:
        service_cls.return_value.install.return_value = result
        res = runner.invoke(app, ["install", "--postgres"])

    assert res.exit_code == 0, res.output
    service_cls.return_value.install.assert_called_once_with()
    assert "READY" in res.output
    assert "VIBEY_PG_URL" in res.output


def test_install_postgres_reports_failure() -> None:
    from unittest.mock import patch

    from vibey.infrastructure.postgres import PostgresInstallResult

    status = PostgresStatus(False, False, False, None, "no package manager")
    result = PostgresInstallResult(
        ok=False, changed=False, detail="no package manager", status=status, commands=()
    )
    with patch("vibey.cli.main.PostgresLocalService") as service_cls:
        service_cls.return_value.install.return_value = result
        res = runner.invoke(app, ["install", "--postgres"])

    assert res.exit_code == 1
    assert "no package manager" in res.output


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (PostgresStatus(True, False, False, None, "unsupported"), "UNSUPPORTED"),
        (PostgresStatus(True, False, True, None, "stopped"), "NOT READY"),
    ],
)
def test_postgres_status_line_reports_unready_states(status: PostgresStatus, expected: str) -> None:
    from vibey.cli.main import _postgres_status_line

    assert expected in _postgres_status_line(status)


def test_doctor_can_install_postgres_explicitly() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult
    from vibey.infrastructure.postgres import PostgresInstallResult, PostgresVersion

    status = PostgresStatus(
        installed=True,
        running=True,
        supported=True,
        version=PostgresVersion(18, 4),
        detail="PostgreSQL 18.4 is accepting local connections",
    )
    result = PostgresInstallResult(True, True, "installed", status, ())
    with (
        patch("vibey.cli.main.PostgresLocalService") as service_cls,
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(return_value=PreflightResult(installed=True, version="1", auth_ok=True)),
        ),
    ):
        service_cls.return_value.install.return_value = result
        res = runner.invoke(app, ["doctor", "--install-postgres", "--engine", "claudeloop"])

    assert res.exit_code == 0, res.output
    service_cls.return_value.install.assert_called_once_with()
    assert "postgresql" in res.output
    assert "READY" in res.output


def test_doctor_install_postgres_failure_exits_one() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult
    from vibey.infrastructure.postgres import PostgresInstallResult

    status = PostgresStatus(False, False, False, None, "could not install")
    result = PostgresInstallResult(False, True, "could not install", status, ())
    with (
        patch("vibey.cli.main.PostgresLocalService") as service_cls,
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(return_value=PreflightResult(installed=True, version="1", auth_ok=True)),
        ),
    ):
        service_cls.return_value.install.return_value = result
        res = runner.invoke(app, ["doctor", "--install-postgres", "--engine", "claudeloop"])

    assert res.exit_code == 1
    assert "could not install" in res.output


def test_cluster_doctor_rejects_local_postgres_install_flag() -> None:
    res = runner.invoke(app, ["doctor", "--cluster", "--install-postgres"])

    assert res.exit_code == 2
    assert "local doctor" in res.output


def listed_engines(output: str) -> set[str]:
    """The engine names `doctor` LISTED, which is not the same as the words it printed.

    `"qwenloop" in res.output` is a claim about the whole report, and the report opens with
    the working directory. Run the suite from a checkout whose path happens to contain an
    engine's name -- `/private/tmp/.../lane/harness-T20a-qwenloop-shell-timeout-config`, say,
    which is exactly what a storm lane for that engine is called -- and the omission test
    fails against a substring of a filesystem path while the engine table is perfectly
    correct. The test was true about the output and wrong about the thing it names, and it
    will bite every lane whose slug mentions an engine.

    An engine row begins with the engine's name at column 0, so that is what is read.
    """
    return {line.split()[0] for line in output.splitlines() if line[:1].isalnum() and line.split()}


def test_doctor_lists_the_sovereign_engine_when_it_is_switched_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Doctrine 8.a makes the sovereign path the preferred way to run. The worker already
    honoured `VIBEY_FEATURE_QWENLOOP`, but `doctor` read DEFAULT_DESCRIPTORS directly — so
    the one command whose job is answering "is my engine healthy?" could not see the engine
    the operator was depending on, unless they already knew to ask for it by name. A
    preferred path you cannot inspect is not a preferred path.
    """
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "1")
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0, res.output
    assert "qwenloop" in listed_engines(res.output)
    assert "claudeloop" in listed_engines(res.output)  # the paid engines are still listed


def test_doctor_omits_the_sovereign_engine_when_it_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "0")
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0, res.output
    assert "qwenloop" not in listed_engines(res.output)


@pytest.mark.parametrize(
    "value, expected",
    [("1", True), ("true", True), ("YES", True), ("on", True), ("0", False), ("nope", False)],
)
def test_the_feature_flag_reads_the_environment_first(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    from vibey.cli.main import _local_engines_from_toml
    from vibey.domain.engine import EngineId

    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", value)
    assert _local_engines_from_toml().enabled(EngineId.QWENLOOP) is expected


def test_the_feature_flag_falls_back_to_project_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same resolver as the worker's, so the health check and the worker can never
    disagree about which engines exist."""
    from vibey.cli.main import _local_engines_from_toml
    from vibey.domain.engine import EngineId

    def on(engine_id: EngineId) -> bool:
        return _local_engines_from_toml(tmp_path).enabled(engine_id)

    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    monkeypatch.delenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", raising=False)
    assert on(EngineId.QWENLOOP) is False  # no config at all

    (tmp_path / "vibey.toml").write_text(
        "[features]\nqwenloop = true\nclaudeloop_local = true\n", encoding="utf-8"
    )
    assert on(EngineId.QWENLOOP) is True
    assert on(EngineId.CLAUDELOOP_LOCAL) is True

    (tmp_path / "vibey.toml").write_text("[features]\nqwenloop = false\n", encoding="utf-8")
    assert on(EngineId.QWENLOOP) is False

    (tmp_path / "vibey.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    assert on(EngineId.QWENLOOP) is False  # no features table

    # A malformed config reports "off" rather than crashing a health check.
    (tmp_path / "vibey.toml").write_text("this is not toml {{{", encoding="utf-8")
    assert on(EngineId.QWENLOOP) is False


def test_doctor_lists_claudeloop_local_when_it_is_switched_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The second local engine is as visible as the first: doctor lists it, and probes
    it with its profile -- the backend its runs will use, not an Anthropic login."""
    from unittest.mock import patch

    from vibey.application.dto import PreflightResult

    monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "1")
    monkeypatch.setenv("VIBEY_CLAUDELOOP_LOCAL_PROFILE", "ollama")
    seen: list[tuple[str, ...]] = []

    async def preflight(self):  # type: ignore[no-untyped-def]
        seen.append((self.descriptor.engine_id.value, *self.descriptor.doctor_args))
        return PreflightResult(installed=True, version="0.8.0", auth_ok=True)

    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=preflight,
    ):
        res = runner.invoke(app, ["doctor"])

    assert res.exit_code == 0, res.output
    assert "claudeloop-local" in res.output
    assert ("claudeloop-local", "--profile", "ollama") in seen
    assert ("claudeloop",) in seen  # the paid engines are still listed


def test_doctor_omits_claudeloop_local_when_it_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "0")
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1", auth_ok=True)),
    ):
        res = runner.invoke(app, ["doctor"])

    assert res.exit_code == 0, res.output
    assert "claudeloop-local" not in res.output


def test_doctor_can_be_asked_for_claudeloop_local_by_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    monkeypatch.delenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", raising=False)
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1", auth_ok=True)),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "claudeloop-local"])

    assert res.exit_code == 0, res.output
    assert res.output.startswith("claudeloop-local")


def test_doctor_specific_engine() -> None:
    res = runner.invoke(app, ["doctor", "--engine", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "claudeloop" in res.output


def test_doctor_unknown_engine() -> None:
    res = runner.invoke(app, ["doctor", "--engine", "nonexistent"])
    assert res.exit_code == 1


def test_doctor_no_detail_skips_detail_line() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    fake_result = PreflightResult(installed=True, auth_ok=True, version="1.0.0", detail="")
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=fake_result),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "detail:" not in res.output
    assert "installed" in res.output


def test_doctor_shows_detail_when_present() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    fake_result = PreflightResult(
        installed=False, auth_ok=False, version=None, detail="claude not found in PATH"
    )
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=fake_result),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "detail:" in res.output
    assert "claude not found in PATH" in res.output


def test_doctor_with_conformance() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import ConformanceCheckResult, ConformanceReport, PreflightResult
    from vibey.domain.engine import EngineId

    fake_report = ConformanceReport(
        engine_id=EngineId.CLAUDELOOP,
        checks=(
            ConformanceCheckResult(name="preflight", ok=True),
            ConformanceCheckResult(name="start_stop", ok=True),
        ),
    )
    # preflight() must also be mocked: the CLI only calls run_conformance
    # when preflight.installed is True, and a CI runner has no engine
    # binaries on PATH -- leaving this real makes the test pass only on a
    # machine that happens to have claudeloop installed.
    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(
                return_value=PreflightResult(installed=True, version="0.5.5", auth_ok=True)
            ),
        ),
        patch(
            "vibey.application.conformance.run_conformance",
            new=AsyncMock(return_value=fake_report),
        ),
    ):
        res = runner.invoke(app, ["doctor", "--conformance", "--engine", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "PASS" in res.output


def test_doctor_with_conformance_failure() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import ConformanceCheckResult, ConformanceReport, PreflightResult
    from vibey.domain.engine import EngineId

    fake_report = ConformanceReport(
        engine_id=EngineId.CLAUDELOOP,
        checks=(
            ConformanceCheckResult(name="preflight", ok=True),
            ConformanceCheckResult(name="start_stop", ok=False, detail="timed out"),
        ),
    )
    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(
                return_value=PreflightResult(installed=True, version="0.5.5", auth_ok=True)
            ),
        ),
        patch(
            "vibey.application.conformance.run_conformance",
            new=AsyncMock(return_value=fake_report),
        ),
    ):
        res = runner.invoke(app, ["doctor", "--conformance", "--engine", "claudeloop"])
    assert res.exit_code == 1
    assert "FAIL" in res.output
    assert "timed out" in res.output


# ── worker command ────────────────────────────────────────────────────────────


@pytest.fixture()
def _fast_engine_preflight():  # type: ignore[no-untyped-def]
    """The worker's startup preflight sweep would otherwise spawn real
    engine subprocesses (doctor runs) in every worker CLI test."""
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1.0.0", auth_ok=True)),
    ):
        yield


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_once_no_job(tmp_path: Path) -> None:
    async def seed_empty() -> None:
        async with build_app() as resources:
            await resources.projects.create("empty-worker", tmp_path, max_cycles=1, config={})

    asyncio.run(seed_empty())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier = AsyncMock()
        mock_notifier_cls.return_value = mock_notifier
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_once_with_job(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("worker-proj", tmp_path, max_cycles=1, config={})
            from vibey.domain.job import idempotency_key

            await resources.jobs.enqueue(
                EnqueueRequest(
                    project_id=p.project_id,
                    cycle=p.cycle,
                    phase=Phase.INTAKE,
                    kind="test.work",
                    idempotency_key=idempotency_key(p.project_id, p.cycle, "test.work", "1"),
                    requirement={},
                )
            )
            return p.project_id

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier = AsyncMock()
        mock_notifier_cls.return_value = mock_notifier
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 0, res.output
    assert "processed one job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_drains_at_once_when_sigterm_arrived_during_startup(tmp_path: Path) -> None:
    """A signal delivered before the event loop existed still has to stop the worker.

    Linux discards SIGTERM sent to PID 1 while its disposition is still SIG_DFL -- it is
    not queued. A worker that only ever asks the event loop therefore never learns that
    Kubernetes asked it to stop, and runs to its grace period: two hours. Observed on
    minikube, where a pod deleted 0.2s after its container started sat out the whole
    window claiming jobs nobody was waiting for.

    So the latch armed at import is consulted once the real handler is in place. Note the
    worker is started WITHOUT `--once`: the point is that a long-lived worker stops, not
    that a single-shot one finishes.
    """

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("drain-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    class _AlreadyFired:
        fired = True

        def release(self) -> None:
            """The real handler is installed by now; nothing to hand back in a test."""

    with (
        patch("vibey.cli.main.SIGTERM_LATCH", _AlreadyFired()),
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls,
    ):
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker"])

    assert res.exit_code == 0, res.output
    assert "SIGTERM arrived during startup" in res.output
    assert "draining flag observed" in res.output
    # It must not have claimed anything on the way out.
    assert "processed one job" not in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_unknown_kind_burns_an_attempt(tmp_path: Path) -> None:
    """The dispatcher rejects unknown kinds as VIBEY failures -- the poison
    path is now a feature to assert, not the stub's silent ack."""

    async def seed() -> UUID:
        async with build_app() as resources:
            p = await resources.projects.create("poison-proj", tmp_path, max_cycles=1, config={})
            from vibey.domain.job import idempotency_key

            job = await resources.jobs.enqueue(
                EnqueueRequest(
                    project_id=p.project_id,
                    cycle=p.cycle,
                    phase=Phase.INTAKE,
                    kind="test.work",
                    idempotency_key=idempotency_key(p.project_id, p.cycle, "test.work", "1"),
                    requirement={},
                )
            )
            return job.id

    job_id = asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 0, res.output
    assert "processed one job" in res.output

    async def inspect() -> tuple[int, str]:
        async with build_app() as resources:
            job = await resources.jobs.get(job_id)
            assert job is not None
            assert job.last_error is not None
            return job.attempts, str(job.last_error)

    attempts, error = asyncio.run(inspect())
    assert attempts == 1
    assert "no handler registered" in error


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_no_projects() -> None:
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier = AsyncMock()
        mock_notifier_cls.return_value = mock_notifier
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_continuous_processes_then_waits(tmp_path: Path) -> None:
    async def seed() -> None:
        async with build_app() as resources:
            p = await resources.projects.create("cont-worker", tmp_path, max_cycles=1, config={})
            from vibey.domain.job import idempotency_key as idem_key

            await resources.jobs.enqueue(
                EnqueueRequest(
                    project_id=p.project_id,
                    cycle=p.cycle,
                    phase=Phase.INTAKE,
                    kind="test.work",
                    idempotency_key=idem_key(p.project_id, p.cycle, "test.work", "1"),
                    requirement={},
                )
            )

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier = AsyncMock()
        mock_notifier.wait_for_job_ready = AsyncMock(side_effect=KeyboardInterrupt)
        mock_notifier_cls.return_value = mock_notifier
        res = runner.invoke(app, ["worker"])
    assert "processed one job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_invalid_engine() -> None:
    res = runner.invoke(app, ["worker", "--engines", "nonexistent"])
    assert res.exit_code == 2


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_invalid_provider() -> None:
    res = runner.invoke(app, ["worker", "--provider", "nonexistent"])
    assert res.exit_code == 2
    assert "provider must be 'scripted', 'claudeloop', or 'gptossloop'" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_project_flag_selects_that_project(tmp_path: Path) -> None:
    async def seed() -> UUID:
        async with build_app() as resources:
            older = await resources.projects.create(
                "older-proj", tmp_path / "older", max_cycles=1, config={}
            )
            await resources.projects.create(
                "newer-proj", tmp_path / "newer", max_cycles=1, config={}
            )
            return older.project_id

    older_id = asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--project", str(older_id)])
    assert res.exit_code == 0, res.output
    assert "project=older-proj" in res.output
    assert "no ready job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_unknown_project_exits_1(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch
    from uuid import uuid4

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("some-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--project", str(uuid4())])
    assert res.exit_code == 1
    assert "no projects found" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_engines_allow_list_with_claudeloop(tmp_path: Path) -> None:
    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("eng-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--engines", "claudeloop,agyloop"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_engines_allow_list_without_claudeloop(tmp_path: Path) -> None:
    """The implementer falls back to the first allowed engine when
    claudeloop isn't in the allow list."""

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("eng2-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--engines", "agyloop"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_refuses_an_allow_list_that_matches_no_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--engines qwenloop` without the feature switch used to start a worker holding
    zero adapters, which then deferred every engine-driven job every five minutes,
    silently, forever. Nothing downstream can recover from that, so the allow-list has
    to be refused at startup -- with the reason and the switch that fixes it."""
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("no-engine-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--engines", "qwenloop"])
    assert res.exit_code == 2, res.output
    assert "matches none of this worker's engines" in res.output
    assert "claudeloop" in res.output
    assert "VIBEY_FEATURE_QWENLOOP=1" in res.output
    assert "worker started" not in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_sweeps_qwenloop_when_the_feature_is_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the feature on, qwenloop is an engine this worker really runs, so it has to
    be preflighted and warned about like every other one. It was the single engine the
    startup sweep could not see: the worker selected it while its health row stayed
    empty, so the operator depending on it had no way to learn it was ineligible."""
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "1")

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("standby-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--engines", "qwenloop"])
    assert res.exit_code == 0, res.output
    assert "no recorded conformance for qwenloop" in res.output
    assert "no ready job" in res.output

    async def check() -> tuple[str, ...]:
        async with build_app() as resources:
            latest = await resources.projects.get_latest()
            assert latest is not None
            records = await resources.engine_health_service.list_for_project(latest.project_id)
            return tuple(sorted(r.engine_id.value for r in records))

    assert asyncio.run(check()) == ("qwenloop",)


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_sweeps_claudeloop_local_when_its_feature_is_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same resolver adds the second local engine to the pool the startup sweep
    preflights -- and, with no --provider, runs DESIGN/DECOMPOSE on the sovereign
    providers (8.a, #115 B5)."""
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "1")

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("local-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--engines", "claudeloop-local"])
    assert res.exit_code == 0, res.output
    assert "no recorded conformance for claudeloop-local" in res.output
    assert "provider=gptossloop" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_defaults_to_the_sovereign_providers_from_the_project_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    monkeypatch.delenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", raising=False)

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create(
                "config-proj",
                tmp_path,
                max_cycles=1,
                config={"features": {"qwenloop": True}},
            )

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 0, res.output
    assert "provider=gptossloop" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_an_explicit_provider_still_wins_over_the_sovereign_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "1")

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("explicit-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--provider", "scripted"])
    assert res.exit_code == 0, res.output
    assert "provider=scripted" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_with_no_local_engine_the_default_provider_is_gptossloop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIBEY_FEATURE_GPTOSSLOOP", "0")
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    monkeypatch.delenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", raising=False)

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("paid-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once"])
    # #322 (sub-doctrine 8.b): the sovereign pair is always on, so no switch is needed.
    assert res.exit_code == 0, res.output
    assert "provider=gptossloop" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_provider_claudeloop_constructs_live_providers(tmp_path: Path) -> None:
    """--provider claudeloop builds the live design provider without any
    subprocess spawn at construction time."""

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("live-prov-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--provider", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "provider=claudeloop" in res.output
    assert "no ready job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_refuses_the_deleted_opencode_provider() -> None:
    """The OpenCode provider was deleted with its engine (sub-doctrine 8.b): naming it is
    refused like any other unknown provider, before anything is built."""
    res = runner.invoke(app, ["worker", "--once", "--provider", "opencode"])
    assert res.exit_code == 2
    assert "provider must be 'scripted', 'claudeloop', or 'gptossloop'" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_provider_gptossloop_constructs_live_providers(tmp_path: Path) -> None:
    """--provider gptossloop (8.a's sovereign path) builds the live design provider
    without any network call at construction time, with no evidence dir configured."""

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("qwenloop-prov-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with (
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls,
        patch.dict(os.environ, {}, clear=False),
    ):
        os.environ.pop("VIBEY_EVIDENCE_DIR", None)
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--provider", "gptossloop"])
    assert res.exit_code == 0, res.output
    assert "provider=gptossloop" in res.output
    assert "is now --provider" not in res.output
    assert "no ready job" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_provider_qwenloop_picks_up_evidence_dir(tmp_path: Path) -> None:
    """VIBEY_EVIDENCE_DIR is how the operator hands the sovereign research stage its
    reading; --provider qwenloop must actually read it rather than ignore it. `qwenloop`
    is the provider's old name, read as gptossloop and said so (ADR-0061)."""

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create(
                "qwenloop-evidence-proj", tmp_path, max_cycles=1, config={}
            )

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    with (
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls,
        patch.dict(os.environ, {"VIBEY_EVIDENCE_DIR": str(evidence_dir)}),
    ):
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once", "--provider", "qwenloop"])
    assert res.exit_code == 0, res.output
    assert "provider=gptossloop" in res.output
    assert "--provider qwenloop is now --provider gptossloop (ADR-0061)" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_parallelism_spawns_gathered_loops(tmp_path: Path) -> None:
    """-j 2 continuous takes the gather branch; the mocked notifier's
    KeyboardInterrupt ends the run once both loops go idle."""

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("par-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier = AsyncMock()
        mock_notifier.wait_for_job_ready = AsyncMock(side_effect=KeyboardInterrupt)
        mock_notifier_cls.return_value = mock_notifier
        res = runner.invoke(app, ["worker", "-j", "2"])
    assert "parallelism=2" in res.output


# ── watch state_fetcher coverage ──────────────────────────────────────────────


def test_watch_state_fetcher_is_invoked(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    pid = asyncio.run(_seed_status_project(tmp_path))
    fetcher_called = False

    with patch("vibey.tui.dashboard.VibeyDashboardApp") as mock_app_cls:

        def capture_init(**kwargs: object) -> AsyncMock:
            fetcher = kwargs.get("state_fetcher")

            async def run_async_calls_fetcher() -> None:
                nonlocal fetcher_called
                if fetcher is not None:
                    await fetcher()
                    fetcher_called = True

            m = AsyncMock()
            m.run_async = run_async_calls_fetcher
            return m

        mock_app_cls.side_effect = capture_init
        res = runner.invoke(app, ["watch", str(pid)])
        assert res.exit_code == 0, res.output
    assert fetcher_called


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_warns_about_engines_without_conformance(tmp_path: Path) -> None:
    """The sweep records preflight but never grants conformance -- until
    doctor --conformance --record runs, engine-driven jobs can't select."""

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("sweep-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 0, res.output
    assert "no recorded conformance" in res.output
    assert "doctor --conformance --record" in res.output
    assert "preflight feasibility: INFEASIBLE" in res.output
    assert "first repair: agent.availability" in res.output

    async def check() -> int:
        async with build_app() as resources:
            latest = await resources.projects.get_latest()
            assert latest is not None
            records = await resources.engine_health_service.list_for_project(latest.project_id)
            assert all(r.installed for r in records)
            assert all(not r.conformance_ok for r in records)
            return len(records)

    # The four paid engines, and gptossloop, the local engine on by default (ADR-0061).
    assert asyncio.run(check()) == 5


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_stays_quiet_when_every_engine_has_conformance(tmp_path: Path) -> None:
    from vibey.application.dto import PreflightResult

    async def seed() -> None:
        async with build_app() as resources:
            project = await resources.projects.create(
                "quiet-sweep-proj", tmp_path, max_cycles=1, config={}
            )
            good = PreflightResult(installed=True, version="1.0.0", auth_ok=True)
            # Every engine this worker runs: the defaults, and gptossloop (ADR-0061).
            for engine_id in (*resources.engine_adapters, EngineId.GPTOSSLOOP):
                await resources.engine_health_service.update_from_preflight(
                    project.project_id, engine_id, good, conformance_ok=True
                )

    asyncio.run(seed())
    from unittest.mock import AsyncMock, patch

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as mock_notifier_cls:
        mock_notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 0, res.output
    assert "no recorded conformance" not in res.output
    assert "preflight feasibility: UNKNOWN" in res.output
    assert "no measured shortfall" in res.output


def test_doctor_record_persists_preflight_only(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("doc-rec-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="9.9.9", auth_ok=True)),
    ):
        res = runner.invoke(app, ["doctor", "--record", "--engine", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "recorded preflight for claudeloop" in res.output

    async def check() -> None:
        async with build_app() as resources:
            latest = await resources.projects.get_latest()
            assert latest is not None
            record = await resources.engine_health_repo.get(latest.project_id, "claudeloop")
            assert record is not None
            assert record.version == "9.9.9"
            assert record.conformance_ok is False

    asyncio.run(check())


def test_doctor_record_with_conformance_grants_eligibility(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import (
        ConformanceCheckResult,
        ConformanceReport,
        PreflightResult,
    )

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("doc-conf-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())
    from vibey.domain.engine import EngineId

    ok_report = ConformanceReport(
        engine_id=EngineId.CLAUDELOOP,
        checks=(ConformanceCheckResult(name="binary", ok=True),),
    )
    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(
                return_value=PreflightResult(installed=True, version="9.9.9", auth_ok=True)
            ),
        ),
        patch(
            "vibey.application.conformance.run_conformance",
            new=AsyncMock(return_value=ok_report),
        ),
    ):
        res = runner.invoke(app, ["doctor", "--conformance", "--record", "--engine", "claudeloop"])
    assert res.exit_code == 0, res.output
    assert "recorded engine_health for claudeloop" in res.output

    async def check() -> None:
        async with build_app() as resources:
            latest = await resources.projects.get_latest()
            assert latest is not None
            record = await resources.engine_health_repo.get(latest.project_id, "claudeloop")
            assert record is not None
            assert record.conformance_ok is True

    asyncio.run(check())


def test_doctor_record_without_projects_exits_1() -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1.0.0", auth_ok=True)),
    ):
        res = runner.invoke(app, ["doctor", "--record", "--engine", "claudeloop"])
    assert res.exit_code == 1
    assert "no projects found" in res.output


def test_doctor_record_specific_project(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    async def seed() -> UUID:
        async with build_app() as resources:
            older = await resources.projects.create(
                "rec-older", tmp_path / "older", max_cycles=1, config={}
            )
            await resources.projects.create(
                "rec-newer", tmp_path / "newer", max_cycles=1, config={}
            )
            return older.project_id

    older_id = asyncio.run(seed())
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1.0.0", auth_ok=True)),
    ):
        res = runner.invoke(
            app, ["doctor", "--record", "--engine", "claudeloop", "--project", str(older_id)]
        )
    assert res.exit_code == 0, res.output

    async def check() -> None:
        async with build_app() as resources:
            record = await resources.engine_health_repo.get(older_id, "claudeloop")
            assert record is not None

    asyncio.run(check())


def test_worker_rejects_unknown_azure_mode() -> None:
    res = runner.invoke(app, ["worker", "--azure", "gcp"])
    assert res.exit_code == 2
    assert "memory" in res.output and "az" in res.output


def test_worker_azure_az_requires_a_logged_in_cli() -> None:
    from unittest.mock import patch

    class _NotLoggedIn:
        returncode = 1
        stdout = ""
        stderr = "Please run 'az login'"

    with patch("vibey.cli.main.subprocess.run", return_value=_NotLoggedIn()):
        res = runner.invoke(app, ["worker", "--azure", "az"])
    assert res.exit_code == 1
    assert "az login" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_azure_az_builds_the_real_adapter_when_logged_in(tmp_path: Path) -> None:
    from unittest.mock import AsyncMock, patch

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("az-proj", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())

    class _LoggedIn:
        returncode = 0
        stdout = ""
        stderr = ""

    with (
        patch("vibey.cli.main.subprocess.run", return_value=_LoggedIn()),
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as notifier_cls,
    ):
        notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--azure", "az", "--once"])
    assert res.exit_code == 0, res.output


def test_worker_without_wait_still_exits_when_no_project_exists() -> None:
    """The one-shot CLI default stays honest: nothing to work on is an
    error, not a hang."""
    res = runner.invoke(app, ["worker"])

    assert res.exit_code == 1
    assert "no projects found" in res.output


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_wait_for_project_polls_until_one_appears(tmp_path: Path) -> None:
    """A long-lived deployment must not exit when no project exists yet:
    exiting is a restart loop that ends only when a human creates one, and
    the crash counter makes a healthy worker look broken (observed on a
    real minikube install before this flag). The project is created from
    inside the sleep, exactly as it would be while a Deployment waits."""
    from unittest.mock import AsyncMock, patch

    async def create_project(_seconds: float) -> None:
        async with build_app() as resources:
            await resources.projects.create("late", tmp_path, max_cycles=1, config={})

    with (
        patch("vibey.cli.main.asyncio.sleep", new=AsyncMock(side_effect=create_project)) as slept,
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as notifier_cls,
    ):
        notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--wait-for-project", "1", "--once"])

    assert res.exit_code == 0, res.output
    assert "no project yet; polling every 1s" in res.output
    assert slept.await_count == 1


@pytest.mark.usefixtures("_fast_engine_preflight")
def test_worker_drains_on_sigterm_rather_than_claiming_more(tmp_path: Path) -> None:
    """Kubernetes scale-in is SIGTERM, a wait, then SIGKILL. Before this,
    the worker ignored SIGTERM entirely: measured on minikube, a pod kept
    processing jobs 77s after the signal and five 'terminated' pods still
    held live Postgres connections while the Deployment reported 0/0.
    Scale-to-zero freed nothing and the eventual SIGKILL would land
    mid-session. The signal arrives here exactly where a real scale-in
    delivers it -- while the worker sits idle waiting for the next job."""
    import signal
    from unittest.mock import AsyncMock, patch

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create("drain", tmp_path, max_cycles=1, config={})

    asyncio.run(seed())

    async def sigterm(*_args: object, **_kwargs: object) -> None:
        os.kill(os.getpid(), signal.SIGTERM)
        # Let the loop's signal self-pipe deliver it before the next claim.
        await asyncio.sleep(0.1)

    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as notifier_cls:
        notifier = AsyncMock()
        notifier.wait_for_job_ready = AsyncMock(side_effect=sigterm)
        notifier_cls.return_value = notifier
        res = runner.invoke(app, ["worker", "-j", "1"])

    assert res.exit_code == 0, res.output
    assert "draining on SIGTERM" in res.output
    # The point of the flag: it stopped claiming. One idle wait, then out.
    assert notifier.wait_for_job_ready.await_count == 1


def test_doctor_cluster_passes_against_a_migrated_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The in-cluster preflight is a different question from engine health:
    it asks whether this deployment is wired correctly at all."""
    from unittest.mock import patch

    async def migrate() -> None:
        async with build_app():
            pass

    asyncio.run(migrate())
    monkeypatch.chdir(tmp_path)
    for var in _ENGINE_KEY_VARS:
        monkeypatch.delenv(var, raising=False)

    # Every engine on PATH and no key: the default chart install on the image
    # since ADR-0037, which bundles every runner. Not a fault -- the worker was
    # never told to use an engine.
    with patch("shutil.which", side_effect=lambda binary: f"/app/.venv/bin/{binary}"):
        res = runner.invoke(app, ["doctor", "--cluster"])

    assert res.exit_code == 0, res.output
    assert "PASS engine-auth" in res.output
    assert "PASS database" in res.output
    assert "PASS migrations" in res.output


# Every variable cluster_preflight.ENGINE_API_KEY_ENVS accepts, so a developer's
# own shell cannot decide these tests.
_ENGINE_KEY_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CURSOR_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


def test_doctor_cluster_holds_the_worker_to_its_engines_allow_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same install told `--engines claudeloop` with no key mounted is the
    misconfiguration this check exists for: Ready, and no BUILD job can run."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    for var in _ENGINE_KEY_VARS:
        monkeypatch.delenv(var, raising=False)

    with patch("shutil.which", side_effect=lambda binary: f"/app/.venv/bin/{binary}"):
        res = runner.invoke(
            app, ["doctor", "--cluster", "--engines", "claudeloop", "--provider", "scripted"]
        )

    assert res.exit_code == 1
    assert "FAIL engine-auth" in res.output
    assert "installed but unauthenticated: claudeloop" in res.output


def test_doctor_cluster_refuses_a_worker_flag_the_worker_would_refuse() -> None:
    res = runner.invoke(app, ["doctor", "--cluster", "--engines", "gpt"])

    assert res.exit_code == 2
    assert "Invalid worker flag" in res.output


@pytest.mark.parametrize("flag", [["--engines", "claudeloop"], ["--provider", "scripted"]])
def test_doctor_worker_flags_without_cluster_are_refused_not_ignored(flag: list[str]) -> None:
    """Silently dropping them would read as a check that ran."""
    res = runner.invoke(app, ["doctor", *flag])

    assert res.exit_code == 2
    assert "apply only with --cluster" in res.output


def test_doctor_cluster_exits_nonzero_when_the_database_is_unreachable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A preflight that reported success against a database nobody reached
    would be worse than no preflight."""
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://nobody@127.0.0.1:1/nothing")

    with patch("shutil.which", return_value=None):
        res = runner.invoke(app, ["doctor", "--cluster"])

    assert res.exit_code == 1
    assert "FAIL database" in res.output


def test_operator_command_runs_the_operator_scoped_to_a_namespace() -> None:
    from unittest.mock import patch

    with patch("vibey.infrastructure.operator.run") as run_operator:
        res = runner.invoke(app, ["operator", "--namespace", "vibey"])

    assert res.exit_code == 0, res.output
    run_operator.assert_called_once_with(namespace="vibey")


def test_operator_command_explains_itself_when_the_extra_is_not_installed() -> None:
    """kopf is an optional extra, so the failure mode has to name the fix
    rather than surfacing a raw ImportError traceback."""
    import sys
    from unittest.mock import patch

    with patch.dict(sys.modules, {"vibey.infrastructure.operator": None}):
        res = runner.invoke(app, ["operator"])

    assert res.exit_code == 1
    assert "vibey[operator]" in res.output


async def test_recorded_spend_is_visible_to_the_budget_brake(tmp_path: Path) -> None:
    """The bug this guards: DESIGN spend reached no ledger, so
    LedgerBudgetSource summed zero for the phase and the project's cap --
    however large or small -- could never trip. Measured live before the
    fix: 83 QuestionAsked events across eight projects and not one
    TurnCompleted or BudgetSpent, while a single design turn had cost
    $0.44.
    """
    from vibey.application.budget_source import LedgerBudgetSource
    from vibey.cli.main import _build_spend_recorder
    from vibey.domain.phase import Phase

    async with build_app() as resources:
        project = await resources.projects.create("brake", tmp_path, max_cycles=1, config={})
        record = _build_spend_recorder(
            resources.ledger, project.project_id, project.cycle, Phase.DESIGN
        )
        await record(2, 0.6916597)

        source = LedgerBudgetSource(resources.ledger, max_dollars=200.0)
        ledger = await source.current(project.project_id, project.cycle)

    assert ledger.turns_spent == 2
    assert ledger.dollars_spent == pytest.approx(0.6916597)


def test_recover_no_args() -> None:
    result = runner.invoke(app, ["recover"])
    assert result.exit_code == 1
    assert "Must specify either --project <id> or --all" in result.stdout


def test_recover_all_projects(tmp_path: Path) -> None:
    async def seed() -> None:
        async with build_app() as resources:
            _ = resources

    asyncio.run(seed())

    result = runner.invoke(app, ["recover", "--all"])
    assert result.exit_code == 0
    assert "Recovered 0 stuck job(s)." in result.stdout


def test_recover_counts_the_jobs_it_put_back(tmp_path: Path) -> None:
    """The bug this guards: the count came from a pattern written
    r"UPDATE (\\d+)" -- a doubled backslash, so it looked for a literal
    backslash and never matched asyncpg's "UPDATE 1" status tag. Every
    recovery, however many rows it reset, reported `Recovered 0 stuck job(s).`
    """

    async def seed() -> UUID:
        async with build_app() as resources:
            project = await resources.projects.create(
                "recover-count", tmp_path, max_cycles=1, config={}
            )
            await resources.jobs.enqueue(
                EnqueueRequest(
                    project_id=project.project_id,
                    cycle=project.cycle,
                    phase=Phase.INTAKE,
                    kind="test.work",
                    idempotency_key=idempotency_key(
                        project.project_id, project.cycle, "test.work", "1"
                    ),
                    requirement={},
                )
            )
            # A worker that crashed mid-job leaves exactly this behind: a job
            # in `leased`, with a lease nobody will ever heartbeat again.
            leased = await resources.jobs.claim(
                project.project_id, owner="crashed-worker", lease=timedelta(minutes=5)
            )
            assert leased is not None
            return project.project_id

    project_id = asyncio.run(seed())

    result = runner.invoke(app, ["recover", "--project", str(project_id)])
    assert result.exit_code == 0
    assert "Recovered 1 stuck job(s)." in result.stdout


def test_recover_with_project(tmp_path: Path) -> None:
    async def seed() -> None:
        async with build_app() as resources:
            _ = resources

    asyncio.run(seed())

    import uuid

    pid = str(uuid.uuid4())
    result = runner.invoke(app, ["recover", "--project", pid])
    assert result.exit_code == 0
    assert "Recovered 0 stuck job(s)." in result.stdout


# ── a project's declared engine environment reaches the probes ────────────────
#
# `engine_environment` in the project record is how a project hands an engine the
# credential its own configuration reads -- a relay's provider key, agyloop's Vertex
# credentials. `build_full_worker` applied it, but the startup preflight sweep and
# `vibey doctor --conformance --record --project X` still probed with the DEFAULT
# policy, so the auth check and the conformance run could not see the credential the
# real session would get: the engine read "auth FAIL" and never became eligible.

_DECLARED_CREDENTIALS = [
    (EngineId.CODEXLOOP, "OPENROUTER_API_KEY"),
    (EngineId.AGYLOOP, "GOOGLE_APPLICATION_CREDENTIALS"),
]


def _probe_recorder(seen: dict[str, dict[str, str]]):  # type: ignore[no-untyped-def]
    """A stand-in `LoopProcessAdapter.preflight` that records the environment the real
    `--version`/`doctor` probes would have been started with."""
    from vibey.application.dto import PreflightResult

    async def preflight(self):  # type: ignore[no-untyped-def]
        seen[self.descriptor.engine_id.value] = self._engine_environment()
        return PreflightResult(installed=True, version="1.0.0", auth_ok=True)

    return preflight


@pytest.mark.parametrize(("engine", "credential"), _DECLARED_CREDENTIALS)
def test_the_startup_preflight_probes_with_the_projects_declared_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: EngineId, credential: str
) -> None:
    from unittest.mock import AsyncMock, patch

    monkeypatch.setenv(credential, "declared-secret")

    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create(
                "declared-env-proj",
                tmp_path,
                max_cycles=1,
                config={"engine_environment": {"engines": {engine.value: [credential]}}},
            )

    asyncio.run(seed())
    seen: dict[str, dict[str, str]] = {}
    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=_probe_recorder(seen),
        ),
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as notifier_cls,
    ):
        notifier_cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--once"])

    assert res.exit_code == 0, res.output
    assert seen[engine.value].get(credential) == "declared-secret"
    assert "VIBEY_PG_URL" not in seen[engine.value]
    # Declared for one engine, it reaches that engine only.
    others = [e for e in seen if e != engine.value]
    assert others and all(credential not in seen[e] for e in others)


@pytest.mark.parametrize(("engine", "credential"), _DECLARED_CREDENTIALS)
def test_doctor_record_probes_and_conforms_with_the_target_projects_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, engine: EngineId, credential: str
) -> None:
    from unittest.mock import patch

    from vibey.application.dto import ConformanceCheckResult, ConformanceReport

    monkeypatch.setenv(credential, "declared-secret")

    async def seed() -> UUID:
        async with build_app() as resources:
            project = await resources.projects.create(
                "doctor-env-proj",
                tmp_path,
                max_cycles=1,
                config={"engine_environment": {"engines": {engine.value: [credential]}}},
            )
            # A newer project without the declaration: --project must pick the older.
            await resources.projects.create("other-proj", tmp_path / "o", max_cycles=1, config={})
            return project.project_id

    project_id = asyncio.run(seed())
    probed: dict[str, dict[str, str]] = {}
    conformed: dict[str, dict[str, str]] = {}

    async def conformance(adapter, **kwargs):  # type: ignore[no-untyped-def]
        conformed[adapter.descriptor.engine_id.value] = adapter._engine_environment()
        return ConformanceReport(
            engine_id=adapter.descriptor.engine_id,
            checks=(ConformanceCheckResult(name="binary", ok=True),),
        )

    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=_probe_recorder(probed),
        ),
        patch("vibey.application.conformance.run_conformance", new=conformance),
    ):
        res = runner.invoke(
            app,
            [
                "doctor",
                "--conformance",
                "--record",
                "--engine",
                engine.value,
                "--project",
                str(project_id),
            ],
        )

    assert res.exit_code == 0, res.output
    assert probed[engine.value].get(credential) == "declared-secret"
    assert conformed[engine.value].get(credential) == "declared-secret"
    assert "VIBEY_PG_URL" not in probed[engine.value]


def test_doctor_without_record_probes_with_the_default_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No --record, no target project: nothing declares anything, so nothing extra."""
    from unittest.mock import patch

    monkeypatch.setenv("OPENROUTER_API_KEY", "undeclared-secret")
    probed: dict[str, dict[str, str]] = {}
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=_probe_recorder(probed),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "codexloop"])

    assert res.exit_code == 0, res.output
    assert "OPENROUTER_API_KEY" not in probed["codexloop"]


def test_doctor_record_refuses_a_project_whose_engine_environment_is_forbidden(
    tmp_path: Path,
) -> None:
    async def seed() -> None:
        async with build_app() as resources:
            await resources.projects.create(
                "forbidden-env-proj",
                tmp_path,
                max_cycles=1,
                config={"engine_environment": {"allow": ["VIBEY_PG_URL"]}},
            )

    asyncio.run(seed())
    res = runner.invoke(app, ["doctor", "--record", "--engine", "codexloop"])

    assert res.exit_code != 0
    assert "VIBEY_PG_URL" in res.output


# ── doctor: is the app database reachable with no password at all? ──────────────


def test_doctor_warns_when_the_app_database_admits_a_passwordless_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult
    from vibey.infrastructure.db.passwordless_reach import (
        PasswordlessReachFinding,
        ReachVerdict,
    )

    seen: list[str] = []

    async def probe(self, dsn):  # type: ignore[no-untyped-def]
        seen.append(dsn)
        return PasswordlessReachFinding(ReachVerdict.WARN, "accepts a password-less login")

    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(return_value=PreflightResult(installed=True, version="1", auth_ok=True)),
        ),
        patch("vibey.infrastructure.db.passwordless_reach.PasswordlessReachProbe.probe", probe),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "claudeloop"])

    # A warning, not a failure: a trusted local database is a choice, said out loud.
    assert res.exit_code == 0, res.output
    assert "WARN db-passwordless" in res.output
    assert "accepts a password-less login" in res.output
    assert seen == [os.environ["VIBEY_PG_URL"]]


def test_doctor_says_it_could_not_check_without_a_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock, patch

    from vibey.application.dto import PreflightResult

    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1", auth_ok=True)),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "claudeloop"])

    assert res.exit_code == 0, res.output
    assert "UNKNOWN db-passwordless" in res.output
    assert "VIBEY_PG_URL is not set" in res.output
