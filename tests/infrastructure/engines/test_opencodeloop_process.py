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
        "not-json\n"
        + json.dumps({"event_type": "chatter.assistant", "payload": {"text": "first"}})
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
            {"event_type": "chatter.assistant", "payload": {"text": '{"synthesized": true}'}}
        )
        + "\n"
    )
    executor = FakeExecutor(CommandResult(4, "", f"Run id: {run_id}\n"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.25)

    result = await process.run(spec(tmp_path))
    assert result.run_id == run_id
    assert result.response == '{"synthesized": true}'


async def test_non_zero_exit_with_garbled_output_raises_runtime_error(
    tmp_path: Path,
) -> None:
    executor = FakeExecutor(CommandResult(2, "standard out", "stderr detail"))
    process = OpenCodeLoopProcess(executor=executor, max_turns=1, max_dollars=0.25)

    with pytest.raises(RuntimeError, match="opencodeloop failed with exit 2: stderr detail"):
        await process.run(spec(tmp_path))
