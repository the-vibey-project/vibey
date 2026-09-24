## Title
feat(loops): sovereignloop's residency schedule uses measured bounds and ledgers each change

## Why
`gap-residency-tuning-1` added the pure rule. ADR-0046's lane (placeholder `loops-residency`)
adds `ResidencySchedule`, with configured `residency_max_wait_seconds` and
`residency_min_hold_runs` (`specs/ADR-two-loops.md:201-205`). 8.g
(`src/vibey_tools/gh/docs/doctrines.md:316-324`) requires those bounds from live evidence, with
each derivation published. The model measurements come from `gap-measure-models-1`
(`SubjectKind.MODEL`, readings `LOAD_SECONDS` and `LATENCY_SECONDS`).

This lane's anchors are in code that another lane writes. **Read `loops-residency`'s landed
`ResidencySchedule` first.** Every name below is from ADR-0046 §4 and §10. If the landed code
differs, map by meaning and write the mapping in the commit body. If `ResidencySchedule` does
not read its bounds from one place per decision, stop and report BLOCKED.

## Required behaviour
1. `ResidencySchedule` (in `src/vibey/infrastructure/loop_service/resident_schedule.py`,
   ADR-0046 §10) gains a constructor keyword
   `tuner: ResidencyBoundsSourceInterface | None = None`. `None` keeps the configured bounds.
2. New `src/vibey/application/residency_bounds.py`, with `class MeasuredResidencyBounds`
   implementing `ResidencyBoundsSourceInterface` (declared beside it in
   `application/interfaces/loops.py`, or wherever ADR-0046 put its loop ports):
   - `__init__(self, *, measurements: MeasurementQueryInterface, recorder: MeasurementPort | BuildLedger, tuning: ResidencyTuningInterface = RESIDENCY_TUNING, defaults: ResidencyBounds)`.
     If D1 left no query port over recorded measurements, read the fleet ledger with
     `LedgerReader` and `MEASUREMENT_CODEC`, as `gap-rotation-derived-weights-3` does.
   - `async def bounds(self, model: str) -> ResidencyBounds`: collect `LOAD_SECONDS` and
     `LATENCY_SECONDS` from `MODEL` measurements named `model`, call `tuning.bounds(...)`, and,
     when the result differs from the last one it returned for `model`, write one
     `ResidencyTuned` event with payload `{"model", "bounds", "defaults", "samples"}`.
3. At each switch decision, the schedule asks `await tuner.bounds(resident_model)` before
   comparing wait and hold. The configured values become the `defaults`.

## Where to change
- The landed `resident_schedule.py` (edit_file), the new `application/residency_bounds.py`, and
  the loop interfaces module (the new Protocol).
- Tests: append to the schedule's test file, with an in-memory measurements double and the in-memory ledger.

## Acceptance criteria
- [ ] With 5 recorded loads of 30 s and runs of 10 s for the resident model, a waiting seat is
      switched to only after `max(120, 600)` s and 3 finished runs, not after the configured 900 s and 1 run.
- [ ] With no measurements, today's configured bounds hold exactly.
- [ ] One `ResidencyTuned` event per change, and none when nothing changed.
- [ ] 100% branch coverage in the layers touched.

## Tests to write first (TDD)
- `test_measured_bounds_replace_the_defaults_at_a_switch`
- `test_without_measurements_the_configured_bounds_hold`
- `test_a_change_is_ledgered_once`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Changing the residency order (ADR-0046 §4's rules 1–4), and docs.

Commit as `feat(loops): residency bounds follow measured load times`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
