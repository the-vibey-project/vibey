## Title
feat(measure): every test-harness answer records its latency, wait, load and outcome for the ledger

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) names "test run" among what is
always measured, and 8.e runs the test harness as one queue-fed instance. Lane T04's records
(`specs/test-harness-lanes.md:567-711`) keep each attempt's evidence in the harness's own file
store (T10), "although these records are not the ledger" (T04 *Why*). This lane measures every
answer the instance gives — executed, reused, parked, saturated — at the one seam every backend
feeds, `HarnessInstanceInterface.handle` (T13, `specs/test-harness-lanes.md:1722-1895`), and
writes the measurement to the family measurement log beside the store (lane
`gap-measure-log-sink`), because the harness process has no database. `vibey measure ingest`
(lanes `gap-measure-log-ingest`, `gap-measure-cli`) then forwards it to the ledger (7.c).

## Required behaviour
1. New `src/vibey/infrastructure/test_harness/measuring_instance.py`,
   `class MeasuringHarnessInstance` (implements `HarnessInstanceInterface`):
   `__init__(self, inner: HarnessInstanceInterface, *, store: TestRunStoreInterface,
   measurements: MeasurementPort, clock: Clock, ids: Callable[[], UUID] = uuid4)`.
   - `async def abandon_current(self) -> None` delegates.
   - `async def handle(self, request: TestRunRequest, *, delivery_count: int = 0) -> TestRunResult`:
     `t0 = clock.now()`; `result = await inner.handle(request, delivery_count=delivery_count)`;
     `t1 = clock.now()`; records one measurement, then returns `result` unchanged:
     - subject `MeasurementSubject(SubjectKind.TEST_RUN, " ".join(request.selection.command))`,
       `instance=result.backend`, `started_at=t0`, `ended_at=t1`,
       `causation_id=result.run_id`, no scope;
     - readings: `LATENCY_SECONDS = (t1 - t0)`; `WAIT_SECONDS = max(0.0, (t0 -
       request.requested_at).total_seconds())`; and, when the status is `EXECUTED` and
       `result.key` is set, the attempt in `store.attempts(result.key)` whose `run_id ==
       result.run_id`: `CPU_LOAD_1M = record.load_after.load1` when `load_after` is set;
     - outcome by `result.status` (`AnswerStatus`, T03): `SATURATED` → `REJECTED`, detail
       `"saturated"`; `PARKED` → `REJECTED`, detail `"parked"`; `STILL_RUNNING` → `SAMPLED`,
       detail `"still running"`; `EXECUTED` and `REUSED` by `result.outcome` (`TestOutcome`,
       T01): `PASSED` → `OK`, `FAILED` and `CRASHED` → `FAILED`, `TIMED_OUT` → `TIMED_OUT`,
       `UNEXECUTABLE` → `REJECTED`, `ABANDONED` → `CANCELLED`, detail
       `f"{result.status.value}:{result.outcome.value}"` (e.g. `"reused:passed"`).
     - If `inner.handle` raises an `Exception`, record `FAILED` with detail
       `f"{type(exc).__name__}: {exc}"[:500]` (instance `""`, no causation), then re-raise.
2. New `src/vibey/infrastructure/test_harness/interfaces/measuring_instance_interface.py`:
   `MeasuringHarnessInstanceInterface` (`handle`, `abandon_current`).
3. `src/vibey/bootstrap.py`, `TestHarnessComposition.instance(backend)` (lane T15): it returns
   `MeasuringHarnessInstance(<the HarnessInstance it builds today>, store=self.store(),
   measurements=JsonlMeasurementSink(settings.state_dir / "measurements.jsonl"),
   clock=<the composition's clock>)`, and its return annotation becomes
   `HarnessInstanceInterface`. Nothing else in the composition changes.

## Where to change
- New `src/vibey/infrastructure/test_harness/measuring_instance.py` and its interface file.
- `src/vibey/bootstrap.py` (`edit_file`, `TestHarnessComposition.instance` only).
- New `tests/infrastructure/test_harness/test_measuring_instance.py`: the inner instance is a
  plain class returning scripted `TestRunResult`s (or raising); the store is
  `InMemoryTestRunStore` (`tests/fakes/harness_fakes.py`, lane `fakes-test-harness`), seeded with
  a finished `TestRunRecord` (T04) through `begin`/`finish`; measurements go to
  `InMemoryMeasurements`; time is `FakeClock`.
- Append one test to `tests/test_bootstrap.py`.

## Acceptance criteria
- [ ] An `EXECUTED`/`PASSED` answer 2 s after a request made 30 s earlier, whose attempt has
      `load_after.load1 == 1.5`, records `ok`, latency 2.0, wait 30.0, `cpu_load_1m` 1.5,
      detail `executed:passed`, caused by the run id, subject `uv run --no-sync pytest`.
- [ ] `REUSED`/`FAILED` is `failed` with detail `reused:failed` and no load reading.
- [ ] `SATURATED` and `PARKED` are `rejected`; `STILL_RUNNING` is `sampled`.
- [ ] A raising inner instance is recorded `failed` and re-raised; the result is otherwise
      returned unchanged in every case.
- [ ] `build_test_harness(None, environ).instance()` is a `MeasuringHarnessInstance` whose sink
      writes `<state_dir>/measurements.jsonl`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_measuring_instance.py`:
- `test_an_executed_run_records_latency_wait_and_load`
- `test_a_reused_answer_is_measured_by_its_outcome`
- `test_refusals_and_running_answers_are_measured` (parametrized over `SATURATED`, `PARKED`,
  `STILL_RUNNING`)
- `test_every_test_outcome_maps_to_a_measured_outcome` (parametrized over `TestOutcome`)
- `test_a_failing_instance_is_recorded_and_reraised`
- `test_abandon_is_delegated`
- `test_the_wrapper_satisfies_its_interfaces`

`tests/test_bootstrap.py` (append): `test_the_harness_instance_is_measured_into_its_state_dir`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/test_bootstrap.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Ingesting the log into the ledger (`gap-measure-log-ingest`, `gap-measure-cli`); the
  harness's own records, dead letters and store (T04, T10, unchanged).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): every test-harness answer records its latency, wait, load and outcome for the ledger`. Do not push.

## Lane card
- **Depends on:** `gap-measure-log-sink`, `harness-T04-test-run-records`,
  `harness-T13-harness-instance`, `harness-T15-test-run-cli`, `fakes-test-harness`.
- **Shares a file with:** `bootstrap.py` (T15's composition; rebase and keep its code).
- **Must keep passing unchanged:** every T-lane test and the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
