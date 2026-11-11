# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The FULL matrix rows of the CI jobs that read their matrix from the plan job (SP1-B).

`ci.yml` no longer declares the `tools`, `postgres-compatibility` and `desktop` matrices: each
reads `fromJSON(needs.plan.outputs.<job>_matrix)`, and the rows live in
`.github/ci-matrices.toml`. The meta tests that pin what a matrix covers therefore read the
FULL rows from there, so they stay the permanent guard against a dropped row: a row removed
from the full tier fails them exactly as a row removed from `ci.yml` used to.
"""

from pathlib import Path
from typing import Any

from vibey_gh.ci_areas import CiAreas

REPO = Path(__file__).resolve().parents[2]
AREAS = REPO / ".github" / "ci-areas.toml"
MATRICES = REPO / ".github" / "ci-matrices.toml"


class CiMatrixRows:
    """Reads the full-tier rows of a matrix job from the declared matrix map."""

    @staticmethod
    def full(job: str) -> list[dict[str, Any]]:
        return CiAreas.load(AREAS, MATRICES).rows(job, "full")

    @staticmethod
    def pr(job: str) -> list[dict[str, Any]]:
        return CiAreas.load(AREAS, MATRICES).rows(job, "pr")
