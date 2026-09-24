## Title
feat(measure): a pure measurement vocabulary, its codec, and the MeasurementRecorded ledger kind

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): "Every loop, lane, queue,
surface, test run and model records its latency, throughput, queue depth and waiting time,
resource use and outcome … Measurements join the ledger (7.c) and are published with the
decisions they drive (10.f)." 7.c (`:82-91`) names "measurement (8.g)" among what the ledger
holds. Today there is no measurement vocabulary at all:
- `EventKind` has no measurement kind (`src/vibey/domain/ledger.py:37-70`);
- `TelemetryMetrics` is five in-process dictionaries, never ledgered and never OpenTelemetry
  (`src/vibey/infrastructure/otel.py:170-218`).

This lane adds the pure value types every later `gap-measure-*` lane records, the codec that turns
one into a ledger payload and back, and the event kind. Readers are forward compatible and
writers strict, exactly as `domain/stored_value.py:1-27` and `ledger.py:6-14` require (#275,
#287). No I/O, no clock, no async: `tests/domain/test_domain_purity.py` walks the AST.

## Required behaviour
All in the new `src/vibey/domain/measurement.py` unless stated.
1. Constants: `MEASUREMENT_SCHEMA: Final = "vibey.measurement/1"`;
   `FLEET_PROJECT_ID: Final = UUID("c457a9aa-2389-5143-b499-7330040326c8")` with the comment
   "uuid5(NAMESPACE_URL, 'https://the-vibey-project.github.io/vibey/fleet-ledger'): the default
   of `[measure] fleet_project_id`, the ledger that holds measurements no one project owns";
   `MAX_NAME_CHARS: Final = 200`, `MAX_DETAIL_CHARS: Final = 500`, `MAX_READINGS: Final = 64`.
2. Three closed vocabularies (`StrEnum`), each with an `Unrecognized*` subclass of
   `UnrecognizedValue` and a shared parser, copying `Provenance`/`UnrecognizedProvenance`/
   `PROVENANCE_PARSER` (`ledger.py:152-177`):
   - `SubjectKind`: `LOOP="loop"`, `LANE="lane"`, `QUEUE="queue"`, `SURFACE="surface"`,
     `TEST_RUN="test_run"`, `MODEL="model"`; `UnrecognizedSubjectKind`; `SUBJECT_KIND_PARSER`;
     `type StoredSubjectKind = SubjectKind | UnrecognizedSubjectKind`.
   - `Metric`: `LATENCY_SECONDS="latency_seconds"`, `LATENCY_P50_SECONDS="latency_p50_seconds"`,
     `LATENCY_P95_SECONDS="latency_p95_seconds"`, `LATENCY_P99_SECONDS="latency_p99_seconds"`,
     `LATENCY_MAX_SECONDS="latency_max_seconds"`, `COUNT="count"`, `ERRORS="errors"`,
     `THROUGHPUT_PER_SECOND="throughput_per_second"`, `DEPTH="depth"`,
     `WAIT_SECONDS="wait_seconds"`, `OLDEST_AGE_SECONDS="oldest_age_seconds"`, `TURNS="turns"`,
     `INPUT_TOKENS="input_tokens"`, `OUTPUT_TOKENS="output_tokens"`,
     `TOKENS_PER_SECOND="tokens_per_second"`, `PROMPT_TOKENS_PER_SECOND="prompt_tokens_per_second"`,
     `LOAD_SECONDS="load_seconds"`, `MEMORY_BYTES="memory_bytes"`, `VRAM_BYTES="vram_bytes"`,
     `CPU_LOAD_1M="cpu_load_1m"`, `COST_USD="cost_usd"`; `UnrecognizedMetric`; `METRIC_PARSER`;
     `type StoredMetric = Metric | UnrecognizedMetric`.
   - `MeasuredOutcome`: `OK="ok"`, `FAILED="failed"`, `REJECTED="rejected"`,
     `TIMED_OUT="timed_out"`, `CANCELLED="cancelled"`, `SAMPLED="sampled"`;
     `UnrecognizedMeasuredOutcome`; `OUTCOME_PARSER`; `type StoredMeasuredOutcome = ...`.
3. `class MalformedMeasurement(VibeyError)` with the comment copied from
   `publication_policy.py:167-172` ("An exception type, so it has no interface beside it …").
4. Frozen, slotted dataclasses (each `__post_init__` raises `ValueError` on a violation):
   - `MeasurementSubject(kind: StoredSubjectKind, name: str)`: `name.strip()` non-empty, at
     most `MAX_NAME_CHARS`, and no character below `" "`.
   - `Reading(metric: StoredMetric, value: float)`: `value` is an `int` or `float` and not a
     `bool`, finite and `>= 0`; stored as `float(value)` via `object.__setattr__`.
   - `MeasurementScope(project_id: UUID, cycle: int, phase: Phase, job_id: UUID | None = None)`:
     `cycle >= 1`.
   - `Measurement(measurement_id: UUID, subject: MeasurementSubject, outcome: StoredMeasuredOutcome,
     started_at: datetime, ended_at: datetime, readings: tuple[Reading, ...] = (),
     instance: str = "", detail: str = "", causation_id: UUID | None = None,
     scope: MeasurementScope | None = None)`:
     - both datetimes timezone-aware (`tzinfo` set and `utcoffset()` not None), else
       `"a measurement's times must be timezone-aware"`;
     - `ended_at >= started_at`, else `"a measurement cannot end before it starts"`;
     - at most `MAX_READINGS`; a metric read twice raises `f"metric {metric} is read twice"`;
     - `instance` at most `MAX_NAME_CHARS` with no character below `" "`; `detail` at most
       `MAX_DETAIL_CHARS`;
     - `readings` is re-stored sorted by `str(reading.metric)`;
     - property `duration_seconds -> float`; method `reading(self, metric: Metric) -> float | None`
       (matched by identity, `r.metric is metric`).
5. `class LatencySummary` with `readings(self, samples: Sequence[float], *, errors: int,
   window_seconds: float) -> tuple[Reading, ...]`: `ValueError` for `errors < 0` or
   `window_seconds < 0`. Always `COUNT=len(samples)` and `ERRORS=errors`;
   `THROUGHPUT_PER_SECOND=len(samples)/window_seconds` only when `window_seconds > 0`; when there
   are samples, `LATENCY_P50/P95/P99/MAX_SECONDS` by nearest rank (`s = sorted(samples)`,
   `rank = max(1, math.ceil(p * len(s)))`, value `s[rank - 1]`). `LATENCY_SUMMARY: Final[LatencySummaryInterface] = LatencySummary()`.
6. `class MeasurementCodec`, `MEASUREMENT_CODEC: Final[MeasurementCodecInterface] = MeasurementCodec()`:
   - `encode(self, measurement: Measurement) -> dict[str, object]` returns exactly
     `{"schema": MEASUREMENT_SCHEMA, "measurement_id": str(id), "subject": {"kind": kind.value,
     "name": name}, "instance": instance, "outcome": outcome.value, "started_at": iso,
     "ended_at": iso, "readings": {metric.value: value, …}, "detail": detail,
     "causation_id": str | None}` (`datetime.isoformat()`). The scope is never in the payload
     (it is the event's own columns). Writers are strict: an `Unrecognized*` kind, outcome or
     metric raises `ValueError(f"a writer names only values this vibey knows; {value!r} is not one")`.
   - `decode(self, payload: Mapping[str, object]) -> Measurement` (scope `None`):
     `schema` must be a `str` starting `"vibey.measurement/"`; required: `measurement_id`,
     `subject` (a mapping with `str` `kind` and `name`), `outcome`, `started_at`, `ended_at`
     (`datetime.fromisoformat`), `readings` (a mapping of `str` to `int`/`float`, not `bool`);
     optional: `instance`, `detail` (`str`, default `""`), `causation_id` (`None` or UUID text).
     Kind, outcome and metric go through their parsers, so unknown ones are kept as
     `Unrecognized*`. Unknown top-level keys are ignored (a newer writer's field, or the
     ledger's `_redactions`). Any missing or mistyped field, or any `ValueError` from the
     constructors, raises `MalformedMeasurement(f"measurement field {name!r}: {reason}")`.
7. `class MeasurementSeries` with `unique(self, measurements: Sequence[Measurement]) ->
   tuple[Measurement, ...]`: the first occurrence of each `measurement_id`, order kept (a log
   ingested twice is read once). `MEASUREMENT_SERIES: Final[MeasurementSeriesInterface] = MeasurementSeries()`.
8. `src/vibey/domain/ledger.py`: after `DELIVERY_ESTIMATE_RECORDED` (`:70`) add, with a one-line
   comment "A measurement (8.g); the payload is `domain/measurement.py`'s codec.",
   `MEASUREMENT_RECORDED = "MeasurementRecorded"`.
9. `src/vibey/domain/publication_policy.py`: in `DEFAULT_ALLOWLIST`, after the
   `DELIVERY_ESTIMATE_RECORDED` entry (`:113-126`), add
   `EventKind.MEASUREMENT_RECORDED: frozenset({"schema", "measurement_id", "subject", "outcome",
   "started_at", "ended_at", "readings", "causation_id"})`. `instance` (a host name) and
   `detail` are withheld; extend the docstring below the mapping by one sentence saying so.

## Where to change
- New `src/vibey/domain/measurement.py`; new `src/vibey/domain/interfaces/measurement_interface.py`
  declaring `MeasurementCodecInterface` (`encode`, `decode`), `LatencySummaryInterface`
  (`readings`), `MeasurementSeriesInterface` (`unique`), and property-only value contracts
  `MeasurementSubjectInterface`, `ReadingInterface`, `MeasurementScopeInterface`,
  `MeasurementInterface` (every field above, plus `duration_seconds` and `reading`). Import the
  concrete types under `TYPE_CHECKING` only (copy `domain/interfaces/ledger_interface.py`).
- `src/vibey/domain/ledger.py` (one member), `src/vibey/domain/publication_policy.py` (one entry,
  one docstring sentence). Use `edit_file`.
- New `tests/domain/test_measurement.py`.

## Acceptance criteria
- [ ] `EVENT_KIND_PARSER.parse("MeasurementRecorded") is EventKind.MEASUREMENT_RECORDED`.
- [ ] `encode(decode(p)) == p` for a payload per subject kind that carries every `Metric`.
- [ ] A payload naming kind `"satellite"`, outcome `"warped"` and metric `"joules"` decodes
      with `UnrecognizedSubjectKind("satellite")` etc., and `encode` of it raises `ValueError`.
- [ ] `PublicationPolicy().decide(event)` for a `MeasurementRecorded` event keeps `readings`
      and `subject` and drops `instance` and `detail`.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
`tests/domain/test_measurement.py`:
- `test_fleet_project_id_is_the_documented_uuid5`
- `test_every_subject_kind_round_trips_with_every_metric` (parametrized over `SubjectKind`)
- `test_decode_keeps_unknown_values_as_their_text`
- `test_encode_refuses_unrecognized_values`
- `test_decode_ignores_unknown_top_level_keys` (payload with `"_redactions": []` and `"future": 1`)
- `test_decode_rejects_malformed_payloads` (parametrized: no `measurement_id`; bad UUID; naive
  `started_at`; end before start; reading `-1`; reading `True`; reading `float("nan")`; schema
  `"other/1"`; `subject` a string; `readings` a list)
- `test_measurement_invariants` (parametrized: naive time, end before start, duplicate metric,
  65 readings, 501-char detail, empty name, `"\x07"` in name, 201-char instance)
- `test_readings_are_sorted_and_read_by_member`
- `test_scope_requires_a_positive_cycle`
- `test_latency_summary_nearest_rank` (samples 0.1…1.0, `errors=2`, `window_seconds=5` → count 10,
  errors 2, throughput 2.0, p50 0.5, p95 1.0, p99 1.0, max 1.0)
- `test_latency_summary_without_samples_reports_counts_only` and
  `test_latency_summary_refuses_negative_inputs`
- `test_series_unique_keeps_the_first_of_each_id`
- `test_measurement_recorded_is_a_known_event_kind`
- `test_publication_keeps_the_measurement_and_withholds_instance_and_detail`
- `test_codec_summary_and_series_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/infrastructure/ledger
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any port, sink, sampler or CLI (the later `gap-measure-*` lanes); `[measure]` keys
  (`gap-measure-config`); `TelemetryMetrics` in `otel.py`, which stays as it is.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): a pure measurement vocabulary, its codec, and the MeasurementRecorded ledger kind`. Do not push.

## Lane card
- **Depends on:** none.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/domain/test_ledger.py`, `test_ledger_chain.py`,
  `test_ledger_query.py`, `test_forward_compatible_readers.py`, `test_publication_policy.py`,
  `tests/infrastructure/ledger/test_unrecognized_kinds_property.py` and the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
