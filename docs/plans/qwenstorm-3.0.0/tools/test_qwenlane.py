"""Tests for qwenlane's wiring into qwenloop: what a lane's run is actually handed.

`testpaths = ["tests"]` in the root pyproject, so this is not collected by the repository
suite. Run it directly:

    python3 -m pytest docs/plans/qwenstorm-3.0.0/tools/test_qwenlane.py -q
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from qwenloop.domain.config import ToolLimits
from qwenloop.domain.model import RunState, RunStatus

SPEC = importlib.util.spec_from_file_location("qwenlane", Path(__file__).with_name("qwenlane.py"))
assert SPEC and SPEC.loader
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
