## Title
feat(ledger): direct local-model calls are TurnRequested and TurnCompleted events with tokens, timings and cost

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks for "every … turn … cost,
measurement … with its time, its actor and its evidence". The sovereign DESIGN, DECOMPOSE and
VISUAL calls write no turn at all (gap E5): `QwenloopDesignProvider` emits design events but no
`TurnRequested`/`TurnCompleted` (`src/vibey/infrastructure/engines/qwenloop_design.py:205-363`).
`gap-ledger-provider-turns-1` gave `OllamaChatClient` a declared seam,
`ModelTurnRecorderInterface`, that sees each exchange. This lane implements it over the ledger.

The engine paths already write these kinds with qwenloop's field names
(`src/vibey_runners/qwen/src/qwenloop/application/runner.py:326-339`: `input_tokens`,
`output_tokens`, `started_at`, `ended_at`, `duration_ms`, `server_timings`), so the direct path uses
the same names, and readers (`LedgerSpendRule`, `src/vibey/domain/phase_timing.py:123-163`; the
budget brake) treat both alike. A local model costs no dollars, and the event says so explicitly:
`cost_usd: 0.0`. A project with `max_cycle_turns` now counts these calls as turns, which is what
that cap was meant to see.

The provider methods carry no project (`batch(stage, prior_events)`, `synthesize(events)`), so the
recorder is bound to one project when it is built, as `_build_spend_recorder` already binds the
paid DESIGN path's spend (`src/vibey/cli/main.py:140-176`). It reads the project's current cycle
and phase at the request, not at wiring time, so a long-running `vibey worker` files each turn
under the phase it happened in; the completion keeps its request's cycle and phase.

## Required behaviour
1. In `src/vibey/infrastructure/engines/model_turns.py`, `class LedgerModelTurnRecorder`,
   declared by `ModelTurnRecorderInterface` (`engines/interfaces/model_turns_interface.py`):
   - `__init__(self, *, ledger: LedgerRepositoryInterface, projects: ProjectStore, project_id: UUID, engine_id: EngineId | None, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None`
     (`LedgerRepositoryInterface` from
     `vibey.infrastructure.db.interfaces.ledger_repository_interface`, lane `fakes-ledger`;
     `ProjectStore` from `vibey.application.interfaces`). It keeps
     `self._open: dict[UUID, tuple[int, Phase, UUID]]`.
   - `requested(start)`: `project = await self._projects.get(self._project_id)`; `None` raises
     `LookupError(f"model turn for unknown project {self._project_id}")`; a phase that is not a
     `Phase` raises `ValueError(f"project {self._project_id} is in phase {project.phase.value!r}, which this vibey does not know; it will not ledger a turn in it")`.
     Append `TURN_REQUESTED` with payload
     `{"turn_id": str(start.turn_id), "model": start.model, "endpoint": start.endpoint, "prompt_chars": start.prompt_chars, "num_ctx": start.num_ctx, "answer_keys": list(start.answer_keys), "started_at": start.started_at.isoformat(), "path": "direct"}`
     and `produced_at=start.started_at`; then
     `self._open[start.turn_id] = (project.cycle, project.phase, event.event_id)`.
   - `completed(end)`: `self._open.pop(end.start.turn_id)`; a missing entry raises
     `LookupError(f"turn {end.start.turn_id} completed but was never requested")`. Append
     `TURN_COMPLETED` under the request's cycle and phase, `causation_id` = the request event's
     id, `produced_at=end.ended_at`, payload
     `{"turn_id": str(end.start.turn_id), "model": end.start.model, "input_tokens": end.input_tokens, "output_tokens": end.output_tokens, "started_at": end.start.started_at.isoformat(), "ended_at": end.ended_at.isoformat(), "duration_ms": round((end.ended_at - end.start.started_at).total_seconds() * 1000), "server_timings": dict(end.server_timings), "cost_usd": 0.0, "outcome": "ok" if end.error is None else "error", "error": end.error, "path": "direct"}`.
   - Both drafts: `engine_id=self._engine_id`, `job_id=None`,
     `correlation_id=self._correlation.for_project(self._project_id).value`,
     `provenance=Provenance.AGENT` (as the tailer files engine turns,
     `src/vibey/infrastructure/engines/tailer.py:65`), `digest=digest_event(payload)`. A private
     `_draft(...)` builds both.
   - Class docstring: the binding reason (above), the `"path": "direct"` marker and the ordering
     rule of `gap-ledger-provider-turns-1` (routed calls are recorded by the loop's events, never here).
2. No other file changes. The recorder needs no registered fake of its own: over `InMemoryLedger`
   and `InMemoryProjectRepository` it is already fully in-memory, and its port's fake
   (`RecordingModelTurns`) was registered by lane 1.

## Where to change
- `src/vibey/infrastructure/engines/model_turns.py` (append the class; edit_file for imports).
- New test file `tests/infrastructure/engines/test_model_turns.py` (no service).

## Acceptance criteria
- [ ] A request for a project in DESIGN, cycle 1, ledgers one `TurnRequested` with phase DESIGN,
      cycle 1, the bound `engine_id`, `path: "direct"`, and the start's fields.
- [ ] Its completion ledgers one `TurnCompleted` whose `causation_id` is the request's
      `event_id`, with the tokens, `server_timings`, `duration_ms`, `cost_usd == 0.0` and `outcome: "ok"`.
- [ ] A completion carrying an error ledgers `outcome: "error"` and the error text.
- [ ] Moving the project to another phase between request and completion leaves the completion
      under the request's phase.
- [ ] An unknown project, a project in an unknown phase, and a completion with no request each raise
      and ledger nothing.
- [ ] `LEDGER_SPEND_RULE.spend_of(<the TurnCompleted event>)` is one turn event and `0.0` dollars.
- [ ] One `OllamaChatClient.ask` through a `FakeTransport` with this recorder ledgers exactly two
      events, request then completion.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/engines/test_model_turns.py` (provenance header on line 1; `InMemoryLedger`
from `tests/fakes/ledger.py`, `InMemoryProjectRepository` from `tests/fakes/projects.py`, a
project created then moved to DESIGN with `transition`):
- `test_a_request_is_ledgered_in_the_projects_current_cycle_and_phase`
- `test_a_completion_points_at_its_request_with_tokens_timings_and_zero_cost`
- `test_a_failed_exchange_is_ledgered_as_an_error_outcome`
- `test_a_completion_keeps_the_phase_of_its_request`
- `test_an_unknown_project_is_refused`
- `test_a_project_in_an_unknown_phase_is_refused` (write the record straight into the fake's
  store, as `fakes-cli-ledger-deploy` behaviour 4 does)
- `test_a_completion_without_its_request_is_refused`
- `test_the_spend_rule_counts_a_direct_turn_at_zero_dollars`
- `test_a_chat_exchange_lands_a_request_and_a_completion` (a transport class in the file returning
  `{"message": {"content": "{\"questions\": []}"}, "prompt_eval_count": 12, "eval_count": 3}`)
- `test_the_recorder_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Wiring the recorder into the CLI (`gap-ledger-provider-turns-3`).
- The prompt and answer text (`TranscriptRecorded`): the answers already land as the phase's own
  events (`QuestionAsked`, the spec); the prompts are a follow-up if the operator wants them held.
- A per-job `job_id` on these turns: the provider ports carry no job; binding per job needs the
  job-scoped context `CorrelationLogContext` describes (`src/vibey/infrastructure/logging.py:153-215`), a follow-up.
- Docs, CHANGELOG.

Commit as `feat(ledger): direct local-model calls are ledgered turns with tokens, timings and cost`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-provider-turns-1`, `fakes-ledger`, `fakes-projects`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
