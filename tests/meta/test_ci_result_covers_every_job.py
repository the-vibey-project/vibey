# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`ci-result` is the one check that is red when any CI job is red.

Only a handful of CI checks are required on develop, so a job outside that set can fail
and still merge. `ci-result` depends on every job and fails unless each one finished
`success` or `skipped`, so a single required check can stand for the whole workflow.

`needs` is derived from the live job list rather than enumerated here: a hard-coded list
is the same defect one layer up (ADR-0018). The step's script is executed, not just
grepped, because a gate that reports success it did not observe is a liability.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
JOB = "ci-result"


def _jobs() -> dict[str, Any]:
    workflow = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs: dict[str, Any] = workflow["jobs"]
    return jobs


def _step() -> dict[str, Any]:
    steps = _jobs()[JOB]["steps"]
    assert len(steps) == 1, f"{JOB} must have exactly one step, found {len(steps)}"
    step: dict[str, Any] = steps[0]
    return step


def _needs_json(results: dict[str, str]) -> str:
    return json.dumps({job: {"result": result, "outputs": {}} for job, result in results.items()})


def _run(needs_json: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "NEEDS_JSON": needs_json}
    return subprocess.run(
        ["bash", "-c", _step()["run"]],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_ci_result_needs_every_other_job() -> None:
    # A pytest function is the collection contract, so ADR-0016 permits it here.
    jobs = _jobs()
    assert JOB in jobs, f"ci.yml has no `{JOB}` job"
    expected = set(jobs) - {JOB}
    actual = set(jobs[JOB]["needs"])
    assert actual == expected, (
        f"{JOB} must need every other job. Missing from needs: {sorted(expected - actual)}; "
        f"needs a job that does not exist: {sorted(actual - expected)}"
    )


def test_ci_result_runs_even_when_a_needed_job_fails() -> None:
    assert _jobs()[JOB]["if"] == "always()"


def test_ci_result_step_fails_on_failure_and_cancellation_but_not_skip(tmp_path: Path) -> None:
    ok = _run(_needs_json({"a": "success", "b": "skipped"}), tmp_path)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "a" in ok.stdout and "b" in ok.stdout

    for results in ({"a": "failure"}, {"a": "cancelled"}, {"a": "success", "b": "weird"}):
        bad = _run(_needs_json(results), tmp_path)
        assert bad.returncode == 1, f"{results} must fail: {bad.stdout}{bad.stderr}"

    for empty in ("", "{}"):
        nothing = _run(empty, tmp_path)
        assert nothing.returncode == 1, f"{empty!r} must fail: nothing ran"


def test_no_workflow_expression_is_interpolated_into_the_script() -> None:
    assert "${{" not in _step()["run"]
    assert _step()["env"]["NEEDS_JSON"] == "${{ toJSON(needs) }}"
