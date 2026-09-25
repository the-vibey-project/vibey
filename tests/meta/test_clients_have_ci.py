# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every client and package the npm workspace or the uv workspace holds is run by CI (ADR-0067)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"
MANIFESTS = ("package.json", "pyproject.toml", "meson.build")


def candidate_directories() -> list[str]:
    """Each directory under clients/ and packages/ that carries its own manifest: npm, Python,
    or Meson (the C desktop app)."""
    found: list[str] = []
    for parent in ("clients", "packages"):
        base = ROOT / parent
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if (
                child.is_dir()
                and not child.name.startswith(".")
                and any((child / name).is_file() for name in MANIFESTS)
            ):
                found.append(child.relative_to(ROOT).as_posix())
    return sorted(found)


def uncovered(jobs: dict[str, Any], directories: list[str]) -> list[str]:
    """The directories no job names anywhere: working directory, run commands or paths."""
    rendered = [yaml.safe_dump(job) for job in jobs.values()]
    return [
        directory for directory in directories if not any(directory in text for text in rendered)
    ]


def _jobs() -> dict[str, Any]:
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    jobs: dict[str, Any] = workflow["jobs"]
    return jobs


def test_there_is_something_to_check() -> None:
    assert "clients/vscode" in candidate_directories()
    assert "clients/desktop" in candidate_directories()
    assert "packages/vibey-core" in candidate_directories()


def test_every_client_and_package_has_a_ci_job() -> None:
    missing = uncovered(_jobs(), candidate_directories())
    assert not missing, f"no CI job runs these: {', '.join(missing)}"


def test_the_checker_notices_a_missing_job() -> None:
    assert uncovered({"x": {"steps": [{"run": "echo hi"}]}}, ["clients/nothing"]) == [
        "clients/nothing"
    ]
