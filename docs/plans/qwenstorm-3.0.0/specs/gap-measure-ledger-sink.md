## Title
feat(measure): measurements are appended to the ledger, in their project or in the fleet ledger

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): "Measurements join the ledger
(7.c)". 7.c (`:82-91`): the ledger holds "measurement (8.g) … with its time, its actor and its
evidence, written as it happens", append-only, redactions recorded. This lane implements
`MeasurementPort` (lane `gap-measure-port`) over the ledger's declared seam,
`LedgerRepositoryInterface` (lane `fakes-ledger`; the ORM append of lane `orm-ledger`), so the
append keeps today's contract: gapless per-project `seq`, redaction then digest before storage
(`src/vibey/infrastructure/db/ledger_repository.py:98-148`), append-only. A measurement with a
scope goes to its project's ledger under its job, cycle and phase; one without goes to the fleet
ledger project (lane `gap-measure-fleet-ledger`). The composition root then gives every process
one `MeasurementPort`.

## Required behaviour
1. New package `src/vibey/infrastructure/measure/` (`__init__.py` holding the provenance line and
   a one-line docstring "Measurement sinks and samplers (sub-doctrine 8.g)."; copy the style of
   `src/vibey/infrastructure/bus/__init__.py`) and `src/vibey/infrastructure/measure/interfaces/__init__.py`
   (the same, "The seams of the measurement sinks and samplers."). Add
   `    vibey.infrastructure.measure.interfaces` to `.importlinter`'s
   `infrastructure-interfaces-declare-only` `source_modules`, after
   `vibey.infrastructure.tracker.interfaces` (`.importlinter:129`).
2. New `src/vibey/infrastructure/measure/ledger_sink.py`, `class LedgerMeasurementSink`:
   `__init__(self, ledger: LedgerRepositoryInterface, fleet: FleetLedgerProjectInterface, *,
   codec: MeasurementCodecInterface = MEASUREMENT_CODEC,
   correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION)`.
   `async def record(self, measurement: Measurement) -> None`:
   - `payload = self._codec.encode(measurement)` first (it refuses unrecognized values, so a
     refused measurement appends nothing);
   - with a scope: `project_id, cycle, phase, job_id` from it; without: `project_id = await
     self._fleet.ensure()`, `cycle = 1`, `phase = Phase.DONE`, `job_id = None`;
   - `engine_id = ENGINE_ID_PARSER.known(measurement.subject.name)` when
     `measurement.subject.kind is SubjectKind.LOOP`, else `None`;
   - `await self._ledger.append(LedgerEventDraft(project_id=…, cycle=…, phase=…,
     kind=EventKind.MEASUREMENT_RECORDED, engine_id=engine_id, job_id=job_id,
     causation_id=measurement.causation_id,
     correlation_id=self._correlation.for_project(project_id).value,
     provenance=Provenance.TRUSTED, produced_at=measurement.ended_at, payload=payload,
     digest=digest_event(payload)))` — copy the draft shape of
     `src/vibey/infrastructure/db/project_repository.py:119-132`. `TRUSTED`: vibey measured
     it itself. Every exception propagates (never a silent omission).
3. New `src/vibey/infrastructure/measure/interfaces/ledger_sink_interface.py`:
   `@runtime_checkable class LedgerMeasurementSinkInterface(Protocol)` declaring
   `async def record(self, measurement: Measurement) -> None`.
4. `src/vibey/bootstrap.py`:
   - `AppResources` (`:133-171`) gains `measurements: MeasurementPort` placed immediately before
     `integration_lock` (`:171`), and `measure: MeasureConfig = MeasureConfig()` after it.
   - In `build_app`, immediately before `yield AppResources(` (`:916`):
     ```python
     measure = (
         resolved_config.measure
         if resolved_config is not None
         else load_measure_config(Path("vibey.toml"))
     )
     measurements: MeasurementPort = LedgerMeasurementSink(
         ledger, FleetLedgerProject(orm, project_id=measure.fleet_project_id)
     )
     ```
     and the yield passes `measurements=measurements, measure=measure`. (`orm` exists since
     lane `orm-app-resources`; `load_measure_config` is lane `gap-measure-config`'s.)
5. `src/vibey/bootstrap_interface.py` `AppResourcesInterface` (`:22-84`) gains
   `@property def measurements(self) -> MeasurementPort: ...` and
   `@property def measure(self) -> MeasureConfig: ...` (import `MeasurementPort` from
   `vibey.application.interfaces` as the file already does at `:14-18`, and `MeasureConfig`
   from `vibey.domain.config`), so `vibey measure` (lane `gap-measure-cli`) reads both through
   the interface.

## Where to change
- New `src/vibey/infrastructure/measure/__init__.py`, `…/measure/ledger_sink.py`,
  `…/measure/interfaces/__init__.py`, `…/measure/interfaces/ledger_sink_interface.py`.
- `.importlinter` (one line), `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`
  (`edit_file` only; `bootstrap.py` is 962 lines).
- New `tests/infrastructure/measure/__init__.py` (provenance line only) and
  `tests/infrastructure/measure/test_ledger_sink.py`.

## Acceptance criteria
- [ ] A scoped measurement is one `MeasurementRecorded` event in its project with its cycle,
      phase, job id, `causation_id`, `produced_at == ended_at`, provenance `trusted`, and a
      payload that `MEASUREMENT_CODEC.decode` turns back into the measurement (scope aside).
- [ ] An unscoped one lands under the fleet id, cycle 1, phase `done`, and the fleet was ensured.
- [ ] A `LOOP` subject named `claudeloop` carries `engine_id` `EngineId.CLAUDELOOP`; a `LOOP`
      named `nobody-loop` and any other kind carry `None`.
- [ ] A measurement with an unrecognized outcome raises `ValueError` and nothing is appended.
- [ ] With `build_app(url=dsn)`, `resources.measurements` records an unscoped measurement that
      `resources.ledger.all_for_project(resources.measure.fleet_project_id)` reads back.
- [ ] `uv run lint-imports` keeps every contract; 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_ledger_sink.py`, with `InMemoryLedger` (`tests/fakes/ledger.py`,
lane `fakes-ledger`) and `InMemoryFleetLedgerProject` (`tests/fakes/measurement.py`):
- `test_a_scoped_measurement_joins_its_projects_ledger`
- `test_an_unscoped_measurement_joins_the_fleet_ledger`
- `test_a_loop_subject_names_its_engine_and_nothing_else_does`
- `test_a_refused_measurement_appends_nothing`
- `test_a_ledger_failure_reaches_the_caller` (`InMemoryLedger.fail_next_append`)
- `test_a_fleet_failure_reaches_the_caller` (`InMemoryFleetLedgerProject.fail_next`)
- `test_the_sink_satisfies_its_interfaces` (`MeasurementPort`, `LedgerMeasurementSinkInterface`)
- `test_build_app_records_measurements_into_the_fleet_ledger` (`@pytest.mark.integration`,
  skipped when `VIBEY_TEST_DATABASE_URL` is unset; copy `_test_dsn` from
  `tests/infrastructure/test_cluster_preflight.py:34-38`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/infrastructure/measure -m integration
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The family telemetry sink and the fan-out composition (`gap-measure-otel-sink`); any producer
  of measurements; publication (the allowlist is `gap-measure-domain`'s).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): measurements are appended to the ledger, in their project or in the fleet ledger`. Do not push.

## Lane card
- **Depends on:** `gap-measure-port`, `gap-measure-config`, `gap-measure-fleet-ledger`,
  `orm-ledger`, `orm-app-resources`, `fakes-ledger`.
- **Shares a file with:** `bootstrap.py` / `bootstrap_interface.py` (the R02 → T15 → R17 → T25 →
  R27 → R28 → T26 chain and the `orm-*` lanes): rebase and keep their code; add fields only.
- **Must keep passing unchanged:** `tests/test_bootstrap.py`, `tests/infrastructure/db/test_ledger_repository.py`,
  the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
