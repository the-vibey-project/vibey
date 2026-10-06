# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The daily self-healer and backlog killer keep the shape that makes them safe unattended.

`scripts/continuation_prompts.py check` already holds that both run daily, by hand, and on
GitHub-hosted CPU runners only. These pin the rest (ADR-0083): the job that runs repairs over the
repository's manifests holds no way to write; nothing a repair or an agent wrote runs where a
token can push; and no person's words reach a shell by interpolation.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def spec(name: str) -> dict[str, Any]:
    data = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def step(job: dict[str, Any], prefix: str) -> dict[str, Any]:
    return next(s for s in job["steps"] if str(s.get("name", "")).startswith(prefix))


def test_the_self_healers_repairs_run_where_nothing_can_write() -> None:
    diagnose = spec("self-healer.yml")["jobs"]["diagnose"]
    assert diagnose["permissions"] == {"contents": "read", "actions": "read"}
    assert "secrets." not in yaml.safe_dump(diagnose)
    checkout = step(diagnose, "Check out")
    assert checkout["with"]["persist-credentials"] is False


def test_the_self_healer_guards_the_patch_before_applying_it() -> None:
    act = spec("self-healer.yml")["jobs"]["act"]
    run = step(act, "Open one pull request")["run"]
    guard = run.index("self_healer.py guard")
    setting = run.index("self_healer.py setting")
    apply = run.index("git apply --index")
    assert guard < apply and setting < apply  # nothing the patch wrote runs here
    assert "--draft" not in run  # scripted, deterministic: its own checks decide
    # Re-runs and the hand-over to keep-green run before any patch exists in this checkout.
    names = [s.get("name", "") for s in act["steps"]]
    assert names.index("Re-run each allowlisted flake once") < names.index(
        "Open one pull request with the scripted repairs"
    )
    assert names.index("Hand what is still red to the keep-green prompt") < names.index(
        "Open one pull request with the scripted repairs"
    )


def test_the_backlog_killer_picks_read_only_and_only_dispatches() -> None:
    jobs = spec("backlog-killer.yml")["jobs"]
    assert all(level == "read" for level in jobs["pick"]["permissions"].values())
    assert jobs["work"]["permissions"] == {"contents": "read", "actions": "write"}
    assert "secrets." not in yaml.safe_dump(jobs)
    dispatch = step(jobs["work"], "Dispatch")["run"]
    assert "${{" not in dispatch  # the pick reaches the shell through env:, never interpolated
    assert "gh workflow run continuation-prompts.yml" in dispatch


def test_the_continuation_lane_takes_a_prompt_list_without_interpolating_it() -> None:
    lane = spec("continuation-prompts.yml")
    dispatch = lane[True]["workflow_dispatch"]  # PyYAML reads the bare key `on` as True
    assert dispatch["inputs"]["prompts"]["default"] == ""
    matrix = step(lane["jobs"]["refresh"], "The prompts, for the run")
    assert matrix["env"]["PROMPTS"] == "${{ inputs.prompts }}"
    assert "inputs." not in matrix["run"]
    # A narrowed run leaves the weekly chores to the weekly run.
    assert lane["jobs"]["keepalive"]["if"] == "${{ !inputs.prompts }}"


def test_the_lane_quotes_the_agents_report_before_applying_its_patch() -> None:
    report = spec("continuation-prompts.yml")["jobs"]["report"]
    run = step(report, "Act")["run"]
    assert run.index("continuation_prompts.py defuse") < run.index("git apply --index")
    assert "--body-file" in run


def test_every_agent_run_records_its_exit_code_under_bash_e() -> None:
    """The runner's shell is `bash -e`: `cmd; code=$?` never reaches the assignment when
    `cmd` fails, so the step dies with its code unrecorded (2026-10-05)."""
    for name in ("continuation-prompts.yml", "chat.yml", "pr-review.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            if "gptossloop run" in line and "timeout" in line:
                block = text[text.index(line) :].split("\n", 3)
                agent = "\n".join(block[:2])
                assert "|| code=$?" in agent, (name, agent)
