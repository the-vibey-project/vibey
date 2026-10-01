# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The release path recovers from what went wrong on 2026-09-29, and says so when it cannot.

Releasing 3.0.0 found four gaps, each silent:

  - The hand-squashed promotion's body quoted a skip-ci marker, so GitHub ran no push
    workflow on main, and the publishing workflows, triggered only on push, could not be
    re-run: there was no run.
  - An optional channel (Open VSX) with no credential failed the `Release` run, so the tag,
    the GitHub Release and the documentation -- which follow only a successful Release --
    never happened, although PyPI had published.
  - main accepted a squash at all, where promotion is a rebase.
  - Nothing in the declaration said what a squash commit's message is made of.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"
PUBLISHERS = ("vibey-engine.yml", "krypton-app.yml")


def load(name: str) -> dict:
    spec = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    # `on` is the YAML 1.1 boolean `True`; safe_load gives that key, not the string.
    spec["on"] = spec.get("on", spec.get(True)) or {}
    return spec


@pytest.mark.parametrize("name", PUBLISHERS)
def test_a_skipped_release_push_can_be_recovered_by_dispatch(name: str) -> None:
    assert "workflow_dispatch" in load(name)["on"], (
        f"{name} must be dispatchable: a push the forge skipped leaves no run to re-run"
    )


@pytest.mark.parametrize("name", PUBLISHERS)
def test_every_publishing_job_is_gated_on_the_branch_not_the_event(name: str) -> None:
    """A dispatch sets `github.ref` to the branch it was run on, so ref-gated publishing
    publishes exactly what that branch's push would have, and nothing from anywhere else."""
    for job_id, job in load(name)["jobs"].items():
        environment = job.get("environment")
        if environment in ("pypi", "testpypi"):
            branch = "main" if environment == "pypi" else "develop"
            assert job.get("if") == f"github.ref == 'refs/heads/{branch}'", (name, job_id)


def test_no_optional_channel_can_fail_the_release_run() -> None:
    """github-release.yml and release-surfaces.yml follow only a SUCCESSFUL Release. A job
    of that run which needs an optional credential decides whether the tag and the docs
    exist at all -- 3.0.0 shipped without both for want of OVSX_PAT."""
    text = (WORKFLOWS / "vibey-engine.yml").read_text(encoding="utf-8")
    assert "secrets.OVSX_PAT" not in text
    assert "openvsx" not in load("vibey-engine.yml")["jobs"]


def test_open_vsx_publishes_after_a_successful_release_and_says_so_without_a_token() -> None:
    spec = load("openvsx.yml")
    assert spec["on"]["workflow_run"] == {
        "workflows": ["Release"],
        "types": ["completed"],
        "branches": ["main"],
    }
    assert load("vibey-engine.yml")["name"] == "Release"
    job = spec["jobs"]["publish"]
    assert "github.event.workflow_run.conclusion == 'success'" in job["if"]
    assert job["permissions"] == {"contents": "read", "issues": "write"}
    missing = next(step for step in job["steps"] if step.get("if") == "env.OVSX_PAT == ''")
    assert "::warning::" in missing["run"] and "vibey-gh tracking-issue raise" in missing["run"]
    assert "exit 1" not in missing["run"]
    publish = next(step for step in job["steps"] if step.get("name") == "Publish, once per version")
    # A real upload failure stays loud: no error is swallowed on the token path.
    assert "|| true" not in publish["run"]


def test_open_vsx_creates_its_namespace_first_tolerating_only_already_exists() -> None:
    """Open VSX refuses a publish into a namespace nobody created, and nothing had created
    `the-vibey-project`. The step creates it from the manifest's own `publisher`, treats
    "already exists" as done, and fails on every other refusal -- never a blanket `|| true`."""
    steps = load("openvsx.yml")["jobs"]["publish"]["steps"]
    names = [step.get("name") for step in steps]
    create = "Make sure the publisher's namespace exists"
    assert names.index(create) < names.index("Publish, once per version")
    step = steps[names.index(create)]
    assert step["if"] == "env.OVSX_PAT != ''"
    run = step["run"]
    assert "ovsx create-namespace" in run and "require('./package.json').publisher" in run
    assert "already exists" in run and "exit 1" in run
    assert "|| true" not in run


def test_main_is_rebase_only_and_squashes_propose_the_pull_requests_own_words() -> None:
    config = tomllib.loads((REPO / ".vibey-gh.toml").read_text(encoding="utf-8"))
    assert config["rulesets"]["release"]["allowed_merge_methods"] == ["rebase"]
    profile = config["repository_profile"]
    assert (profile["squash_merge_commit_title"], profile["squash_merge_commit_message"]) == (
        "PR_TITLE",
        "PR_BODY",
    )


def test_the_skip_marker_guard_gates_both_permanent_branches() -> None:
    config = tomllib.loads((REPO / ".vibey-gh.toml").read_text(encoding="utf-8"))
    for branch in ("integration", "release"):
        assert "No skip markers" in config["rulesets"][branch]["required_checks"], branch
    assert "Skip markers" in config["pr_automation"]["scan_workflows"]
    assert config["skip_markers"]["exempt_authors"] == []
    for name in ("skip-markers.yml", "branch-health.yml", "ruleset-drift.yml"):
        assert name in config["install"]["workflows"], name
        assert (WORKFLOWS / name).is_file(), name
