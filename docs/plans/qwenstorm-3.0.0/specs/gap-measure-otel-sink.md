## Title
feat(measure): measurements also reach the family's telemetry, composed beside the ledger sink

## Why
Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`): "if a capability exists inside
this family, the family's is used". vibey's own "OpenTelemetry" module is five in-process
dictionaries (`src/vibey/infrastructure/otel.py:170-218`) that no exporter ever reads. The family
already ships what a live operator reads: `vibey_bootstrap.tracing.latency` (per-operation
latency histograms, `_record_latency`, `src/vibey_tools/bootstrap/vibey_bootstrap/tracing/latency.py:42-61`,
exported from `vibey_bootstrap.tracing` `__all__`), `vibey_bootstrap.counters.bump_counter`
(`counters/__init__.py:19-27`), both surfaced by `vibey_bootstrap.metrics.build_metrics_snapshot`
(`metrics/__init__.py:16-40`), and OpenTelemetry spans through `TelemetryManager.create_span`
(`services/telemetry.py:206-212`), which returns a span only when the family's telemetry is
configured. This lane adds a `MeasurementPort` sink over those three and composes it after the
ledger sink (lane `gap-measure-ledger-sink`) through `MeasurementFanOut` (lane `gap-measure-port`),
so the ledger always receives a measurement first (7.c).

Spans are opt-in (`[measure] family_spans`, default `false`, lane `gap-measure-config`):
importing `vibey_bootstrap.services.telemetry` logs a warning when the `vibey[azure]` extra is
absent (`services/telemetry.py:17-25`), and only that extra carries OpenTelemetry
(`pyproject.toml` `[project.optional-dependencies] azure`).

## Required behaviour
1. New `src/vibey/infrastructure/measure/interfaces/family_telemetry_sink_interface.py`:
   - `class LatencyRecorderInterface(Protocol)`: `def __call__(self, operation: str, seconds:
     float, *, error: bool, slow: bool) -> None: ...` (the shape of `_record_latency`);
   - `class CounterInterface(Protocol)`: `def __call__(self, name: str, n: int = 1) -> None: ...`
     (the shape of `bump_counter`);
   - `@runtime_checkable class SpanFactoryInterface(Protocol)`: `def create_span(self, name: str,
     attributes: dict[str, Any] | None = None) -> Any: ...` (what `TelemetryManager` offers);
   - `@runtime_checkable class FamilyTelemetrySinkInterface(Protocol)`: `async def record(self,
     measurement: Measurement) -> None: ...`.
2. New `src/vibey/infrastructure/measure/family_telemetry_sink.py`,
   `class FamilyTelemetryMeasurementSink`:
   `__init__(self, *, latency: LatencyRecorderInterface = _record_latency, counter:
   CounterInterface = bump_counter, spans: SpanFactoryInterface | None = None)` — imports
   `from vibey_bootstrap.tracing import _record_latency` and
   `from vibey_bootstrap.counters import bump_counter`.
   `async def record(self, measurement)`:
   - `base = f"vibey.measure.{measurement.subject.kind}.{measurement.subject.name}"`;
   - `failed = measurement.outcome in (MeasuredOutcome.FAILED, MeasuredOutcome.TIMED_OUT,
     MeasuredOutcome.REJECTED)`;
   - for each reading whose metric's text ends in `"_seconds"`:
     `self._latency(f"{base}.{reading.metric}", reading.value, error=failed, slow=False)`;
   - `self._counter(f"{base}.outcome.{measurement.outcome}", 1)`;
   - when `self._spans` is set: `span = self._spans.create_span(f"vibey.measure.{kind}",
     attributes={"vibey.measurement_id": str(id), "vibey.subject.kind": str(kind),
     "vibey.subject.name": name, "vibey.instance": instance, "vibey.outcome": str(outcome),
     **{f"vibey.reading.{r.metric}": r.value for r in readings}})`; if `span is not None`,
     `span.end()`.
   It never raises for an unrecognized kind, outcome or metric: it uses their text.
3. `src/vibey/bootstrap.py` `build_app`: the `measurements` built by lane `gap-measure-ledger-sink`
   becomes
   ```python
   ledger_sink = LedgerMeasurementSink(
       ledger, FleetLedgerProject(orm, project_id=measure.fleet_project_id)
   )
   measurements: MeasurementPort = ledger_sink
   if measure.family_telemetry:
       spans: SpanFactoryInterface | None = None
       if measure.family_spans:
           from vibey_bootstrap.services.telemetry import telemetry_manager

           spans = telemetry_manager
       measurements = MeasurementFanOut((ledger_sink, FamilyTelemetryMeasurementSink(spans=spans)))
   ```
   The local import carries the comment "imported only when spans are asked for: the module
   warns at import without the vibey[azure] extra".

## Where to change
- New `src/vibey/infrastructure/measure/family_telemetry_sink.py` and its interface file.
- `src/vibey/bootstrap.py` (`edit_file` only).
- New `tests/infrastructure/measure/test_family_telemetry_sink.py`.

## Acceptance criteria
- [ ] With recording doubles (plain classes with `__call__` / `create_span`, no mocks), a
      measurement with readings `latency_seconds=1.5`, `wait_seconds=0.5`, `depth=3` and outcome
      `failed` records two latencies (both `error=True`), one counter
      `vibey.measure.queue.<name>.outcome.failed`, and one ended span with every attribute.
- [ ] With the real family functions, after `record`, `vibey_bootstrap.tracing.latency_snapshot()`
      has the operation and `vibey_bootstrap.counters.counter_snapshot()` the counter (use a
      subject name unique to the test, e.g. with `uuid4().hex`).
- [ ] `create_span` returning `None` (telemetry not configured) is not an error.
- [ ] `build_app` composes `MeasurementFanOut` with the ledger sink first when
      `family_telemetry` is on, and the bare ledger sink when it is off (integration).
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_family_telemetry_sink.py`:
- `test_seconds_readings_become_family_latencies`
- `test_the_outcome_is_counted`
- `test_a_configured_span_factory_gets_one_ended_span`
- `test_an_unconfigured_span_factory_is_ignored`
- `test_unrecognized_values_are_recorded_by_their_text`
- `test_the_real_family_registries_see_the_measurement`
- `test_the_sink_satisfies_its_interfaces`
- `test_build_app_puts_the_ledger_sink_first` (`@pytest.mark.integration`; with
  `VIBEY_MEASURE_FAMILY_TELEMETRY=false` set by `monkeypatch.setenv` and no `vibey.toml` in
  `tmp_path` (`monkeypatch.chdir`), `resources.measurements` is the bare `LedgerMeasurementSink`;
  without it, a `MeasurementFanOut` whose `sinks[0]` is the ledger sink)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure -m integration
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Configuring the family telemetry (`TelemetryManager.configure` reformats the root logger's
  handlers, `services/telemetry.py:167-200`; vibey never calls it here); a vendor-neutral OTLP
  exporter in `vibey_bootstrap` (a family capability gap, flagged for the operator);
  `infrastructure/otel.py`, which is unchanged.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): measurements also reach the family's telemetry, composed beside the ledger sink`. Do not push.

## Lane card
- **Depends on:** `gap-measure-ledger-sink`.
- **Must keep passing unchanged:** `tests/test_bootstrap.py`, `tests/infrastructure/test_otel.py`
  and the protected tests. Substitution is by constructor keyword only (9.b).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
