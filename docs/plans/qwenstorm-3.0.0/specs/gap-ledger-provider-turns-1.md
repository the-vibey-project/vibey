## Title
feat(engines): the local-model chat client reports every exchange, with tokens and timings, through a declared turn seam

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks for "every … turn … cost,
measurement" in the ledger, and 8.g (`:316`) for every model's latency and throughput. The
sovereign DESIGN provider (`QwenloopDesignProvider`,
`src/vibey/infrastructure/engines/qwenloop_design.py:177-363`), the DECOMPOSE producer
(`qwenloop_decompose.py:128`) and #324's VISUAL provider (`split-324-1-visual-provider`) all call
the local model through one client, `OllamaChatClient.ask`
(`src/vibey/infrastructure/engines/ollama_chat.py:147-177`). It returns only the parsed answer
and drops what Ollama reports beside it: `prompt_eval_count`, `eval_count`, `total_duration`,
`load_duration`, `prompt_eval_duration`, `eval_duration` (nanoseconds). No `TurnRequested` or
`TurnCompleted` is written, so these calls cost the ledger nothing and measure nothing.

This lane gives the client a declared seam that sees every exchange (start, and end with tokens,
timings or the error). `gap-ledger-provider-turns-2` implements the seam over the ledger;
`gap-ledger-provider-turns-3` wires it in the CLI.

**Ordering rule with `gap-design-via-sovereignloop`.** A model call's turns are recorded by
exactly one party: the component that sends the request to the model. On the direct path
(today, and `invocation = subprocess` after gap A4) that is this client, through this seam. When
a call is routed through sovereignloop, the providers do not call `OllamaChatClient.ask`; the
loop's run events become the ledger's turn events through the tailer (sovereignloop's
`turn.completed` → `TurnCompleted`, `src/vibey/infrastructure/engines/loop_events.py:207-218`). No call takes both paths, so no turn
is recorded twice, in whichever order the lanes land. Direct-path events carry `"path": "direct"`
(lane 2) so a reader can tell them apart.

## Required behaviour
1. New `src/vibey/infrastructure/engines/model_turns.py` (provenance header on line 1) with two
   frozen, slotted dataclasses:
   - `ModelTurnStart`: `turn_id: UUID`, `model: str`, `endpoint: str`, `prompt_chars: int`,
     `num_ctx: int`, `answer_keys: tuple[str, ...]`, `started_at: datetime`.
   - `ModelTurnEnd`: `start: ModelTurnStart`, `ended_at: datetime`,
     `input_tokens: int | None`, `output_tokens: int | None`,
     `server_timings: Mapping[str, int]`, `error: str | None`.
2. New `src/vibey/infrastructure/engines/interfaces/model_turns_interface.py`:
   `@runtime_checkable class ModelTurnRecorderInterface(Protocol)` with
   `async def requested(self, start: ModelTurnStart) -> None` and
   `async def completed(self, end: ModelTurnEnd) -> None` (DTOs under `TYPE_CHECKING`; copy the
   header of `ollama_chat_interface.py:1-9`). Export it from `engines/interfaces/__init__.py`
   (import block and `__all__`, sorted).
3. `OllamaChatClient.__init__` gains keywords `turns: ModelTurnRecorderInterface | None = None`
   and `clock: Clock | None = None` (`vibey.application.interfaces.system.Clock`);
   `from_environment` gains the same two keywords and passes them through. A private
   `_now(self) -> datetime` returns `self._clock.now()` or `datetime.now(UTC)` (the pattern of
   `engine_health_service.py:50-51`).
4. `ask(system, user, schema)` keeps its signature and result:
   - `num_ctx = self.context_window(len(system) + len(user))` is computed once and used in the
     request `options` as today.
   - `start = ModelTurnStart(turn_id=uuid4(), model=self._model, endpoint=self._base_url, prompt_chars=len(system) + len(user), num_ctx=num_ctx, answer_keys=keys, started_at=self._now())`,
     where `keys` is `tuple(sorted(k for k in required if isinstance(k, str)))` when
     `required = schema.get("required")` is a `list`, and `()` otherwise.
   - If `self._turns` is not `None`, `await self._turns.requested(start)` **before** the request
     is sent. If it raises, the model is not called.
   - The request and parsing are today's (`:165-177`), moved into a private `_answer(body)`.
     Any `Exception` from the transport or from `_answer` is re-raised after
     `await self._finish(start, body, error=f"{type(exc).__name__}: {exc}")`, where `body` is the
     response if one arrived and `None` otherwise. On success, `await self._finish(start, body, error=None)`
     and return the answer. (`asyncio.CancelledError` is not an `Exception`: a cancelled call
     leaves a requested turn with no completion, which is the truth.)
   - `_finish` does nothing when `self._turns is None`. Otherwise it builds `ModelTurnEnd` with
     `ended_at=self._now()`, `input_tokens` = `body["prompt_eval_count"]` and `output_tokens` =
     `body["eval_count"]` when each is an `int` and not a `bool` (else `None`), and
     `server_timings` maps `"total_ms"` to `body["total_duration"] // 1_000_000`, `"load_ms"` to
     `body["load_duration"] // 1_000_000`, `"prompt_eval_ms"` to `body["prompt_eval_duration"] // 1_000_000`
     and `"eval_ms"` to `body["eval_duration"] // 1_000_000`, each key present only when its source
     is an `int` and not a `bool` (`{}` when `body` is `None`).
5. **The fake.** `tests/fakes/engines.py` gains `class RecordingModelTurns`
   (`ModelTurnRecorderInterface`): `starts: list[ModelTurnStart]`, `ends: list[ModelTurnEnd]`,
   and `fail_next_request(exc: BaseException)`, which makes the next `requested` raise `exc` and
   record nothing. Register it in `tests/fakes/registry.py`: `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/engines/model_turns.py`,
  `src/vibey/infrastructure/engines/interfaces/model_turns_interface.py`.
- `src/vibey/infrastructure/engines/interfaces/__init__.py`, `src/vibey/infrastructure/engines/ollama_chat.py` (edit_file only).
- `tests/fakes/engines.py`, `tests/fakes/registry.py`.
- Append to `tests/infrastructure/engines/test_ollama_chat.py` (its `FakeTransport`, `:27-37`,
  already answers with a canned body; give it the usage keys in the new tests).

## Acceptance criteria
- [ ] With no recorder, every existing test in `test_ollama_chat.py`, `test_qwenloop_decompose.py`
      and `tests/infrastructure/test_qwenloop_design.py` passes unchanged.
- [ ] One `ask` with a recorder records one start (`model`, `endpoint`, `prompt_chars`, `num_ctx`
      equal to the request's `options.num_ctx`, `answer_keys == ("questions",)` for
      `QUESTIONS_SCHEMA`) before the transport is called, and one end with `input_tokens`,
      `output_tokens`, and `server_timings` in whole milliseconds.
- [ ] A body whose content is not JSON records an end with the tokens it carried and an `error`
      starting `"JSONDecodeError"`, then raises as today.
- [ ] A transport that raises records an end with `input_tokens is None` and the error, then re-raises.
- [ ] A recorder whose `requested` raises stops the call: the transport is never called.
- [ ] A `bool` token count is recorded as `None`.
- [ ] `tests/fakes/test_port_parity.py` passes; 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/engines/test_ollama_chat.py` (a fixed `Clock` class in the file):
- `test_an_exchange_is_reported_before_and_after_the_request`
- `test_tokens_and_server_timings_come_from_the_response`
- `test_an_unparseable_answer_is_reported_with_its_error_then_raised`
- `test_a_transport_failure_is_reported_then_raised`
- `test_a_failing_turn_recorder_stops_the_call_before_the_model`
- `test_a_boolean_count_is_not_a_token_count`
- `test_without_a_recorder_nothing_changes`
- `test_a_schema_without_a_required_list_reports_no_answer_keys`
- `test_from_environment_passes_the_recorder_through`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/test_qwenloop_design.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Writing ledger events (`gap-ledger-provider-turns-2`) and wiring the CLI (`-3`).
- The providers' code (unchanged: they call `ask` as today).
- vibey-gh's `local_review.py` (a tenant with no vibey ledger; gap A5 routes it through the loop).
- Docs, CHANGELOG.

Commit as `feat(engines): the local-model chat client reports every exchange through a turn seam`. Do not push.

## Lane card
- **Depends on:** `fakes-engines`.
- **Must keep passing unchanged:** the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
