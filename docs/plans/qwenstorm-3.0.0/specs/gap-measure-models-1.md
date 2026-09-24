## Title
feat(measure): every local-model call records the model's tokens per second, load time and latency

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) measures every model, and 8.d's
default (`gpt-oss:20b` on Ollama) was chosen by a benchmark that lives outside the tree (gap D3,
another lane). The live path records nothing: the DESIGN and DECOMPOSE providers ask the local
model through `OllamaChatClient.ask` (`src/vibey/infrastructure/engines/ollama_chat.py:147-177`),
which reads `message.content` and drops the timings Ollama returns in the same body
(`total_duration`, `load_duration`, `prompt_eval_count`, `prompt_eval_duration`, `eval_count`,
`eval_duration`, all nanoseconds except the counts). The client already takes its transport as a
declared seam (`OllamaTransportInterface`, `src/vibey/infrastructure/engines/interfaces/ollama_chat_interface.py:12-20`;
`ollama_chat.py:96-105`), so a measuring transport wraps the real one without touching the
client. BUILD runs are measured by `gap-measure-engine-runs-1`; resident memory by
`gap-measure-models-2`.

## Required behaviour
1. New `src/vibey/infrastructure/measure/model_meter.py`, `class MeasuringOllamaTransport`
   (implements `OllamaTransportInterface`):
   `__init__(self, inner: OllamaTransportInterface, *, measurements: MeasurementPort, clock:
   Clock, instance: str = "", ids: Callable[[], UUID] = uuid4)`.
   `async def post_json(self, url, payload, *, timeout) -> dict[str, object]`:
   - `model = payload.get("model")` if it is a non-empty `str`, else `"unknown"`;
     `started = clock.now()`;
   - `body = await self._inner.post_json(url, payload, timeout=timeout)`. If it raises an
     `Exception`: record `Measurement(subject=MeasurementSubject(SubjectKind.MODEL, model),
     outcome=TIMED_OUT if isinstance(exc, TimeoutError) else FAILED, started_at=started,
     ended_at=clock.now(), readings=(Reading(Metric.LATENCY_SECONDS, wall),), instance=…,
     detail=f"{type(exc).__name__}: {exc}"[:500], measurement_id=ids())`, then re-raise;
   - on success, readings from `body`, each only when its inputs are numbers (not `bool`),
     finite and `>= 0`: `LATENCY_SECONDS = total_duration / 1e9` (else the wall time);
     `LOAD_SECONDS = load_duration / 1e9`; `INPUT_TOKENS = prompt_eval_count`;
     `OUTPUT_TOKENS = eval_count`; `TOKENS_PER_SECOND = eval_count / (eval_duration / 1e9)` and
     `PROMPT_TOKENS_PER_SECOND = prompt_eval_count / (prompt_eval_duration / 1e9)` when the
     duration is `> 0`. Outcome `OK`, detail `url.rsplit("/", 1)[-1]` (e.g. `"chat"`), no scope
     (the model serves the whole machine). Record it, then return `body` unchanged.
   A failure to record propagates (never a silent omission).
2. New `src/vibey/infrastructure/measure/interfaces/model_meter_interface.py`:
   `MeasuringOllamaTransportInterface` (`post_json`).
3. `src/vibey/cli/main.py`, both places that build the client — `_work_once` (`:449-451`) and
   `worker` (`:1604`) — pass
   `transport=MeasuringOllamaTransport(UrllibOllamaTransport(), measurements=resources.measurements,
   clock=resources.clock, instance=platform.node())` to `OllamaChatClient.from_environment(...)`.
   Import `UrllibOllamaTransport` in the existing block at `:67-72`; import
   `MeasuringOllamaTransport` and `platform` beside it (not above the SIGTERM latch).

## Where to change
- New `src/vibey/infrastructure/measure/model_meter.py` and its interface file.
- `src/vibey/cli/main.py` (`edit_file`; two call sites and the imports).
- New `tests/infrastructure/measure/test_model_meter.py`: the inner transport is a plain class
  returning a scripted body or raising (the `OllamaTransportInterface` shape), measurements go
  to `InMemoryMeasurements`, time to `FakeClock`.

## Acceptance criteria
- [ ] A body with `total_duration 2_000_000_000`, `load_duration 500_000_000`,
      `prompt_eval_count 100`, `prompt_eval_duration 250_000_000`, `eval_count 40`,
      `eval_duration 1_000_000_000` records model `gpt-oss:20b` with latency 2.0, load 0.5,
      input 100, output 40, tokens/s 40.0, prompt tokens/s 400.0, outcome `ok`, detail `chat`;
      the body is returned unchanged.
- [ ] A body with none of those keys records the wall-clock latency only.
- [ ] `TimeoutError` records `timed_out`, `ValueError("bad")` records `failed` with detail
      `"ValueError: bad"`; both are re-raised.
- [ ] An AST test finds `transport=` on every `OllamaChatClient.from_environment(` call in
      `src/vibey/cli/main.py`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/` and `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_model_meter.py`:
- `test_ollama_timings_become_model_readings`
- `test_missing_timings_fall_back_to_wall_time`
- `test_malformed_timings_are_skipped` (`True`, `-1`, `"40"`, `eval_duration 0`)
- `test_a_timeout_is_recorded_timed_out_and_reraised`
- `test_any_other_failure_is_recorded_failed_and_reraised`
- `test_a_payload_without_a_model_is_measured_as_unknown`
- `test_the_transport_satisfies_its_interfaces`
- `test_every_cli_ollama_client_is_measured` (the AST check)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure tests/cli tests/infrastructure/engines
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Resident memory (`gap-measure-models-2`); the model benchmark and catalogue evidence (gap D3,
  another writer's lane); qwenloop's in-run server timings (#382, already in its run directory).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): every local-model call records the model's tokens per second, load time and latency`. Do not push.

## Lane card
- **Depends on:** `gap-measure-ledger-sink`, `fakes-observability`.
- **Shares a file with:** `cli/main.py` (see `gap-measure-ticker`); rebase and keep others' code.
- **Must keep passing unchanged:** `tests/infrastructure/engines/test_ollama_chat.py`,
  `tests/cli/test_sovereign_provider_options.py`, the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
