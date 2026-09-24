# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

import yaml


def test_delivery_estimate_publish_is_limited_to_trusted_events() -> None:
    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load(
        (root / ".github/workflows/delivery-estimate.yml").read_text(encoding="utf-8")
    )
    publish = workflow["jobs"]["publish"]
    condition = publish["if"]
    assert "github.event_name == 'schedule'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "github.event_name == 'push'" not in condition
    assert "github.event_name == 'issues'" not in condition
    assert "github.event_name == 'pull_request'" not in condition


def _workflow(root: Path) -> dict:
    loaded = yaml.safe_load(
        (root / ".github/workflows/delivery-estimate.yml").read_text(encoding="utf-8")
    )
    return loaded


def test_the_estimate_refreshes_once_an_hour_and_by_hand_only() -> None:
    """The operator's rule (2026-09-24): hourly, never per push, pull request or issue."""
    root = Path(__file__).resolve().parents[4]
    workflow = _workflow(root)
    # YAML 1.1 reads the bare key `on` as True.
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    (cron,) = [entry["cron"] for entry in triggers["schedule"]]
    minute, hour, *_ = cron.split()
    assert minute.isdigit() and hour == "*", f"not once an hour: {cron!r}"


def test_the_estimate_pull_request_runs_every_ci_gate() -> None:
    """No `[skip ci]`: the refresh's pull request is checked like any change to develop.

    With it, #1125 merged a ledger record that broke develop's paper-figure check, because
    no check ran on the pull request at all.
    """
    root = Path(__file__).resolve().parents[4]
    publish = _workflow(root)["jobs"]["publish"]
    script = "\n".join(step.get("run", "") for step in publish["steps"])
    commit = [line for line in script.splitlines() if "git commit" in line]
    assert commit, "the publish step no longer commits"
    assert not any("skip ci" in line.lower() for line in commit)
    assert "[skip ci]" not in script and "[ci skip]" not in script


def test_delivery_estimate_publishes_through_a_pull_request() -> None:
    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load(
        (root / ".github/workflows/delivery-estimate.yml").read_text(encoding="utf-8")
    )
    publish = workflow["jobs"]["publish"]
    assert publish["permissions"]["pull-requests"] == "write"
    script = "\n".join(step.get("run", "") for step in publish["steps"])
    assert "git push origin HEAD:develop" not in script
    assert "--base develop" in script
    assert "gh pr create" in script
