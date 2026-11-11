# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keep the finite CI PostgreSQL matrix aligned with runtime support policy."""

from pathlib import Path

import yaml

from vibey.infrastructure.postgres import POSTGRES_SUPPORTED_MAJORS

from .ci_matrix_rows import CiMatrixRows

_WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def test_ci_exercises_every_currently_supported_postgres_major() -> None:
    workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    job = workflow["jobs"]["postgres-compatibility"]

    # The matrix is the plan job's `postgres_matrix`; the rows it can run are the FULL rows of
    # .github/ci-matrices.toml, so that is what must cover every supported major.
    assert job["strategy"]["matrix"].startswith(
        "${{ fromJSON(needs.plan.outputs.postgres_matrix || '"
    )
    full = tuple(row["postgres"] for row in CiMatrixRows.full("postgres-compatibility"))
    assert full == POSTGRES_SUPPORTED_MAJORS
    assert job["services"]["postgres"]["image"] == "postgres:${{ matrix.postgres }}"
