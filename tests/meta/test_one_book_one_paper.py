# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The release surfaces workflow publishes one book and one paper from root sources (ADR-0032, #155).

The repository tracks one published paper (`docs/paper.md`) and one publishing book
definition (`properdocs.yml`). Tenant copies (`src/**/docs/paper.md` and `src/**/properdocs.yml`)
still exist as legacy debt tracked in `tests/meta/single_source.toml` and are deliberately
not touched here (#155 open question 1), but the publishing workflow
(`.github/workflows/release-surfaces.yml`) must never build or render from any of them.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_protected_paths_agree.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"


def test_exactly_one_root_workflow_builds_the_book_and_the_paper() -> None:
    book_workflows = [
        path.name
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if re.search(r"\bvibey-gh\s+book\b", path.read_text(encoding="utf-8"))
    ]
    paper_workflows = [
        path.name
        for path in sorted(WORKFLOWS.glob("*.yml"))
        if re.search(r"\bvibey-gh\s+paper\b", path.read_text(encoding="utf-8"))
    ]
    assert book_workflows == ["release-surfaces.yml"]
    assert paper_workflows == ["release-surfaces.yml"]


def test_the_book_is_built_from_the_root_definition() -> None:
    text = (WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8")
    assert "config=properdocs.yml" in text
    assert re.search(r"src/[^\s\"']*properdocs\.yml", text) is None


def test_the_paper_is_rendered_from_docs_paper_md() -> None:
    text = (WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8")
    assert "[ -f docs/paper.md ]" in text
    assert re.search(r"src/[^\s\"']*docs/paper\.md", text) is None
    assert "PAPER_SOURCE=docs/paper.md" in text
    for line in text.splitlines():
        if re.search(r"\bvibey-gh\s+paper\b", line):
            assert "src/" not in line


def test_no_publishing_step_runs_inside_a_tenant() -> None:
    workflow = yaml.safe_load((WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8"))
    for job_name, job in workflow.get("jobs", {}).items():
        if not isinstance(job, dict):
            continue
        job_wd = job.get("defaults", {}).get("run", {}).get("working-directory", "")
        assert not str(job_wd).startswith("src/"), f"Job {job_name} has working-directory {job_wd}"
        for step in job.get("steps", []):
            if isinstance(step, dict):
                step_wd = step.get("working-directory", "")
                assert not str(step_wd).startswith("src/"), (
                    f"Step in {job_name} has working-directory {step_wd}"
                )
