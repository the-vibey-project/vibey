"""The open-weights repair of a failing review (#1400).

A review that fails on findings is corrected rather than left for a person, where the
repository declares `[pr_automation.sovereign_repair]`: the composer marks the failure
repairable, the repair job asks the bounded budget before it spends an attempt, and the
workflow renders the declared runner, models and limits -- or, undeclared, never schedules
the job at all.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from vibey_gh import cli, pr_automation as pa
from vibey_gh.config import (
    GhConfig,
    PrAutomationConfig,
    PrAutomationSovereignRepairConfig,
    load_config,
)
from vibey_gh.install import WORKFLOWS, render_workflow
from vibey_gh.review_composition import FULL, NO_PAID, REVIEW_COMPOSER
from vibey_gh.review_contract import (
    DIFF_GROUNDABLE,
    REQUIRES_WIDER_CONTEXT,
    REVIEW_CONTRACT,
)

FINDING = {"severity": "blocking", "file": "a.py", "line": 3, "message": "off by one"}


def _sovereign_whole(**changes: Any) -> dict[str, Any]:
    """A whole-review verdict as `local-review --scope full` publishes it."""
    answer: dict[str, Any] = {name: True for name in REVIEW_CONTRACT.requires_wider_context}
    answer.update({"pass": True, "summary": "Adds a flag.", "findings": []})
    answer[REVIEW_CONTRACT.scope_field] = [DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT]
    answer.update(changes)
    return answer


def _repairing() -> Any:
    return dataclasses.replace(REVIEW_COMPOSER, sovereign_repair=True)


# --------------------------------------------------------------------------------------
# The declaration
# --------------------------------------------------------------------------------------


def test_the_repair_is_off_unless_declared():
    """A local model's finding starting an edit is a decision a repository says aloud."""
    declared = PrAutomationConfig().sovereign_repair
    assert declared == PrAutomationSovereignRepairConfig()
    assert declared.enabled is False
    assert declared.models == ("gpt-oss:20b",)


def test_the_table_is_read_with_every_key_it_leaves_out_at_its_default(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        'owner = "owner"\n'
        "[pr_automation.sovereign_repair]\n"
        "enabled = true\n"
        'models = ["gpt-oss:20b", "qwen3:4b"]\n'
        "max_turns = 12\n",
        encoding="utf-8",
    )
    declared = load_config(tmp_path).pr_automation.sovereign_repair
    assert declared.enabled is True
    assert declared.models == ("gpt-oss:20b", "qwen3:4b")
    assert declared.max_turns == 12
    assert declared.runs_on == "ubuntu-24.04-arm"
    assert declared.timeout_minutes == 150


@pytest.mark.parametrize(
    ("table", "match"),
    [
        ({"enabled": "yes"}, "must be true or false"),
        ({"runs_on": "ubuntu latest"}, "one runner label"),
        ({"runs_on": ""}, "one runner label"),
        ({"models": []}, "at least one model"),
        ({"models": ["gpt-oss:20b; rm -rf ~"]}, "not an Ollama model"),
        ({"models": [42]}, "not an Ollama model"),
        ({"models": ["gpt-oss:20b", "gpt-oss:20b"]}, "must not repeat"),
        ({"max_turns": 0}, "from 1 to 200"),
        ({"max_turns": True}, "from 1 to 200"),
        ({"timeout_minutes": 331}, "from 10 to 330"),
        ({"timeout_minutes": 5}, "from 10 to 330"),
        ({"enable": True}, "does not know enable"),
    ],
)
def test_every_value_that_reaches_a_rendered_workflow_is_refused_unless_well_formed(table, match):
    """Each value lands in YAML or a shell line; a typo is refused, never rendered."""
    with pytest.raises(ValueError, match=match):
        PrAutomationSovereignRepairConfig.from_table(table)


# --------------------------------------------------------------------------------------
# The composer
# --------------------------------------------------------------------------------------


def test_undeclared_a_sovereign_failure_is_still_a_lead_for_a_person():
    envelope = REVIEW_COMPOSER.compose(
        None,
        half=NO_PAID,
        sovereign=_sovereign_whole(**{"pass": False}, findings=[FINDING]),
        head_sha="abc",
    )
    assert envelope["repairable"] is False
    assert envelope["verdict"]["repairable"] is False


def test_declared_a_sovereign_failure_with_findings_goes_to_repair():
    """The workflow reads the envelope's own `repairable`; the verdict carries the same."""
    envelope = _repairing().compose(
        None,
        half=NO_PAID,
        sovereign=_sovereign_whole(**{"pass": False}, findings=[FINDING]),
        head_sha="abc",
    )
    assert envelope["halves"][FULL]["passed"] is False
    assert envelope["repairable"] is True
    assert envelope["verdict"]["repairable"] is True


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(_sovereign_whole(), id="it passed"),
        pytest.param(_sovereign_whole(**{"pass": False}), id="it failed with nothing to act on"),
    ],
)
def test_declared_a_review_with_nothing_to_correct_is_not_repaired(answer):
    envelope = _repairing().compose(None, half=NO_PAID, sovereign=answer, head_sha="abc")
    assert envelope["repairable"] is False


def test_combine_reads_the_declaration_from_the_configuration(monkeypatch, capsys, tmp_path):
    declared = GhConfig(
        root=tmp_path,
        owner="owner",
        pr_automation=PrAutomationConfig(
            sovereign_repair=PrAutomationSovereignRepairConfig(enabled=True)
        ),
    )
    monkeypatch.setattr(cli, "load_config", lambda *a, **k: declared)
    answer = _sovereign_whole(**{"pass": False}, findings=[FINDING])
    code = cli.main(
        [
            "pr-automation",
            "combine",
            "--half",
            NO_PAID,
            "--sovereign",
            json.dumps(answer),
            "--head-sha",
            "abc",
        ]
    )
    assert code == 0
    assert json.loads(capsys.readouterr().out)["repairable"] is True


# --------------------------------------------------------------------------------------
# The budget
# --------------------------------------------------------------------------------------


def _pr(comments: list[Any]) -> dict[str, Any]:
    return {"number": 12, "headRefOid": "abc", "comments": comments}


@pytest.mark.parametrize(
    ("attempts", "remaining"),
    [(None, 3), (0, 3), (2, 1), (3, 0), (5, 0)],
)
def test_the_budget_reports_what_is_left_of_the_bounded_attempts(
    monkeypatch, tmp_path, attempts, remaining
):
    """The same-run path never passes `evaluate_pr`; the job asks this before it spends."""
    comments = (
        []
        if attempts is None
        else [pa.state_body(pa.AutomationState("abc", "abc", attempts=attempts), "x")]
    )
    monkeypatch.setattr(pa, "fetch_pr", lambda number: _pr(comments))
    budget = pa.repair_budget(12, GhConfig(root=tmp_path, owner="owner"))
    assert budget == {
        "pr": 12,
        "attempts": attempts or 0,
        "max": 3,
        "remaining": remaining,
    }


def test_the_budget_is_asked_from_the_command_line(monkeypatch, capsys):
    monkeypatch.setattr(pa, "fetch_pr", lambda number: _pr([]))
    assert cli.main(["pr-automation", "repair-budget", "--pr", "12"]) == 0
    assert json.loads(capsys.readouterr().out)["remaining"] >= 1


# --------------------------------------------------------------------------------------
# The workflow
# --------------------------------------------------------------------------------------


def _render(tmp_path: Path, repair: PrAutomationSovereignRepairConfig) -> dict[str, Any]:
    cfg = GhConfig(
        root=tmp_path,
        owner="owner",
        pr_automation=PrAutomationConfig(sovereign_repair=repair),
    )
    text = render_workflow(WORKFLOWS / "pr-review.yml", cfg)
    assert "__VIBEY_GH_SOVEREIGN_REPAIR" not in text
    return yaml.safe_load(text)


def test_undeclared_the_repair_jobs_are_never_scheduled(tmp_path):
    jobs = _render(tmp_path, PrAutomationSovereignRepairConfig())["jobs"]
    for name in ("repair-sovereign", "publish-sovereign-repair"):
        assert jobs[name]["if"].startswith("false && ")


def test_declared_the_repair_renders_its_runner_models_and_limits(tmp_path):
    declared = PrAutomationSovereignRepairConfig(
        enabled=True, runs_on="ubuntu-24.04", models=("qwen3:4b",), max_turns=9, timeout_minutes=60
    )
    spec = _render(tmp_path, declared)
    repair = spec["jobs"]["repair-sovereign"]
    assert repair["if"].startswith("true && !false && ")
    assert repair["runs-on"] == "ubuntu-24.04"
    # Read-only: the patch is applied elsewhere, from a trusted checkout.
    assert repair["permissions"] == {"contents": "read", "pull-requests": "read"}
    steps = {step.get("name"): step for step in repair["steps"]}
    assert steps["Start an open-weights model, with every declared fallback"]["env"] == {
        "MODELS": "qwen3:4b"
    }
    agent = steps["Correct the findings with gptossloop"]["run"]
    assert 'timeout "60m" gptossloop run' in agent and "--max-turns 9" in agent
    assert "repair-budget" in steps["Ask the repair budget"]["run"]
    gate = spec["jobs"]["gate"]
    assert {"repair-sovereign", "publish-sovereign-repair"} <= set(gate["needs"])


def test_a_declared_paid_repair_keeps_the_open_weights_one_off(tmp_path):
    """Two engines never edit one branch for one review."""
    cfg = GhConfig(
        root=tmp_path,
        owner="owner",
        pr_automation=PrAutomationConfig(
            paid_repair=True,
            sovereign_repair=PrAutomationSovereignRepairConfig(enabled=True),
        ),
    )
    spec = yaml.safe_load(render_workflow(WORKFLOWS / "pr-review.yml", cfg))
    assert spec["jobs"]["repair-sovereign"]["if"].startswith("true && !true && ")


def test_the_publish_step_keeps_the_paid_repairs_guards():
    """Stale heads, workflow edits and an empty patch are each refused, never pushed."""
    spec = yaml.safe_load((WORKFLOWS / "pr-review.yml").read_text(encoding="utf-8"))
    publish = spec["jobs"]["publish-sovereign-repair"]
    run = next(
        s["run"]
        for s in publish["steps"]
        if s.get("name") == "Apply and publish one guarded repair commit"
    )
    for guard in (
        "outcome=no-patch",
        "outcome=refused-workflows",
        "outcome=stale",
        "outcome=unappliable",
    ):
        assert guard in run
    record = next(
        s["run"]
        for s in publish["steps"]
        if s.get("name") == "Record the attempt, or hand the branch to a person"
    )
    assert "record-repair" in record and "vibey-gh:automation-blocked" in record
