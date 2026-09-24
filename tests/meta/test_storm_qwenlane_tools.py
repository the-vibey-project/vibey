# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for qwenlane's wiring into qwenloop: what a storm lane's run is actually handed.

A `[tools]` table in `qwen-storm.toml` bounds what one tool call may read or return. If the
lane driver loads that config and then does not pass it to `_run_plan`, every lane runs with
the defaults while the file says otherwise -- a setting that reads as honoured and is not.

This lives under tests/ rather than beside the tool for the reason
`test_storm_check_parser.py` gives: `testpaths = ["tests"]`, so a test beside the tool is
never collected and cannot fail anyone. `qwenlane.py` is addressed by path because it is a
script, not an importable module. If the storm's tools are removed this fails loudly --
delete it in the same commit that deletes them.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from qwenloop.domain.config import ToolLimits
from qwenloop.domain.model import RunState, RunStatus

TOOL = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools/qwenlane.py"
SPEC = importlib.util.spec_from_file_location("qwenlane", TOOL)
assert SPEC and SPEC.loader, f"the storm's lane driver is missing: {TOOL}"
qwenlane = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qwenlane)


def test_the_storm_config_tools_table_reaches_every_lane_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A `[tools]` table in qwen-storm.toml must bound the lane's tools, not be read and
    # then dropped at the `_run_plan` call.
    config = tmp_path / "qwen-storm.toml"
    config.write_text('[tools]\nmax_search_matches = 7\nskip_dirs = ["vendor"]\n')
    monkeypatch.setenv("QWENLOOP_CONFIG", str(config))
    lane = tmp_path / "lane"
    lane.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=lane, check=True)
    body = tmp_path / "issue.md"
    body.write_text("do the item\n")
    calls: list[dict[str, object]] = []

    async def run_plan(*args: object, **kwargs: object) -> RunState:
        calls.append(kwargs)
        return RunState("run", status=RunStatus.FAILED, turns=1)

    monkeypatch.setattr(qwenlane, "_run_plan", run_plan)
    monkeypatch.setattr(qwenlane, "_server_for", lambda _config: (object(), object()))
    monkeypatch.setattr(qwenlane, "_tracked_repository_context", lambda _lane: "")
    monkeypatch.setattr(
        sys, "argv", ["qwenlane.py", str(lane), "1", "a title", str(body), "--max-attempts", "2"]
    )
    qwenlane.main()
    assert len(calls) == 2
    for kwargs in calls:
        assert kwargs["tool_limits"] == ToolLimits(max_search_matches=7, skip_dirs=("vendor",))
