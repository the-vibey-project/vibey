## Title
feat(surfaces): each surface lane retunes its read concurrency from measured latency and ledgers every change

## Why
`gap-lane-capacity-1` added the pure rule. ADR-0047's lane host (placeholder
`surfaces-lane-host`, lanes S14–S27, `specs/ADR-surface-lanes.md:343`) consumes the read queue
with prefetch `read_prefetch` (`:86`, `:154`). 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`)
requires lane capacity from live evidence, published with its evidence.

**Read the landed lane host first.** The names below are ADR-0047's. If the host does not
expose a way to change the read consumer's prefetch at runtime (AMQP `basic.qos` on the read
channel), stop and report BLOCKED, naming the missing seam.

## Required behaviour
1. The lane host (`src/vibey/infrastructure/surface_lanes/host.py`, ADR-0047 §12) gains an
   optional `capacity: LaneCapacityTuningInterface | None = None` and a
   `retune_every_seconds: float = 60.0` key (12.c), both from `[surfaces]` config
   (`surface_lane_retune_seconds`, env `VIBEY_SURFACES_LANE_RETUNE_SECONDS`).
2. Every `retune_every_seconds`, when `capacity` is set, the host:
   - takes the read latencies it measured since the last retune (the same values
     `gap-measure-surfaces-*` records);
   - calls `capacity.next_prefetch(current=…, read_latencies=…)`;
   - if the result differs, applies it to the read consumer's QoS and writes one
     `LaneCapacityChanged` event with payload `{"surface", "from", "to", "p95_seconds", "samples"}`
     through the fleet ledger the measurement sink uses.
3. `capacity=None` keeps today's fixed `read_prefetch` exactly.
4. The write queue's prefetch is never touched. A test asserts it stays 1 after any number of retunes.

## Where to change
- The landed `surface_lanes/host.py` (edit_file), `src/vibey/domain/config.py` (`SurfacesConfig`:
  one key; coordinate with `gap-surface-timeouts-1`, which also extends it), and the config loader's env overrides.
- Tests: append to the host's test file, with `InMemoryAmqpClient` from `vibey_bootstrap` and
  a controllable clock.

## Acceptance criteria
- [ ] With fast reads, the read prefetch rises by `step` at each retune, and one
      `LaneCapacityChanged` is written per change.
- [ ] Slow reads halve it.
- [ ] `capacity=None` never changes QoS.
- [ ] Write prefetch stays 1.
- [ ] 100% branch coverage in the layers touched.

## Tests to write first (TDD)
- `test_read_capacity_rises_under_target`
- `test_read_capacity_halves_over_target`
- `test_no_tuner_keeps_the_fixed_prefetch`
- `test_writes_are_never_retuned`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The instance count, which is fixed at 1 by 8.f, and docs.

Commit as `feat(surfaces): lanes retune read capacity from measured latency`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
