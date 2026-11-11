# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every CI job declares its time limit, and the workflow holds the least token permission.

A job without `timeout-minutes` runs under GitHub's 360-minute default, so one hung job
occupies a scarce runner slot for six hours (20 concurrent, 5 macOS). The limits live in
`tests/meta/ci_job_limits.toml`, each beside the measurement it came from, and this test
makes the workflow and that file say the same thing in both directions: a job with no
entry is named, and an entry for a job that no longer exists is named too, so the list
shrinks when its reason goes (sub-doctrine 12.e, ADR-0018).

The token is read-only by default. A job that needs more is declared under
`[permission_exceptions]` with its reason, and must carry its own `permissions:` block.

Checks are module-level functions: pytest collects functions, and ADR-0016 permits that
for a collection contract.
"""

import tomllib
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
LIMITS = REPO / "tests/meta/ci_job_limits.toml"
READ_ONLY = {"contents": "read"}


def _workflow() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return loaded


def _limits() -> dict[str, Any]:
    loaded: dict[str, Any] = tomllib.loads(LIMITS.read_text(encoding="utf-8"))
    return loaded


def timeout_problems(jobs: dict[str, Any], limits: dict[str, Any]) -> list[str]:
    """What is wrong between the workflow's jobs and the limits file, one line each."""
    problems: list[str] = []
    default = limits["default_timeout_minutes"]
    entries: dict[str, Any] = limits.get("jobs", {})
    for job_id in sorted(set(jobs) - set(entries)):
        problems.append(f"job `{job_id}` has no entry in {LIMITS.name}")
    for job_id in sorted(set(entries) - set(jobs)):
        problems.append(f"{LIMITS.name} has an entry for `{job_id}`, which is not a job in ci.yml")
    for job_id, job in sorted(jobs.items()):
        expected = entries.get(job_id, {}).get("timeout_minutes", default)
        actual = job.get("timeout-minutes")
        if actual != expected:
            problems.append(f"job `{job_id}` has timeout-minutes {actual!r}, expected {expected!r}")
    return problems


def permission_problems(workflow: dict[str, Any], limits: dict[str, Any]) -> list[str]:
    """What is wrong with the token permissions, one line each."""
    problems: list[str] = []
    top = workflow.get("permissions")
    if top != READ_ONLY:
        problems.append(f"top-level permissions is {top!r}, expected {READ_ONLY!r}")
    jobs: dict[str, Any] = workflow["jobs"]
    exceptions: dict[str, Any] = limits.get("permission_exceptions", {})
    for job_id, reason in sorted(exceptions.items()):
        if job_id not in jobs:
            problems.append(f"permission exception `{job_id}` is not a job in ci.yml")
        elif "permissions" not in jobs[job_id]:
            problems.append(f"permission exception `{job_id}` has no permissions block of its own")
        if not reason:
            problems.append(f"permission exception `{job_id}` states no reason")
    for job_id, job in sorted(jobs.items()):
        if "permissions" in job and job_id not in exceptions:
            problems.append(
                f"job `{job_id}` widens its permissions but is not a declared exception"
            )
    return problems


def checkout_problems(workflow: dict[str, Any]) -> list[str]:
    """A checkout that sets persist-credentials must set it false; absence is not required."""
    problems: list[str] = []
    for job_id, job in sorted(workflow["jobs"].items()):
        for step in job.get("steps", []):
            if str(step.get("uses", "")).startswith("actions/checkout@"):
                value = (step.get("with") or {}).get("persist-credentials")
                if value not in (None, False):
                    problems.append(f"job `{job_id}` checkout sets persist-credentials: {value!r}")
    return problems


def test_every_job_has_the_timeout_its_entry_declares() -> None:
    problems = timeout_problems(_workflow()["jobs"], _limits())
    assert not problems, "\n".join(problems)


def test_a_job_missing_from_the_limits_file_is_named() -> None:
    jobs = {"alpha": {"timeout-minutes": 10}, "beta": {"timeout-minutes": 10}}
    limits = {"default_timeout_minutes": 10, "jobs": {"alpha": {"timeout_minutes": 10}}}
    assert timeout_problems(jobs, limits) == ["job `beta` has no entry in ci_job_limits.toml"]


def test_an_entry_for_a_vanished_job_is_named() -> None:
    jobs = {"alpha": {"timeout-minutes": 10}}
    limits = {
        "default_timeout_minutes": 10,
        "jobs": {"alpha": {"timeout_minutes": 10}, "gone": {"timeout_minutes": 10}},
    }
    problems = timeout_problems(jobs, limits)
    assert problems == ["ci_job_limits.toml has an entry for `gone`, which is not a job in ci.yml"]


def test_a_missing_or_wrong_timeout_is_named() -> None:
    jobs = {"alpha": {}, "beta": {"timeout-minutes": 99}}
    limits = {
        "default_timeout_minutes": 10,
        "jobs": {"alpha": {"timeout_minutes": 15}, "beta": {"timeout_minutes": 20}},
    }
    problems = timeout_problems(jobs, limits)
    assert len(problems) == 2
    assert "`alpha`" in problems[0] and "None" in problems[0]
    assert "`beta`" in problems[1] and "99" in problems[1]


def test_ci_result_and_lint_have_declared_limits() -> None:
    entries = _limits()["jobs"]
    for job_id in ("ci-result", "lint"):
        assert job_id in entries, f"{LIMITS.name} has no entry for `{job_id}`"


def test_every_entry_records_its_evidence() -> None:
    # A limit with no measurement beside it is a guess; the comment is the evidence, and
    # the keys below are the machine-readable half of it.
    for job_id, entry in sorted(_limits()["jobs"].items()):
        assert isinstance(entry["timeout_minutes"], int), job_id
        assert entry["basis"] in {"measured", "unmeasured", "kept"}, job_id


def test_the_workflow_token_is_read_only_unless_a_job_is_a_declared_exception() -> None:
    problems = permission_problems(_workflow(), _limits())
    assert not problems, "\n".join(problems)


def test_a_widened_token_is_named() -> None:
    workflow = {
        "permissions": {"contents": "write"},
        "jobs": {"a": {"permissions": {"checks": "write"}}},
    }
    problems = permission_problems(workflow, {"default_timeout_minutes": 10})
    assert len(problems) == 2
    assert "top-level permissions" in problems[0]
    assert "`a` widens" in problems[1]


def test_an_exception_must_exist_carry_a_block_and_give_a_reason() -> None:
    workflow = {"permissions": READ_ONLY, "jobs": {"a": {}}}
    limits = {"permission_exceptions": {"a": "needs it", "ghost": "", "b": "x"}}
    problems = permission_problems(workflow, limits)
    assert any("`a` has no permissions block" in line for line in problems)
    assert any("`ghost` is not a job" in line for line in problems)
    assert any("`ghost` states no reason" in line for line in problems)


def test_a_checkout_that_sets_persist_credentials_sets_it_false() -> None:
    assert not checkout_problems(_workflow())
    bad = {
        "jobs": {
            "a": {"steps": [{"uses": "actions/checkout@v4", "with": {"persist-credentials": True}}]}
        }
    }
    assert checkout_problems(bad) == ["job `a` checkout sets persist-credentials: True"]
