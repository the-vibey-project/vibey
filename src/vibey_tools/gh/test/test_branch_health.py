# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A red permanent branch is announced in one issue, and the issue closes when it is green."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest
from test_tracking_issue import REPO, FakeForge

from vibey_gh import cli
from vibey_gh.branch_health import BranchHealth
from vibey_gh.config import (
    BranchHealthConfig,
    GhConfig,
    RulesetConfig,
    RulesetsConfig,
    load_config,
)
from vibey_gh.interfaces.branch_health_interface import BranchHealthInterface, BranchHealthVerdict
from vibey_gh.tracking_issue import TrackingIssue

SHA = "c" * 40
RUN = 7


def config(tmp_path: Path, **changes) -> GhConfig:
    base = GhConfig(
        root=tmp_path,
        rulesets=RulesetsConfig(
            integration=RulesetConfig(required_checks=("gates", "No-loss")),
            release=RulesetConfig(required_checks=("gates", "uv.lock")),
        ),
    )
    return dataclasses.replace(base, **changes)


def forge_with(
    jobs: list[dict],
    *,
    branch: str = "develop",
    event: str = "push",
    conclusion: str = "failure",
    tip: str = SHA,
) -> FakeForge:
    forge = FakeForge()
    forge.extra[f"repos/{REPO}/actions/runs/{RUN}"] = {
        "head_branch": branch,
        "head_sha": SHA,
        "event": event,
        "conclusion": conclusion,
        "html_url": f"https://example.test/runs/{RUN}",
    }
    forge.extra[f"repos/{REPO}/branches/{branch}"] = {"commit": {"sha": tip}}
    # Two pages, as `--paginate --jq .jobs` prints them.
    half = len(jobs) // 2
    forge.extra[f"repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100"] = json.dumps(
        jobs[:half]
    ) + json.dumps(jobs[half:])
    return forge


def health(tmp_path: Path, forge: FakeForge, **changes) -> BranchHealth:
    cfg = config(tmp_path, **changes)
    return BranchHealth(config=lambda: cfg, transport=forge, repository=lambda: REPO)


def job(name: str, conclusion: str) -> dict:
    return {"name": name, "conclusion": conclusion}


# ------------------------------------------------------------------------- judging


@pytest.mark.parametrize(
    "jobs, run_conclusion, expected",
    [
        ([job("gates", "failure"), job("lint", "success")], "failure", ("red", ("gates",))),
        ([job("gates", "timed_out")], "failure", ("red", ("gates",))),
        ([], "startup_failure", ("red", ())),
        ([job("gates", "success"), job("No-loss", "skipped")], "success", ("green", ())),
        ([job("gates", "success"), job("other", "failure")], "failure", ("green", ())),
        ([job("gates", "cancelled")], "cancelled", ("unknown", ())),
        ([job("gates", "skipped")], "success", ("unknown", ())),
        ([job("gates", None)], "", ("unknown", ())),
        ([job("unwatched", "failure")], "failure", ("unknown", ())),
        # A run that failed before any job existed -- a workflow file the forge refused.
        ([], "failure", ("red", ())),
        ([], "success", ("unknown", ())),
    ],
)
def test_a_run_is_judged_by_its_watched_jobs_alone(jobs, run_conclusion, expected):
    assert BranchHealth().judge(jobs, ("gates", "No-loss"), run_conclusion) == expected


def test_the_check_and_its_verdict_honour_their_interface():
    assert isinstance(BranchHealth(), BranchHealthInterface)
    assert BranchHealthVerdict("red", "why").issue is None


# ------------------------------------------------------------------------- reporting


def test_a_red_push_opens_one_issue_naming_the_failed_checks(tmp_path):
    forge = forge_with([job("gates", "failure"), job("No-loss", "success")])
    verdict = health(tmp_path, forge).report(RUN)
    assert verdict == BranchHealthVerdict("red", "develop is red: gates", 1)
    issue = forge.issues[1]
    assert issue["title"] == "develop is red: gates"
    assert SHA in issue["body"] and "gates, No-loss" in issue["body"]
    assert TrackingIssue.marker("red-branch:develop") in issue["body"]
    assert "run-7" in forge.comments[1][0]["body"]
    # Replayed: the same one issue, the same one comment.
    health(tmp_path, forge).report(RUN)
    assert len(forge.issues) == 1 and len(forge.comments[1]) == 1


def test_a_run_that_could_not_start_is_red_too(tmp_path):
    forge = forge_with([], conclusion="startup_failure")
    verdict = health(tmp_path, forge).report(RUN)
    assert verdict.state == "red"
    assert forge.issues[1]["title"] == "develop is red: the workflow could not start"


def test_a_green_tip_closes_the_open_issue(tmp_path):
    forge = forge_with([job("gates", "success")], conclusion="success")
    TrackingIssue(transport=forge, repository=lambda: REPO).raise_issue(
        "red-branch:develop", "develop is red: gates", "b"
    )
    verdict = health(tmp_path, forge).report(RUN)
    assert verdict == BranchHealthVerdict("green", "develop is green at " + SHA[:12], 1)
    assert forge.issues[1]["state"] == "closed"


def test_a_green_tip_with_nothing_open_changes_nothing(tmp_path):
    forge = forge_with([job("gates", "success")], conclusion="success")
    assert health(tmp_path, forge).report(RUN).issue is None
    assert forge.issues == {}


def test_an_unproven_run_leaves_the_alert_alone(tmp_path):
    forge = forge_with([job("gates", "cancelled")], conclusion="cancelled")
    verdict = health(tmp_path, forge).report(RUN)
    assert verdict.state == "unknown" and forge.issues == {}


def test_a_stale_run_decides_nothing(tmp_path):
    forge = forge_with([job("gates", "failure")], tip="d" * 40)
    verdict = health(tmp_path, forge).report(RUN)
    assert verdict.state == "ignored" and "no longer the tip" in verdict.reason
    assert forge.issues == {}


@pytest.mark.parametrize("branch, event", [("feature", "push"), ("develop", "pull_request")])
def test_only_pushes_to_a_permanent_branch_are_watched(tmp_path, branch, event):
    forge = forge_with([job("gates", "failure")], branch=branch, event=event)
    assert health(tmp_path, forge).report(RUN).state == "ignored"
    assert forge.issues == {}


def test_a_disabled_alert_does_nothing(tmp_path):
    forge = forge_with([job("gates", "failure")])
    verdict = health(tmp_path, forge, branch_health=BranchHealthConfig(enabled=False)).report(RUN)
    assert verdict.state == "ignored" and forge.issues == {}


def test_the_release_branch_is_judged_by_its_own_required_checks(tmp_path):
    forge = forge_with([job("uv.lock", "failure"), job("No-loss", "failure")], branch="main")
    verdict = health(tmp_path, forge).report(RUN)
    assert verdict.reason == "main is red: uv.lock"


def test_declared_checks_override_the_required_checks(tmp_path):
    forge = forge_with([job("gates", "failure"), job("smoke", "failure")])
    declared = BranchHealthConfig(checks=("smoke",), labels=("ci-red",))
    verdict = health(tmp_path, forge, branch_health=declared).report(RUN)
    assert verdict.reason == "develop is red: smoke"
    assert forge.issues[1]["labels"] == ["ci-red"]


def test_a_job_listing_the_forge_refused_raises(tmp_path):
    forge = forge_with([job("gates", "failure")])
    forge.fail = "/jobs"
    del forge.extra[f"repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100"]
    with pytest.raises(RuntimeError, match="HTTP 502"):
        health(tmp_path, forge).report(RUN)


# ---------------------------------------------------------------------------- command


def test_the_cli_reports_the_verdict(monkeypatch, capsys, tmp_path):
    verdicts = iter(
        [
            BranchHealthVerdict("red", "develop is red: gates", 3),
            BranchHealthVerdict("unknown", "x"),
        ]
    )
    monkeypatch.setattr(BranchHealth, "report", lambda self, run_id: next(verdicts))
    assert cli.main(["branch-health", "--run-id", "7"]) == 0
    assert "red — develop is red: gates (#3)" in capsys.readouterr().out
    assert cli.main(["branch-health", "--run-id", "7"]) == 0
    assert capsys.readouterr().out.strip() == "vibey-gh: unknown — x"


def test_the_cli_fails_when_the_forge_cannot_be_read(monkeypatch, capsys):
    def refused(self, run_id):
        raise RuntimeError("gh api: HTTP 404")

    monkeypatch.setattr(BranchHealth, "report", refused)
    assert cli.main(["branch-health", "--run-id", "7"]) == 1
    assert "HTTP 404" in capsys.readouterr().out


# ------------------------------------------------------------------------- config


def test_branch_health_loads_from_toml(tmp_path):
    assert load_config(tmp_path).branch_health == BranchHealthConfig()
    (tmp_path / ".vibey-gh.toml").write_text(
        '[branch_health]\nenabled = false\nchecks = ["gates"]\nlabels = ["red"]\n',
        encoding="utf-8",
    )
    assert load_config(tmp_path).branch_health == BranchHealthConfig(False, ("gates",), ("red",))


@pytest.mark.parametrize("field", ["checks", "labels"])
def test_branch_health_lists_must_be_unique_and_nonempty(field):
    with pytest.raises(ValueError, match=f"branch_health.{field}"):
        BranchHealthConfig(**{field: ("a", "a")})
