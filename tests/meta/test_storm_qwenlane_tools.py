# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for qwenlane's wiring into qwenloop: what a storm lane's run is actually handed.

A `[tools]` table in `qwen-storm.toml` bounds what one tool call may read or return. If the
lane driver loads that config and then does not pass it to `_run_plan`, every lane runs with
the defaults while the file says otherwise -- a setting that reads as honoured and is not.

Each attempt runs in a child process of its own (`qwenlane.py --attempt`, see
lane_watchdog.py), so the call that must carry the table is the child's: `run_attempt`.
The test drives that half directly, handing it a spec, the spec's digest and a report pipe
exactly as the parent does, and stubs only the model call.

This lives under tests/ rather than beside the tool for the reason
`test_storm_check_parser.py` gives: `testpaths = ["tests"]`, so a test beside the tool is
never collected and cannot fail anyone. `qwenlane.py` is addressed by path because it is a
script, not an importable module. If the storm's tools are removed this fails loudly --
delete it in the same commit that deletes them.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from qwenloop.domain.config import ToolLimits
from qwenloop.domain.model import RunState, RunStatus

TOOL = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools/qwenlane.py"
# qwenlane imports its sibling tools (storm_paths, lane_watchdog) by name, as it does when run
# from its own directory.
if str(TOOL.parent) not in sys.path:
    sys.path.insert(0, str(TOOL.parent))
SPEC = importlib.util.spec_from_file_location("qwenlane", TOOL)
assert SPEC and SPEC.loader, f"the storm's lane driver is missing: {TOOL}"
qwenlane = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qwenlane)


def test_the_storm_config_tools_table_reaches_every_lane_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A `[tools]` table in qwen-storm.toml must bound the lane's tools, not be read and
    # then dropped at the child's `_run_plan` call.
    config = tmp_path / "qwen-storm.toml"
    config.write_text('[tools]\nmax_search_matches = 7\nskip_dirs = ["vendor"]\n')
    monkeypatch.setenv("QWENLOOP_CONFIG", str(config))
    lane = tmp_path / "lane"
    (lane / ".qwenstorm").mkdir(parents=True)
    calls: list[dict[str, object]] = []

    async def run_plan(*args: object, **kwargs: object) -> RunState:
        calls.append(kwargs)
        return RunState("run", status=RunStatus.FAILED, turns=1)

    monkeypatch.setattr(qwenlane, "_run_plan", run_plan)
    monkeypatch.setattr(qwenlane, "_server_for", lambda _config: (object(), object()))
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "lane": str(lane),
                "run_id": "run-1",
                "plan": "the plan",
                "events": str(lane / ".qwenloop/runs/run-1/events.jsonl"),
                "poll_seconds": 60,
            }
        )
    )
    monkeypatch.setenv(qwenlane.SPEC_SHA256_ENV, hashlib.sha256(spec.read_bytes()).hexdigest())
    read_end, write_end = os.pipe()
    monkeypatch.setenv(qwenlane.REPORT_FD_ENV, str(write_end))
    try:
        assert qwenlane.run_attempt(spec) == 0
    finally:
        os.close(write_end)
        os.close(read_end)
    assert len(calls) == 1
    assert calls[0]["tool_limits"] == ToolLimits(max_search_matches=7, skip_dirs=("vendor",))


def test_the_storm_config_recording_bounds_reach_every_lane_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The empty-reply retry bound and the two recording caps are declared in the storm's
    # config; the child's `_run_plan` call must carry them, not fall back to the defaults.
    config = tmp_path / "qwen-storm.toml"
    config.write_text(
        "max_empty_reply_retries = 4\n"
        "max_recorded_argument_chars = 64\n"
        "empty_reply_reasoning_excerpt_chars = 32\n"
    )
    monkeypatch.setenv("QWENLOOP_CONFIG", str(config))
    lane = tmp_path / "lane"
    (lane / ".qwenstorm").mkdir(parents=True)
    calls: list[dict[str, object]] = []

    async def run_plan(*args: object, **kwargs: object) -> RunState:
        calls.append(kwargs)
        return RunState("run", status=RunStatus.FAILED, turns=1)

    monkeypatch.setattr(qwenlane, "_run_plan", run_plan)
    monkeypatch.setattr(qwenlane, "_server_for", lambda _config: (object(), object()))
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "lane": str(lane),
                "run_id": "run-1",
                "plan": "the plan",
                "events": str(lane / ".qwenloop/runs/run-1/events.jsonl"),
                "poll_seconds": 60,
            }
        )
    )
    monkeypatch.setenv(qwenlane.SPEC_SHA256_ENV, hashlib.sha256(spec.read_bytes()).hexdigest())
    read_end, write_end = os.pipe()
    monkeypatch.setenv(qwenlane.REPORT_FD_ENV, str(write_end))
    try:
        assert qwenlane.run_attempt(spec) == 0
    finally:
        os.close(write_end)
        os.close(read_end)
    assert len(calls) == 1
    assert (
        calls[0]["max_empty_reply_retries"],
        calls[0]["max_recorded_argument_chars"],
        calls[0]["empty_reply_reasoning_excerpt_chars"],
    ) == (4, 64, 32)
