## Title
feat(measure): the worker samples every measurement source on the [measure] period

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) asks for measurements "as it
works, continuously and in real time". Queue depth, a surface's call window and a model's
resident memory are not events anyone emits: they are sampled. `MeasurementSource` (lane
`gap-measure-port`) is that seam; this lane adds the one loop that collects every source on the
period `[measure] sample_seconds` (lane `gap-measure-config`, default 60) and records what it
collects through the process's `MeasurementPort`, and hosts it in `vibey worker`, the
long-running process (`src/vibey/cli/main.py:1418-1761`). A source that fails is recorded as a
failed measurement, never skipped in silence (7.c, `:82-91`), and never stops the other sources.

## Required behaviour
1. New `src/vibey/application/measurement_ticker.py`, `class MeasurementTicker`:
   `__init__(self, sources: Sequence[MeasurementSource], measurements: MeasurementPort, *,
   clock: Clock, interval_seconds: float, logger: Logger, instance: str = "",
   ids: Callable[[], UUID] = uuid4)`; `interval_seconds <= 0` raises
   `ValueError("a measurement period must be positive")`. Sources are kept as a tuple.
   - `async def tick(self) -> int`: for each source in order, `batch = await source.collect()`.
     If `collect` raises an `Exception` (the broad catch carries the comment "one broken source
     is recorded, and never silences the others"), record instead
     `Measurement(measurement_id=ids(), subject=MeasurementSubject(SubjectKind.LANE,
     f"measure-source:{source.name}"), outcome=MeasuredOutcome.FAILED, started_at=now,
     ended_at=now, instance=instance, detail=f"{type(exc).__name__}: {exc}"[:500])`. Every
     measurement of every batch is recorded with `await measurements.record(m)`. Returns how
     many were recorded. An exception from `measurements.record` propagates.
   - `async def run(self, stop: asyncio.Event) -> None`: until `stop` is set: `await self.tick()`
     (an `Exception` from it is passed to `logger.error("measurement tick failed",
     error=f"{type(exc).__name__}: {exc}")` and the loop goes on), then waits
     `asyncio.wait_for(stop.wait(), timeout=interval_seconds)`, treating `TimeoutError` as "tick
     again". It returns when `stop` is set.
2. `MeasurementTickerInterface` (`tick`, `run`) is appended to
   `src/vibey/application/interfaces/measurement.py` and exported;
   `tests/fakes/registry.py` `EXEMPT` gains `MeasurementTickerInterface: ExemptReason.CLASS_CONTRACT`.
3. `src/vibey/bootstrap.py`: `AppResources` gains
   `measurement_sources: tuple[MeasurementSource, ...] = ()` after `measure`; `build_app` passes
   `measurement_sources=()` (later lanes add their sources there). `bootstrap_interface.py` gains
   `@property def measurement_sources(self) -> tuple[MeasurementSource, ...]: ...`.
4. `vibey worker` (`src/vibey/cli/main.py`, inside `run_worker`):
   - after `await notifier.connect()` (`:1714`), build
     `worker_sources: list[MeasurementSource] = []` (worker-only sources; later lanes append),
     then
     ```python
     measure_stop = asyncio.Event()
     ticker = MeasurementTicker(
         (*resources.measurement_sources, *worker_sources),
         resources.measurements,
         clock=resources.clock,
         interval_seconds=float(resources.measure.sample_seconds),
         logger=StructlogAppLogger(component="measure-ticker"),
         instance=platform.node(),
     )
     ticker_task = asyncio.create_task(ticker.run(measure_stop))
     ```
   - in the existing `finally:` (`:1757-1758`), before `await notifier.close()`:
     `measure_stop.set()` then `await ticker_task`.
   `StructlogAppLogger` is `src/vibey/infrastructure/logging.py:224`.

## Where to change
- New `src/vibey/application/measurement_ticker.py`; `src/vibey/application/interfaces/measurement.py`,
  `src/vibey/application/interfaces/__init__.py`; `tests/fakes/registry.py` (one line).
- `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`, `src/vibey/cli/main.py` (all with
  `edit_file`; `main.py` is 1761 lines and arms a SIGTERM latch before its imports, so put new
  imports inside `worker` beside `:1464-1469`, never at the top).
- New `tests/application/test_measurement_ticker.py`.

## Acceptance criteria
- [ ] Two `ScriptedMeasurementSource`s (`tests/fakes/measurement.py`), the first raising
      `RuntimeError("down")`, the second yielding two measurements: `tick()` returns 3 and
      `InMemoryMeasurements` holds one `LANE` `failed` measurement named
      `measure-source:<first name>` with detail `"RuntimeError: down"`, then the two.
- [ ] `run(stop)` with a 0.01 s period ticks at least twice before `stop` is set, and returns.
- [ ] A sink that raises during `tick` inside `run` is logged through `RecordingLogger`
      (`tests/fakes/observability.py`) and the loop keeps ticking.
- [ ] An AST test finds, inside `worker` in `src/vibey/cli/main.py`, a `MeasurementTicker(` call
      and an `asyncio.create_task(` whose argument is a `.run(` call.
- [ ] 100% branch coverage of `src/vibey/application/` and `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/application/test_measurement_ticker.py`:
- `test_tick_records_every_batch_and_a_failure_for_a_broken_source`
- `test_a_failing_sink_reaches_the_caller_of_tick`
- `test_run_ticks_until_stopped`
- `test_run_logs_a_failed_tick_and_goes_on`
- `test_a_period_must_be_positive`
- `test_the_ticker_satisfies_its_interface`
- `test_the_worker_hosts_the_ticker` (the AST check above)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_measurement_ticker.py tests/cli tests/fakes tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Any source (`gap-measure-queue-sampler`, `gap-measure-queue-sampler-rmq`,
  `gap-measure-surfaces-2`, `gap-measure-models-2`); hosting in the loop services or the surface
  lane host (ADR-0046, ADR-0047 lanes).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): the worker samples every measurement source on the [measure] period`. Do not push.

## Lane card
- **Depends on:** `gap-measure-port`, `gap-measure-config`, `gap-measure-ledger-sink`,
  `fakes-observability`.
- **Shares a file with:** `cli/main.py` and `bootstrap.py` (R02, R17, R27, R28, R33, T15 edit
  other parts); rebase and keep their code.
- **Must keep passing unchanged:** `tests/cli/test_operational_commands.py`, `tests/cli/test_main.py`,
  the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
