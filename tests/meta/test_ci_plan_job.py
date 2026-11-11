# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `plan` job reports the changed areas and the tier, and can never cause a skip (SP1-B).

A skipped required check passes on GitHub, so `plan` is built so that it cannot be the reason
anything is skipped: a failing step does not cut a dependant (job-level `continue-on-error`:
the check run still concludes `failure`, `needs.plan.result` is `success`), it has no `needs`, its
first step writes the all-full defaults (the full matrices as literals), and later steps only
overwrite them. The jobs that read its outputs, and how, are pinned in
`test_ci_tiers_keep_every_row.py`; here a test says that nothing reads its `result`.

The shell of the `vibey-gh ci-areas` step is executed with a stub `vibey-gh` that echoes its
arguments and a stub `git` that fails if called, so the per-event arguments are proved by
running them, not by grepping them. The github.event field names (`merge_group.base_sha` and
the rest) are NOT verifiable here: the first merge-queue run is the proof.

Checks are module-level functions: pytest collects functions (ADR-0016 permits it).
"""

import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
LIMITS = REPO / "tests/meta/ci_job_limits.toml"
OUTPUTS = {
    "areas",
    "full",
    "tier",
    "tools_any",
    "postgres_any",
    "desktop_any",
    "tools_matrix",
    "postgres_matrix",
    "desktop_matrix",
}
ZEROS = "0" * 40


def _jobs() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    return loaded


def _plan() -> dict[str, Any]:
    plan: dict[str, Any] = _jobs()["plan"]
    return plan


def _steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = _plan()["steps"]
    return steps


def _step(step_id: str) -> dict[str, Any]:
    (found,) = [s for s in _steps() if s.get("id") == step_id]
    return found


def test_plan_is_a_job_with_the_declared_shape() -> None:
    plan = _plan()
    assert plan["name"] == "CI plan"
    assert plan["runs-on"] == "ubuntu-latest"
    assert plan["timeout-minutes"] == 10
    assert plan["continue-on-error"] is True
    assert "needs" not in plan
    assert "if" not in plan
    assert set(plan["outputs"]) == OUTPUTS


def test_plan_has_a_limits_entry_marked_unmeasured() -> None:
    entry = tomllib.loads(LIMITS.read_text(encoding="utf-8"))["jobs"]["plan"]
    assert entry == {"timeout_minutes": 10, "basis": "unmeasured"}


def test_plan_is_needed_by_ci_result() -> None:
    assert "plan" in _jobs()["ci-result"]["needs"]


def test_the_first_step_writes_the_all_full_defaults_before_anything_else() -> None:
    first = _steps()[0]
    assert first["id"] == "defaults"
    assert "uses" not in first, "the first step must need nothing: not even a checkout"
    script = first["run"]
    for line in (
        "full=true",
        "tier=full",
        "tools_any=true",
        "postgres_any=true",
        "desktop_any=true",
    ):
        assert line in script, line
    assert "areas=[]" in script
    assert "$GITHUB_OUTPUT" in script


def test_the_checkout_is_deep_and_keeps_no_credentials() -> None:
    (checkout,) = [s for s in _steps() if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {"fetch-depth": 0, "persist-credentials": False}
    order = [s.get("id") or s.get("uses") for s in _steps()]
    assert order.index("defaults") < order.index("actions/checkout@v4")


def test_only_vibey_gh_is_installed_from_the_checkout() -> None:
    installs = [
        s["run"]
        for s in _steps()
        if s.get("id") != "defaults" and "pip install" in s.get("run", "")
    ]
    assert installs == ["pip install -e src/vibey_tools/gh"]


def test_the_matrix_defaults_are_literals_written_by_the_first_step() -> None:
    # A plan that dies before the `cli` step (a failed checkout or install) must still hand
    # the matrix jobs their full matrices, so the first step writes them as literals instead
    # of asking vibey-gh. tests/meta/test_ci_tiers_keep_every_row.py holds each literal to
    # `vibey-gh ci-matrix --job <job> --tier full`.
    ids = [s.get("id") for s in _steps()]
    assert "matrices" not in ids
    script = _step("defaults")["run"]
    for key in ("tools_matrix=", "postgres_matrix=", "desktop_matrix="):
        assert key in script
    # (the literals themselves mention `pip install`: they are data, never run by this step)
    assert "vibey-gh ci-" not in script.replace("`vibey-gh ci-matrix", ""), (
        "needs nothing installed"
    )
    assert not [
        ln for ln in script.splitlines() if ln.strip().startswith(("pip ", "uv ", "vibey-gh"))
    ]


def test_no_workflow_expression_is_interpolated_into_a_script() -> None:
    for step in _steps():
        assert "${{" not in step.get("run", ""), step.get("name")


def test_every_output_falls_through_from_the_cli_to_the_defaults() -> None:
    pattern = re.compile(
        r"^\$\{\{ steps\.cli\.outputs\.(\w+) \|\| steps\.(defaults)\.outputs\.(\w+) \}\}$"
    )
    for name, expression in _plan()["outputs"].items():
        match = pattern.match(expression)
        assert match, f"{name}: {expression}"
        assert match.group(1) == match.group(3) == name
        assert match.group(2) == "defaults"


def test_the_jobs_read_the_plans_outputs_and_never_its_result() -> None:
    # `needs.plan.result` is unproven for a timed-out or cancelled plan, so no job may depend
    # on it: each reads outputs (which fall through to the full defaults) and replaces the
    # implicit `success()` with `!cancelled()`.
    for job_id, job in _jobs().items():
        blob = yaml.safe_dump(job)
        assert "needs.plan.result" not in blob, job_id
        assert "needs.plan.conclusion" not in blob, job_id
    consumers = {j for j, spec in _jobs().items() if "plan" in (spec.get("needs") or [])}
    assert consumers - {"ci-result"} == {
        "noloss",
        "postgres-compatibility",
        "tools",
        "tools-lint",
        "krypton-app",
        "vibey-core",
        "app",
        "vscode-extension-ubuntu",
        "vscode-extension-macos",
        "desktop",
        "image",
        "chart",
        "cluster-smoke",
    }
    assert "gates" not in consumers and "lint" not in consumers and "uv-lock" not in consumers


# --- the shell of the `vibey-gh ci-areas` step, executed -----------------------------------


def _run_cli_step(tmp_path: Path, env: dict[str, str]) -> tuple[list[str], str, int]:
    """Run the step's script; return the stub's argv, the step summary and the exit status."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "vibey-gh").write_text(
        '#!/bin/bash\nprintf "%s\\n" "$@" > "$STUB_ARGS"\n'
        'echo "areas=[\\"docs\\"]"\necho "full=false"\necho "tier=pr"\n'
        'echo "reason: stub" >&2\n',
        encoding="utf-8",
    )
    (bin_dir / "git").write_text('#!/bin/bash\necho "git called" >> "$STUB_GIT"\nexit 99\n')
    for stub in bin_dir.iterdir():
        stub.chmod(0o755)
    output, summary = tmp_path / "output", tmp_path / "summary"
    output.touch()
    summary.touch()
    full_env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GITHUB_OUTPUT": str(output),
        "GITHUB_STEP_SUMMARY": str(summary),
        "STUB_ARGS": str(tmp_path / "args"),
        "STUB_GIT": str(tmp_path / "git-calls"),
        "TMPDIR": str(tmp_path),
        **env,
    }
    done = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", _step("cli")["run"]],
        cwd=tmp_path,
        env=full_env,
        capture_output=True,
        text=True,
        check=False,
    )
    args_file = tmp_path / "args"
    argv = args_file.read_text(encoding="utf-8").split() if args_file.exists() else []
    assert not (tmp_path / "git-calls").exists(), "the step must never call git itself"
    text = summary.read_text(encoding="utf-8")
    return argv, text + "\n--output--\n" + output.read_text(encoding="utf-8"), done.returncode


CASES: list[tuple[str, dict[str, str], list[str]]] = [
    (
        "pull_request",
        {"PR_BASE_SHA": "b1", "PR_HEAD_SHA": "h1", "PR_BASE_REF": "develop"},
        [
            "ci-areas",
            "--event",
            "pull_request",
            "--base",
            "b1",
            "--head",
            "h1",
            "--base-ref",
            "develop",
        ],
    ),
    (
        "push",
        {"PUSH_BEFORE": "b2", "PUSH_AFTER": "h2", "PUSH_REF_NAME": "develop"},
        [
            "ci-areas",
            "--event",
            "push",
            "--base",
            "b2",
            "--head",
            "h2",
            "--base-ref",
            "develop",
        ],
    ),
    (
        "merge_group",
        {"MQ_BASE_SHA": "b3", "MQ_HEAD_SHA": "h3"},
        ["ci-areas", "--event", "merge_group", "--base", "b3", "--head", "h3"],
    ),
    ("workflow_dispatch", {}, ["ci-areas", "--event", "workflow_dispatch"]),
    ("schedule", {}, ["ci-areas", "--event", "schedule"]),
]


@pytest.mark.parametrize(("event", "env", "expected"), CASES, ids=[c[0] for c in CASES])
def test_each_event_passes_exactly_its_own_arguments(
    tmp_path: Path, event: str, env: dict[str, str], expected: list[str]
) -> None:
    argv, text, status = _run_cli_step(tmp_path, {"EVENT_NAME": event, **env})
    assert status == 0, text
    assert argv == expected
    assert "tier=pr" in text.split("--output--")[1], "the CLI's lines reach $GITHUB_OUTPUT"
    assert "reason: stub" in text, "the CLI's reasons reach the step summary"


def test_the_merge_group_summary_prints_the_base_and_head_it_used(tmp_path: Path) -> None:
    _, text, status = _run_cli_step(
        tmp_path, {"EVENT_NAME": "merge_group", "MQ_BASE_SHA": "b3", "MQ_HEAD_SHA": "h3"}
    )
    assert status == 0
    summary = text.split("--output--")[0]
    assert "base" in summary and "b3" in summary
    assert "head" in summary and "h3" in summary


def test_an_all_zero_before_takes_the_full_path_without_git_or_a_diff(tmp_path: Path) -> None:
    argv, text, status = _run_cli_step(
        tmp_path,
        {
            "EVENT_NAME": "push",
            "PUSH_BEFORE": ZEROS,
            "PUSH_AFTER": "h2",
            "PUSH_REF_NAME": "feature",
        },
    )
    assert status == 0, text
    assert argv == ["ci-areas", "--event", "push", "--base-ref", "feature"]
    assert "new branch" in text


def test_an_unrecognised_event_is_handed_to_the_cli_to_decide(tmp_path: Path) -> None:
    argv, _, status = _run_cli_step(tmp_path, {"EVENT_NAME": "release"})
    assert status == 0
    assert argv == ["ci-areas", "--event", "release"]


def test_a_failing_cli_fails_the_step_and_writes_nothing(tmp_path: Path) -> None:
    # The job's `continue-on-error` is what keeps this from being a skip; the step itself
    # fails loudly, and the defaults written by the first step are what the job reports.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "vibey-gh").write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    (bin_dir / "vibey-gh").chmod(0o755)
    output = tmp_path / "output"
    output.touch()
    done = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", _step("cli")["run"]],
        cwd=tmp_path,
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
            "TMPDIR": str(tmp_path),
            "EVENT_NAME": "workflow_dispatch",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode != 0
    assert output.read_text(encoding="utf-8") == ""


def test_the_cli_step_reads_every_github_value_from_env() -> None:
    env = _step("cli")["env"]
    assert env["EVENT_NAME"] == "${{ github.event_name }}"
    assert env["PR_BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert env["PR_HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert env["PR_BASE_REF"] == "${{ github.event.pull_request.base.ref }}"
    assert env["PUSH_BEFORE"] == "${{ github.event.before }}"
    assert env["PUSH_AFTER"] == "${{ github.sha }}"
    assert env["PUSH_REF_NAME"] == "${{ github.ref_name }}"
    assert env["MQ_BASE_SHA"] == "${{ github.event.merge_group.base_sha }}"
    assert env["MQ_HEAD_SHA"] == "${{ github.event.merge_group.head_sha }}"
