# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey loops`: the document the VS Code extension reads, and the table a person reads.

Everything here runs with no database: `VIBEY_PG_URL` is removed for every call, and the
command must not notice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from vibey.application.dto import EngineContext
from vibey.application.loops import LoopCatalog
from vibey.cli.interfaces.loops_interface import LoopsCommandInterface, LoopsPresenterInterface
from vibey.cli.loops import LOOPS, LOOPS_PRESENTER, LoopsCommand, LoopsPresenter
from vibey.cli.main import app
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineDescriptor, EngineId, EngineInvocation, EngineTier
from vibey.infrastructure.engines.descriptors import CLAUDELOOP

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})

# Every variable the command reads, cleared, so the machine running the suite cannot leak
# into what it reports. `None` unsets it for the call.
CLEAN: dict[str, str | None] = {
    "VIBEY_PG_URL": None,
    "VIBEY_FEATURE_QWENLOOP": None,
    "VIBEY_FEATURE_CLAUDELOOP_LOCAL": None,
    "VIBEY_CLAUDELOOP_LOCAL_PROFILE": None,
    "VIBEY_OLLAMA_URL": None,
    "VIBEY_OLLAMA_MODEL": None,
    "QWENLOOP_MODEL": None,
}
ENGINE_KEYS = [
    "engine_id",
    "binary",
    "state_dir",
    "enabled",
    "switch",
    "cost_per_mtok_in",
    "cost_per_mtok_out",
    "default_model",
    "efforts",
    "capabilities",
    "done_marker",
    "plan_flag",
    "supports_cwd_flag",
    "base_weight",
    "run",
    "controls",
    "events",
    "env",
    "notes",
]
EFFORTS = ["TRIVIAL", "LOW", "STANDARD", "HIGH", "MAX"]


@pytest.fixture(autouse=True)
def _in_a_directory_without_vibey_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def _document(**env: str) -> dict[str, Any]:
    result = runner.invoke(app, ["loops", "--json"], env={**CLEAN, **env})
    assert result.exit_code == 0, result.output
    document: dict[str, Any] = json.loads(result.stdout)
    return document


def _engine(document: dict[str, Any], engine_id: str) -> dict[str, Any]:
    engines = [e for loop in document["loops"] for e in loop["engines"]]
    (engine,) = [e for e in engines if e["engine_id"] == engine_id]
    return engine


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(LOOPS, LoopsCommandInterface)
    assert isinstance(LOOPS_PRESENTER, LoopsPresenterInterface)


def test_the_document_has_the_contracts_shape_without_a_database() -> None:
    document = _document()

    assert list(document) == [
        "efforts",
        "default_loop",
        "paid_default_engine",
        "paid_default",
        "ladder",
        "loops",
    ]
    assert document["efforts"] == EFFORTS
    assert (document["default_loop"], document["paid_default_engine"]) == (
        "sovereignloop",
        "claudeloop",
    )
    assert document["paid_default"] == "claudeloop"
    assert document["ladder"] == {
        "phase_base": {
            "DESIGN": "HIGH",
            "VISUAL_DESIGN": "HIGH",
            "BUILD": "LOW",
            "REVIEW": "HIGH",
            "DEPLOY_DESIGN": "HIGH",
            "DEPLOY_EXECUTE": "LOW",
            "DEPLOY_REVIEW": "HIGH",
            "DEPLOY": "LOW",
        },
        "build_attempts": ["LOW", "LOW", "STANDARD", "STANDARD", "HIGH", "HIGH"],
        "exhausted_after": 6,
        "rotates_when_effort_rises": True,
    }
    sovereign, paid = document["loops"]
    assert list(sovereign) == ["loop", "tier", "default", "declared_only", "engines", "by_effort"]
    assert (sovereign["loop"], sovereign["tier"], sovereign["default"]) == (
        "sovereignloop",
        "local",
        True,
    )
    assert sovereign["declared_only"] is False
    assert (paid["loop"], paid["tier"], paid["default"], paid["declared_only"]) == (
        "paidloop",
        "paid",
        False,
        True,
    )
    assert [e["engine_id"] for e in sovereign["engines"]] == [
        "opencode",
        "qwenloop",
        "claudeloop-local",
    ]
    assert [e["engine_id"] for e in paid["engines"]] == [
        "claudeloop",
        "codexloop",
        "cursorloop",
        "agyloop",
    ]
    for loop in document["loops"]:
        assert list(loop["by_effort"]) == EFFORTS
        for engine in loop["engines"]:
            assert list(engine) == ENGINE_KEYS, engine["engine_id"]
            assert [run["effort"] for run in engine["efforts"]] == EFFORTS
            assert list(engine["efforts"][0]) == ["effort", "argv", "achieved", "model", "notes"]
            assert list(engine["capabilities"]) == [
                "images",
                "files",
                "paste_text",
                "paste_images",
                "plugins",
                "mcp",
                "evidence",
            ]
            assert list(engine["controls"]) == ["stop", "wind_down", "prompt"]
            assert list(engine["events"]) == ["path", "envelope"]
            assert list(engine["env"]) == ["auth", "passthrough"]


def test_qwenloop_reads_as_the_contract_shows_it() -> None:
    qwenloop = _engine(_document(), "qwenloop")

    assert qwenloop["efforts"][0] == {
        "effort": "TRIVIAL",
        "argv": ["--max-turns", "8"],
        "achieved": "TRIVIAL",
        "model": "gpt-oss:20b",
        "notes": "",
    }
    assert (qwenloop["binary"], qwenloop["state_dir"]) == ("qwenloop", ".qwenloop")
    assert (qwenloop["enabled"], qwenloop["switch"]) == (False, "VIBEY_FEATURE_QWENLOOP")
    assert (qwenloop["cost_per_mtok_in"], qwenloop["cost_per_mtok_out"]) == (0.0, 0.0)
    assert qwenloop["default_model"] == "gpt-oss:20b"
    assert qwenloop["capabilities"]["images"] is False
    assert qwenloop["capabilities"]["plugins"] == "skills-context"
    assert "read_file" in qwenloop["capabilities"]["evidence"]["images"]
    assert qwenloop["controls"] == {
        "stop": ["stop", "{run_id}", "--cwd", "{cwd}"],
        "wind_down": ["wind-down", "{run_id}", "--cwd", "{cwd}"],
        "prompt": None,
    }
    assert qwenloop["events"] == {
        "path": "{cwd}/{state_dir}/runs/{run_id}/events.jsonl",
        "envelope": "type",
    }
    assert qwenloop["env"] == {"auth": [], "passthrough": ["QWENLOOP_*"]}
    assert qwenloop["done_marker"] == "QWENLOOP_TASK_FULLY_COMPLETE"
    assert qwenloop["run"] == [
        "{binary}",
        "run",
        "{plan}",
        "--run-id",
        "{run_id}",
        "{effort_argv...}",
        "--cwd",
        "{cwd}",
    ]


def test_a_paid_engine_is_listed_as_on_with_no_switch_and_its_model_chooser_noted() -> None:
    document = _document()
    claudeloop = _engine(document, "claudeloop")

    assert (claudeloop["enabled"], claudeloop["switch"], claudeloop["default_model"]) == (
        True,
        None,
        None,
    )
    assert claudeloop["efforts"][3] == {
        "effort": "HIGH",
        "argv": ["--preset", "high", "--effort", "high"],
        "achieved": "HIGH",
        "model": None,
        "notes": "claudeloop preset high",
    }
    assert claudeloop["capabilities"]["plugins"] == "claude-plugins"
    assert _engine(document, "cursorloop")["efforts"][0]["model"] == "composer-fast"
    assert _engine(document, "cursorloop")["plan_flag"] == "--plan"
    assert _engine(document, "codexloop")["supports_cwd_flag"] is False
    assert _engine(document, "agyloop")["controls"]["wind_down"] is None


def test_opencode_is_reported_as_the_code_says_and_the_canon_is_noted() -> None:
    opencode = _engine(_document(), "opencode")

    assert opencode["notes"] == [
        "sub-doctrine 8.b repeals opencode from both loops; reported here as its descriptor "
        "says, tier local"
    ]
    assert opencode["controls"] == {"stop": None, "wind_down": None, "prompt": None}
    assert opencode["events"]["envelope"] == "event_type"


def test_by_effort_lists_exact_matches_first() -> None:
    sovereign = _document()["loops"][0]

    assert sovereign["by_effort"]["STANDARD"] == [
        {"engine_id": "claudeloop-local", "model": None, "achieved": "STANDARD"},
        {"engine_id": "opencode", "model": None, "achieved": "STANDARD"},
        {"engine_id": "qwenloop", "model": "gpt-oss:20b", "achieved": "STANDARD"},
    ]
    assert [c["engine_id"] for c in sovereign["by_effort"]["MAX"]] == [
        "qwenloop",
        "claudeloop-local",
        "opencode",
    ]


def test_a_local_engine_is_on_as_the_environment_or_vibey_toml_says(tmp_path: Path) -> None:
    assert _engine(_document(VIBEY_FEATURE_QWENLOOP="1"), "qwenloop")["enabled"] is True
    (tmp_path / "vibey.toml").write_text("[features]\nclaudeloop_local = true\n")
    assert _engine(_document(), "claudeloop-local")["enabled"] is True


def test_claudeloop_local_is_listed_on_the_profile_it_would_run() -> None:
    local = _engine(_document(VIBEY_CLAUDELOOP_LOCAL_PROFILE="gpu"), "claudeloop-local")

    assert local["efforts"][0]["argv"] == ["--profile", "gpu", "--preset", "low"]
    assert local["efforts"][0]["notes"] == "claudeloop profile gpu, preset low"
    assert local["switch"] == "VIBEY_FEATURE_CLAUDELOOP_LOCAL"


def test_qwenloops_model_is_the_one_it_would_run() -> None:
    assert _engine(_document(VIBEY_OLLAMA_MODEL="qwen3-coder"), "qwenloop")["default_model"] == (
        "qwen3-coder"
    )
    qwenloop = _engine(_document(QWENLOOP_MODEL="llama3.3"), "qwenloop")
    assert {run["model"] for run in qwenloop["efforts"]} == {"llama3.3"}


def test_environment_names_are_copied_and_never_their_values() -> None:
    result = runner.invoke(
        app, ["loops", "--json"], env={**CLEAN, "ANTHROPIC_API_KEY": "sk-never-printed"}
    )

    assert "sk-never-printed" not in result.stdout
    claudeloop = _engine(json.loads(result.stdout), "claudeloop")
    assert claudeloop["env"] == {
        "auth": ["ANTHROPIC_API_KEY"],
        "passthrough": ["CLAUDELOOP_*", "CLAUDE_CODE_*", "CLAUDE_CONFIG_DIR", "ANTHROPIC_*"],
    }


def test_the_table_says_what_each_effort_passes_and_how_to_switch_a_local_engine_on() -> None:
    result = runner.invoke(app, ["loops"], env=CLEAN)

    assert result.exit_code == 0, result.output
    lines = result.stdout.splitlines()
    assert lines[0] == "sovereignloop (tier local): the default loop, always on"
    assert "paidloop (tier paid): declared only: it runs when a paid engine is declared" in lines
    assert any(line.split()[:1] == ["TRIVIAL"] and "max-turns 8" in line for line in lines)
    assert any("(no flags) -> STANDARD" in line for line in lines)
    assert (
        "  qwenloop is switched on by VIBEY_FEATURE_QWENLOOP=1, or by its key under [features] "
        "in vibey.toml"
    ) in lines
    assert any(line.startswith("  note on opencode: sub-doctrine 8.b") for line in lines)
    assert lines[-1] == (
        "A paid declaration reaches claudeloop unless it names another paid engine. "
        "`vibey loops --json` has every engine's full facts."
    )


# -- the presenter and the command, around engines nobody has checked -------------------------


def _unchecked() -> EngineDescriptor:
    """A local engine whose descriptor declares nothing new: every fact unknown."""
    return EngineDescriptor(
        engine_id=EngineId.QWENLOOP,
        binary="probe",
        min_version="0.1.0",
        state_dir=".probe",
        done_marker="DONE",
        auth_env=(),
        capabilities=frozenset(),
        effort_projection={e: EngineInvocation((), achieved=e) for e in Effort},
        session_verb="sessions",
        isolation_flags={},
        cost_per_mtok_in=0.0,
        cost_per_mtok_out=0.0,
        context_window=1,
        tier=EngineTier.LOCAL,
    )


def test_an_engine_that_declares_nothing_reports_every_fact_as_null() -> None:
    report = LoopCatalog().report([EngineContext(descriptor=_unchecked(), enabled=True, run=())])

    (engine,) = json.loads(LoopsPresenter().json(report))["loops"][0]["engines"]

    assert engine["capabilities"] == {
        "images": None,
        "files": None,
        "paste_text": None,
        "paste_images": None,
        "plugins": None,
        "mcp": None,
        "evidence": {},
    }
    assert engine["controls"] == {"stop": None, "wind_down": None, "prompt": None}
    assert engine["events"] == {"path": None, "envelope": None}


def test_a_loop_without_engines_says_so() -> None:
    report = LoopCatalog().report([EngineContext(descriptor=CLAUDELOOP, enabled=True, run=())])

    lines = LoopsPresenter().lines(report)

    assert lines[:2] == ["sovereignloop (tier local): the default loop, always on", "  no engines"]


def test_the_command_reads_the_environment_and_directory_it_is_given(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "vibey.toml").write_text("[features]\nqwenloop = true\n")
    command = LoopsCommand(environ={}, workdir=tmp_path)

    command.run(as_json=True)

    qwenloop = _engine(json.loads(capsys.readouterr().out), "qwenloop")
    assert qwenloop["enabled"] is True


def test_a_broken_local_endpoint_is_refused_as_the_worker_would_refuse_it() -> None:
    result = runner.invoke(app, ["loops"], env={**CLEAN, "VIBEY_OLLAMA_URL": "ftp://nowhere"})

    assert result.exit_code == 3
    assert "Error:" in result.stderr and "VIBEY_OLLAMA_URL" in result.stderr
