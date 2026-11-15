# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The nightly full CI run: its schedule, its full matrix, its skip guard and its report (SP1-B Task 4).

A pull request into develop runs only what its diff can affect, on a small matrix. Every night
ci.yml runs on a `schedule` against develop's tip (GitHub runs a cron on the DEFAULT branch
only, and develop is it), and the `schedule` event is a full-tier event, so every row the
pull-request tier dropped is proven daily. The run is skipped when its commit is the head of
the last GREEN scheduled run (a position-based watermark from the Actions API, never a time),
and a red nightly keeps one tracking issue open through `vibey-gh ci-nightly report`.

What a scheduled run does cannot be observed before this merges: the first run on develop is
the proof. These tests pin everything that can be pinned without it -- the trigger, the plan's
schedule path (its shell executed against stubs), every guard expression (evaluated, by the
evaluator test_ci_tiers_keep_every_row.py defines) and the real CLI's outputs for both a due
and an unchanged nightly.

Checks are module-level functions: pytest collects functions (ADR-0016 permits it).
"""

import json
import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml
from vibey_gh.ci_areas import CiAreas, CiAreasCommand

from .ci_matrix_rows import CiMatrixRows
from .test_ci_tiers_keep_every_row import AREA_JOBS, MATRIX_JOBS, ExpressionEvaluator

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
AREAS = REPO / ".github/ci-areas.toml"
MATRICES = REPO / ".github/ci-matrices.toml"
TIP = "a" * 40
OLDER = "b" * 40
NON_SCHEDULE_EVENTS = ("pull_request", "push", "merge_group", "workflow_dispatch")


def _workflow() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return loaded


def _jobs() -> dict[str, Any]:
    jobs: dict[str, Any] = _workflow()["jobs"]
    return jobs


def _on() -> dict[str, Any]:
    # PyYAML reads the bare key `on` as the boolean True.
    workflow = _workflow()
    on: dict[str, Any] = workflow.get("on", workflow.get(True))
    return on


def _expression(job: str) -> ExpressionEvaluator:
    text = str(_jobs()[job]["if"]).strip()
    assert text.startswith("${{ ") and text.endswith(" }}"), job
    return ExpressionEvaluator(text[4:-3])


def _plan_step(step_id: str) -> dict[str, Any]:
    (found,) = [s for s in _jobs()["plan"]["steps"] if s.get("id") == step_id]
    return found


# ------------------------------------------------------------------------------- the trigger


def test_the_nightly_is_a_schedule_on_ci_yml_at_06_17_utc() -> None:
    assert _on()["schedule"] == [{"cron": "17 6 * * *"}]


def test_the_other_triggers_are_unchanged() -> None:
    on = _on()
    assert set(on) == {"push", "pull_request", "merge_group", "schedule"}
    assert on["push"] == {"branches": ["main", "develop"]}
    assert on["pull_request"] == {"branches": ["main", "develop"]}


def test_the_cron_runs_on_the_declared_integration_branch() -> None:
    # A cron runs on the repository's DEFAULT branch only. That it is develop was read from the
    # forge when this was written (`gh api repos/<repo> --jq .default_branch`); what can be
    # pinned offline is that develop is the declared integration branch, the one the nightly is
    # for, and that the plan reads the branch from the event rather than naming it.
    config = tomllib.loads((REPO / ".vibey-gh.toml").read_text(encoding="utf-8"))
    assert config["branches"]["integration"] == "develop"
    assert _plan_step("watermark")["env"]["BRANCH"] == "${{ github.ref_name }}"


def test_a_scheduled_run_is_never_cancelled_by_concurrency() -> None:
    assert _workflow()["concurrency"]["cancel-in-progress"] == (
        "${{ github.event_name == 'pull_request' }}"
    )


# ------------------------------------------------------------------------------- the watermark


def test_the_watermark_step_runs_on_a_schedule_only_and_before_the_decision() -> None:
    step = _plan_step("watermark")
    assert step["if"] == "github.event_name == 'schedule'"
    assert step["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "GH_REPO": "${{ github.repository }}",
        "WORKFLOW_REF": "${{ github.workflow_ref }}",
        "BRANCH": "${{ github.ref_name }}",
    }
    assert "${{" not in step["run"]
    ids = [s.get("id") or s.get("name") for s in _jobs()["plan"]["steps"]]
    assert ids.index("Install vibey-gh") < ids.index("watermark") < ids.index("cli")


def test_only_the_watermark_step_is_handed_the_token() -> None:
    holders = [
        s.get("id") or s.get("name")
        for s in _jobs()["plan"]["steps"]
        if "GH_TOKEN" in (s.get("env") or {})
    ]
    assert holders == ["watermark"]
    assert _jobs()["plan"]["permissions"] == {"actions": "read", "contents": "read"}


def test_the_watermark_step_prints_the_cli_line_into_the_outputs(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "vibey-gh"
    stub.write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$@" > "$STUB_ARGS"\necho "last_green={TIP}"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    output = tmp_path / "output"
    output.touch()
    done = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", _plan_step("watermark")["run"]],
        cwd=tmp_path,
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "STUB_ARGS": str(tmp_path / "args"),
            "WORKFLOW_REF": "o/r/.github/workflows/ci.yml@refs/heads/develop",
            "BRANCH": "develop",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert output.read_text(encoding="utf-8") == f"last_green={TIP}\n"
    assert (tmp_path / "args").read_text(encoding="utf-8").split() == [
        "ci-nightly",
        "last-green",
        "--workflow-ref",
        "o/r/.github/workflows/ci.yml@refs/heads/develop",
        "--branch",
        "develop",
    ]


# ------------------------------------------------------------------------------- the CLI's answer


def _areas_outputs(capsys: pytest.CaptureFixture[str], **overrides: str) -> dict[str, str]:
    args = {
        "base": "",
        "head": TIP,
        "event": "schedule",
        "base_ref": "develop",
        "fmt": "github-output",
    }
    args.update(overrides)
    status = CiAreasCommand().areas(
        base=args["base"],
        head=args["head"],
        event=args["event"],
        base_ref=args["base_ref"],
        fmt=args["fmt"],
        paths=(REPO, AREAS, MATRICES),
        last_green=args.get("last_green", ""),
    )
    assert status == 0
    return dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())


def _area_jobs_that_run(outputs: dict[str, str]) -> set[str]:
    every = {"uv-lock": "success", "lint": "success", "plan": "success"}
    return {
        job
        for job in AREA_JOBS
        if _expression(job).evaluate(every, outputs, cancelled=False, event="schedule")
    }


def _lint_runs(outputs: dict[str, str], event: str = "schedule", **results: str) -> bool:
    every = {"uv-lock": "success", **results}
    return _expression("lint").evaluate(every, outputs, cancelled=False, event=event)


@pytest.mark.parametrize("last_green", ["", OLDER, "not-a-commit"])
def test_a_due_nightly_runs_the_full_matrix_and_every_job(
    capsys: pytest.CaptureFixture[str], last_green: str
) -> None:
    outputs = _areas_outputs(capsys, last_green=last_green)
    assert (outputs["full"], outputs["tier"]) == ("true", "full")
    assert _area_jobs_that_run(outputs) == set(AREA_JOBS)
    assert _lint_runs(outputs)
    for job, output in MATRIX_JOBS.items():
        assert json.loads(outputs[f"{output}_matrix"]) == {"include": CiMatrixRows.full(job)}


def test_an_unchanged_nightly_runs_nothing_but_the_plan_uv_lock_and_ci_result(
    capsys: pytest.CaptureFixture[str],
) -> None:
    outputs = _areas_outputs(capsys, last_green=TIP)
    assert (outputs["full"], outputs["tier"], outputs["areas"]) == ("false", "skip", "[]")
    assert _area_jobs_that_run(outputs) == set()
    assert not _lint_runs(outputs)
    # `gates` has no `if:`: it needs `lint`, so the implicit success() skips it with `lint`.
    gates = _jobs()["gates"]
    assert "if" not in gates and "lint" in gates["needs"]
    # ... and the report says nothing about a run that proved nothing.
    report = _expression("nightly-report")
    assert not report.evaluate({}, outputs, cancelled=False, event="schedule")


def test_the_skip_outputs_come_from_the_map_not_from_the_workflow() -> None:
    ci = CiAreas.load(AREAS, MATRICES)
    assert ci.skip_unchanged_events == ("schedule",)
    assert ci.outputs(ci.skip_decision("x"))["tier"] == "skip"


# ------------------------------------------------------------------------------- `lint`'s guard


def test_lint_reads_only_its_chain_the_event_and_the_tier() -> None:
    assert _expression("lint").references() == {
        "cancelled()",
        "needs.uv-lock.result",
        "github.event_name",
        "needs.plan.outputs.tier",
    }


@pytest.mark.parametrize("event", NON_SCHEDULE_EVENTS)
def test_lint_never_skips_off_a_schedule_whatever_the_plan_says(event: str) -> None:
    # A required check: even a (wrong) `skip` tier on a pull request must not skip it.
    for outputs in ({}, {"tier": "skip"}, {"tier": "full"}, {"tier": "pr"}):
        assert _lint_runs(outputs, event=event), (event, outputs)


@pytest.mark.parametrize("outputs", [{}, {"tier": ""}, {"tier": "full"}, {"tier": "pr"}])
def test_lint_runs_on_a_schedule_unless_the_tier_is_skip(outputs: dict[str, str]) -> None:
    assert _lint_runs(outputs)


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped"])
def test_lint_still_waits_for_uv_lock(result: str) -> None:
    assert not _lint_runs({}, event="pull_request", **{"uv-lock": result})
    assert not _expression("lint").evaluate(
        {"uv-lock": "success"}, {}, cancelled=True, event="pull_request"
    )


# ------------------------------------------------------------------------------- the report


def test_the_report_comes_after_ci_result_and_only_on_a_due_schedule() -> None:
    job = _jobs()["nightly-report"]
    assert job["name"] == "Nightly report"
    assert set(job["needs"]) == {"plan", "ci-result"}
    report = _expression("nightly-report")
    assert report.references() == {"cancelled()", "github.event_name", "needs.plan.outputs.tier"}
    for event in NON_SCHEDULE_EVENTS:
        assert not report.evaluate({}, {}, cancelled=False, event=event), event
    for outputs in ({}, {"tier": "full"}):
        assert report.evaluate({}, outputs, cancelled=False, event="schedule")
    assert not report.evaluate({}, {"tier": "skip"}, cancelled=False, event="schedule")
    assert not report.evaluate({}, {}, cancelled=True, event="schedule")


def test_the_report_holds_least_privilege_and_calls_the_family_command() -> None:
    job = _jobs()["nightly-report"]
    assert job["permissions"] == {"actions": "read", "contents": "read", "issues": "write"}
    (step,) = [s for s in job["steps"] if "vibey-gh ci-nightly report" in s.get("run", "")]
    assert "${{" not in step["run"]
    assert step["env"]["RESULT"] == "${{ needs.ci-result.result }}"
    assert step["env"]["RUN_ID"] == "${{ github.run_id }}"
    assert '--ignore-job "CI result"' in step["run"]
    assert "gh issue" not in yaml.safe_dump(job), "issues go through vibey-gh, not by hand"
    (checkout,) = [s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/checkout")]
    assert checkout["with"]["persist-credentials"] is False


def test_nothing_in_ci_yml_can_publish() -> None:
    # The only write any job holds is the nightly report's `issues: write`.
    writes = {
        (job_id, scope)
        for job_id, job in _jobs().items()
        for scope, level in (job.get("permissions") or {}).items()
        if level != "read"
    }
    assert writes == {("nightly-report", "issues")}
    assert _workflow()["permissions"] == {"contents": "read"}
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "push: true" not in text
    for publisher in ("pypi-publish", "gh release", "npm publish", "vsce publish", "ovsx publish"):
        assert publisher not in text, publisher
