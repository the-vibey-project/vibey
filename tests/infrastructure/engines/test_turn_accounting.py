# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One real turn, one TurnCompleted -- end to end, from a runner's own
events.jsonl through LoopProcessAdapter.tail and the tailer into the budget
brake (LedgerBudgetSource) that counts TurnCompleted against
``max_cycle_turns``.

Until this was fixed, ``chatter.assistant`` mapped to TurnCompleted beside
``turn.completed``, so claudeloop and agyloop under their default
``log_chatter=summary`` counted every turn twice and the cap tripped at half
the configured turns; every qwenloop ``text_delta`` counted as a turn.

The streams below mirror what each runner actually writes: claudeloop's and
agyloop's ``application/runner.py`` (turn.starting, chatter.prompt,
chatter.assistant, turn.completed, with ``chatter_event_payload``'s summary
shape), codexloop's ``infrastructure/agent/gateway.py::_event_to_dict`` (flat
``type`` records), and qwenloop's ``application/runner.py`` (a text_delta per
streamed fragment, one turn.completed per model call).
"""

import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.dto import EngineEvent, RunHandle
from vibey.domain.engine import EngineDescriptor, EngineId
from vibey.domain.ledger import EventKind, LedgerEvent
from vibey.domain.phase import Phase
from vibey.infrastructure.engines.descriptors import AGYLOOP, CLAUDELOOP, CODEXLOOP, QWENLOOP
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.engines.tailer import translate_event

Record = dict[str, object]


def _summary_chatter(event_type: str, text: str) -> Record:
    """The payload claudeloop/agyloop's ``chatter_event_payload`` builds in
    summary mode: the full text plus a console preview."""
    return {
        "event_type": event_type,
        "payload": {
            "text": text,
            "length": len(text),
            "truncated": False,
            "preview": text,
            "preview_truncated": False,
        },
    }


def _claude_family_run(turn_costs: list[float]) -> list[Record]:
    records: list[Record] = [
        {"event_type": "run.started", "payload": {}},
        {"event_type": "preflight", "payload": {"phase": "WORK"}},
    ]
    for turn, cost in enumerate(turn_costs, start=1):
        records += [
            {"event_type": "turn.starting", "payload": {"prompt_preview": f"step {turn}"}},
            _summary_chatter("chatter.prompt", f"do step {turn}"),
            {"event_type": "chatter.tool", "payload": {"tool": "Edit"}},
            _summary_chatter("chatter.assistant", f"did step {turn}"),
            {
                "event_type": "turn.completed",
                "payload": {
                    "capacity": "Available",
                    "cost_usd": cost,
                    "verdict": "Continue",
                    "model": "m",
                    "effort": "high",
                },
            },
            {"event_type": "savepoint", "payload": {"label": f"turn-{turn}"}},
            {"event_type": "capacity.forecast", "payload": {"headroom": 0.5}},
        ]
    records.append({"event_type": "finished", "payload": {"success": True}})
    return records


def _qwen_run(deltas_per_turn: list[int]) -> list[Record]:
    records: list[Record] = []
    for turn, deltas in enumerate(deltas_per_turn, start=1):
        records += [{"type": "text_delta", "text": f"tok{i}"} for i in range(deltas)]
        records.append({"type": "tool_result", "name": "write_file", "result": {}})
        records.append(
            {
                "type": "turn.completed",
                "turn": turn,
                "input_tokens": 10,
                "output_tokens": deltas,
                "tool_called": True,
            }
        )
    records.append({"type": "completed", "turn": len(deltas_per_turn)})
    return records


def _codex_run(outcomes: list[str]) -> list[Record]:
    records: list[Record] = [{"type": "thread.started", "thread_id": "t"}]
    for outcome in outcomes:
        records += [
            {"type": "turn.started"},
            {"type": "item.started", "item": {"type": "command_execution"}},
            {"type": "item.completed", "item": {"type": "agent_message"}},
        ]
        if outcome == "completed":
            records.append({"type": "turn.completed", "usage": {"input_tokens": 1}})
        else:
            records.append({"type": "turn.failed", "error": {"message": "stream error"}})
    records.append({"type": "run.verdict", "success": True, "complete": True})
    return records


async def _tail_events(
    tmp_path: Path, descriptor: EngineDescriptor, records: list[Record]
) -> list[EngineEvent]:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    (run_dir / "meta.json").write_text('{"status":"finished"}')
    handle = RunHandle(run_id=uuid4(), engine_id=descriptor.engine_id, run_dir=run_dir, pid=None)
    return [event async for event in LoopProcessAdapter(descriptor=descriptor).tail(handle)]


async def _tail(tmp_path: Path, descriptor: EngineDescriptor, records: list[Record]) -> list[str]:
    return [event.kind for event in await _tail_events(tmp_path, descriptor, records)]


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, AGYLOOP], ids=lambda d: d.engine_id.value)
@pytest.mark.parametrize("turns", [1, 3, 7])
async def test_claude_family_summary_chatter_yields_one_turn_per_turn(
    tmp_path: Path, descriptor: EngineDescriptor, turns: int
) -> None:
    kinds = await _tail(tmp_path, descriptor, _claude_family_run([0.1] * turns))

    assert kinds.count(EventKind.TURN_COMPLETED.value) == turns
    assert kinds.count(EventKind.TURN_REQUESTED.value) == turns
    # The chatter is kept -- two echoes per turn -- as transcript, not dropped.
    assert kinds.count(EventKind.TRANSCRIPT_RECORDED.value) == 2 * turns


@pytest.mark.parametrize("deltas_per_turn", [[1], [5, 40], [3, 3, 3, 3]])
async def test_qwenloop_delta_stream_yields_one_turn_per_completion(
    tmp_path: Path, deltas_per_turn: list[int]
) -> None:
    kinds = await _tail(tmp_path, QWENLOOP, _qwen_run(deltas_per_turn))

    assert kinds.count(EventKind.TURN_COMPLETED.value) == len(deltas_per_turn)
    assert kinds.count(EventKind.TRANSCRIPT_RECORDED.value) == sum(deltas_per_turn)
    assert kinds[-1] == EventKind.VERDICT_RENDERED.value


async def test_codexloop_failed_turn_is_one_turn_attempt_not_two(tmp_path: Path) -> None:
    """codex closes every turn with exactly one of turn.completed or
    turn.failed. Both count, once each: a failed turn is still a turn the
    vendor served, and a run failing turn after turn is the runaway the cap
    exists to stop."""
    kinds = await _tail(tmp_path, CODEXLOOP, _codex_run(["completed", "failed", "completed"]))

    assert kinds.count(EventKind.TURN_COMPLETED.value) == 3
    assert kinds.count(EventKind.TURN_REQUESTED.value) == 3


class _Reader:
    def __init__(self, events: list[LedgerEvent]) -> None:
        self._events = events

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        del project_id
        return tuple(self._events)


def _to_ledger(
    events: list[EngineEvent], *, project_id: UUID, engine_id: EngineId
) -> list[LedgerEvent]:
    ledger: list[LedgerEvent] = []
    correlation_id = uuid4()
    for seq, event in enumerate(events, start=1):
        draft = translate_event(
            event,
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            engine_id=engine_id,
            job_id=None,
            correlation_id=correlation_id,
        )
        assert draft is not None
        ledger.append(
            LedgerEvent(
                event_id=uuid4(),
                project_id=draft.project_id,
                cycle=draft.cycle,
                phase=draft.phase,
                seq=seq,
                kind=draft.kind,
                engine_id=draft.engine_id,
                job_id=draft.job_id,
                causation_id=draft.causation_id,
                correlation_id=draft.correlation_id,
                provenance=draft.provenance,
                produced_at=draft.produced_at,
                payload=draft.payload,
                digest=draft.digest,
            )
        )
    return ledger


async def _brake(
    tmp_path: Path, descriptor: EngineDescriptor, records: list[Record], max_turns: int
) -> tuple[int, float, bool]:
    project_id = uuid4()
    events = await _tail_events(tmp_path, descriptor, records)
    ledger = _to_ledger(events, project_id=project_id, engine_id=descriptor.engine_id)
    budget = await LedgerBudgetSource(_Reader(ledger), max_turns=max_turns).current(project_id, 1)
    return budget.turns_spent, budget.dollars_spent, budget.any_exhausted


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, AGYLOOP], ids=lambda d: d.engine_id.value)
async def test_turn_cap_trips_at_the_configured_turn_not_half_of_it(
    tmp_path: Path, descriptor: EngineDescriptor
) -> None:
    # Three real turns against a cap of four: under the old mapping the
    # chatter doubled this to six and parked the cycle a turn and a half early.
    turns, dollars, exhausted = await _brake(
        tmp_path, descriptor, _claude_family_run([0.5, 0.25, 1.0]), max_turns=4
    )
    assert turns == 3
    # Dollars were never double counted -- only turn.completed carries cost_usd.
    assert dollars == pytest.approx(1.75)
    assert not exhausted


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, AGYLOOP], ids=lambda d: d.engine_id.value)
async def test_turn_cap_trips_once_the_configured_turns_are_spent(
    tmp_path: Path, descriptor: EngineDescriptor
) -> None:
    turns, _, exhausted = await _brake(
        tmp_path, descriptor, _claude_family_run([0.1] * 4), max_turns=4
    )
    assert turns == 4
    assert exhausted


async def test_qwenloop_turn_cap_counts_model_calls_not_token_deltas(tmp_path: Path) -> None:
    # Two model calls streaming 45 fragments: two turns, well under a cap of three.
    turns, dollars, exhausted = await _brake(tmp_path, QWENLOOP, _qwen_run([5, 40]), max_turns=3)
    assert turns == 2
    assert dollars == 0.0
    assert not exhausted
