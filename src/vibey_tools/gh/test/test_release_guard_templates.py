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


# The pull request that introduces skip-markers.yml, and every one after it until a
# promotion, runs the default branch's older vibey-gh, which has no skip-marker-check.
# The guard must still refuse a marker there -- and still let a clean change through,
# or the promotion that carries the command could never merge.
def _bootstrap_run(tmp_path: Path, *, message: str, title: str = "", body: str = ""):
    import os
    import subprocess

    _, spec = rendered("skip-markers.yml", GhConfig(root=tmp_path))
    script = spec["jobs"]["check"]["steps"][-1]["run"]
    tmp_path.mkdir(exist_ok=True)
    target = tmp_path / "target"
    automation = tmp_path / "automation"
    bin_dir = tmp_path / "bin"
    for directory in (target, automation, bin_dir):
        directory.mkdir()
    # An older vibey-gh: every subcommand it lacks is an argparse error, exit 2.
    fake = bin_dir / "vibey-gh"
    fake.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    fake.chmod(0o755)
    git = [
        "git",
        "-c",
        "user.name=guard-test",
        "-c",
        "user.email=guard-test@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "core.hooksPath=/dev/null",
        "-C",
        str(target),
    ]
    subprocess.run([*git, "init", "-q", "-b", "develop"], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "chore: base"], check=True)
    base = subprocess.run(
        [*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", message], check=True)
    head = subprocess.run(
        [*git, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    env = {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PR_TITLE": title,
        "PR_BODY": body,
        "BASE_SHA": base,
        "HEAD_SHA": head,
        "BASE_REF": "develop",
    }
    return subprocess.run(
        ["bash", "-c", script],
        cwd=automation,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_bootstrap_scan_knows_every_marker_the_command_knows(tmp_path):
    from vibey_gh.config import SKIP_MARKERS

    _, spec = rendered("skip-markers.yml", GhConfig(root=tmp_path))
    script = spec["jobs"]["check"]["steps"][-1]["run"]
    alternation = script.split("bracketed='\\[(", 1)[1].split(")\\]'", 1)[0]
    assert {f"[{spelling}]" for spelling in alternation.split("|")} == set(SKIP_MARKERS)


def test_older_tooling_still_refuses_a_marker_in_a_commit(tmp_path):
    marker = "[" + "skip ci" + "]"
    done = _bootstrap_run(tmp_path, message=f"docs: quiet change {marker}")
    assert done.returncode == 1, done.stdout + done.stderr
    assert "bootstrap scan" in done.stdout


def test_older_tooling_still_refuses_a_marker_in_the_body_or_a_trailer(tmp_path):
    body = "Squashed text\n\n" + "skip-checks" + ": true\n"
    assert _bootstrap_run(tmp_path / "body", message="fix: ok", body=body).returncode == 1
    title = "chore: x " + "[" + "CI SKIP" + "]"
    assert _bootstrap_run(tmp_path / "title", message="fix: ok", title=title).returncode == 1


def test_older_tooling_lets_a_clean_change_through(tmp_path):
    done = _bootstrap_run(
        tmp_path, message="feat: add the guard", title="feat: add the guard", body="skip-ci is fine"
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "no skip marker" in done.stdout
