## Title
feat(rotation): derive each engine's evidence factor from its measured runs, and ledger every change as `WeightsDerived`

## Why
8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) requires rotation weights to be "chosen from
live evidence" and each derivation to be published with its evidence. 7.c (`:82-91`) requires it
written as it happens. The evidence exists after D1:
- `gap-measure-engine-runs-1` records, per engine run, a `MeasurementRecorded` event with
  subject `SubjectKind.LOOP` named by the engine id;
- the outcome is `ok`, `failed`, `rejected` or `cancelled`;
- the reading `LATENCY_SECONDS`;
- `MEASUREMENT_CODEC` decodes it (`gap-measure-domain`).

`gap-rotation-derived-weights-1` has the pure rule, and `-2` the declared band. This lane joins
them. **A capacity rejection is never a failure sample**: `rejected` and `cancelled` are
excluded. Credits are not a rate limit, and neither is evidence of quality.

## Required behaviour
1. New `src/vibey/application/evidence_weights.py`, with a `class EvidenceWeightsDeriver`:
   - `__init__(self, *, ledger: LedgerReader, recorder: BuildLedger, config: EvidenceConfig, clock: Clock, weighting: EvidenceWeightingInterface = EVIDENCE_WEIGHTING)`.
     `BuildLedger` is the port `run_and_record` already writes through (`build_engine_run.py`);
     `LedgerReader` is at `application/interfaces/ledger.py:124-128`.
   - `async def factors(self, project_id: UUID, engines: Sequence[EngineId]) -> Mapping[EngineId, float]`:
     - When `config.enabled` is false, return 1.0 for each engine.
     - Read `await ledger.all_for_project(project_id)`. Keep interpretable events of kind
       `MEASUREMENT_RECORDED`, decode each with `MEASUREMENT_CODEC.decode(event.payload)`, and
       skip a `MalformedMeasurement` with a log line, not an error.
     - Keep measurements whose subject is `(LOOP, engine.value)` for an engine in `engines`.
       Per engine, take the last `config.window` of them in ledger order.
     - `EngineEvidence(engine, successes=#ok, failures=#failed, median_latency_s=median(LATENCY_SECONDS of ok runs) or None)`.
     - `result = weighting.factors(evidence)`, with the weighting built from `config.band()`.
       Construct `EvidenceWeighting(config.band())` when the default is injected.
     - Find the last `WEIGHTS_DERIVED` event in the same read. If its `payload["factors"]`
       differs from `{e.value: f for e, f in result.items()}`, append a new `WeightsDerived`
       event through `recorder.record(...)`, with engine id None and the payload
       `{"factors": {...}, "evidence": {engine: {"successes", "failures", "median_latency_s", "samples"}}, "band": {...}, "window": config.window}`.
       This is append-only, and there is no event when nothing changed.
     - Return `result`.
2. Add `EvidenceWeightsDeriverInterface` to `application/interfaces/engines.py`, in its
   existing style (`engines.py:113-120` explains the family grouping), and export it. Exempt it
   in `tests/fakes/registry.py` as `CLASS_CONTRACT`, or register a fake
   `FixedEvidenceWeights(factors)` in `tests/fakes/engines.py`. Register the fake: the selector lane (`-4`) uses it.

## Where to change
- New `src/vibey/application/evidence_weights.py`.
- `src/vibey/application/interfaces/engines.py` and `__init__.py` (the interface and export).
- `tests/fakes/engines.py` (`FixedEvidenceWeights`) and `tests/fakes/registry.py`.
- New `tests/application/test_evidence_weights.py`, which uses the in-memory ledger from
  `fakes-ledger` and `InMemoryMeasurements`-shaped events built with `MEASUREMENT_CODEC.encode`.

## Acceptance criteria
- [ ] Two engines with 25 measured `ok` runs each, at median latencies 10 s and 20 s, give the
      factors from `-1`'s worked example (1.2247 and 0.866), and write one `WeightsDerived`.
- [ ] A second call over the same ledger writes nothing more.
- [ ] `rejected` and `cancelled` runs change no count.
- [ ] With the window 5, only the last 5 runs per engine count.
- [ ] `enabled=false` gives all 1.0, and writes and reads nothing (a ledger double that raises proves the no-read).
- [ ] A malformed measurement payload is skipped.
- [ ] 100% branch coverage of `src/vibey/application/*`.

## Tests to write first (TDD)
`tests/application/test_evidence_weights.py`:
- `test_factors_follow_measured_latency`
- `test_unchanged_factors_write_no_event`
- `test_capacity_rejections_are_not_failures`
- `test_window_limits_the_samples`
- `test_disabled_reads_nothing`
- `test_malformed_measurement_is_skipped`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Applying the factors in selection (`-4`), fleet-wide rather than per-project evidence (a follow-up), and docs.

Commit as `feat(rotation): derive evidence factors from measured runs`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
