# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey loops`: the document the VS Code extension reads, and the table a person reads.

Everything here runs with no database: `VIBEY_PG_URL` is removed for every call, and the
command must not notice.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from vibey.application.dto import EngineContext
from vibey.application.loops import LoopCatalog
from vibey.cli.interfaces.loops_interface import LoopsCommandInterface, LoopsPresenterInterface
from vibey.cli.loops import (
    LOOPS,
    LOOPS_PRESENTER,
    MALFORMED_SETTING,
    LoopsCommand,
    LoopsPresenter,
)
from vibey.cli.main import app
from vibey.domain.effort import Effort
from vibey.domain.engine import (
    RENAMED_ENGINES,
    EngineDescriptor,
    EngineId,
    EngineInvocation,
    EngineTier,
)
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.local_engines import LocalEndpointEnvironment, LocalEngineSettings

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})

# Every variable the command reads, cleared, so the machine running the suite cannot leak
# into what it reports. `None` unsets it for the call.
CLEAN: dict[str, str | None] = {
    "VIBEY_PG_URL": None,
    "VIBEY_FEATURE_GPTOSSLOOP": None,
    "VIBEY_FEATURE_QWENLOOP": None,
    "VIBEY_FEATURE_CLAUDELOOP_LOCAL": None,
    "VIBEY_CLAUDELOOP_LOCAL_PROFILE": None,
    "VIBEY_OLLAMA_URL": None,
    "VIBEY_OLLAMA_MODEL": None,
    "VIBEY_OLLAMA_TIMEOUT": None,
    "GPTOSSLOOP_MODEL": None,
    "GPTOSSLOOP_BASE_URL": None,
    "QWENLOOP_MODEL": None,
    "QWENLOOP_BASE_URL": None,
}
ENGINE_KEYS = [
    "engine_id",
    "binary",
    "state_dir",
    "enabled",
    "switch",
    "on_by_default",
    "repealed",
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
OWN_CHOICE = "gptossloop's own configuration chooses the model"
QWEN_OWN_CHOICE = "qwenloop's own configuration chooses the model"
ENDPOINT = {"VIBEY_OLLAMA_URL": "http://127.0.0.1:11434"}

# The golden: the document in one fixed environment -- every variable above cleared, then
# pointed at a local endpoint, so gptossloop (on by default) runs vibey's model and
# qwenloop (off) its own -- committed so the VS Code extension's parser is tested against
# exactly what this command prints (amendment 7).
GOLDEN = Path(__file__).parent / "golden" / "vibey-loops.json"
GOLDEN_ENVIRONMENT = {**ENDPOINT}
UPDATE_GOLDENS = "VIBEY_UPDATE_GOLDENS"


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
        "gptossloop",
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


def test_gptossloop_is_on_by_default_and_switched_off_only_by_saying_so() -> None:
    """ADR-0060: the sovereign default engine ships on."""
    gptossloop = _engine(_document(), "gptossloop")

    assert (gptossloop["binary"], gptossloop["state_dir"]) == ("gptossloop", ".qwenloop")
    assert (gptossloop["enabled"], gptossloop["switch"], gptossloop["on_by_default"]) == (
        True,
        "VIBEY_FEATURE_GPTOSSLOOP",
        True,
    )
    assert gptossloop["env"] == {"auth": [], "passthrough": ["GPTOSSLOOP_*"]}
    assert gptossloop["done_marker"] == "QWENLOOP_TASK_FULLY_COMPLETE"
    assert gptossloop["notes"] == []
    assert _engine(_document(VIBEY_FEATURE_GPTOSSLOOP="0"), "gptossloop")["enabled"] is False


def test_qwenloop_reads_as_the_contract_shows_it() -> None:
    qwenloop = _engine(_document(), "qwenloop")

    assert qwenloop["efforts"][0] == {
        "effort": "TRIVIAL",
        "argv": ["--max-turns", "8"],
        "achieved": "TRIVIAL",
        "model": None,
        "notes": QWEN_OWN_CHOICE,
    }
    assert (qwenloop["binary"], qwenloop["state_dir"]) == ("qwenloop", ".qwenloop")
    assert (qwenloop["enabled"], qwenloop["switch"], qwenloop["on_by_default"]) == (
        False,
        "VIBEY_FEATURE_QWENLOOP",
        False,
    )
    assert qwenloop["notes"] == [RENAMED_ENGINES[EngineId.QWENLOOP]]
    assert qwenloop["repealed"] is False
    assert (qwenloop["cost_per_mtok_in"], qwenloop["cost_per_mtok_out"]) == (0.0, 0.0)
    assert qwenloop["default_model"] is None
    assert qwenloop["capabilities"]["images"] is False
    assert qwenloop["capabilities"]["plugins"] == "skills-context"
    assert "read_file" in qwenloop["capabilities"]["evidence"]["images"]
    assert qwenloop["controls"] == {
        "stop": ["stop", "{run_id}", "--cwd", "{cwd}"],
        "wind_down": ["wind-down", "{run_id}", "--cwd", "{cwd}"],
        "prompt": ["prompt", "{run_id}", "{text}", "--cwd", "{cwd}"],
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


def test_only_a_runner_that_acts_on_a_mid_run_prompt_offers_a_prompt_control() -> None:
    """cursorloop's CLI writes a `prompt` control, but its runner reads its inbox only while
    it waits, acts on stop and wind-down alone, and drops the rest unread (amendment 3).
    qwenloop's runner reads one at each turn boundary, since #1133."""
    document = _document()

    prompts = {
        engine["engine_id"]: engine["controls"]["prompt"] is not None
        for loop in document["loops"]
        for engine in loop["engines"]
    }
    assert prompts == {
        "opencode": False,
        "gptossloop": True,
        "qwenloop": True,
        "claudeloop-local": True,
        "claudeloop": True,
        "codexloop": True,
        "cursorloop": False,
        "agyloop": True,
    }
    cursorloop = _engine(document, "cursorloop")
    assert cursorloop["controls"]["stop"] == ["stop", "--run-id", "{run_id}", "--cwd", "{cwd}"]
    assert "prompt" not in cursorloop["capabilities"]["evidence"]["paste_text"]


def test_opencode_is_reported_as_the_code_says_and_the_canon_is_noted() -> None:
    document = _document()
    opencode = _engine(document, "opencode")

    assert opencode["repealed"] is True
    assert opencode["notes"] == [
        "sub-doctrine 8.b repeals opencode from both loops; reported here as its descriptor "
        "says, tier local"
    ]
    assert opencode["controls"] == {"stop": None, "wind_down": None, "prompt": None}
    assert opencode["events"]["envelope"] == "event_type"
    others = [e for loop in document["loops"] for e in loop["engines"] if e is not opencode]
    assert {engine["repealed"] for engine in others} == {False}
    others = [e for e in others if e["engine_id"] != "qwenloop"]
    assert {len(engine["notes"]) for engine in others} == {0}
    assert {engine["repealed"] for engine in others} == {False}


def test_a_repealed_engine_is_never_offered_by_effort() -> None:
    """Listed for transparency, and out of every by-effort view, so neither the extension's
    auto mode nor any other consumer of `by_effort` selects it (amendment 5)."""
    for loop in _document()["loops"]:
        for effort, choices in loop["by_effort"].items():
            assert "opencode" not in [choice["engine_id"] for choice in choices], effort


def test_by_effort_lists_exact_matches_first() -> None:
    sovereign = _document()["loops"][0]

    assert sovereign["by_effort"]["STANDARD"] == [
        {"engine_id": "claudeloop-local", "model": None, "achieved": "STANDARD"},
        {"engine_id": "gptossloop", "model": None, "achieved": "STANDARD"},
        {"engine_id": "qwenloop", "model": None, "achieved": "STANDARD"},
    ]
    assert sovereign["by_effort"]["MAX"] == [
        {"engine_id": "gptossloop", "model": None, "achieved": "MAX"},
        {"engine_id": "qwenloop", "model": None, "achieved": "MAX"},
        {"engine_id": "claudeloop-local", "model": None, "achieved": "STANDARD"},
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


def _models(
    engine_id: str = "gptossloop", **env: str
) -> tuple[str | None, set[str | None], set[str]]:
    """A local runner's default model, every effort's model, and every effort's notes."""
    engine = _engine(_document(**env), engine_id)
    runs = engine["efforts"]
    return (
        engine["default_model"],
        {run["model"] for run in runs},
        {run["notes"] for run in runs},
    )


def test_gptossloops_model_mirrors_how_the_model_reaches_it() -> None:
    """GPTOSSLOOP_MODEL when set; else vibey's model only while VIBEY_OLLAMA_URL is set,
    the one path by which it reaches the session; else none, and gptossloop's own
    configuration chooses (amendment 4)."""
    nothing = (None, {None}, {OWN_CHOICE})
    assert _models() == nothing
    assert _models(VIBEY_OLLAMA_MODEL="qwen3-coder") == nothing
    assert _models(**ENDPOINT) == ("gpt-oss:20b", {"gpt-oss:20b"}, {""})
    assert _models(**ENDPOINT, VIBEY_OLLAMA_MODEL="qwen3-coder") == (
        "qwen3-coder",
        {"qwen3-coder"},
        {""},
    )
    assert _models(GPTOSSLOOP_MODEL="llama3.3") == ("llama3.3", {"llama3.3"}, {""})
    assert _models(**ENDPOINT, GPTOSSLOOP_MODEL="llama3.3") == ("llama3.3", {"llama3.3"}, {""})
    assert _models(**ENDPOINT, GPTOSSLOOP_MODEL="  ") == nothing


def test_qwenloops_model_is_its_own_unless_qwenloop_model_names_one() -> None:
    """ADR-0060: vibey hands qwenloop the endpoint and never this era's default model, so
    the model reported is QWENLOOP_MODEL when set and otherwise qwenloop's own choice."""
    nothing = (None, {None}, {QWEN_OWN_CHOICE})
    assert _models("qwenloop") == nothing
    assert _models("qwenloop", **ENDPOINT, VIBEY_OLLAMA_MODEL="qwen3-coder") == nothing
    assert _models("qwenloop", QWENLOOP_MODEL="qwen3:32b") == ("qwen3:32b", {"qwen3:32b"}, {""})


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
    assert lines[0] == (
        "sovereignloop (tier local): the default loop by canon 8.b; a local engine runs only "
        "while its switch is on"
    )
    assert (
        "paidloop (tier paid): declared only by canon 8.b; the selector does not read a paid "
        "declaration yet, and picks a paid engine whenever no local engine is eligible"
    ) in lines
    assert any(line.split()[:1] == ["TRIVIAL"] and "max-turns 8" in line for line in lines)
    assert any("(no flags) -> STANDARD" in line for line in lines)
    assert (
        "  qwenloop is switched on by VIBEY_FEATURE_QWENLOOP=1, or by its key under [features] "
        "in vibey.toml"
    ) in lines
    assert (
        "  gptossloop is on unless switched off by VIBEY_FEATURE_GPTOSSLOOP=0, or by its key "
        "under [features] in vibey.toml"
    ) in lines
    assert any(line.startswith("  note on qwenloop: since ADR-0060") for line in lines)
    assert any(line.startswith("  note on opencode: sub-doctrine 8.b") for line in lines)
    assert lines[-1] == (
        "Canon 8.b names claudeloop the paid default; the selector does not apply it yet, and "
        "rotates paid engines by weight. `vibey loops --json` has every engine's full facts."
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

    assert lines[1] == "  no engines"
    assert lines[0].startswith("sovereignloop (tier local): the default loop by canon 8.b")


def test_the_command_asks_the_resolvers_it_is_given(capsys: pytest.CaptureFixture[str]) -> None:
    """Built from interfaces: with its resolvers handed in, it reads neither the process's
    environment nor `./vibey.toml`."""
    settings = LocalEngineSettings(environ={}, config={"features": {"qwenloop": True}})
    endpoint = LocalEndpointEnvironment({"QWENLOOP_MODEL": "llama3.3"})

    LoopsCommand(settings=settings, endpoint=endpoint).run(as_json=True)

    qwenloop = _engine(json.loads(capsys.readouterr().out), "qwenloop")
    assert (qwenloop["enabled"], qwenloop["default_model"]) == (True, "llama3.3")


SECRET = "s3cret-token"


@pytest.mark.parametrize(
    ("setting", "env", "toml"),
    [
        ("VIBEY_OLLAMA_URL", {"VIBEY_OLLAMA_URL": f"ftp://operator:{SECRET}@nowhere"}, ""),
        ("VIBEY_OLLAMA_TIMEOUT", {**ENDPOINT, "VIBEY_OLLAMA_TIMEOUT": SECRET}, ""),
        ("VIBEY_OLLAMA_TIMEOUT", {**ENDPOINT, "VIBEY_OLLAMA_TIMEOUT": "-424242"}, ""),
        ("engines.claudeloop_local", {}, f'[engines]\nclaudeloop_local = "{SECRET}"\n'),
    ],
    ids=["url", "timeout-word", "timeout-negative", "vibey-toml"],
)
def test_a_malformed_setting_is_named_and_its_value_never_shown(
    setting: str, env: dict[str, str], toml: str, tmp_path: Path
) -> None:
    """Exit 3 names the setting and never prints its value: a URL can carry `user:token@`,
    and this message reaches a terminal, a log and a CI transcript (amendment 6)."""
    if toml:
        (tmp_path / "vibey.toml").write_text(toml)

    result = runner.invoke(app, ["loops", "--json"], env={**CLEAN, **env})

    assert result.exit_code == 3
    assert result.stderr.startswith(f"Error: {setting}: {MALFORMED_SETTING}")
    for value in (SECRET, "424242"):
        assert value not in result.stdout and value not in result.stderr


# -- the golden ------------------------------------------------------------------------------


def test_the_committed_golden_is_what_the_command_prints_in_its_fixed_environment() -> None:
    """The VS Code extension's parser is tested against this file, so the producer and the
    consumer cannot drift apart (amendment 7, sub-doctrine 12.e). After an intended change,
    regenerate it and commit the diff with the change:

        VIBEY_UPDATE_GOLDENS=1 uv run pytest tests/cli/test_loops_cli.py -k golden
    """
    result = runner.invoke(app, ["loops", "--json"], env={**CLEAN, **GOLDEN_ENVIRONMENT})
    assert result.exit_code == 0, result.output

    if os.environ.get(UPDATE_GOLDENS) == "1":
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(result.stdout, encoding="utf-8")
    assert GOLDEN.is_file(), f"{GOLDEN} is missing; regenerate it with {UPDATE_GOLDENS}=1"
    assert result.stdout == GOLDEN.read_text(encoding="utf-8"), (
        f"`vibey loops --json` no longer prints {GOLDEN.name}. If that is intended, "
        f"regenerate it with {UPDATE_GOLDENS}=1 and commit it with the change."
    )


def test_the_golden_shows_every_kind_of_value_a_parser_must_read() -> None:
    """The fixed environment is chosen so the file carries each field both ways: an engine
    on and one off, a model and none, a switch and none, a repealed engine and the rest."""
    engines = [e for loop in json.loads(GOLDEN.read_text())["loops"] for e in loop["engines"]]

    for field in ("enabled", "repealed"):
        assert {engine[field] for engine in engines} == {True, False}, field
    for field in ("default_model", "switch"):
        values = {engine[field] for engine in engines}
        assert None in values and values - {None}, field
