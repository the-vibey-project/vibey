# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from pathlib import Path
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from vibey import __version__
from vibey.cli import main as cli_main
from vibey.cli.main import app
from vibey.domain.errors import InvalidAnswer

# Typer force-enables rich ANSI styling whenever GITHUB_ACTIONS is set
# (typer/rich_utils.py), which CI always has and a local shell never does.
# That embeds escape codes inside option names, breaking plain substring
# checks against --help output -- disable it the way Typer itself exposes.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


def _krypton_app_version(monkeypatch: pytest.MonkeyPatch, version: str | None) -> None:
    """Make `importlib.metadata.version("krypton-app")` answer `version`, or say it is absent."""
    import importlib.metadata as metadata

    real = metadata.version

    def fake(name: str) -> str:
        if name != "krypton-app":
            return real(name)
        if version is None:
            raise metadata.PackageNotFoundError(name)
        return version

    monkeypatch.setattr(metadata, "version", fake)


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_version_and_dash_v_print_both_versions(flag: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _krypton_app_version(monkeypatch, "9.8.7")

    result = runner.invoke(app, [flag])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [f"vibey-engine {__version__}", "krypton-app 9.8.7"]


def test_dash_v_with_a_subcommand_prints_the_version_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`-v` is eager like `--version`: it answers before the subcommand is parsed or run."""
    _krypton_app_version(monkeypatch, "1.2.3")

    result = runner.invoke(app, ["-v", "status", "--help"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [f"vibey-engine {__version__}", "krypton-app 1.2.3"]


def test_krypton_app_not_installed_is_named_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _krypton_app_version(monkeypatch, None)

    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        f"vibey-engine {__version__}",
        "krypton-app not installed",
    ]
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    ("argv", "level_args"),
    [(["-d"], 1), (["-dd"], 2), (["-ddd"], 3), (["--verbose", "--verbose"], 2)],
)
def test_dash_d_counts_like_the_old_verbose(
    argv: list[str], level_args: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[int] = []
    real = cli_main.resolve_log_plan

    def spy(*, verbose: int, quiet: bool, log_level: str | None) -> object:
        seen.append(verbose)
        return real(verbose=verbose, quiet=quiet, log_level=log_level)

    monkeypatch.setattr(cli_main, "resolve_log_plan", spy)
    monkeypatch.setenv("VIBEY_LLM_WIRE_LOG", "x")

    result = runner.invoke(app, [*argv, "sabbath"])

    assert seen == [level_args], result.output


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])

    assert "vibey" in result.stdout


def test_cli_commands_are_exposed() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "new" in result.stdout
    assert "design" in result.stdout
    assert "answer" in result.stdout
    assert "work" in result.stdout
    assert "watch" in result.stdout
    assert "status" in result.stdout
    assert "engines" in result.stdout
    assert "cost" in result.stdout
    assert "ledger" in result.stdout
    assert "deploy" in result.stdout


def test_design_command_enqueues_interview(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    project_id = uuid4()

    async def fake_enqueue(received, *, priority):  # type: ignore[no-untyped-def]
        assert received == project_id
        assert priority is False
        return "job-1"

    monkeypatch.setattr(cli_main, "_enqueue_design", fake_enqueue)
    result = runner.invoke(app, ["design", "resume", str(project_id)])
    assert result.exit_code == 0
    assert "design job job-1" in result.stdout


def test_work_command_runs_one_queue_item(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    project_id = uuid4()

    async def fake_work(received, provider, max_turns, max_dollars, ollama_model):  # type: ignore[no-untyped-def]
        assert received == project_id
        # Unstated: the default is resolved once the project's own config is known
        # (sovereign when a local engine is on, else scripted -- ADR-0038).
        assert provider is None
        assert max_turns == 1
        assert max_dollars == 0.25
        assert ollama_model is None
        return True

    monkeypatch.setattr(cli_main, "_work_once", fake_work)
    result = runner.invoke(app, ["work", str(project_id)])
    assert result.exit_code == 0
    assert "processed one job" in result.stdout


def test_load_spec_json(tmp_path: Path) -> None:
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(
            {
                "objective": "Ship",
                "constraints": [{"text": "Offline", "kind": "hard"}],
                "non_goals": ["Cloud"],
                "criteria": [
                    {
                        "criterion_id": "AC-1",
                        "given": "input",
                        "when": "run",
                        "then": "output",
                        "fit": "test passes",
                    }
                ],
                "nfrs": [],
                "walking_skeleton": "one path",
            }
        )
    )
    spec = cli_main._load_spec(path)
    assert spec.is_buildable() == ()
    assert spec.hard_constraints() == ("Offline",)


def test_load_spec_json_keeps_the_research_gaps_it_was_given(tmp_path: Path) -> None:
    """An edited spec that is imported must still say what was not researched."""
    path = tmp_path / "spec.json"
    criterion = {"criterion_id": "AC-1", "given": "g", "when": "w", "then": "t", "fit": "f"}
    path.write_text(
        json.dumps(
            {
                "objective": "Ship",
                "criteria": [criterion],
                "walking_skeleton": "one path",
                "research_gaps": [{"topic": "prior-art", "reason": "no web access"}],
            }
        )
    )
    spec = cli_main._load_spec(path)
    assert [gap.statement() for gap in spec.research_gaps] == [
        "prior-art: not researched. no web access"
    ]

    path.write_text(
        json.dumps({"objective": "Ship", "criteria": [criterion], "walking_skeleton": "one"})
    )
    assert cli_main._load_spec(path).research_gaps == ()


def test_load_spec_json_refuses_a_research_gap_that_gives_no_reason(tmp_path: Path) -> None:
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(
            {
                "objective": "Ship",
                "criteria": [
                    {"criterion_id": "AC-1", "given": "g", "when": "w", "then": "t", "fit": "f"}
                ],
                "walking_skeleton": "one path",
                "research_gaps": [{"topic": "prior-art", "reason": " "}],
            }
        )
    )
    with pytest.raises(ValueError, match="says why"):
        cli_main._load_spec(path)


def test_parse_question_answers_builds_the_handler_payload() -> None:
    assert cli_main._parse_question_answers(("q-1=Ship it", "q-2=default=allowed")) == {
        "answers": {"q-1": "Ship it", "q-2": "default=allowed"}
    }


def test_parse_question_answers_rejects_unkeyed_text() -> None:
    """A VibeyError, not a bare ValueError, so the CLI guard can render it as
    a sentence instead of an asyncio traceback."""
    with pytest.raises(InvalidAnswer, match="QUESTION_ID=ANSWER"):
        cli_main._parse_question_answers(("Ship it",))
