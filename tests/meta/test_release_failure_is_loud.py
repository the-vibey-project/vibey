# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A failed develop publish must open (or comment on) an issue, never pass silently."""

from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
TITLE = "Release: develop publish failed"


def _testpypi() -> dict[str, Any]:
    workflow = yaml.safe_load(
        (REPO / ".github/workflows/vibey-engine.yml").read_text(encoding="utf-8")
    )
    job: dict[str, Any] = workflow["jobs"]["testpypi"]
    return job


def _notify(job: dict[str, Any]) -> dict[str, Any]:
    steps = [
        s for s in job["steps"] if s.get("if") == "failure()" and "gh issue" in s.get("run", "")
    ]
    assert len(steps) == 1, "testpypi needs exactly one failure() step that runs `gh issue`"
    return steps[0]


def test_failed_publish_opens_an_issue() -> None:
    # A pytest function is the collection contract, so ADR-0016 permits it here.
    job = _testpypi()
    assert job["permissions"]["issues"] == "write"
    run = _notify(job)["run"]
    assert TITLE in run
    assert "release-health" in run
    assert "gh issue create" in run


def test_repeated_failures_comment_instead_of_opening_another_issue() -> None:
    run = _notify(_testpypi())["run"]
    assert "gh issue list --state open --search" in run
    assert "gh issue comment" in run
    assert run.index("gh issue list") < run.index("gh issue create")


def test_the_publish_step_still_fails_the_job() -> None:
    job = _testpypi()
    assert "continue-on-error" not in job
    publish = next(s for s in job["steps"] if "gh-action-pypi-publish" in s.get("uses", ""))
    assert "continue-on-error" not in publish


def test_the_issue_names_the_testpypi_storage_limit() -> None:
    run = _notify(_testpypi())["run"]
    assert "Project size too large" in run
    assert "docs.pypi.org/project-management/storage-limits" in run


def test_the_notify_step_carries_no_expression_in_its_script() -> None:
    # Values reach the script through `env`, never by `${{ }}` interpolation into shell.
    assert "${{" not in _notify(_testpypi())["run"]


def test_the_notify_step_cannot_hide_the_publish_failure() -> None:
    assert _notify(_testpypi())["continue-on-error"] is True


def test_the_job_keeps_trusted_publishing_and_gains_only_issues_write() -> None:
    permissions = _testpypi()["permissions"]
    assert permissions["id-token"] == "write"
    assert permissions["issues"] == "write"


def test_the_notify_step_names_its_repository_and_token_in_env() -> None:
    env = _notify(_testpypi())["env"]
    assert "GH_REPO" in env
    assert "GH_TOKEN" in env


def test_the_issue_lookup_matches_the_title_exactly() -> None:
    # A search is fuzzy: only an exact title match may count as the existing issue.
    assert "select(.title ==" in _notify(_testpypi())["run"]


def test_the_notify_step_comes_after_the_publish_step() -> None:
    steps = _testpypi()["steps"]
    publish = next(i for i, s in enumerate(steps) if "gh-action-pypi-publish" in s.get("uses", ""))
    assert steps.index(_notify(_testpypi())) > publish
