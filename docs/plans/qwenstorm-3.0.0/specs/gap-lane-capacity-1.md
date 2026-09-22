## Title
feat(domain): a surface lane's read concurrency chosen from its measured read latency, within a declared band

## Why
ADR-0047 (`specs/ADR-surface-lanes.md:86`) says: "Capacity inside the instance is a key; the
instance count is not. Reads run concurrently up to `read_prefetch` (default 64)". That default
is fixed. 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) names "lane capacity" among the
settings "chosen from live evidence" (`issue-audit/gaps.md` D2). `gap-measure-surfaces-*`
records per-surface latency. This lane is the pure rule; `-2` wires it into the lane host
(placeholder `surfaces-lane-host`).

The rule is additive-increase, multiplicative-decrease against a latency target. It raises
concurrency while p95 read latency stays under target, and halves it when latency overshoots.
The write queue's prefetch stays 1: FIFO writes are what make replay safe (ADR-0047 §8), so
they are never tuned.

## Required behaviour
1. New pure module `src/vibey/domain/lane_capacity.py`:
   - `@dataclass(frozen=True, slots=True) class LaneCapacityBand` with:
     - `min_prefetch: int = 1`, `max_prefetch: int = 256`;
     - `target_p95_seconds: float = 0.050`;
     - `step: int = 8`;
     - `min_samples: int = 50`.

     Validation: positive values, and `min <= max`.
   - `class LaneCapacityTuning` with `__init__(self, band: LaneCapacityBand = LaneCapacityBand())` and
     `next_prefetch(self, *, current: int, read_latencies: Sequence[float]) -> int`:
     - Fewer than `min_samples` positive samples return `current`, clamped to the band.
     - `p95` is the nearest-rank 95th percentile of the positive samples.
     - `p95 <= target` gives `min(current + step, max_prefetch)`.
     - `p95 > target` gives `max(current // 2, min_prefetch)`.
   - `LANE_CAPACITY: Final[LaneCapacityTuningInterface] = LaneCapacityTuning()`.
2. Interface `src/vibey/domain/interfaces/lane_capacity_interface.py`, exported.
3. `EventKind` gains `LANE_CAPACITY_CHANGED = "LaneCapacityChanged"`, appended last.

## Where to change
- New: `src/vibey/domain/lane_capacity.py` and its interface.
- `src/vibey/domain/interfaces/__init__.py` and `src/vibey/domain/ledger.py`.
- New test `tests/domain/test_lane_capacity.py`.

## Acceptance criteria
- [ ] With `current=64` and 50 samples at 0.01 s, the result is 72. At 0.2 s it is 32.
- [ ] At the ceiling the result stays 256, and at the floor it stays 1.
- [ ] 49 samples return `current`. `current=999` with too few samples returns 256.
- [ ] The nearest-rank p95 is pinned on a known 20-sample list.
- [ ] Domain purity passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_lane_capacity.py`:
- `test_capacity_grows_under_target`
- `test_capacity_halves_over_target`
- `test_capacity_is_clamped`
- `test_too_few_samples_keep_current`
- `test_p95_nearest_rank`
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
- Write-queue prefetch (never tuned), the lane host wiring (`-2`), and docs.

Commit as `feat(domain): lane read capacity from measured latency`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
