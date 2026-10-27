# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every step `[branch_health.reproduce]` names still exists in ci.yml (#1690).

The red-branch issue looks its reproduction command up by `check :: step`. A step renamed in
`ci.yml` would make the lookup fall back to "no command declared" with nothing saying the map
had drifted, so the drift is a red build here instead (12.e: the check that says out loud
when a step was missed).

Module-level test functions rather than a class: pytest collects `test_*` functions, and the
class-and-interface rule is about production code (ADR-0016).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
CONFIG = tomllib.loads((REPO / ".vibey-gh.toml").read_text(encoding="utf-8"))
CI = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))


def _jobs_by_name() -> dict[str, list[str]]:
    return {
        str(job.get("name", key)): [str(step.get("name", "")) for step in job.get("steps", [])]
        for key, job in CI["jobs"].items()
    }


def test_every_declared_step_exists_in_its_ci_job() -> None:
    jobs = _jobs_by_name()
    missing = []
    for key in CONFIG["branch_health"]["reproduce"]:
        check, _, step = key.partition(" :: ")
        if check not in jobs:
            missing.append(f"{key}: no CI job is named {check!r}")
        elif step and step not in jobs[check]:
            missing.append(f"{key}: job {check!r} has no step {step!r}")
    assert not missing, "\n".join(missing)


def test_every_declared_check_is_a_watched_required_check() -> None:
    watched = set(CONFIG["rulesets"]["integration"]["required_checks"])
    declared = {key.partition(" :: ")[0] for key in CONFIG["branch_health"]["reproduce"]}
    assert declared <= watched, sorted(declared - watched)
