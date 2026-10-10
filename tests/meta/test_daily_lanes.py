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

import re
import tomllib
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


def _field_values(field: str, low: int, high: int) -> set[int]:
    """The values a cron field (`*`, `v`, `a-b`, `*/s`, `a-b/s`, or a comma list) selects."""
    values: set[int] = set()
    for part in field.split(","):
        span, _, step = part.partition("/")
        lo, _, hi = span.partition("-")
        first, last = (low, high) if span == "*" else (int(lo), int(hi or lo))
        values.update(range(first, last + 1, int(step or 1)))
    return values


def _cron_minutes(cron: str) -> set[int]:
    """The minutes of the day a cron (`M H * * *`) fires at; `M` and `H` may each be a value,
    a range, a step or a list, so `3,23,43 * * * *` and `23 0-21/3 * * *` both parse."""
    minute, hour, *rest = cron.split()
    assert rest == ["*", "*", "*"], f"{cron!r} is not a daily schedule"
    minutes = _field_values(minute, 0, 59)
    return {h * 60 + m for h in _field_values(hour, 0, 23) for m in minutes}


def test_the_backlog_killer_fires_once_per_declared_slot() -> None:
    """Cron cannot say "every 90 minutes", so a schedule can drift from the interval the pick
    rotates by; this holds the crons to `[backlog_killer] interval_minutes` (12.e). With the
    chain on the crons are the watchdog instead, and are held to `watchdog_minutes`."""
    settings = tomllib.loads((WORKFLOWS.parents[1] / "scripts" / "daily_lanes.toml").read_text())
    killer = settings["backlog_killer"]
    interval = int(killer["watchdog_minutes" if killer.get("chain") else "interval_minutes"])
    text = (WORKFLOWS / "backlog-killer.yml").read_text(encoding="utf-8")
    crons = re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', text, re.MULTILINE)
    fires = sorted(set().union(*(_cron_minutes(c) for c in crons)))
    gaps = {b - a for a, b in zip(fires, fires[1:] + [fires[0] + 24 * 60], strict=True)}
    assert gaps == {interval}, (
        f"backlog-killer.yml fires at gaps {sorted(gaps)}, not every {interval}"
    )


def test_the_backlog_killer_chain_is_bounded_and_can_start_nothing_else() -> None:
    """The chain re-dispatches its own workflow, so every bound on it is pinned here (12.d)."""
    settings = tomllib.loads((WORKFLOWS.parents[1] / "scripts" / "daily_lanes.toml").read_text())
    killer = settings["backlog_killer"]
    assert killer["chain"] is True and 0 < killer["chain_max_links"] <= 144
    assert killer["watchdog_minutes"] > killer["interval_minutes"]
    lane = spec("backlog-killer.yml")
    # One run at a time, and a waiting run is replaced rather than queued behind: links cannot pile up.
    assert lane["concurrency"]["cancel-in-progress"] is False
    chain = lane["jobs"]["chain"]
    assert chain["needs"] == ["pick", "work"]
    assert chain["permissions"] == {"contents": "read", "actions": "write"}
    assert chain["timeout-minutes"] > killer["interval_minutes"]  # long enough to wait one slot
    # The switch and the maximum gate both the wait and the dispatch.
    assert step(chain, "Wait for the next slot")["if"] == "steps.plan.outputs.proceed == 'true'"
    dispatch = step(chain, "Dispatch the next link")
    assert dispatch["if"] == "steps.plan.outputs.proceed == 'true'"
    assert re.findall(r"gh workflow run (\S+)", dispatch["run"]) == ["backlog-killer.yml"]  # itself
    assert lane["jobs"]["pick"]["permissions"]["actions"] == "read"  # the pick only counts runs


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
    assert "--fenced" in run  # model output cannot close its own quote
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


def test_the_documentation_updaters_generators_run_where_nothing_can_write() -> None:
    render = spec("docs-updater.yml")["jobs"]["render"]
    assert render["permissions"] == {"contents": "read"}
    assert "secrets." not in yaml.safe_dump(render)
    checkout = step(render, "Check out")
    assert checkout["with"]["persist-credentials"] is False
    assert checkout["with"]["fetch-depth"] == 0  # the paper's figures read the whole history
    assert "--lane docs_updater" in step(render, "Run every declared generator")["run"]


def test_the_documentation_updater_guards_its_own_table_before_applying() -> None:
    act = spec("docs-updater.yml")["jobs"]["act"]
    run = step(act, "Open one pull request")["run"]
    assert 'self_healer.py guard "$patch" --lane docs_updater' in run
    assert run.index("self_healer.py guard") < run.index("git apply --index")
    assert run.index("self_healer.py setting") < run.index("git apply --index")
    names = [s.get("name", "") for s in act["steps"]]
    last = names.index("Open one pull request with the regenerated pages")
    assert names.index("Rebuild the published develop book if it is behind its release") < last
    assert names.index("Hand the written pages to the docs prompt") < last


def test_the_book_is_only_ever_rebuilt_from_a_release_that_already_succeeded() -> None:
    book = step(spec("docs-updater.yml")["jobs"]["act"], "Rebuild the published develop book")
    run = book["run"]
    assert "docs_updater.py book" in run
    assert (
        'gh workflow run release-surfaces.yml --ref develop -f branch=develop -f run_id="$run_id"'
        in run
    )
    assert "${{" not in run  # the run id reaches the shell from the script, never interpolated
    assert "vibey-engine.yml" not in run  # it never cuts or re-runs a release


def test_the_backlog_killer_has_a_real_pause_and_it_says_why_it_is_used() -> None:
    """`chain = false` does not pause (the watchdog cron still runs a link), so the lane has a
    master switch; whichever way it is set, it is a declared boolean with its reason beside it."""
    text = (WORKFLOWS.parents[1] / "scripts" / "daily_lanes.toml").read_text()
    settings = tomllib.loads(text)["backlog_killer"]
    assert isinstance(settings.get("enabled", True), bool)
    if settings.get("enabled", True) is False:
        # A paused lane records why and what ends the pause, or nobody remembers to end it.
        block = text[text.index("[backlog_killer]") : text.index("interval_minutes")]
        assert "Paused" in block and "Switch it back on" in block
