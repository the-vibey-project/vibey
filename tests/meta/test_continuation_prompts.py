# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The continuation prompts hold on this repository, on every pull request (sub-doctrine 10.l).

`scripts/continuation_prompts.py check` is what says out loud that a prompt names something
gone, that a new lane or skill has no prompt, or that a page's generated state is stale. CI
runs it here, so none of those can land. The rest pins the lane that runs the prompts: it
exists, it is scheduled weekly, it can be run by hand, and it runs on GitHub-hosted runners.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
LANE = REPO / ".github" / "workflows" / "continuation-prompts.yml"


def test_every_continuation_prompt_holds_on_this_repository() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/continuation_prompts.py", "check"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


def test_the_lane_runs_weekly_by_hand_and_on_github_hosted_runners() -> None:
    spec = yaml.safe_load(LANE.read_text(encoding="utf-8"))
    triggers = spec[True]  # PyYAML reads the bare key `on` as the boolean True
    crons = [entry["cron"] for entry in triggers["schedule"]]
    assert len(crons) == 1 and crons[0].split()[2:] == ["*", "*", "1"], crons
    assert "workflow_dispatch" in triggers
    for name, job in spec["jobs"].items():
        assert "self-hosted" not in str(job["runs-on"]), name


def test_the_agent_job_holds_no_write_permission_and_no_secret() -> None:
    """The agent reads untrusted text with root on its VM: it may not hold a way to write."""
    spec = yaml.safe_load(LANE.read_text(encoding="utf-8"))
    run = spec["jobs"]["run"]
    assert all(level != "write" for level in run["permissions"].values()), run["permissions"]
    assert "secrets." not in yaml.safe_dump(run)


def test_only_the_fresh_report_job_writes_and_it_refuses_protected_paths() -> None:
    text = LANE.read_text(encoding="utf-8")
    spec = yaml.safe_load(text)
    writers = {
        name
        for name, job in spec["jobs"].items()
        if any(level == "write" for level in (job.get("permissions") or {}).values())
    }
    assert writers == {"keepalive", "report"}, writers
    act = next(s for s in spec["jobs"]["report"]["steps"] if s["name"].startswith("Act"))
    for guarded in (r"\.github/", "doctrines", "constitution", r"\.vibey-gh\.toml"):
        assert guarded in act["run"], guarded
    assert "--draft" in act["run"]
