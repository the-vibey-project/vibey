# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A red branch's issue names the failed step, the first failing test and a command (#1690)."""

from __future__ import annotations

import pytest
from test_branch_health import RUN, forge_with, health
from test_tracking_issue import REPO

from vibey_gh.config import BranchHealthConfig
from vibey_gh.failure_evidence import FailureEvidence
from vibey_gh.interfaces.failure_evidence_interface import (
    FailingTest,
    FailureEvidenceInterface,
    Reproduction,
    StepFailure,
)

JOB_URL = "https://example.test/runs/7/job/99"
STAMP = "2026-10-23T10:51:02.1234567Z "
TEST_ID = "tests/meta/test_paper_figures.py::test_pins"
LOG = (
    f"{STAMP}collected 3 items\n"
    f"{STAMP}##[group]Run pytest\n"
    f"{STAMP}FAILED {TEST_ID} - AssertionError\n"
    f"{STAMP}FAILED tests/other.py::test_two - boom\n"
)
MAPPING = (
    ("gates :: Run test suite with coverage", "uv run pytest {test} -q"),
    ("gates", "make gates"),
    ("lint", "ruff check ."),
)


def failing_job(name: str = "gates", **extra) -> dict:
    return {
        "id": 99,
        "name": name,
        "conclusion": "failure",
        "html_url": JOB_URL,
        "steps": [
            {"name": "Set up job", "number": 1, "conclusion": "success"},
            {"name": "Run test suite with coverage", "number": 14, "conclusion": "failure"},
            {"name": "Post", "number": 15, "conclusion": "skipped"},
        ],
        **extra,
    }


def logged(jobs, log: str | None = LOG, **kw):
    forge = forge_with(jobs, **kw)
    if log is not None:
        forge.extra[f"repos/{REPO}/actions/jobs/99/logs"] = log
    return forge


def declared(**changes) -> dict:
    return {"branch_health": BranchHealthConfig(reproduce=MAPPING, **changes)}


# ---------------------------------------------------------------------------- the report


def test_the_1680_shape_names_step_test_and_command_in_body_and_comment(tmp_path):
    forge = logged([failing_job()])
    health(tmp_path, forge, **declared()).report(RUN)
    expected = (
        "**gates**\n"
        f"- step: [Run test suite with coverage (step 14)]({JOB_URL}#step:14:1)\n"
        f"- first failing test: `{TEST_ID}`, job-log line 3\n"
        f"- reproduce: `uv run pytest {TEST_ID} -q`"
    )
    assert expected in forge.issues[1]["body"]
    assert expected in forge.comments[1][0]["body"]
    # Replayed: still one comment per run.
    health(tmp_path, forge, **declared()).report(RUN)
    assert len(forge.comments[1]) == 1


def test_an_unmapped_check_is_reported_unmapped_not_guessed(tmp_path):
    forge = logged([failing_job("VS Code extension (ubuntu)")])
    forge.extra[f"repos/{REPO}/actions/runs/{RUN}"]["conclusion"] = "failure"
    cfg = declared(checks=("VS Code extension (ubuntu)",))
    health(tmp_path, forge, **cfg).report(RUN)
    assert "- reproduce: unknown: no reproduction command is declared" in forge.issues[1]["body"]


def test_a_job_without_steps_still_files_the_alert(tmp_path):
    bare = {"id": 99, "name": "gates", "conclusion": "failure"}
    forge = logged([bare])
    health(tmp_path, forge, **declared()).report(RUN)
    body = forge.issues[1]["body"]
    assert "- step: unknown: the forge reported no failed step" in body
    assert "- reproduce: `make gates`" in body


def test_a_step_without_a_job_url_is_named_without_a_link(tmp_path):
    job = failing_job()
    del job["html_url"]
    forge = logged([job])
    health(tmp_path, forge).report(RUN)
    assert "- step: Run test suite with coverage (step 14)\n" in forge.issues[1]["body"]


def test_an_unreadable_log_degrades_and_still_files(tmp_path):
    forge = logged([failing_job()])
    forge.fail = "/logs"
    health(tmp_path, forge, **declared()).report(RUN)
    body = forge.issues[1]["body"]
    assert "unknown: the job log could not be read" in body
    # The step-level command needs a test id the log never gave: no command, no guess.
    assert "- reproduce: unknown: the declared command needs a test id" in body


def test_a_job_without_an_id_has_no_log_to_read(tmp_path):
    job = failing_job()
    del job["id"]
    forge = logged([job])
    health(tmp_path, forge).report(RUN)
    assert "the job log could not be read" in forge.issues[1]["body"]
    assert not any("/logs" in " ".join(call) for call in forge.calls)


def test_a_log_without_a_failing_test_falls_back_to_the_error_line(tmp_path):
    forge = logged([failing_job()], log=f"{STAMP}ok\n{STAMP}##[error]Process completed\n")
    health(tmp_path, forge).report(RUN)
    assert (
        "no failing test id in the log; first `##[error]` at job-log line 2"
        in forge.issues[1]["body"]
    )


def test_a_log_with_nothing_to_name_says_so(tmp_path):
    forge = logged([failing_job()], log="all quiet\n")
    health(tmp_path, forge).report(RUN)
    assert "- first failing test: unknown: no failing test id in the log\n" in (
        forge.issues[1]["body"]
    )


def test_a_truncated_log_keeps_its_tail_and_drops_line_numbers(tmp_path):
    log = "x" * 500 + "\n" + f"FAILED {TEST_ID}\n"
    forge = logged([failing_job()], log=log)
    health(tmp_path, forge, **declared(log_bytes=100)).report(RUN)
    body = forge.issues[1]["body"]
    assert f"`{TEST_ID}` (log truncated to its tail; no line numbers)" in body


def test_a_truncated_log_with_no_test_or_error_is_marked(tmp_path):
    forge = logged([failing_job()], log="y" * 300)
    health(tmp_path, forge, **declared(log_bytes=50)).report(RUN)
    assert "in the log (log truncated to its tail; no line numbers)" in forge.issues[1]["body"]


def test_a_test_id_cannot_break_out_of_the_markdown_or_the_command(tmp_path):
    forge = logged([failing_job()], log="FAILED a`b;rm\n")
    health(tmp_path, forge, **declared()).report(RUN)
    body = forge.issues[1]["body"]
    assert "`a'b;rm`" in body
    assert "uv run pytest 'a`b;rm' -q" in body


def test_green_and_unknown_verdicts_read_no_log(tmp_path):
    forge = logged([{**failing_job(), "conclusion": "success"}], conclusion="success")
    health(tmp_path, forge).report(RUN)
    assert not any("/logs" in " ".join(call) for call in forge.calls)


def test_a_run_that_could_not_start_has_no_job_to_describe(tmp_path):
    forge = logged([], conclusion="startup_failure")
    health(tmp_path, forge).report(RUN)
    assert "**" not in forge.issues[1]["body"]


# ----------------------------------------------------------------------- the evidence class


def test_the_evidence_class_honours_its_interface():
    assert isinstance(FailureEvidence(), FailureEvidenceInterface)
    assert FailingTest("t").line is None


def test_failed_steps_tolerate_missing_fields():
    job = {"steps": [{"conclusion": "failure"}, {"name": "ok", "conclusion": "success"}]}
    assert FailureEvidence().failed_steps(job) == (StepFailure("", 0),)
    assert FailureEvidence().failed_steps({}) == ()


@pytest.mark.parametrize(
    "check, step, test, expected",
    [
        ("gates", "Run test suite with coverage", "a::b", "uv run pytest a::b -q"),
        ("gates", "Gate 1", None, "make gates"),
        ("gates", None, None, "make gates"),
        ("lint", "any step", None, "ruff check ."),
    ],
)
def test_the_most_specific_declared_command_wins(check, step, test, expected):
    got = FailureEvidence().reproduction(check, step, test, MAPPING)
    assert got == Reproduction(expected, "declared")


def test_a_placeholder_without_a_test_id_yields_no_command():
    got = FailureEvidence().reproduction("gates", "Run test suite with coverage", None, MAPPING)
    assert got.command is None and "test id" in got.reason


def test_an_undeclared_check_yields_no_command():
    got = FailureEvidence().reproduction("nope", None, "a::b", MAPPING)
    assert got.command is None and "no reproduction command" in got.reason


def test_a_pattern_without_a_group_returns_the_whole_match():
    found = FailureEvidence().first_failing_test("x\nERROR boom\n", r"^ERROR \w+")
    assert found == FailingTest("ERROR boom", 2)


def test_no_match_is_none_and_a_truncated_error_line_is_unplaceable():
    assert FailureEvidence().first_failing_test("nothing", r"^FAILED (\S+)") is None
    assert FailureEvidence().first_error_line("##[error]x", truncated=True) is None
    assert FailureEvidence().first_error_line("ok") is None
