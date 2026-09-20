# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keep the finite CI PostgreSQL matrix aligned with runtime support policy."""

from pathlib import Path

import yaml

from vibey.infrastructure.postgres import POSTGRES_SUPPORTED_MAJORS

_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def test_ci_exercises_every_currently_supported_postgres_major() -> None:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["postgres-compatibility"]

    assert tuple(job["strategy"]["matrix"]["postgres"]) == POSTGRES_SUPPORTED_MAJORS
    assert job["services"]["postgres"]["image"] == "postgres:${{ matrix.postgres }}"
