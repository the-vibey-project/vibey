# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every job in the other workflows declares a time limit, behind a ratchet.

`tests/meta/test_ci_job_hygiene.py` covers `ci.yml` in full. This census covers every other
workflow in `.github/workflows/`. A job with no `timeout-minutes` runs under GitHub's 360-minute
default, so one hung job holds a scarce runner slot for six hours. The jobs still without a limit
are counted and held to `ceiling` in `tests/meta/workflow_job_limits.toml`: above it fails, and
below it fails too, naming the number to lower it to, so a fixed job cannot lose its limit
unnoticed (sub-doctrine 12.e).

The ceiling falls to zero in two steps. The hand-written workflows get their limits directly. The
managed ones are rendered from `vibey_gh/templates/workflows/`, so their limits are written in the
template and the rendered copy follows; until then they are counted, not fixed here. A job that is
a reusable-workflow call (`uses:` at job level) takes no `timeout-minutes` and is exempt.

Each limit that is set is listed under `[jobs."<file>.<job>"]` beside the measurement it came
from, and must match the workflow, in both directions: a listed limit the workflow does not carry,
and a listed job that no longer exists, are both named.

Checks are module-level functions: pytest collects functions, and ADR-0016 permits that for a
collection contract.
"""

import tomllib
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github/workflows"
LIMITS = REPO / "tests/meta/workflow_job_limits.toml"
COVERED_ELSEWHERE = {"ci.yml"}


def _limits() -> dict[str, Any]:
    loaded: dict[str, Any] = tomllib.loads(LIMITS.read_text(encoding="utf-8"))
    return loaded


def _jobs(path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    jobs: dict[str, Any] = loaded.get("jobs") or {}
    return jobs


def workflow_paths() -> list[Path]:
    """The workflows this census covers: every one except `ci.yml`."""
    return sorted(p for p in WORKFLOWS.glob("*.yml") if p.name not in COVERED_ELSEWHERE)


def is_exempt(job: dict[str, Any]) -> bool:
    """A reusable-workflow call takes no `timeout-minutes`; the called workflow sets its own."""
    return "uses" in job


def jobs_without_a_limit(path: Path) -> list[str]:
    """Qualified ids (`<file>.<job>`) of the jobs in `path` that have no limit and are not exempt."""
    return [
        f"{path.name}.{job_id}"
        for job_id, job in _jobs(path).items()
        if not is_exempt(job) and "timeout-minutes" not in job
    ]


def all_jobs_without_a_limit() -> list[str]:
    return [job for path in workflow_paths() for job in jobs_without_a_limit(path)]


def listed_limit_problems(paths: list[Path], limits: dict[str, Any]) -> list[str]:
    """What is wrong between the listed limits and the workflows, one line each."""
    problems: list[str] = []
    entries: dict[str, Any] = limits.get("jobs", {})
    existing: dict[str, Any] = {}
    for path in paths:
        for job_id, job in _jobs(path).items():
            existing[f"{path.name}.{job_id}"] = job
    for key in sorted(set(entries) - set(existing)):
        problems.append(f"{LIMITS.name} lists `{key}`, which is not a job in a covered workflow")
    for key, entry in sorted(entries.items()):
        job = existing.get(key)
        if job is None:
            continue
        if is_exempt(job):
            problems.append(
                f"{LIMITS.name} lists `{key}`, a reusable-workflow call, which is exempt"
            )
        elif job.get("timeout-minutes") != entry.get("timeout_minutes"):
            problems.append(
                f"`{key}` has timeout-minutes {job.get('timeout-minutes')!r}, "
                f"{LIMITS.name} says {entry.get('timeout_minutes')!r}"
            )
        if entry.get("basis") not in ("measured", "unmeasured", "kept"):
            problems.append(f"`{key}` has basis {entry.get('basis')!r} in {LIMITS.name}")
    return problems


def test_every_job_without_a_limit_is_counted_against_the_ceiling() -> None:
    unlimited = all_jobs_without_a_limit()
    ceiling = int(_limits()["ceiling"])
    assert len(unlimited) <= ceiling, (
        f"{len(unlimited)} jobs have no timeout-minutes, above the ceiling of {ceiling}; "
        "give the new job a limit:\n" + "\n".join(unlimited)
    )


def test_the_ceiling_is_exactly_the_count() -> None:
    count = len(all_jobs_without_a_limit())
    ceiling = int(_limits()["ceiling"])
    assert count >= ceiling, f"{count} jobs have no timeout-minutes; lower the ceiling to {count}"


def test_a_listed_limit_must_match_the_workflow() -> None:
    problems = listed_limit_problems(workflow_paths(), _limits())
    assert not problems, "\n".join(problems)


def test_a_reusable_workflow_call_job_is_exempt(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(
        "jobs:\n"
        "  call:\n"
        "    uses: ./.github/workflows/other.yml\n"
        "  bare:\n"
        "    runs-on: ubuntu-latest\n"
        "  limited:\n"
        "    runs-on: ubuntu-latest\n"
        "    timeout-minutes: 10\n",
        encoding="utf-8",
    )
    assert jobs_without_a_limit(workflow) == ["w.yml.bare"]


def test_a_listed_limit_that_disagrees_with_the_workflow_is_named(tmp_path: Path) -> None:
    workflow = tmp_path / "w.yml"
    workflow.write_text(
        "jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 10\n  call:\n    uses: ./x.yml\n",
        encoding="utf-8",
    )
    limits = {
        "jobs": {
            "w.yml.a": {"timeout_minutes": 15, "basis": "measured"},
            "w.yml.gone": {"timeout_minutes": 10, "basis": "measured"},
            "w.yml.call": {"timeout_minutes": 10, "basis": "measured"},
        }
    }
    problems = listed_limit_problems([workflow], limits)
    assert len(problems) == 3
    assert any("`w.yml.a` has timeout-minutes 10" in p for p in problems)
    assert any("`w.yml.gone`" in p for p in problems)
    assert any("`w.yml.call`" in p for p in problems)
