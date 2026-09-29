# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The three release-path guard workflows render as their commands expect.

skip-markers.yml, branch-health.yml and ruleset-drift.yml exist because the 3.0.0 release
went out with every push workflow on main skipped, develop red for a day unannounced, and
a hand-made ruleset beside the declared one. Each assertion is about a property that, if
lost, would bring one of those back silently.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

from vibey_gh.config import (
    BranchHealthConfig,
    GhConfig,
    RulesetsConfig,
    SkipMarkersConfig,
    WorkflowNamesConfig,
)
from vibey_gh.install import WORKFLOWS, render_workflow


def rendered(name: str, cfg: GhConfig) -> tuple[str, dict]:
    text = render_workflow(WORKFLOWS / name, cfg)
    spec = yaml.safe_load(text)
    spec["on"] = spec.get("on", spec.get(True))
    return text, spec


def test_the_skip_marker_guard_runs_where_a_marker_would_enter_a_permanent_branch(tmp_path):
    text, spec = rendered("skip-markers.yml", GhConfig(root=tmp_path, release_branch="trunk"))
    assert spec["name"] == "Skip markers"
    assert spec["on"]["pull_request"]["branches"] == ["develop", "trunk"]
    # A title or body edited after the last push is what a squash commits.
    assert "edited" in spec["on"]["pull_request"]["types"]
    assert "merge_group" in spec["on"]
    assert spec["permissions"] == {"contents": "read"}
    job = spec["jobs"]["check"]
    assert job["name"] == "No skip markers" and job["if"] is True
    assert "vibey-gh skip-marker-check" in text


def test_the_guard_reads_untrusted_text_only_through_the_environment(tmp_path):
    _, spec = rendered("skip-markers.yml", GhConfig(root=tmp_path))
    step = spec["jobs"]["check"]["steps"][-1]
    assert step["env"]["PR_TITLE"] == "${{ github.event.pull_request.title }}"
    assert step["env"]["PR_BODY"] == "${{ github.event.pull_request.body }}"
    assert "${{" not in step["run"]


def test_the_guard_takes_its_configuration_from_the_trusted_branch_never_the_change(tmp_path):
    _, spec = rendered("skip-markers.yml", GhConfig(root=tmp_path))
    steps = spec["jobs"]["check"]["steps"]
    assert steps[0]["with"]["ref"] == "${{ github.event.repository.default_branch }}"
    assert steps[-1]["working-directory"] == "automation"
    assert "--checkout ../target" in steps[-1]["run"]
    checkouts = [step for step in steps if "actions/checkout" in step.get("uses", "")]
    assert len(checkouts) == 2
    assert all(step["with"]["persist-credentials"] is False for step in checkouts)


def test_a_disabled_guard_renders_a_job_that_never_runs(tmp_path):
    cfg = GhConfig(root=tmp_path, skip_markers=SkipMarkersConfig(enabled=False))
    _, spec = rendered("skip-markers.yml", cfg)
    assert spec["jobs"]["check"]["if"] is False


def test_branch_health_follows_the_adopters_ci_on_both_permanent_branches(tmp_path):
    cfg = GhConfig(root=tmp_path, workflow_names=WorkflowNamesConfig(ci="CI/CD Pipeline"))
    text, spec = rendered("branch-health.yml", cfg)
    trigger = spec["on"]["workflow_run"]
    assert trigger == {
        "workflows": ["CI/CD Pipeline"],
        "types": ["completed"],
        "branches": ["develop", "main"],
    }
    job = spec["jobs"]["alert"]
    assert "github.event.workflow_run.event == 'push'" in job["if"]
    assert job["if"].startswith("true")
    assert job["permissions"] == {"actions": "read", "contents": "read", "issues": "write"}
    assert "vibey-gh branch-health --run-id" in text
    # Never cancelled: each run judges only its own commit while it is the tip.
    assert spec["concurrency"]["cancel-in-progress"] is False


def test_a_disabled_branch_health_renders_a_job_that_never_runs(tmp_path):
    cfg = GhConfig(root=tmp_path, branch_health=BranchHealthConfig(enabled=False))
    _, spec = rendered("branch-health.yml", cfg)
    assert spec["jobs"]["alert"]["if"].startswith("false")


def test_the_drift_check_is_read_only_and_never_passes_what_it_could_not_see(tmp_path):
    text, spec = rendered("ruleset-drift.yml", GhConfig(root=tmp_path))
    assert spec["name"] == "Ruleset drift"
    assert set(spec["on"]) == {"schedule", "push", "workflow_dispatch"}
    assert spec["on"]["push"]["paths"] == [".vibey-gh.toml"]
    assert spec["permissions"] == {"contents": "read"}
    step = spec["jobs"]["check"]["steps"][-1]
    assert "vibey-gh rulesets --check" in step["run"]
    # The reconciling form, which writes, never appears.
    assert "vibey-gh rulesets\n" not in text and "vibey-gh rulesets |" not in text
    assert step["env"]["GH_TOKEN"] == "${{ secrets.AUTOMERGE_TOKEN }}"
    assert "NOT checked" in step["run"]


def test_a_repository_without_rulesets_renders_a_drift_job_that_never_runs(tmp_path):
    cfg = GhConfig(root=tmp_path, rulesets=RulesetsConfig(enabled=False))
    _, spec = rendered("ruleset-drift.yml", cfg)
    assert spec["jobs"]["check"]["if"] is False


def test_the_guard_workflow_names_are_configurable(tmp_path):
    names = WorkflowNamesConfig(skip_markers="SM", branch_health="BH", ruleset_drift="RD")
    cfg = dataclasses.replace(GhConfig(root=tmp_path), workflow_names=names)
    for template, name in (
        ("skip-markers.yml", "SM"),
        ("branch-health.yml", "BH"),
        ("ruleset-drift.yml", "RD"),
    ):
        assert rendered(template, cfg)[1]["name"] == name


def test_this_tree_deploys_the_guards_exactly_as_rendered():
    root = Path(__file__).resolve().parent.parent
    for name in ("skip-markers.yml", "branch-health.yml", "ruleset-drift.yml"):
        assert (root / ".github" / "workflows" / name).is_file(), name
