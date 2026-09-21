# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from vibey.application.dto import RunSpec
from vibey.application.worker import CapacityDeferred
from vibey.domain.effort import Effort
from vibey.domain.engine import IsolationLevel
from vibey.infrastructure.engines.opencodeloop_process import (
    AsyncSubprocessExecutor,
    CommandResult,
    OpenCodeLoopProcess,
    _run_spend,
)


class FakeExecutor:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        return self.result


class CancellingSubprocess:
    returncode = None

    def __init__(self) -> None:
        self.terminated = False
        self.waited = False

    async def communicate(self):  # type: ignore[no-untyped-def]
        raise asyncio.CancelledError

    def terminate(self) -> None:
        self.terminated = True

    async def wait(self) -> None:
        self.waited = True


class MockProcess:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


def spec(tmp_path: Path) -> RunSpec:
    return RunSpec(
        run_id=UUID("00000000-0000-0000-0000-000000000123"),
        worktree_path=tmp_path,
        prompt="# Bounded DESIGN research\n",
        effort=Effort.STANDARD,
        isolation=IsolationLevel.WORKTREE,
    )


async def test_cancelling_executor_terminates_and_reaps_its_child(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    child = CancellingSubprocess()

    async def fake_create(*args, **kwargs):  # type: ignore[no-untyped-def]
        return child

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    with pytest.raises(asyncio.CancelledError):
        await AsyncSubprocessExecutor().execute(("opencodeloop", "run"))
    assert child.terminated
    assert child.waited


async def test_successful_executor_runs_and_returns_result(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    proc = MockProcess(0, b"success out", b"success err")

    async def fake_create(*args, **kwargs):  # type: ignore[no-untyped-def]
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create)
    res = await AsyncSubprocessExecutor().execute(("opencodeloop", "run"))
    assert res.returncode == 0
    assert res.stdout == "success out"
    assert res.stderr == "success err"


def test_invalid_bounds_raise_value_error() -> None:
    with pytest.raises(ValueError, match="positive turn cap"):
        OpenCodeLoopProcess(
            executor=FakeExecutor(CommandResult(0, "", "")), max_turns=0, max_dollars=1.0
        )
    with pytest.raises(ValueError, match="dollar cap at most 10"):
        OpenCodeLoopProcess(
            executor=FakeExecutor(CommandResult(0, "", "")), max_turns=1, max_dollars=0.0
        )
    with pytest.raises(ValueError, match="dollar cap at most 10"):
        OpenCodeLoopProcess(
            executor=FakeExecutor(CommandResult(0, "", "")), max_turns=1, max_dollars=11.0
        )


async def test_run_materializes_plan_enforces_caps_and_reads_latest_response(
    tmp_path: Path,
) -> None:
    run_id = "20260814T120000Z-abcd1234"
    events = tmp_path / ".opencodeloop" / "runs" / run_id / "events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "first"}})
        + "\n"
        + json.dumps(
            {"event_type": "sdk.message", "payload": {"type": "ResultMessage", "result": "final"}}
        )
        + "\n"
    )
    executor = FakeExecutor(CommandResult(0, "", f"Run id: {run_id}\nTrace id: trace-1\n"))
    recorded_spends = []

    async def spend_recorder(turns: int, dollars: float) -> None:
        recorded_spends.append((turns, dollars))

    process = OpenCodeLoopProcess(
        executor=executor, max_turns=1, max_dollars=0.25, spend_recorder=spend_recorder
    )

    result = await process.run(spec(tmp_path), web_search=True)

    plan = tmp_path / ".vibey" / "plans" / "00000000-0000-0000-0000-000000000123.md"
    assert plan.read_text() == "# Bounded DESIGN research\n"
    assert executor.calls == [
        (
            "opencodeloop",
            "run",
            str(plan),
            "--run-id",
            "00000000-0000-0000-0000-000000000123",
            "--cwd",
            str(tmp_path),
            "--max-turns",
            "1",
            "--max-dollars",
            "0.25",
            "--no-auto-model",
            "--max-wait",
            "1",
            "--web-search",
        )
    ]
    assert result.run_id == run_id
    assert result.response == "final"
    # Spend check: sdk.message doesn't increment turn count or dollars (only turn.completed does)
    assert result.turns == 0
    assert result.cost_usd == 0.0
    assert recorded_spends == []


async def test_reusable_result_reads_from_disk_instead_of_spawning(
    tmp_path: Path,
) -> None:
    run_id = "20260814T120000Z-abcd1234"
    run_dir = tmp_path / ".opencodeloop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    plan_path = tmp_path / ".vibey" / "plans" / "00000000-0000-0000-0000-000000000123.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("# Bounded DESIGN research\n")

    (run_dir / "meta.json").write_text(json.dumps({"plan_path": str(plan_path)}))
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "turn.completed", "payload": {"cost_usd": 0.1}})
        + "\n"
        + json.dumps({"event_type": "chatter.assistant", "payload": {"text": '{"result": "ok"}'}})
        + "\n"
    )

    executor = FakeExecutor(CommandResult(0, "", ""))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.25)

    result = await process.run(spec(tmp_path))

    assert executor.calls == []
    assert result.run_id == run_id
    assert result.response == '{"result": "ok"}'
    assert result.turns == 1
    assert result.cost_usd == 0.1


async def test_rate_limit_event_raises_capacity_deferred(
    tmp_path: Path,
) -> None:
    run_id = "20260814T120000Z-abcd1234"
    run_dir = tmp_path / ".opencodeloop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    events = run_dir / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "event_type": "turn.completed",
                "payload": {
                    "type": "RateLimitEvent",
                    "status": "rejected",
                    "resets_at": 1782000000,
                    "rate_limit_type": "tier",
                },
            }
        )
        + "\n"
    )
    executor = FakeExecutor(CommandResult(1, "", f"Run id: {run_id}\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.25)

    with pytest.raises(CapacityDeferred) as exc_info:
        await process.run(spec(tmp_path))
    assert exc_info.value.retry_at == datetime.fromtimestamp(1782000000, UTC)
    assert "tier capacity exhausted" in exc_info.value.detail


async def test_non_zero_exit_without_capacity_recovers_structured_result(
    tmp_path: Path,
) -> None:
    run_id = "20260814T120000Z-abcd1234"
    run_dir = tmp_path / ".opencodeloop" / "runs" / run_id
    run_dir.mkdir(parents=True)
    events = run_dir / "events.jsonl"
    events.write_text(
        json.dumps(
            {
                "event_type": "chatter.assistant",
                "payload": {"text": '```json\n{\n  "synthesized": true\n}\n```'},
            }
        )
        + "\n"
    )
    executor = FakeExecutor(CommandResult(4, "", f"Run id: {run_id}\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.25)

    result = await process.run(spec(tmp_path))
    assert result.run_id == run_id
    assert result.response == '```json\n{\n  "synthesized": true\n}\n```'


async def test_non_zero_exit_with_garbled_output_raises_runtime_error(
    tmp_path: Path,
) -> None:
    executor = FakeExecutor(CommandResult(2, "standard out", "stderr detail"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.25)

    with pytest.raises(RuntimeError, match="opencodeloop failed with exit 2: stderr detail"):
        await process.run(spec(tmp_path))


async def test_find_reusable_skips_non_dir_entries(tmp_path: Path) -> None:
    runs_root = tmp_path / ".opencodeloop" / "runs"
    runs_root.mkdir(parents=True)
    (runs_root / "not-a-dir.txt").write_text("file not dir")
    executor = FakeExecutor(CommandResult(0, "", "Run id: new-run\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.1)
    new_run = tmp_path / ".opencodeloop" / "runs" / "new-run"
    new_run.mkdir()
    (new_run / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "{}"}})
    )
    await process.run(spec(tmp_path))
    assert len(executor.calls) == 1


async def test_find_reusable_skips_invalid_run_id_names(tmp_path: Path) -> None:
    runs_root = tmp_path / ".opencodeloop" / "runs"
    runs_root.mkdir(parents=True)
    (runs_root / "!!!invalid").mkdir()
    executor = FakeExecutor(CommandResult(0, "", "Run id: new-run\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.1)
    new_run = runs_root / "new-run"
    new_run.mkdir()
    (new_run / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "{}"}})
    )
    await process.run(spec(tmp_path))
    assert len(executor.calls) == 1


async def test_find_reusable_skips_missing_meta_json(tmp_path: Path) -> None:
    runs_root = tmp_path / ".opencodeloop" / "runs"
    old_run = runs_root / "20260814T120000Z-abcd1234"
    old_run.mkdir(parents=True)
    (old_run / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "{}"}})
    )
    executor = FakeExecutor(CommandResult(0, "", "Run id: 20260814T130000Z-abcd1234\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.1)
    new_run = runs_root / "20260814T130000Z-abcd1234"
    new_run.mkdir()
    (new_run / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "{}"}})
    )
    await process.run(spec(tmp_path))
    assert len(executor.calls) == 1


def test_looks_structured_rejects_unclosed_fence() -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _looks_structured

    assert _looks_structured('```json\n{"a":1}') is False


def test_looks_structured_rejects_non_dict() -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _looks_structured

    assert _looks_structured("[1, 2, 3]") is False


def test_looks_structured_rejects_invalid_json() -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _looks_structured

    assert _looks_structured("not json at all") is False


def test_reported_run_id_skips_invalid_format() -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _reported_run_id

    stderr = "Run id: !!!invalid\nRun id: valid-20260814T120000Z\n"
    assert _reported_run_id(stderr) == "valid-20260814T120000Z"


def test_reported_run_id_raises_runtime_error_if_none_found() -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _reported_run_id

    with pytest.raises(RuntimeError, match="did not report a run id"):
        _reported_run_id("no run id in stderr output")


def test_capacity_deferred_edge_cases(tmp_path: Path) -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _capacity_deferred

    # 1. No run id in stderr
    assert _capacity_deferred(tmp_path, "stderr with no run id") is None

    # 2. Run id exists but no events file
    assert _capacity_deferred(tmp_path, "Run id: r-1") is None

    # 3. Bad JSON in events file
    run_dir = tmp_path / ".opencodeloop" / "runs" / "r-1"
    run_dir.mkdir(parents=True)
    events = run_dir / "events.jsonl"
    events.write_text("invalid json line\n")
    assert _capacity_deferred(tmp_path, "Run id: r-1") is None

    # 4. JSON ok but not RateLimitEvent
    events.write_text(
        json.dumps({"event_type": "turn.completed", "payload": {"type": "NormalEvent"}}) + "\n"
    )
    assert _capacity_deferred(tmp_path, "Run id: r-1") is None

    # 5. RateLimitEvent but status is not rejected
    events.write_text(
        json.dumps(
            {
                "event_type": "turn.completed",
                "payload": {"type": "RateLimitEvent", "status": "allowed"},
            }
        )
        + "\n"
    )
    assert _capacity_deferred(tmp_path, "Run id: r-1") is None


def test_reported_structured_result_edge_cases(tmp_path: Path) -> None:
    from vibey.infrastructure.engines.opencodeloop_process import _reported_structured_result

    # 1. No run id in stderr
    assert _reported_structured_result(tmp_path, "no run id") is None

    # 2. Run id exists but output is not structured
    run_dir = tmp_path / ".opencodeloop" / "runs" / "r-2"
    run_dir.mkdir(parents=True)
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "plain text"}}) + "\n"
    )
    assert _reported_structured_result(tmp_path, "Run id: r-2") is None


async def test_find_reusable_skips_plan_outside_plans_root(tmp_path: Path) -> None:
    runs_root = tmp_path / ".opencodeloop" / "runs"
    old_run = runs_root / "20260814T120000Z-abcd1234"
    old_run.mkdir(parents=True)
    outside_plan = tmp_path / "outside" / "plan.md"
    outside_plan.parent.mkdir(parents=True)
    outside_plan.write_text("# Bounded DESIGN research\n")
    (old_run / "meta.json").write_text(json.dumps({"plan_path": str(outside_plan)}))
    (old_run / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "{}"}})
    )
    executor = FakeExecutor(CommandResult(0, "", "Run id: 20260814T130000Z-abcd1234\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.1)
    new_run = runs_root / "20260814T130000Z-abcd1234"
    new_run.mkdir()
    (new_run / "events.jsonl").write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "{}"}})
    )
    await process.run(spec(tmp_path))
    assert len(executor.calls) == 1


async def test_find_reusable_skips_different_plan_content(tmp_path: Path) -> None:
    runs_root = tmp_path / ".opencodeloop" / "runs"
    old_run = runs_root / "20260814T120000Z-abcd1234"
    old_run.mkdir(parents=True)
    plan_path = tmp_path / ".vibey" / "plans" / "00000000-0000-0000-0000-000000000123.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("different plan content\n")
    (old_run / "meta.json").write_text(json.dumps({"plan_path": str(plan_path)}))
    executor = FakeExecutor(CommandResult(0, "", "Run id: 20260814T130000Z-abcd1234\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.1)
    await process.run(spec(tmp_path))
    assert len(executor.calls) == 1


def _events(run_dir: Path, lines: list[dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text("\n".join(json.dumps(line) for line in lines))


def _run_dir(tmp_path: Path, run_id: str) -> Path:
    return tmp_path / ".opencodeloop" / "runs" / run_id


_RID = "9651ebf4-fe65-4193-96f2-177a36ce9cfa"


async def test_a_completed_run_reports_the_spend_its_events_recorded(tmp_path: Path) -> None:
    _events(
        _run_dir(tmp_path, _RID),
        [
            {"event_type": "turn.completed", "payload": {"cost_usd": 0.4416597}},
            {"event_type": "turn.completed", "payload": {"cost_usd": 0.25}},
            {"event_type": "chatter.assistant", "payload": {"text": "done"}},
        ],
    )
    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
    )
    result = await process.run(spec(tmp_path))

    assert result.turns == 2
    assert result.cost_usd == pytest.approx(0.6916597)


async def test_the_recorder_receives_the_spend_so_the_brake_can_see_it(tmp_path: Path) -> None:
    _events(
        _run_dir(tmp_path, _RID),
        [{"event_type": "turn.completed", "payload": {"cost_usd": 1.5}}],
    )
    seen: list[tuple[int, float]] = []

    async def recorder(turns: int, dollars: float) -> None:
        seen.append((turns, dollars))

    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
        spend_recorder=recorder,
    )
    await process.run(spec(tmp_path))

    assert seen == [(1, 1.5)]


async def test_a_turn_without_usable_cost_still_counts_as_a_turn(tmp_path: Path) -> None:
    _events(
        _run_dir(tmp_path, _RID),
        [
            {"event_type": "turn.completed", "payload": {}},
            {"event_type": "turn.completed", "payload": {"cost_usd": "not a number"}},
            {"event_type": "turn.completed", "payload": {"cost_usd": True}},
            {"event_type": "turn.completed"},
            {"not json at all": 1},
            {"event_type": "sdk.message", "payload": {"total_cost_usd": 99.0}},
        ],
    )
    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
    )
    result = await process.run(spec(tmp_path))

    assert result.turns == 4
    assert result.cost_usd == 0.0


async def test_a_run_with_no_events_file_reports_no_spend(tmp_path: Path) -> None:
    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
    )
    (tmp_path / ".opencodeloop" / "runs" / _RID).mkdir(parents=True)
    result = await process.run(spec(tmp_path))

    assert (result.turns, result.cost_usd) == (0, 0.0)


async def test_a_free_run_is_not_reported_to_the_recorder(tmp_path: Path) -> None:
    seen: list[tuple[int, float]] = []

    async def recorder(turns: int, dollars: float) -> None:
        seen.append((turns, dollars))

    _events(_run_dir(tmp_path, _RID), [{"event_type": "chatter.assistant", "payload": {}}])
    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
        spend_recorder=recorder,
    )
    await process.run(spec(tmp_path))

    assert seen == []


async def test_last_response_skips_sdk_message_of_wrong_type(tmp_path: Path) -> None:
    _events(
        _run_dir(tmp_path, _RID),
        [
            {"event_type": "sdk.message", "payload": {"type": "OtherMessage"}},
            {
                "event_type": "sdk.message",
                "payload": {"type": "ResultMessage", "result": "matched"},
            },
        ],
    )
    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
    )
    result = await process.run(spec(tmp_path))
    assert result.response == "matched"


async def test_last_response_ignores_bad_json(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, _RID)
    run_dir.mkdir(parents=True)
    events = run_dir / "events.jsonl"
    events.write_text(
        json.dumps({"event_type": "chatter.assistant", "payload": {"text": "first"}})
        + "\n"
        + "invalid json line\n"
    )
    process = OpenCodeLoopProcess(
        executor=FakeExecutor(CommandResult(0, "", f"Run id: {_RID}")),
        max_turns=5,
        max_dollars=10,
    )
    result = await process.run(spec(tmp_path))
    assert result.response == "first"


def test_run_spend_returns_zero_if_no_file(tmp_path: Path) -> None:
    assert _run_spend(tmp_path / "does-not-exist") == (0, 0.0)


async def test_find_reusable_skips_unstructured_response(tmp_path: Path) -> None:
    runs_root = tmp_path / ".opencodeloop" / "runs"
    old_run = runs_root / "20260814T120000Z-abcd1234"
    old_run.mkdir(parents=True)
    plan_path = tmp_path / ".vibey" / "plans" / "00000000-0000-0000-0000-000000000123.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("# Bounded DESIGN research\n")
    (old_run / "meta.json").write_text(json.dumps({"plan_path": str(plan_path)}))
    (old_run / "events.jsonl").write_text(
        json.dumps(
            {"event_type": "chatter.assistant", "payload": {"text": "plain text unstructured"}}
        )
        + "\n"
    )
    executor = FakeExecutor(CommandResult(0, "", "Run id: 20260814T130000Z-abcd1234\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.1)
    await process.run(spec(tmp_path))
    assert len(executor.calls) == 1
