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


# --- `lint`: the cheap static gates run first, so a lint failure stops the fan-out ---------

LINT = "lint"
# Every job that runs Python or the container waits for `lint`. The JS and desktop jobs have
# their own typecheck and gain nothing from waiting on Python lint, and `chart` is a Helm
# render; they stay ungated so they keep running in parallel.
GATED_BY_LINT = {
    "gates",
    "noloss",
    "postgres-compatibility",
    "tools",
    "tools-lint",
    "image",
    "cluster-smoke",
}
UNGATED_BY_LINT = {"krypton-app", "vibey-core", "app", "vscode-extension", "desktop", "chart"}
# Moved verbatim from `gates` into `lint`, in this order.
MOVED_STEPS = [
    "Install uv",
    "Set up Python",
    "Install dependencies",
    "Install the TypeScript compiler",
    "Gate 0a - committed JavaScript is generated from TypeScript",
    "Gate 0 - governance corpus index",
    "Gate 1 - ruff check",
    "Gate 2 - ruff format --check",
    "Gate 3 - mypy --strict",
    "Gate 5 - lint-imports (onion contract)",
]
# Moved gates only: setup is duplicated on purpose, a gate must run exactly once.
MOVED_GATES = MOVED_STEPS[4:]
STAYING_GATES = [
    "Run test suite with coverage",
    "Gate 4a - pytest domain layer (100% coverage)",
    "Gate 4b - pytest application layer (100% coverage)",
    "Gate 4c - pytest infrastructure layer (100% coverage)",
    "Gate 4d - pytest CLI layer (100% coverage)",
    "Gate 6 - bandit",
    "Gate 7 - pip-audit",
]


def _step_names(job: str) -> list[str]:
    return [str(step.get("name", "")) for step in _jobs()[job]["steps"]]


def _needs(job: str) -> set[str]:
    needs = _jobs()[job].get("needs", [])
    return {needs} if isinstance(needs, str) else set(needs)


def test_lint_job_exists_after_uv_lock_with_its_declared_name() -> None:
    jobs = _jobs()
    assert LINT in jobs, "ci.yml has no `lint` job"
    assert jobs[LINT]["name"] == "Lint and static gates"
    assert _needs(LINT) == {"uv-lock"}


def test_exactly_the_python_and_container_jobs_wait_for_lint() -> None:
    jobs = _jobs()
    waiting = {job for job in jobs if LINT in _needs(job)} - {"ci-result"}
    assert waiting == GATED_BY_LINT, (
        f"jobs gated by lint: {sorted(waiting)}; expected {sorted(GATED_BY_LINT)}"
    )
    assert set(jobs) - {LINT, "ci-result", "uv-lock"} == GATED_BY_LINT | UNGATED_BY_LINT


def test_jobs_that_waited_for_uv_lock_still_do() -> None:
    for job in ("gates", "noloss", "postgres-compatibility", "tools", "tools-lint"):
        assert {"uv-lock", LINT} <= _needs(job), job


def test_moved_steps_live_in_lint_in_order_and_gates_are_not_duplicated() -> None:
    names = _step_names(LINT)
    assert [n for n in names if n in MOVED_STEPS] == MOVED_STEPS
    gates_names = _step_names("gates")
    assert not set(MOVED_GATES) & set(gates_names), "a moved gate is still in `gates`"
    every_gate = [n for job in _jobs() for n in _step_names(job) if n.startswith("Gate ")]
    assert len(every_gate) == len(set(every_gate)), "a gate runs in more than one job"


def test_gates_keeps_the_test_suite_and_the_remaining_gates() -> None:
    names = _step_names("gates")
    for step in STAYING_GATES:
        assert step in names, f"`gates` lost {step!r}"
        assert step not in _step_names(LINT)


def test_gates_keeps_the_environment_the_test_suite_needs() -> None:
    names = _step_names("gates")
    for setup in ("Install uv", "Set up Python", "Install dependencies"):
        assert setup in names
    # The suite recompiles the TypeScript artifacts (tests/meta/test_typescript_artifacts.py),
    # so `gates` still needs Node and the compiler even though Gate 0a moved out.
    assert "Install the TypeScript compiler" in names


def test_ci_result_needs_lint() -> None:
    assert LINT in _needs("ci-result")
