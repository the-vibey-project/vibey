# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh ci-nightly`: the nightly's watermark, and one tracking issue while it is red.

`last-green` reads the head commit of the last green scheduled run from the forge's Actions
API: a position in the data, never a timestamp. Any doubt answers no watermark, which runs the
nightly (the skip itself is decided by `CiAreas.unchanged`, test_ci_areas_nightly.py).

`report` opens, updates or closes ONE tracking issue through `TrackingIssue`, the family's
issue primitive: red opens it (or brings it current and comments once per run), green closes
it, anything else changes nothing. The in-memory forge is the one test_tracking_issue.py uses.
"""

from __future__ import annotations

import json

import pytest
from test_tracking_issue import REPO, FakeForge

from vibey_gh import cli
from vibey_gh.ci_nightly import CiNightly
from vibey_gh.interfaces.ci_nightly_interface import CiNightlyInterface, NightlyVerdict
from vibey_gh.tracking_issue import TrackingIssue

TIP = "c" * 40
RUN = 41
REF = "o/r/.github/workflows/ci.yml@refs/heads/develop"
RUNS = (
    f"repos/{REPO}/actions/workflows/ci.yml/runs"
    "?branch=develop&event=schedule&status=success&per_page=1"
)
RUN_PATH = f"repos/{REPO}/actions/runs/{RUN}"
JOBS = f"repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100"


def nightly(forge: FakeForge) -> CiNightly:
    return CiNightly(transport=forge, repository=lambda: REPO)


def green_run(sha: str = TIP, **over: str) -> dict:
    return {
        "workflow_runs": [
            {
                "head_sha": sha,
                "head_branch": "develop",
                "event": "schedule",
                "conclusion": "success",
                **over,
            }
        ]
    }


def red_forge(jobs: list[dict]) -> FakeForge:
    forge = FakeForge()
    forge.extra[RUN_PATH] = {
        "head_branch": "develop",
        "head_sha": TIP,
        "html_url": f"https://example.test/runs/{RUN}",
    }
    half = len(jobs) // 2
    forge.extra[JOBS] = json.dumps(jobs[:half]) + json.dumps(jobs[half:])
    return forge


def job(name: str, conclusion: str | None, url: str = "") -> dict:
    return {"name": name, "conclusion": conclusion, "html_url": url}


def test_the_implementation_honours_its_interface() -> None:
    assert isinstance(nightly(FakeForge()), CiNightlyInterface)
    assert isinstance(CiNightly(), CiNightlyInterface)


# ------------------------------------------------------------------------------ the watermark


@pytest.mark.parametrize(
    ("ref", "expected"),
    [
        (REF, "ci.yml"),
        ("o/r/.github/workflows/ci-nightly.yaml@refs/heads/main", "ci-nightly.yaml"),
        ("o/r/.github/workflows/ci.yml", "ci.yml"),
        ("", ""),
        ("ci.yml", ""),
        ("o/r/.github/workflows/../secrets@x", ""),
        ("o/r/.github/workflows/a b.yml@x", ""),
        ("o/r/.github/workflows/sub/ci.yml@x", ""),
    ],
)
def test_the_workflow_file_is_read_from_the_workflow_ref(ref: str, expected: str) -> None:
    assert CiNightly.workflow_file(ref) == expected


def test_the_last_green_scheduled_run_is_its_head_commit() -> None:
    forge = FakeForge()
    forge.extra[RUNS] = green_run()
    assert nightly(forge).last_green("ci.yml", "develop", "schedule") == TIP
    assert forge.calls == [("api", RUNS)]


@pytest.mark.parametrize(
    "answer",
    [
        {"workflow_runs": []},
        {},
        None,
        {"workflow_runs": "x"},
        {"workflow_runs": ["x"]},
        green_run(conclusion="failure"),  # the API ignored a filter: never trusted
        green_run(head_branch="feature"),
        green_run(event="push"),
        green_run(sha="not-a-sha"),
    ],
)
def test_no_trustworthy_green_run_is_no_watermark(answer: object) -> None:
    forge = FakeForge()
    forge.extra[RUNS] = answer
    assert nightly(forge).last_green("ci.yml", "develop", "schedule") == ""


def test_a_branch_or_event_is_quoted_into_the_query() -> None:
    forge = FakeForge()
    path = (
        f"repos/{REPO}/actions/workflows/ci.yml/runs"
        "?branch=feat%2Fx%26y&event=schedule&status=success&per_page=1"
    )
    forge.extra[path] = green_run(head_branch="feat/x&y")
    assert nightly(forge).last_green("ci.yml", "feat/x&y", "schedule") == TIP


def test_the_command_prints_the_watermark(capsys) -> None:
    forge = FakeForge()
    forge.extra[RUNS] = green_run()
    status = CiNightly.run_last_green(
        nightly(forge), workflow_ref=REF, branch="develop", event="schedule"
    )
    assert status == 0
    assert capsys.readouterr().out == f"last_green={TIP}\n"


@pytest.mark.parametrize("ref", ["", "nonsense"])
def test_an_unreadable_workflow_ref_prints_no_watermark_and_asks_nothing(ref, capsys) -> None:
    forge = FakeForge()
    status = CiNightly.run_last_green(
        nightly(forge), workflow_ref=ref, branch="develop", event="schedule"
    )
    captured = capsys.readouterr()
    assert status == 0 and captured.out == "last_green=\n"
    assert "workflow" in captured.err
    assert forge.calls == []


def test_a_forge_failure_prints_no_watermark_and_exits_zero(capsys) -> None:
    forge = FakeForge()
    forge.fail = "actions/workflows"
    status = CiNightly.run_last_green(
        nightly(forge), workflow_ref=REF, branch="develop", event="schedule"
    )
    captured = capsys.readouterr()
    assert status == 0 and captured.out == "last_green=\n"
    assert "HTTP 502" in captured.err


def test_no_green_run_on_record_says_so(capsys) -> None:
    forge = FakeForge()
    forge.extra[RUNS] = {"workflow_runs": []}
    CiNightly.run_last_green(nightly(forge), workflow_ref=REF, branch="develop", event="schedule")
    captured = capsys.readouterr()
    assert captured.out == "last_green=\n"
    assert "no green" in captured.err


# ------------------------------------------------------------------------------ the report


def test_a_red_nightly_opens_one_issue_naming_the_failed_jobs() -> None:
    forge = red_forge(
        [
            job("gates", "failure", "https://example.test/j/1"),
            job("PostgreSQL 15 compatibility", "timed_out"),
            job("CI result", "failure"),
            job("lint", "success"),
            job("desktop", "skipped"),
            job("Nightly report", None),
        ]
    )
    verdict = nightly(forge).report(RUN, "failure", ignore=("CI result",), labels=("ci",))
    assert verdict == NightlyVerdict(
        "red", "Nightly CI is red on develop: gates, PostgreSQL 15 compatibility", 1
    )
    issue = forge.issues[1]
    assert issue["title"] == verdict.reason
    assert issue["labels"] == ["ci"]
    assert issue["body"].startswith(TrackingIssue.marker(CiNightly.key("develop")))
    assert TIP in issue["body"] and f"https://example.test/runs/{RUN}" in issue["body"]
    assert "[gates](https://example.test/j/1)" in issue["body"]
    assert "CI result" not in issue["body"]
    (comment,) = forge.comments[1]
    assert f"run-{RUN}" in comment["body"] and TIP[:12] in comment["body"]


def test_a_repeated_red_nightly_comments_on_the_same_issue_once_per_run() -> None:
    forge = red_forge([job("gates", "failure")])
    tracker = nightly(forge)
    tracker.report(RUN, "failure")
    tracker.report(RUN, "failure")  # a replay of the same run adds nothing
    assert len(forge.comments[1]) == 1
    other = RUN + 1
    forge.extra[f"repos/{REPO}/actions/runs/{other}"] = forge.extra[RUN_PATH]
    forge.extra[f"repos/{REPO}/actions/runs/{other}/jobs?per_page=100"] = json.dumps(
        [job("noloss", "failure")]
    )
    verdict = tracker.report(other, "failure")
    assert verdict.issue == 1 and len(forge.issues) == 1
    assert len(forge.comments[1]) == 2
    assert "noloss" in forge.issues[1]["title"]


def test_many_failed_jobs_are_counted_in_the_title_and_all_listed_in_the_body() -> None:
    names = [f"job {n}" for n in range(8)]
    forge = red_forge([job(name, "failure") for name in names])
    verdict = nightly(forge).report(RUN, "failure")
    assert verdict.reason.endswith("job 0, job 1, job 2, job 3, job 4 and 3 more")
    for name in names:
        assert f"- {name}" in forge.issues[1]["body"]


def test_a_red_result_with_no_failed_job_still_opens_the_issue() -> None:
    forge = red_forge([job("lint", "success")])
    verdict = nightly(forge).report(RUN, "failure")
    assert verdict.state == "red" and verdict.issue == 1
    assert "no job reported a failure" in forge.issues[1]["body"]


def test_an_unreadable_job_list_still_opens_the_issue_and_says_why() -> None:
    forge = red_forge([])
    forge.fail = "/jobs"
    verdict = nightly(forge).report(RUN, "failure")
    assert verdict.state == "red"
    assert "could not be read" in forge.issues[1]["body"]
    assert "HTTP 502" in forge.issues[1]["body"]


def test_a_green_nightly_closes_the_open_issue() -> None:
    forge = red_forge([job("gates", "failure")])
    nightly(forge).report(RUN, "failure")
    verdict = nightly(forge).report(RUN, "success")
    assert verdict == NightlyVerdict("green", f"the nightly on develop is green at {TIP[:12]}", 1)
    assert forge.issues[1]["state"] == "closed"
    assert TIP in forge.comments[1][-1]["body"]


def test_a_green_nightly_with_nothing_open_changes_nothing() -> None:
    forge = red_forge([])
    verdict = nightly(forge).report(RUN, "success")
    assert verdict.state == "green" and verdict.issue is None
    assert forge.issues == {}


@pytest.mark.parametrize("result", ["cancelled", "skipped", "", "weird"])
def test_a_result_that_proves_nothing_changes_nothing(result: str) -> None:
    forge = red_forge([job("gates", "failure")])
    verdict = nightly(forge).report(RUN, result)
    assert verdict.state == "unknown" and verdict.issue is None
    assert forge.issues == {}
    assert not [call for call in forge.calls if "--method" in call]


def test_the_run_is_read_for_its_branch_and_commit() -> None:
    forge = red_forge([job("gates", "failure")])
    forge.extra[RUN_PATH] = {"head_branch": "main", "head_sha": TIP, "html_url": "u"}
    nightly(forge).report(RUN, "failure")
    assert forge.issues[1]["body"].startswith(TrackingIssue.marker("red-nightly:main"))


# ------------------------------------------------------------------------------ the command


def wire(monkeypatch, forge: FakeForge) -> None:
    monkeypatch.setattr("vibey_gh.ci_nightly.GhTransport", lambda: forge)
    monkeypatch.setenv("GH_REPO", REPO)


def test_the_cli_reports(monkeypatch, capsys) -> None:
    forge = red_forge([job("gates", "failure")])
    wire(monkeypatch, forge)
    status = cli.main(
        [
            "ci-nightly",
            "report",
            "--run-id",
            str(RUN),
            "--result",
            "failure",
            "--ignore-job",
            "CI result",
            "--label",
            "ci",
        ]
    )
    assert status == 0
    assert capsys.readouterr().out.startswith("vibey-gh: red — Nightly CI is red on develop")
    assert forge.issues[1]["labels"] == ["ci"]


def test_the_cli_reports_an_unknown_result_without_an_issue_number(monkeypatch, capsys) -> None:
    forge = red_forge([])
    wire(monkeypatch, forge)
    assert cli.main(["ci-nightly", "report", "--run-id", str(RUN), "--result", "cancelled"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("vibey-gh: unknown") and "#" not in out


def test_the_cli_fails_loudly_when_the_run_cannot_be_read(monkeypatch, capsys) -> None:
    forge = FakeForge()
    forge.fail = "actions/runs"
    wire(monkeypatch, forge)
    assert cli.main(["ci-nightly", "report", "--run-id", str(RUN), "--result", "failure"]) == 1
    assert "HTTP 502" in capsys.readouterr().out


def test_the_cli_prints_the_watermark(monkeypatch, capsys) -> None:
    forge = FakeForge()
    forge.extra[RUNS] = green_run()
    wire(monkeypatch, forge)
    status = cli.main(["ci-nightly", "last-green", "--workflow-ref", REF, "--branch", "develop"])
    assert status == 0
    assert capsys.readouterr().out == f"last_green={TIP}\n"
