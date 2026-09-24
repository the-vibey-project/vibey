# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The storm's turn pool: storm turns as the payloads qwenloop sends (ADR-0058).

`vibey-gh slots calibrate` replays these payloads to measure how many runs of the model fit
on a device, so a pool built wrongly would measure the wrong work. Both sources use
qwenloop's own runner functions. The `lanes` rebuild is held to the runner's own sequence --
preamble, repair text on a later attempt, tool results truncated as the runner truncates
them, the retry prompt a turn appends before its answering call, and the continue and
invalid-completion prompts it appends after. The `specs` build is held to the window: no
payload it writes can overflow it. The tools are addressed by path for the reason
`test_storm_check_parser.py` gives.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOLS = REPO / "docs/plans/qwenstorm-3.0.0/tools"
QWENLOOP = REPO / "src/vibey_runners/qwen/src"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


storm_turn_pool = _load("storm_turn_pool", "storm_turn_pool.py")
declared = _load("storm_turn_pool_interface", "interfaces/storm_turn_pool_interface.py")


def event(**fields: object) -> str:
    return json.dumps(fields)


def lane(tmp_path: Path, name: str, runs: list[list[str]], plan: str | None = "# plan") -> Path:
    root = tmp_path / "lanes" / name
    (root / ".qwenstorm").mkdir(parents=True)
    if plan is not None:
        (root / ".qwenstorm" / "plan.md").write_text(plan)
    for number, events in enumerate(runs):
        run = root / ".qwenloop" / "runs" / f"run{number}"
        run.mkdir(parents=True)
        (run / "meta.json").write_text(
            json.dumps({"run_id": f"{name}-{number}", "cwd": str(root), "context_window": 65536})
        )
        (run / "events.jsonl").write_text("\n".join(events) + "\n")
    return root


def turn(number: int, started: str, tokens: int) -> str:
    return event(
        type="turn.completed",
        turn=number,
        input_tokens=tokens,
        output_tokens=5,
        model_ms=10,
        started_at=started,
    )


def test_the_lanes_pool_rebuilds_each_payload_in_the_runners_own_order(tmp_path: Path) -> None:
    first = [
        event(type="text_delta", text="reading"),
        event(type="tool_result", name="read_file", result={"content": "x" * 9000}),
        turn(1, "2026-09-23T01:00:00Z", 5000),
        event(type="turn.retried", turn=2, retry=1, reason="tool_call_parse_error"),
        event(type="text_delta", text="thinking aloud"),
        turn(2, "2026-09-23T01:00:05Z", 6000),
        event(type="text_delta", text="QWENLOOP_TASK_FULLY_COMPLETE"),
        turn(3, "2026-09-23T01:00:09Z", 6100),
    ]
    second = [turn(1, "2026-09-23T02:00:00Z", 5200)]
    root = lane(tmp_path, "a", [second, first])
    lane(tmp_path, "no-plan", [second], plan=None)
    pool = storm_turn_pool.QwenloopTurnPool(QWENLOOP)
    assert pool.runs(tmp_path / "nowhere") == []
    runs = pool.runs(tmp_path / "lanes")
    assert [r.parents[2].name for r in runs] == ["a", "a", "no-plan"]
    assert runs[0].name == "run1" and runs[1].name == "run0"  # oldest first, by start time
    lines = list(pool.build(runs))
    assert len(lines) == 2  # a lane without plan.md cannot be rebuilt and is left out
    early, late = lines
    assert early["schema"] == "vibey-gh/turn-pool/1" and early["run"] == "a-1"
    assert early["preamble"][0]["role"] == "system" and str(root) in early["preamble"][0]["content"]
    assert early["preamble"][1] == {"role": "user", "content": "# plan"}
    assert "repair attempt 2 of 3" in late["preamble"][1]["content"]
    assert "{} arguments" in early["notes"][0]
    one, two, three = early["turns"]
    assert one["recorded_input_tokens"] == 5000 and one["before"] == []
    assistant, tool = one["after"]
    assert assistant["tool_calls"] == [{"function": {"name": "read_file", "arguments": {}}}]
    assert tool["role"] == "tool" and tool["tool_name"] == "read_file"
    assert tool["content"].endswith("characters]") and len(tool["content"]) < 9100
    assert "not a valid tool call" in two["before"][0]["content"]
    assert [m["role"] for m in two["after"]] == ["assistant", "user"]
    assert "Continue the plan" in two["after"][1]["content"]
    assert three["after"][-1]["role"] == "user"
    assert "Continue the plan" not in three["after"][-1]["content"]
    assert "messages" not in one


def test_a_trimmed_turn_carries_its_whole_payload(tmp_path: Path) -> None:
    big = {"content": "y" * 7999}
    events = []
    for number in range(1, 40):
        events.append(event(type="tool_result", name="read_file", result=big))
        events.append(turn(number, f"2026-09-23T01:{number:02d}:00Z", 1000 * number))
    lane(tmp_path, "deep", [events])
    pool = storm_turn_pool.QwenloopTurnPool(QWENLOOP)
    (line,) = list(pool.build(pool.runs(tmp_path / "lanes")))
    trimmed = [t for t in line["turns"] if "messages" in t]
    assert trimmed, "39 turns of 8,000-character results must pass the trim budget"
    marker = trimmed[0]["messages"][2]
    assert marker["role"] == "system" and "omitted to fit" in marker["content"]


def test_the_repair_text_is_read_not_imported(tmp_path: Path) -> None:
    text = storm_turn_pool.QwenloopTurnPool.repair_text(TOOLS / "qwenlane.py")
    assert "{attempt}" in text and "{max_attempts}" in text
    (tmp_path / "q.py").write_text("OTHER = 1\n")
    with pytest.raises(ValueError, match="no longer defines REPAIR"):
        storm_turn_pool.QwenloopTurnPool.repair_text(tmp_path / "q.py")


def test_the_specs_pool_reads_real_files_and_never_overflows_the_window() -> None:
    specs = sorted((REPO / "docs/plans/qwenstorm-3.0.0/specs").glob("*.md"))[:2]
    pool = storm_turn_pool.SpecTurnPool(QWENLOOP, REPO, seed=3, context_window=16384)
    lines = list(pool.build(specs))
    assert len(lines) == 2
    for line in lines:
        assert line["run"].startswith("spec:") and line["source"].endswith(pool.commit[:12])
        assert line["preamble"][0]["role"] == "system" and line["preamble"][1]["role"] == "user"
        assert "Storm-shaped, not replayed" in line["notes"][0]
        assert line["turns"], "every spec reads at least one file"
        depths = [t["recorded_input_tokens"] for t in line["turns"]]
        assert depths == sorted(depths)
        call, result = line["turns"][0]["after"]
        path = call["tool_calls"][0]["function"]["arguments"]["path"]
        assert (REPO / path).is_file() and result["tool_name"] == "read_file"
        full = line["preamble"] + [m for t in line["turns"] for m in t["after"]]
        assert pool.depth(full) <= 16384 - 2048


def test_the_pool_estimate_is_the_fit_calculus_own() -> None:
    from vibey_gh.fit import DEFAULT_CHARS_PER_TOKEN

    assert storm_turn_pool.CHARS_PER_TOKEN == DEFAULT_CHARS_PER_TOKEN


def test_each_builder_honours_the_interface_declared_beside_it() -> None:
    pairs = [
        (storm_turn_pool.QwenloopTurnPool(QWENLOOP), declared.TurnPoolBuilderInterface),
        (storm_turn_pool.SpecTurnPool(QWENLOOP, REPO), declared.SpecTurnPoolInterface),
    ]
    for instance, interface in pairs:
        assert isinstance(instance, interface)
        for name in vars(interface):
            if name.startswith("_") or not callable(getattr(instance, name, None)):
                continue
            want = [
                p for p in inspect.signature(getattr(interface, name)).parameters if p != "self"
            ]
            have = list(inspect.signature(getattr(instance, name)).parameters)
            assert have == want, f"{type(instance).__name__}.{name}: {have} != {want}"
