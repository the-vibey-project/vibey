## Title
feat(domain): per-phase duration and dollar distributions from the phase timeline — count, min, median, p90, max

## Why
Issue #88, "Proposed child issues" 2 (rewrite `issue-audit/updates/88.md`). Scope 2 asks for
per-milestone time and cost predictions "from the conductor's own phase-timing distributions".
Sub-doctrines 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) and 10.f (`:419`) require
predictions to come from measurements, with unknown kept unknown.

Half of this exists and is not duplicated here. `src/vibey/domain/phase_timing.py` projects
**one project's** ledger into visits and per-`(cycle, phase)` totals:
- `PhaseTimingProjection.project`, `:246-286`;
- `PhaseTotal`, `:203-212`, whose `measured` is true only when every visit under it is closed,
  observably entered and not clock-skewed (`PhaseVisit.measured`, `:197-200`);
- spend follows `LedgerSpendRule`, the budget brake's own rule (`:123-160`).

It predicts nothing and aggregates nothing across projects or cycles; its docstring says a
later slice consumes it (`:6-9`). There is no distribution anywhere in `src/vibey`.

What is new:
- `Distribution`, one sample's count and nearest-rank order statistics;
- `PhaseDistribution`, one phase's duration and dollar distributions plus a count of what
  could not be sampled;
- `PhaseDistributionProjection`, which folds many timelines (or many projects' ledgers
  through the existing projection) into one `PhaseDistribution` per phase.

It extends `phase_timing.py`, never a parallel module. `domain/` stays pure (no I/O, clock or
async; `tests/domain/test_domain_purity.py`).

## Required behaviour
All in `src/vibey/domain/phase_timing.py`, appended after `PHASE_TIMING` (`:343-348`), with
the interfaces in `src/vibey/domain/interfaces/phase_timing_interface.py`.

1. **The sample unit is one measured `PhaseTotal`.** That is one project's whole stay in one
   phase in one cycle, all visits summed: BUILD⇄REVIEW revisits are one sample, which is
   what a cycle (a milestone's unit) spends in the phase.
   - A total whose `measured` is false is never sampled. That covers open, entry-unobserved
     and clock-skewed totals. It is counted in `unmeasured`, so nothing is dropped silently.
   - The seconds sample is `total.duration.total_seconds()`; the dollars sample is
     `total.spend.dollars`. Both come from the same totals, so both counts are equal.
   - Unattributed spend (`PhaseTimeline.unattributed`) belongs to no phase sample, and turn
     counts are not distributed (`TURN_EVENT_CAVEAT`, `:86-94`).
2. `@dataclass(frozen=True, slots=True) class Distribution` with fields `count: int`,
   `minimum: float | None`, `median: float | None`, `p90: float | None`,
   `maximum: float | None`, and:
   - `@classmethod def of(cls, values: Sequence[float]) -> "Distribution"`:
     `ordered = sorted(values)`. Empty gives `cls(0, None, None, None, None)`, which is
     unknown, never zero (10.f). Otherwise it gives
     `cls(len(ordered), ordered[0], cls._nearest_rank(ordered, 50), cls._nearest_rank(ordered, 90), ordered[-1])`.
   - `@staticmethod def _nearest_rank(ordered: Sequence[float], percent: int) -> float`:
     `rank = max(1, -(-len(ordered) * percent // 100))` (the ceiling of `n·p/100` in integer
     arithmetic); return `ordered[rank - 1]`. So the median of an even count is the lower
     middle value, and p90 of ten samples is the ninth. Say at the definition: "the
     nearest-rank rule of lane `gap-measure-domain`'s `LatencySummary`, stated here in integer
     arithmetic because that class emits latency readings, not a dollar distribution; one
     shared order-statistics helper replaces both when it exists (10.e)."
3. `@dataclass(frozen=True, slots=True) class PhaseDistribution` with `phase: StoredPhase`,
   `seconds: Distribution`, `dollars: Distribution`, `unmeasured: int`.
4. `class PhaseDistributionProjection`:
   - `__init__(self, *, timing: PhaseTimingProjectionInterface = PHASE_TIMING) -> None`.
   - `distribute(self, timelines: Sequence[PhaseTimelineInterface]) -> tuple[PhaseDistribution, ...]`:
     for every total of every timeline, `if total.measured and total.duration is not None:`
     append its seconds and dollars to that phase's samples, `else:` add 1 to that phase's
     `unmeasured`. Every phase that appears in any total gets one `PhaseDistribution`.
     - Order: `Phase` members in declaration order (`src/vibey/domain/phase.py:17-28`), then
       unrecognized phases sorted by `.value`. Use the sort key
       `(0, index, "")` for a `Phase` and `(1, 0, phase.value)` otherwise, where `index` comes
       from `{p: i for i, p in enumerate(Phase)}`.
     - The result does not depend on the order of `timelines`.
   - `of_ledgers(self, ledgers: Sequence[Sequence[LedgerEvent]]) -> tuple[PhaseDistribution, ...]`:
     `return self.distribute(tuple(self._timing.project(events) for events in ledgers))`. Each
     inner sequence is one project's events. A mixed one raises the projection's `ValueError`
     (`:288-294`), unchanged.
5. `PHASE_DISTRIBUTIONS: Final[PhaseDistributionProjectionInterface] = PhaseDistributionProjection()`,
   with a docstring saying the annotation is load-bearing, as `PHASE_TIMING`'s does (`:344-348`).
6. In `phase_timing_interface.py`, after `PhaseTimingProjectionInterface` (`:186-194`), add
   three `@runtime_checkable` Protocols:
   - `DistributionInterface`: the five fields as read-only properties;
   - `PhaseDistributionInterface`: `phase`, `seconds` and `dollars` (typed
     `DistributionInterface`), and `unmeasured`;
   - `PhaseDistributionProjectionInterface`: `distribute` and `of_ledgers`, both returning
     `tuple[PhaseDistributionInterface, ...]`.

   Put the concrete types under the existing `TYPE_CHECKING` block only (`:16-21`).
7. Append one paragraph to the module docstring of `phase_timing.py`, before its closing
   `"""` (`:71`): "**Distributions** fold many timelines into one `PhaseDistribution` per
   phase: one sample per measured `(project, cycle, phase)` total, nearest-rank order
   statistics, and a count of the totals that could not be measured. A phase with no measured
   total has an empty distribution (count 0, every statistic None), never a zero."

## Where to change
- `src/vibey/domain/phase_timing.py` (348 lines: use `edit_file` only).
- `src/vibey/domain/interfaces/phase_timing_interface.py` (use `edit_file`).
- New `tests/domain/test_phase_distribution.py`. Line 1 is the provenance header, copied
  byte-for-byte from `tests/domain/test_phase_timing.py:1`. Copy that file's `_event` and
  `_moved` helpers (`:44-83`) into the new file, typing their `phase` and `to` parameters
  `StoredPhase` (`vibey.domain.phase`) so an `UnrecognizedPhase` can be passed; do not import
  them from a test module.
- Do not edit `src/vibey/domain/interfaces/__init__.py`, which another lane edits. The test
  imports the new Protocols from `vibey.domain.interfaces.phase_timing_interface`.

## Acceptance criteria
- [ ] `Distribution.of([10, 9, 8, 7, 6, 5, 4, 3, 2, 1])` gives count 10, minimum 1, median 5,
      p90 9, maximum 10.
- [ ] The two-project scenario below gives exactly the listed distributions, in the order
      DESIGN, BUILD, REVIEW, DONE.
- [ ] `tests/domain/test_domain_purity.py` and the whole of `tests/domain/test_phase_timing.py`
      pass unchanged.
- [ ] 100% branch coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
`tests/domain/test_phase_distribution.py`, with `T0 = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)`
and two project ids:
- `test_nearest_rank_of_one_to_ten`: the first acceptance criterion, with the input shuffled.
- `test_a_single_sample_is_every_statistic`: `Distribution.of([3.5])` has count 1 and all four
  statistics equal to 3.5.
- `test_an_empty_distribution_is_unknown_not_zero`: `Distribution.of([])` has count 0 and
  minimum, median, p90 and maximum all `None`.
- `test_the_median_of_an_even_count_is_the_lower_middle`: `[4, 1, 3, 2]` gives median 2 and
  p90 4.
- `test_each_measured_cycle_is_one_sample_per_phase`: `PHASE_DISTRIBUTIONS.of_ledgers([a, b])`,
  where `a` is project A, cycle 1, with these events (`_moved` for transitions):
  - seq1 → DESIGN at `T0`;
  - seq2 `BUDGET_SPENT` DESIGN `{"dollars": 1.0}`;
  - seq3 → BUILD at `T0+60s`;
  - seq4 `TURN_COMPLETED` BUILD `{"cost_usd": 2.0}`;
  - seq5 → REVIEW at `T0+160s`;
  - seq6 → BUILD at `T0+170s`;
  - seq7 `TURN_COMPLETED` BUILD `{"cost_usd": 3.0}`;
  - seq8 → REVIEW at `T0+370s`;
  - seq9 → DONE at `T0+400s`.

  And `b` is project B:
  - seq1 → DESIGN at `T0`;
  - seq2 → BUILD at `T0+120s`;
  - seq3 `TURN_COMPLETED` BUILD `{"cost_usd": 7.0}`;
  - seq4 → REVIEW at `T0+1000s`.

  Expect:

  | phase | seconds (count, min, median, p90, max) | dollars (count, min, median, p90, max) | unmeasured |
  |---|---|---|---|
  | DESIGN | 2, 60, 60, 120, 120 | 2, 0.0, 0.0, 1.0, 1.0 | 0 |
  | BUILD | 2, 300, 300, 880, 880 | 2, 5.0, 5.0, 7.0, 7.0 | 0 |
  | REVIEW | 1, 40, 40, 40, 40 | 1, 0.0, 0.0, 0.0, 0.0 | 1 |
  | DONE | 0, None, None, None, None | 0, None, None, None, None | 1 |
- `test_the_order_of_the_timelines_changes_nothing`: `of_ledgers([b, a]) == of_ledgers([a, b])`.
- `test_an_unobserved_entry_is_counted_not_sampled`: a ledger that begins with a
  `TURN_COMPLETED` in BUILD at `T0`, then → REVIEW at `T0+50s`, then → DONE at `T0+60s`.
  BUILD has count 0 and `unmeasured == 1`. REVIEW has seconds count 1 with median 10.
- `test_a_clock_skewed_total_is_counted_not_sampled`: → DESIGN at `T0+100s`, then → BUILD at
  `T0`. DESIGN has count 0 and `unmeasured == 1`.
- `test_unrecognized_phases_follow_known_ones_sorted_by_value`: transitions into
  `UnrecognizedPhase("zeta")`, `UnrecognizedPhase("alpha")` and `Phase.DESIGN`, closed by a
  final → DONE. The phase order is DESIGN, DONE, `alpha`, `zeta`.
- `test_a_mixed_project_ledger_is_refused`: `of_ledgers([a + b])` raises `ValueError`.
- `test_distribute_takes_the_existing_projection`:
  `PhaseDistributionProjection().distribute([PHASE_TIMING.project(a)])` equals
  `of_ledgers([a])`.
- `test_every_new_object_satisfies_its_declared_seam`:
  `isinstance(PHASE_DISTRIBUTIONS, PhaseDistributionProjectionInterface)`, plus
  `PhaseDistributionInterface` and `DistributionInterface` on a result row.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_phase_distribution.py tests/domain/test_phase_timing.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any consumer: milestones and per-milestone predictions (#88 children 3–4, blocked on the
  milestone design and #86), a `vibey forecast` command, vibey-gh.
- Changing `PhaseTimingProjection`, `LedgerSpendRule` or the turn caveat.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
