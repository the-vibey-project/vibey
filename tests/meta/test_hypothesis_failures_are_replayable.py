# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A failing Hypothesis example can be replayed from the log and from the run's artifacts.

CI shows a shrunk counterexample once, in a log that scrolls away. With `print_blob=True`
the failure also prints a `@reproduce_failure` blob, and the `gates` and `noloss` jobs
upload `.hypothesis/` (its example database) when they fail, so the example is
reproducible locally instead of being lost to a flaky-looking rerun.

Checks are module-level functions: pytest collects functions, and ADR-0016 permits that
for a collection contract.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import settings

import tests.conftest  # noqa: F401  (registers the profiles)

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
PROFILES = ("vibey", "noloss")
JOBS = ("gates", "noloss")


def _upload_steps(job: str) -> list[dict[str, Any]]:
    workflow: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = workflow["jobs"][job]["steps"]
    return [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")]


@pytest.mark.parametrize("name", PROFILES)
def test_profile_prints_the_reproduction_blob(name: str) -> None:
    assert settings.get_profile(name).print_blob is True


@pytest.mark.parametrize("job", JOBS)
def test_job_uploads_the_example_database_on_failure(job: str) -> None:
    steps = [s for s in _upload_steps(job) if s.get("with", {}).get("path") == ".hypothesis"]
    assert len(steps) == 1, f"`{job}` needs one upload-artifact step for .hypothesis"
    step = steps[0]
    assert step["if"] == "failure()"
    assert step["with"]["name"] == f"hypothesis-examples-{job}"
    assert step["with"]["retention-days"] == 7
    assert step["with"]["if-no-files-found"] == "ignore"


def test_upload_pin_matches_the_other_uploads() -> None:
    workflow: dict[str, Any] = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    pins = {
        s["uses"]
        for job in workflow["jobs"].values()
        for s in job.get("steps", [])
        if str(s.get("uses", "")).startswith("actions/upload-artifact@")
    }
    assert len(pins) == 1, f"upload-artifact is pinned inconsistently: {sorted(pins)}"
