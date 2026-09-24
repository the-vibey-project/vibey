## Title
feat(measure): every BUILD engine run records its latency, turns, tokens, spend and outcome

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): every loop "records its
latency, throughput … resource use and outcome". Only qwenloop records per-turn timing today
(#382, `src/vibey_runners/qwen/src/qwenloop/application/runner.py:329-338`), inside its own run
directory; nothing reaches the ledger as a measurement, and no other engine records anything.
Every engine run vibey drives goes through one function, `run_and_record`
(`src/vibey/application/build_engine_run.py:70-159`), called by `build.implement`
(`build_implement_handler.py:232-239`) and `build.verify` (`build_verify_handler.py:256-263`). It
already sees every event: turns (`:112-113`), completion (`:114-115`) and capacity rejection
(`:116-120`). Every runner's `TurnCompleted` payload carries `input_tokens`, `output_tokens`,
`cost_usd` and `model` (claudeloop: `src/vibey_runners/claude/src/claudeloop/application/runner.py:545-555`;
qwenloop: `runner.py:329-330`). So one meter there measures every adapter.

"A capacity rejection always outranks a completion claim" (CLAUDE.md): a run that was rejected
and also claimed completion is measured `rejected`.

## Required behaviour
1. New `src/vibey/application/engine_run_meter.py`, `class EngineRunMeter`:
   - `__init__(self, *, engine_id: EngineId, started_at: datetime)`.
   - `observe(self, event: EngineEvent) -> None`: only `event.kind == EventKind.TURN_COMPLETED.value`
     counts. It adds 1 to turns; adds `input_tokens`, `output_tokens` and `cost_usd` when each is
     an `int` or `float`, not a `bool`, finite and `>= 0` (anything else is skipped); keeps the
     last non-empty `str` `model`.
   - `measurements(self, *, outcome: RunOutcomeInterface, job: JobRecord, run_id: UUID,
     ended_at: datetime, ids: Callable[[], UUID] = uuid4) -> tuple[Measurement, ...]`:
     - `job.phase` must be a `Phase` member, else `ValueError(f"job {job.id} is in phase
       {job.phase}, which this vibey does not know; it will not measure into it")`;
     - scope `MeasurementScope(job.project_id, job.cycle, job.phase, job.id)`,
       `causation_id=run_id` (the id the run's ledger rows already carry as causation,
       `build_engine_run.py:79-83`);
     - outcome, first match wins: `outcome.capacity_rejected` → `REJECTED`, detail
       `outcome.capacity_state or "capacity rejected"`; `outcome.complete` → `OK`, detail `""`;
       `outcome.exit_code == EXIT_CODE_WIND_DOWN` → `CANCELLED`, detail `"wind-down (exit 75)"`;
       else `FAILED`, detail `f"exit {outcome.exit_code}"` or `"incomplete"` when it is `None`;
     - the **loop** measurement: subject `MeasurementSubject(SubjectKind.LOOP, engine_id.value)`,
       readings `LATENCY_SECONDS = (ended_at - started_at).total_seconds()`, `TURNS`,
       `INPUT_TOKENS`, `OUTPUT_TOKENS`, plus `COST_USD` when any cost was seen and
       `TOKENS_PER_SECOND = output_tokens / latency` when both are `> 0`;
     - when a model name was seen, a second **model** measurement: subject
       `MeasurementSubject(SubjectKind.MODEL, model)`, the same outcome, times, scope and
       causation, readings `TURNS`, `INPUT_TOKENS`, `OUTPUT_TOKENS` and the same
       `TOKENS_PER_SECOND` rule, detail `f"via {engine_id.value}"`;
     - each gets `measurement_id=ids()`.
2. `EngineRunMeterInterface` (`observe`, `measurements`) is appended to
   `src/vibey/application/interfaces/measurement.py` (lane `gap-measure-port`) and exported from
   `application/interfaces/__init__.py`. `tests/fakes/registry.py` `EXEMPT` gains
   `EngineRunMeterInterface: ExemptReason.PURE_POLICY` (it does no I/O).
3. `run_and_record` (`build_engine_run.py:70-78`) gains two keyword parameters,
   `measurements: MeasurementPort | None = None` and `clock: Clock | None = None`:
   - `measurements` given without `clock` raises `ValueError("a measured run needs a clock")`
     before the tail starts;
   - with `measurements`, it builds `EngineRunMeter(engine_id=engine.descriptor.engine_id,
     started_at=clock.now())` before the `async for` (`:90`), calls `meter.observe(event)` for
     every event after the ledger write, and, once the `RunOutcome` is built (`:153-159`),
     awaits `measurements.record(m)` for each of `meter.measurements(outcome=outcome, job=job,
     run_id=handle.run_id, ended_at=clock.now())` before returning it;
   - without `measurements`, behaviour is exactly today's.

## Where to change
- New `src/vibey/application/engine_run_meter.py`.
- `src/vibey/application/build_engine_run.py` (`edit_file`), `src/vibey/application/interfaces/measurement.py`,
  `src/vibey/application/interfaces/__init__.py`, `tests/fakes/registry.py` (one `EXEMPT` line).
- New `tests/application/test_engine_run_meter.py`. Its engines are small plain classes like
  `tests/application/test_build_engine_run.py:17-68` (`descriptor = CLAUDELOOP`, an async `tail`);
  its measurements go to `InMemoryMeasurements` (`tests/fakes/measurement.py`), its clock is
  `FakeClock` (`tests/fakes/system.py`, lane `fakes-observability`), its ledger is
  `build_ledger(InMemoryLedger())` (lane `fakes-ledger`).

## Acceptance criteria
- [ ] Two `TurnCompleted` events carrying `input_tokens` 10/20, `output_tokens` 5/15, `cost_usd`
      0.01/0.02 and `model` `"claude-x"`, with the clock advanced 10 s, give a loop measurement
      with turns 2, input 30, output 20, cost 0.03, latency 10.0, tokens/s 2.0, and a model
      measurement named `claude-x`; both scoped to the job and caused by `handle.run_id`.
- [ ] A run that emits both `CapacityRejected` and a completing `VerdictRendered` is `rejected`.
- [ ] `run_and_record` without `measurements` records nothing and returns what it returns today
      (every test in `tests/application/test_build_engine_run.py` passes unchanged).
- [ ] 100% branch coverage of `src/vibey/application/`.

## Tests to write first (TDD)
`tests/application/test_engine_run_meter.py`:
- `test_a_completed_run_records_a_loop_and_a_model_measurement`
- `test_a_capacity_rejection_outranks_a_completion_claim`
- `test_a_wound_down_run_is_cancelled_and_any_other_exit_failed` (parametrized: exit 75, exit 1, `None`)
- `test_malformed_turn_payload_values_are_skipped` (`True`, `-1`, `"3"`, `float("inf")`)
- `test_no_model_seen_means_no_model_measurement`
- `test_an_unknown_job_phase_is_refused`
- `test_a_measured_run_without_a_clock_is_refused`
- `test_an_unmeasured_run_records_nothing`
- `test_the_meter_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_engine_run_meter.py tests/application/test_build_engine_run.py tests/application/test_build_implement_handler.py tests/application/test_build_verify_handler.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Passing the port from the handlers and the composition root (`gap-measure-engine-runs-2`);
  conformance probes (`application/conformance.py`), which run no job; the runners' own event
  vocabularies.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): every BUILD engine run records its latency, turns, tokens, spend and outcome`. Do not push.

## Lane card
- **Depends on:** `gap-measure-port`, `fakes-ledger`, `fakes-observability`.
- **Must keep passing unchanged:** `tests/application/test_build_engine_run.py`, both BUILD
  handler test files, the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
