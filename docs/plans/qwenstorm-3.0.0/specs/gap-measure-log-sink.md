## Title
feat(measure): a process without a database records measurements to the family measurement log

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) leaves no component unmeasured,
and some of vibey's own processes have no database: the test harness instance runs pytest from a
file store (ADR-0045 §3, `specs/test-harness-lanes.md` T10) and a hook runs before any worker.
They need a `MeasurementPort` (lane `gap-measure-port`) that does not touch PostgreSQL and loses
nothing. The family already has that store: vibey-gh's append-only, digest-chained measurement
log (lane `gap-measure-gh-1`, `vibey_gh.measurement_log.MeasurementLog`), whose payload is
exactly vibey's `vibey.measurement/1` encoding. Family first (10.e, `:417`): vibey writes through
it rather than a second log writer, and `vibey measure ingest` (lanes `gap-measure-log-ingest`,
`gap-measure-cli`) later moves what it holds into the ledger (7.c). vibey's domain may import
vibey-gh (dependency-free); this is infrastructure, so it may too.

## Required behaviour
1. New `src/vibey/infrastructure/measure/log_sink.py`, `class JsonlMeasurementSink`:
   `__init__(self, path: Path, *, log: MeasurementLogInterface | None = None,
   codec: MeasurementCodecInterface = MEASUREMENT_CODEC)`; `log` defaults to
   `vibey_gh.measurement_log.MeasurementLog()`; `path` property.
   `async def record(self, measurement: Measurement) -> None`:
   - a measurement with a `scope` raises `ValueError("a measurement log keeps no project scope;
     record scoped measurements through the ledger sink")` and writes nothing — a log cannot
     carry the event columns a scope becomes, and dropping it silently would misfile the
     measurement;
   - otherwise `payload = self._codec.encode(measurement)` (unrecognized values are refused
     there) and `await asyncio.to_thread(self._log.append, payload, self._path)`; the log's own
     errors propagate.
2. New `src/vibey/infrastructure/measure/interfaces/log_sink_interface.py`:
   `JsonlMeasurementSinkInterface` (`path`, `record`).
3. A contract test proves the two sides agree on the format: a measurement per `SubjectKind`
   carrying every `Metric`, recorded through this sink into a real `MeasurementLog` on
   `tmp_path`, reads back with `MeasurementLog().read(path)` and each envelope's `payload`
   decodes with `MEASUREMENT_CODEC.decode` to the original measurement.

## Where to change
- New `src/vibey/infrastructure/measure/log_sink.py` and its interface file.
- New `tests/infrastructure/measure/test_log_sink.py`.

## Acceptance criteria
- [ ] The contract test above passes for all six subject kinds.
- [ ] Recording the same measurement twice leaves one record (the log is idempotent by id).
- [ ] A scoped measurement raises `ValueError` and the file is not created.
- [ ] A log double that raises `OSError` on `append` (a plain class, not a mock) makes `record`
      raise it.
- [ ] `isinstance(JsonlMeasurementSink(tmp_path / "m.jsonl"), MeasurementPort)`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_log_sink.py`:
- `test_the_log_and_the_codec_agree_on_every_kind_and_metric` (parametrized over `SubjectKind`)
- `test_recording_twice_keeps_one_record`
- `test_a_scoped_measurement_is_refused`
- `test_a_log_failure_reaches_the_caller`
- `test_the_sink_satisfies_its_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Which process uses it (`gap-measure-test-runs`); ingesting the log (`gap-measure-log-ingest`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): a process without a database records measurements to the family measurement log`. Do not push.

## Lane card
- **Depends on:** `gap-measure-port`, `gap-measure-gh-1`, `gap-measure-ledger-sink` (the
  `infrastructure/measure/` package).
- **Must keep passing unchanged:** every vibey-gh test and the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
