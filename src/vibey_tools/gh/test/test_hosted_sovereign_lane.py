# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign lane on a GitHub-hosted runner (`[pr_automation.fallback] runs_on`).

The operator's decision, 2026-10-03: every CI job runs on GitHub-hosted runners. Declared,
the review job renders that runner, starts its own model there, and is always ready --
a hosted runner cannot be offline, which is the one thing the heartbeat exists to say.
Undeclared, everything renders exactly as the self-hosted lane always has.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from vibey_gh import cli
from vibey_gh.config import (
    GhConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
    load_config,
)
from vibey_gh.install import WORKFLOWS, render_workflow


def _cfg(tmp_path: Path, **fallback: Any) -> GhConfig:
    return GhConfig(
        root=tmp_path,
        owner="owner",
        pr_automation=PrAutomationConfig(fallback=PrAutomationFallbackConfig(**fallback)),
    )


def _local(job: dict[str, Any]) -> bool:
    return any(step.get("name") == "Start the model on this runner" for step in job["steps"])


def test_the_lane_stays_self_hosted_unless_a_hosted_runner_is_declared(tmp_path):
    assert PrAutomationFallbackConfig().runs_on == ""
    text = render_workflow(WORKFLOWS / "pr-review.yml", _cfg(tmp_path, runner_label="box"))
    job = yaml.safe_load(text)["jobs"]["review-sovereign"]
    assert job["runs-on"] == ["self-hosted", "box"]
    start = next(s for s in job["steps"] if s.get("name") == "Start the model on this runner")
    assert start["if"] is False


@pytest.mark.parametrize("workflow", ["pr-review.yml", "issue-automation.yml"])
def test_declared_the_lane_runs_hosted_and_starts_its_own_model(tmp_path, workflow):
    text = render_workflow(
        WORKFLOWS / workflow, _cfg(tmp_path, runs_on="ubuntu-24.04-arm", model="qwen3:4b")
    )
    assert "__VIBEY_GH_FALLBACK_" not in text
    jobs = yaml.safe_load(text)["jobs"]
    hosted = [job for job in jobs.values() if _local(job)]
    assert len(hosted) == 1
    job = hosted[0]
    assert job["runs-on"] == "ubuntu-24.04-arm"
    start = next(s for s in job["steps"] if s.get("name") == "Start the model on this runner")
    assert start["if"] is True
    assert start["env"] == {"MODEL": "qwen3:4b"}
    assert 'ollama pull "$MODEL"' in start["run"]


def test_the_declaration_is_read_from_the_table(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        'owner = "owner"\n[pr_automation.fallback]\nruns_on = "ubuntu-24.04-arm"\n',
        encoding="utf-8",
    )
    assert load_config(tmp_path).pr_automation.fallback.runs_on == "ubuntu-24.04-arm"


@pytest.mark.parametrize("runs_on", ["ubuntu latest", "[self-hosted, x]", 7])
def test_anything_but_one_runner_label_is_refused(runs_on):
    """The value is rendered straight into `runs-on:`; only a plain label may reach it."""
    with pytest.raises(ValueError, match="runs_on must be empty"):
        PrAutomationFallbackConfig(runs_on=runs_on)  # type: ignore[arg-type]


def test_a_hosted_lane_is_ready_without_a_heartbeat(monkeypatch, capsys, tmp_path):
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        cli, "load_config", lambda *a, **k: _cfg(tmp_path, runs_on="ubuntu-24.04-arm")
    )
    monkeypatch.setattr(cli, "_sabbath_guard", lambda cfg: _NoHold())
    assert cli.main(["sovereign"]) == 0
    assert "ready=true" in output.read_text(encoding="utf-8")
    assert "GitHub-hosted runner (ubuntu-24.04-arm)" in capsys.readouterr().out


class _NoHold:
    """A Sabbath guard outside its window: nothing is held."""

    def hold(self) -> None:
        return None
