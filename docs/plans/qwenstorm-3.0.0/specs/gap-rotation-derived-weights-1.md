## Title
feat(rotation): a measured-evidence factor in each candidate's effective weight, clamped to a declared band

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-325`) says rotation weights,
residency, lane capacity and defaults "are chosen from live evidence, never from assumption".
Today a candidate's effective weight is
`base_weight × health × fidelity × cost × affinity` (`src/vibey/domain/rotation.py:30-58`).
The base weights are static (`src/vibey/domain/config.py:113`, `:413-416`, and descriptor
`base_weight`s), and ADR-0038 fixed every base weight at 1. `select()` uses the weights as
given (`rotation.py:161-182`). No factor comes from measured outcomes
(`issue-audit/gaps.md` D2, lines 269-280).

This lane adds the pure rule. The factor is 1.0 until there is evidence, so nothing is ever
assumed. `gap-rotation-derived-weights-2` feeds it from the measurement port
(`gap-measure-port`) and ledgers each derivation.

## Required behaviour
1. New pure module `src/vibey/domain/evidence_weighting.py`, with the provenance header, stdlib
   imports and `vibey.domain` only:
   - `@dataclass(frozen=True, slots=True) class EngineEvidence` with fields
     `engine_id: EngineId`, `successes: int`, `failures: int` and
     `median_latency_s: float | None`.
     - `__post_init__` raises `ValueError` for negative counts or for a non-positive latency
       that is not `None`.
     - Property `samples = successes + failures`.
     - Property `success_rate`: `successes / samples`, or `None` when `samples == 0`.
   - `@dataclass(frozen=True, slots=True) class EvidenceBand` with fields `floor: float = 0.5`,
     `ceiling: float = 1.5`, `min_samples: int = 20` and `success_share: float = 0.5`.
     `__post_init__` requires `0 < floor <= 1 <= ceiling`, `min_samples >= 1` and
     `0 <= success_share <= 1`. Otherwise it raises `ValueError` naming the field.
   - `class EvidenceWeighting` with `__init__(self, band: EvidenceBand = EvidenceBand())` and
     `factors(self, evidence: Sequence[EngineEvidence]) -> Mapping[EngineId, float]`:
     - An engine is **measured** when `samples >= band.min_samples` and it has a latency.
     - Every engine in `evidence` gets 1.0, unless at least **two** engines are measured,
       since there is nothing to compare against otherwise. Unmeasured engines always get 1.0.
     - For a measured engine:
       - `s = success_rate / mean(success_rate of measured engines)`, or `s = 1.0` if that mean is 0;
       - `l = median(latencies of measured engines) / its latency`;
       - `factor = clamp(s ** success_share * l ** (1 - success_share), floor, ceiling)`,
         rounded to 4 decimals.
     - The result is ordered like the input. Duplicate `engine_id`s raise `ValueError`.
   - `EVIDENCE_WEIGHTING: Final[EvidenceWeightingInterface] = EvidenceWeighting()`.
2. New interface `src/vibey/domain/interfaces/evidence_weighting_interface.py` with
   `EvidenceWeightingInterface(Protocol)` (`factors`), `@runtime_checkable`. Export it from
   `src/vibey/domain/interfaces/__init__.py`.
3. `Candidate` (`rotation.py:30-58`) gains the field `evidence_factor: float = 1.0`, after
   `affinity_factor` and before `tier`, so existing positional construction still works.
   `effective_weight` multiplies it in. The "positive never rounds to zero" rule (`:50-58`)
   is unchanged. Every existing `Candidate(...)` call site keeps working without change
   (`src/vibey/application/engine_selector.py:195-205` passes keywords).
4. `EventKind` (`src/vibey/domain/ledger.py:37-69`) gains `WEIGHTS_DERIVED = "WeightsDerived"`,
   appended last, with the comment "Evidence factors derived for rotation (8.g)". There is no
   migration: `event.kind` is plain text.
5. Credits never become a rate limit. This rule reads success and failure counts only. It never
   reads or produces a `resets_at`, and a capacity rejection is not a "failure" sample here.
   Lane -2 feeds only completed-or-failed run outcomes. Write that as a sentence in the module
   docstring.

## Where to change
- New: `src/vibey/domain/evidence_weighting.py`,
  `src/vibey/domain/interfaces/evidence_weighting_interface.py`.
- Edit with edit_file: `src/vibey/domain/rotation.py` (the `Candidate` field and
  `effective_weight`), `src/vibey/domain/ledger.py` (one member), and
  `src/vibey/domain/interfaces/__init__.py`.
- New test file `tests/domain/test_evidence_weighting.py`. Append one test to
  `tests/domain/test_rotation.py` for the new factor.

## Acceptance criteria
- [ ] With one measured engine and one unmeasured engine, both factors are 1.0.
- [ ] Two measured engines with equal success rates, at latencies 10 s and 20 s, and
      `success_share=0.5`: the median is 15, `l` is 1.5 and 0.75, `s` is 1, so the factors are
      `round(1.5 ** 0.5, 4) = 1.2247` and `round(0.75 ** 0.5, 4) = 0.866`.
- [ ] Clamping holds: a far slower and failing engine is exactly `floor`, and a far better one
      exactly `ceiling`.
- [ ] `success_share=1.0` ignores latency, and `0.0` ignores success.
- [ ] An engine below `min_samples` keeps 1.0 even when others are measured.
- [ ] `Candidate(..., evidence_factor=0.5)` halves the effective weight before rounding, and a
      tiny positive product still rounds to 1.
- [ ] `EventKind("WeightsDerived")` resolves.
- [ ] Invalid bands and evidence raise `ValueError` naming the field.
- [ ] Every existing test in `tests/domain` passes unchanged. 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_evidence_weighting.py`:
- `test_no_comparison_means_no_change`
- `test_two_measured_engines_worked_example`
- `test_factors_are_clamped_to_the_band`
- `test_success_share_extremes`
- `test_under_sampled_engine_keeps_one`
- `test_invalid_band_and_evidence_are_refused` (parametrized)
- `test_duplicate_engines_are_refused`
- `test_weighting_satisfies_its_interface`
- `test_weights_derived_is_a_ledger_kind`

Append to `tests/domain/test_rotation.py`: `test_evidence_factor_scales_effective_weight`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain tests/application/test_engine_selector.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Reading measurements, config keys for the band, and writing `WeightsDerived` events
  (`gap-rotation-derived-weights-2`).
- Residency and lane capacity (`gap-residency-tuning`, `gap-lane-capacity`).
- Docs.

Commit as `feat(rotation): a measured-evidence factor in effective weight`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
