# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Bounded OpenCodeLoop subprocess boundary for live DESIGN work.

Every invocation has explicit turn and dollar ceilings and disables automatic
model escalation. The executor is injected so command construction and run
artifact parsing can be verified without launching or paying for a model run.
"""

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from vibey.application.dto import RunSpec
from vibey.application.worker import CapacityDeferred
from vibey.infrastructure.engines.argv import build_argv
from vibey.infrastructure.engines.descriptors import OPENCODE
from vibey.infrastructure.engines.plan_writer import write_plan
from vibey.infrastructure.interfaces import CommandExecutor

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class AsyncSubprocessExecutor:
    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise
        return CommandResult(process.returncode or 0, stdout.decode(), stderr.decode())


# (turns, dollars) from one completed run. Async because the only real
# implementation writes to the ledger.
SpendRecorder = Callable[[int, float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class OpenCodeLoopResult:
    run_id: str
    run_dir: Path
    response: str
    turns: int = 0
    cost_usd: float = 0.0


class OpenCodeLoopProcess:
    def __init__(
        self,
        *,
        executor: CommandExecutor,
        max_turns: int,
        max_dollars: float,
        spend_recorder: SpendRecorder | None = None,
    ) -> None:
        if max_turns < 1 or not 0 < max_dollars <= 10:
            raise ValueError("live runs require a positive turn cap and a dollar cap at most 10")
        self._executor = executor
        self._max_turns = max_turns
        self._max_dollars = max_dollars
        self._spend_recorder = spend_recorder

    async def run(self, spec: RunSpec, *, web_search: bool = False) -> OpenCodeLoopResult:
        reusable = _find_reusable_result(spec)
        if reusable is not None:
            return reusable
        write_plan(spec)
        argv = (
            *build_argv(OPENCODE, spec),
            "--max-turns",
            str(self._max_turns),
            "--max-dollars",
            format(self._max_dollars, "g"),
            "--no-auto-model",
            "--max-wait",
            "1",
            *(("--web-search",) if web_search else ()),
        )
        completed = await self._executor.execute(argv)
        if completed.returncode != 0:
            capacity = _capacity_deferred(spec.worktree_path, completed.stderr)
            if capacity is not None:
                raise capacity
            recovered = _reported_structured_result(spec.worktree_path, completed.stderr)
            if recovered is not None:
                await self._record(recovered)
                return recovered
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"opencodeloop failed with exit {completed.returncode}: {detail}")
        run_id = _reported_run_id(completed.stderr)
        run_dir = spec.worktree_path / OPENCODE.state_dir / "runs" / run_id
        events_path = run_dir / "events.jsonl"
        turns, dollars = _run_spend(events_path)
        result = OpenCodeLoopResult(run_id, run_dir, _last_response(events_path), turns, dollars)
        await self._record(result)
        return result

    async def _record(self, result: OpenCodeLoopResult) -> None:
        if self._spend_recorder is None:
            return
        if result.turns == 0 and result.cost_usd == 0.0:
            return
        await self._spend_recorder(result.turns, result.cost_usd)


def _reported_run_id(stderr: str) -> str:
    for line in stderr.splitlines():
        if line.startswith("Run id:"):
            run_id = line.partition(":")[2].strip()
            if _RUN_ID.fullmatch(run_id):
                return run_id
    raise RuntimeError("opencodeloop did not report a run id")


def _capacity_deferred(worktree_path: Path, stderr: str) -> CapacityDeferred | None:
    try:
        run_id = _reported_run_id(stderr)
    except RuntimeError:
        return None
    events_path = worktree_path / OPENCODE.state_dir / "runs" / run_id / "events.jsonl"
    if not events_path.is_file():
        return None
    for line in reversed(events_path.read_text().splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "RateLimitEvent":
            continue
        reset = payload.get("resets_at")
        if payload.get("status") != "rejected" or not isinstance(reset, int | float):
            continue
        retry_at = datetime.fromtimestamp(reset, UTC)
        limit = str(payload.get("rate_limit_type", "provider"))
        detail = f"opencodeloop {limit} capacity exhausted until {retry_at.isoformat()}"
        return CapacityDeferred(retry_at, detail)
    return None


def _reported_structured_result(worktree_path: Path, stderr: str) -> OpenCodeLoopResult | None:
    try:
        run_id = _reported_run_id(stderr)
    except RuntimeError:
        return None
    run_dir = worktree_path / OPENCODE.state_dir / "runs" / run_id
    response = _last_response(run_dir / "events.jsonl")
    if not _looks_structured(response):
        return None
    return OpenCodeLoopResult(run_id, run_dir, response)


def _run_spend(events_path: Path) -> tuple[int, float]:
    if not events_path.is_file():
        return 0, 0.0
    turns = 0
    dollars = 0.0
    for line in events_path.read_text().splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event_type") != "turn.completed":
            continue
        turns += 1
        payload = record.get("payload")
        cost = payload.get("cost_usd") if isinstance(payload, dict) else None
        if isinstance(cost, int | float) and not isinstance(cost, bool):
            dollars += float(cost)
    return turns, dollars


def _last_response(events_path: Path) -> str:
    if not events_path.is_file():
        return ""
    for line in reversed(events_path.read_text().splitlines()):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        event_type = record.get("event_type")
        if event_type == "chatter.assistant" and isinstance(payload.get("text"), str):
            return str(payload["text"])
        if (
            event_type == "sdk.message"
            and payload.get("type") == "ResultMessage"
            and isinstance(payload.get("result"), str)
        ):
            return str(payload["result"])
    return ""


def _find_reusable_result(spec: RunSpec) -> OpenCodeLoopResult | None:
    runs_root = spec.worktree_path / OPENCODE.state_dir / "runs"
    plans_root = (spec.worktree_path / ".vibey" / "plans").resolve()
    if not runs_root.is_dir():
        return None
    for run_dir in sorted(runs_root.iterdir(), reverse=True):
        if not run_dir.is_dir() or not _RUN_ID.fullmatch(run_dir.name):
            continue
        try:
            meta = json.loads((run_dir / "meta.json").read_text())
            plan = Path(str(meta["plan_path"])).resolve()
            if not plan.is_relative_to(plans_root) or plan.read_text() != spec.prompt:
                continue
        except (FileNotFoundError, KeyError, json.JSONDecodeError, OSError):
            continue
        events_path = run_dir / "events.jsonl"
        response = _last_response(events_path)
        if _looks_structured(response):
            turns, dollars = _run_spend(events_path)
            return OpenCodeLoopResult(run_dir.name, run_dir, response, turns, dollars)
    return None


def _looks_structured(response: str) -> bool:
    stripped = response.lstrip()
    candidate = stripped
    fence = stripped.find("```json")
    if fence >= 0:
        closing_fence = stripped.find("```", fence + 7)
        if closing_fence < 0:
            return False
        candidate = stripped[fence + 7 : closing_fence].strip()
    try:
        return isinstance(json.loads(candidate), dict)
    except json.JSONDecodeError:
        return False
