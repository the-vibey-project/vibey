# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hourly backlog lane can consume the debt it observes."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def test_read_only_survey_cannot_block_the_write_authorized_apply() -> None:
    # A pytest function is the collection contract, so ADR-0016 permits it here.
    workflow = yaml.safe_load(
        (REPO / ".github/workflows/backlog-cleanup.yml").read_text(encoding="utf-8")
    )
    cleanup_steps = workflow["jobs"]["cleanup"]["steps"]
    publish_steps = workflow["jobs"]["publish"]["steps"]
    survey = next(
        step["run"] for step in cleanup_steps if step.get("name") == "Run the backlog loop"
    )
    apply = next(
        step["run"]
        for step in publish_steps
        if step.get("name") == "Run the backlog loop with write permission"
    )
    assert "backlog_cleanup.py --survey" in survey
    assert "backlog_cleanup.py --check" not in survey
    assert "backlog_cleanup.py --apply" not in survey
    assert "backlog_cleanup.py --apply" in apply
