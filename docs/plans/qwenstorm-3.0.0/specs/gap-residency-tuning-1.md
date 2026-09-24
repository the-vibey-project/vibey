## Title
feat(domain): residency hold and switch bounds tuned from measured model load and run times

## Why
ADR-0046 §4 (`specs/ADR-two-loops.md:193-222`) switches sovereignloop's resident model only
between runs. It switches when another seat's oldest request has waited
`residency_max_wait_seconds` (default 900) and at least `residency_min_hold_runs` (default 1)
runs have finished since the last switch. A switch costs a model load, "13–16 GB (tens of
seconds)" (`:434`). Both bounds are fixed defaults. 8.g
(`src/vibey_tools/gh/docs/doctrines.md:316-324`) names "model residency" among the settings
"chosen from live evidence, never from assumption" (`issue-audit/gaps.md` D2).

`gap-measure-models-1` records each local model call's `LOAD_SECONDS` and `LATENCY_SECONDS`.
This lane is the pure rule. `-2` wires it into ADR-0046's `ResidencySchedule`.

## Required behaviour
1. New pure module `src/vibey/domain/residency_tuning.py`:
   - `@dataclass(frozen=True, slots=True) class ResidencyBounds` with
     `max_wait_seconds: float` and `min_hold_runs: int`.
   - `@dataclass(frozen=True, slots=True) class ResidencyTuningBand` with fields:
     - `min_samples: int = 5`;
     - `wait_per_load: float = 20.0`: waiting up to 20 loads' worth before forcing a switch;
     - `wait_floor_seconds: float = 120.0`, `wait_ceiling_seconds: float = 3600.0`;
     - `hold_ceiling_runs: int = 10`.

     `__post_init__` requires positive values and `floor <= ceiling`.
   - `class ResidencyTuning` with `__init__(self, band: ResidencyTuningBand = ResidencyTuningBand())` and
     `bounds(self, *, load_seconds: Sequence[float], run_seconds: Sequence[float], defaults: ResidencyBounds) -> ResidencyBounds`:
     - If `len(load_seconds) < band.min_samples` or `len(run_seconds) < band.min_samples`,
       return `defaults` unchanged: no evidence, no change.
     - `load = median(load_seconds)`, `run = median(run_seconds)`, with each sample > 0
       (non-positive samples are dropped before counting).
     - `max_wait = clamp(band.wait_per_load * load, wait_floor_seconds, wait_ceiling_seconds)`.
     - `min_hold = clamp(ceil(load / run), 1, hold_ceiling_runs)`. When a load costs more than
       a run, hold for enough runs to repay it.
   - `RESIDENCY_TUNING: Final[ResidencyTuningInterface] = ResidencyTuning()`.
2. Interface `src/vibey/domain/interfaces/residency_tuning_interface.py` (`bounds`), exported.
3. `EventKind` gains `RESIDENCY_TUNED = "ResidencyTuned"`, appended last. `-2` writes it.

## Where to change
- New: `src/vibey/domain/residency_tuning.py` and its interface.
- `src/vibey/domain/interfaces/__init__.py` and `src/vibey/domain/ledger.py` (one member each).
- New test `tests/domain/test_residency_tuning.py`.

## Acceptance criteria
- [ ] With 5 loads of 30 s and 5 runs of 60 s, `bounds` is `(max_wait=600.0, min_hold=1)`.
- [ ] Loads of 30 s and runs of 10 s give `min_hold=3`.
- [ ] Loads of 1 s give `max_wait` clamped to 120. Loads of 400 s give it clamped to 3600.
- [ ] Four samples return the defaults unchanged.
- [ ] Non-positive samples are dropped before counting.
- [ ] Domain purity passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_residency_tuning.py`:
- `test_bounds_follow_measured_load_and_run`
- `test_hold_repays_an_expensive_load`
- `test_wait_is_clamped`
- `test_too_few_samples_keep_the_defaults`
- `test_non_positive_samples_are_ignored`
- `test_invalid_band_is_refused`
- `test_tuning_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The schedule itself (ADR-0046's `ResidencySchedule`), the wiring (`-2`), and docs.

Commit as `feat(domain): residency bounds from measured load and run times`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
