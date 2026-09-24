# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`answer_with`: the `vibey answer` command `vibey gates` prints for each kind of gate.

Every gate kind vibey raises is answered here with the options and default its own handler
raises it with, and the table is held to the source: a kind raised anywhere in `src/vibey`
without a rule, or a rule for a kind nothing raises, fails
`test_every_gate_kind_vibey_raises_has_exactly_one_rule`.
"""

from __future__ import annotations

import ast
import importlib
import shlex
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from typer.testing import CliRunner

import vibey
from vibey.application.dto import HumanGateRecord
from vibey.cli.gate_answers import (
    ANSWER_RULES,
    FREE_FORM,
    GATE_ANSWERS,
    GateAnswerCommands,
    GrantAnswer,
    OptionAnswer,
)
from vibey.cli.interfaces.gate_answers_interface import (
    AnswerRuleInterface,
    GateAnswerCommandsInterface,
)
from vibey.cli.main import app

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
GATE_ID = UUID("0b5c9a4e-1d4c-4c47-9a2a-3c1d2b8f9e10")


def _gate(
    kind: str, options: tuple[str, ...] = (), default_answer: str | None = None
) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=GATE_ID,
        project_id=uuid4(),
        job_id=None,
        kind=kind,
        prompt="a question",
        options=options,
        default_answer=default_answer,
        answer=None,
        raised_at=datetime(2026, 9, 24, 12, 0, tzinfo=UTC),
        timeout_at=None,
        answered_at=None,
        answered_by=None,
    )


# Each kind with the options and default its handler raises it with, and the exact command.
EVERY_KIND: list[tuple[str, tuple[str, ...], str | None, str]] = [
    ("question", ("a CLI", "Python 3.12"), None, "--defaults"),
    ("approval", ("accept", "changes", "cancel"), None, "--verdict accept"),
    ("deploy_demo_review", ("approve", "request_changes"), "approve", "--verdict approve"),
    ("choice", ("local_only", "deploy"), "local_only", "--choice local_only"),
    (
        "deploy_interview",
        ("accept_defaults", "custom"),
        "accept_defaults",
        "--choice accept_defaults",
    ),
    ("deploy_acceptance", ("accept", "reject"), "reject", "--choice reject"),
    (
        "deploy_failure_triage",
        ("LOOP_DEPLOY_DESIGN", "RETRY_DEPLOY_EXECUTE", "ABORT_DEPLOYMENT"),
        "LOOP_DEPLOY_DESIGN",
        "--choice LOOP_DEPLOY_DESIGN",
    ),
    ("bus_dead_lettered", ("replay", "dismiss"), None, "--choice replay"),
    ("budget_exhausted", (), None, """--raw '{"max_dollars": N}'"""),
    ("escalation_exhausted", (), None, """--raw '{"max_attempts": N}'"""),
    ("attempts_exhausted", (), None, """--raw '{"max_attempts": N}'"""),
    ("verify_repair_exhausted", (), None, """--raw '{"max_rounds": N}'"""),
    ("integrate_repair_exhausted", (), None, """--raw '{"max_rounds": N}'"""),
    ("delivery_exhausted", (), None, "--raw '{}'"),
    ("research_evidence", (), None, "--raw '{}'"),
    ("engine_misconfigured", (), None, "--raw '{}'"),
    ("handoff_gate_failed", (), None, "--raw '<json>'"),
    ("too_many_wind_downs", (), None, "--raw '<json>'"),
]


def test_the_shared_renderer_and_every_rule_satisfy_their_interfaces() -> None:
    assert isinstance(GATE_ANSWERS, GateAnswerCommandsInterface)
    for rule in ANSWER_RULES.values():
        assert isinstance(rule, AnswerRuleInterface)


def test_every_rule_in_the_table_is_exercised_below() -> None:
    assert {kind for kind, *_ in EVERY_KIND} == set(ANSWER_RULES)


@pytest.mark.parametrize(
    ("kind", "options", "default_answer", "arguments"),
    EVERY_KIND,
    ids=[entry[0] for entry in EVERY_KIND],
)
def test_every_kind_is_answered_with_its_exact_command(
    kind: str, options: tuple[str, ...], default_answer: str | None, arguments: str
) -> None:
    command = GATE_ANSWERS.command(_gate(kind, options, default_answer))
    assert command == f"vibey answer {GATE_ID} {arguments}"


@pytest.mark.parametrize(
    ("kind", "options", "default_answer", "arguments"),
    EVERY_KIND,
    ids=[entry[0] for entry in EVERY_KIND],
)
def test_every_command_is_one_line_a_shell_splits_back_into_its_words(
    kind: str, options: tuple[str, ...], default_answer: str | None, arguments: str
) -> None:
    gate = _gate(kind, options, default_answer)
    words = shlex.split(GATE_ANSWERS.command(gate))
    rule = GATE_ANSWERS.rule(kind)
    assert words == ["vibey", "answer", str(GATE_ID), *rule.arguments(gate)]


def test_a_kind_with_no_rule_is_answered_free_form() -> None:
    gate = _gate("a_kind_a_newer_vibey_raises", ("yes", "no"), "yes")
    assert GATE_ANSWERS.rule(gate.kind) is FREE_FORM
    assert GATE_ANSWERS.command(gate) == f"vibey answer {GATE_ID} --raw '<json>'"
    assert GATE_ANSWERS.rule(gate.kind).fill_in(gate) == (
        "<json> with a JSON object that answers the prompt"
    )


def test_an_option_gate_that_offers_nothing_falls_back_rather_than_inventing_a_value() -> None:
    gate = _gate("approval")
    rule = GATE_ANSWERS.rule("approval")
    assert GATE_ANSWERS.command(gate) == f"vibey answer {GATE_ID} --raw '<json>'"
    assert rule.fill_in(gate) == "<json> with a JSON object that answers the prompt"


def test_an_option_gate_prefers_its_declared_default_to_its_first_option() -> None:
    gate = _gate("choice", ("deploy", "local_only"), "local_only")
    assert GATE_ANSWERS.command(gate).endswith("--choice local_only")
    assert GATE_ANSWERS.rule("choice").fill_in(gate) is None


def test_an_option_the_shell_would_split_is_quoted() -> None:
    gate = _gate("choice", ("local only; date",), None)
    command = GATE_ANSWERS.command(gate)
    assert command == f"vibey answer {GATE_ID} --choice 'local only; date'"
    assert shlex.split(command)[-1] == "local only; date"


def test_a_grant_names_the_key_its_handler_reads_and_says_what_to_fill_in() -> None:
    gate = _gate("budget_exhausted")
    rule = GATE_ANSWERS.rule("budget_exhausted")
    assert rule.arguments(gate) == ("--raw", '{"max_dollars": N}')
    assert rule.fill_in(gate) == "N with the new max_dollars"


def test_answers_that_run_as_printed_ask_nothing_to_be_filled_in() -> None:
    for kind in ("question", "approval", "delivery_exhausted"):
        gate = _gate(kind, ("accept",), None)
        assert GATE_ANSWERS.rule(kind).fill_in(gate) is None, kind


def test_the_renderer_is_configurable() -> None:
    commands = GateAnswerCommands(
        {"approval": GrantAnswer("max_turns", placeholder="TURNS")},
        fallback=OptionAnswer("--choice", fallback=FREE_FORM),
        program=("uv", "run", "vibey", "answer"),
    )
    assert commands.command(_gate("approval")) == (
        f"""uv run vibey answer {GATE_ID} --raw '{{"max_turns": TURNS}}'"""
    )
    assert commands.command(_gate("other", ("go",))) == f"uv run vibey answer {GATE_ID} --choice go"


@pytest.mark.parametrize("placeholder", ['{"max_dollars": N}', "<json>"])
def test_a_placeholder_pasted_unfilled_is_refused_not_sent(placeholder: str) -> None:
    """A placeholder is not JSON, so `vibey answer` refuses it before touching a gate."""
    result = runner.invoke(app, ["answer", str(uuid4()), "--raw", placeholder])
    assert result.exit_code == 2
    assert "--raw must be valid JSON" in result.output


# -- the table against the source ---------------------------------------------------------------


def _called_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _module_name(root: Path, path: Path) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(("vibey", *parts))


def _raised_gate_kinds() -> set[str]:
    """Every gate kind a `HumanGateRequest(...)` in `src/vibey` names. A literal is read as
    written, a name from the module that uses it; `kind=gate.kind` re-raises a gate that
    already exists and names nothing new. Anything else cannot be read here, and fails."""
    root = Path(vibey.__file__).resolve().parent
    kinds: set[str] = set()
    unread: list[str] = []
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _called_name(node.func) != "HumanGateRequest":
                continue
            named = [keyword.value for keyword in node.keywords if keyword.arg == "kind"]
            kind = named[0] if named else (node.args[0] if node.args else None)
            if isinstance(kind, ast.Constant) and isinstance(kind.value, str):
                kinds.add(kind.value)
            elif isinstance(kind, ast.Name):
                kinds.add(getattr(importlib.import_module(_module_name(root, path)), kind.id))
            elif isinstance(kind, ast.Attribute) and kind.attr == "kind":
                continue
            else:
                unread.append(f"{path.relative_to(root)}:{node.lineno}")
    assert unread == [], f"gate kinds this test cannot read: {unread}"
    return kinds


def test_every_gate_kind_vibey_raises_has_exactly_one_rule() -> None:
    raised = _raised_gate_kinds()
    assert {"question", "approval", "budget_exhausted"} <= raised, "the scan found nothing"
    missing = sorted(raised - set(ANSWER_RULES))
    stale = sorted(set(ANSWER_RULES) - raised)
    assert missing == [], f"raised with no answer rule in vibey.cli.gate_answers: {missing}"
    assert stale == [], f"rules for kinds nothing raises any more: {stale}"
