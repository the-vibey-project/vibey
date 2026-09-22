## Title
feat(explorer): the capability-first scorer — fit, boundedness and verifiability gate; attention only ranks

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, Scope 4 "Capability-first scoring per runbook 21",
"Proposed child issues" 6). Runbook 21 (`docs/runbooks/expansion/21-vibey-explorer.md`, "1.
Capability-first selection, not popularity-first") is exact about the rule: score on **Fit**
("Python/typed, test-suited, onion-friendly, CLI/API/library shaped, reproducible locally,
dependencies installable"), **Boundedness** ("a clear definition of done"), **Verifiability** ("a
failing test can be written first") and **Attention** ("Real, and last"); "Fit gates; attention
ranks. A candidate that fails fit is not rescued by being popular"; and (Design 2) "The scorer is a
pure, testable function over candidate features, so its judgement can be inspected and
property-tested". The runbook gives no numeric thresholds, and this lane invents none: the gates are
booleans supplied with the candidate, and attention is the number the source measured. Rate caps
are out (#87 open question 3).

## Required behaviour
In `src/vibey_tools/explorer/vibey_explorer/scoring.py`, contracts in
`vibey_explorer/interfaces/scoring_interface.py` (stdlib only):
1. `@dataclass(frozen=True, slots=True) class FitAssessment`: six booleans, in runbook order —
   `language_supported`, `has_tests`, `layered`, `interface_shaped`, `reproducible_locally`,
   `dependencies_installable`. `failed(self) -> tuple[str, ...]`: the names that are False, in
   declaration order.
2. `@dataclass(frozen=True, slots=True) class CandidateFeatures`: `fit: FitAssessment`,
   `bounded: bool`, `verifiable: bool`, `attention: float`. `attention < 0` or not finite →
   `ValueError("attention must be a finite, non-negative number")`.
3. `@dataclass(frozen=True, slots=True) class GateVerdict`: `passed: bool`, `failed: tuple[str, ...]`.
4. `class CapabilityScorer` (stateless):
   - `gate(self, features: CandidateFeatures) -> GateVerdict`: `failed` = `features.fit.failed()` +
     `("bounded",)` if not bounded + `("verifiable",)` if not verifiable; `passed = not failed`.
     Attention is never read here.
   - `rank(self, scored: Sequence[tuple[Candidate, CandidateFeatures]]) -> list[Candidate]`: only
     candidates whose gate passes, ordered by `attention` descending, then `source_url` ascending
     (deterministic). An empty result is correct ("the quiet bar": a day with nothing passing ships
     nothing).
5. Docstring: quote "Fit gates; attention ranks." and "the quiet bar".

## Where to change
- New: `vibey_explorer/scoring.py`, `vibey_explorer/interfaces/scoring_interface.py` (provenance header).
- New test file `src/vibey_tools/explorer/test/test_scoring.py`.

## Acceptance criteria
- [ ] A candidate failing any fit/bounded/verifiable check is never ranked, whatever its attention.
- [ ] Among passing candidates the order is attention-descending, `source_url`-ascending on ties.
- [ ] The gate names every failed criterion in order.
- [ ] 100% branch coverage; mypy clean; stdlib only.

## Tests to write first (TDD)
`src/vibey_tools/explorer/test/test_scoring.py` (seeded `random.Random` loops for the properties;
no hypothesis, the tenant is stdlib-only):
- `test_the_gate_names_every_failed_criterion`
- `test_popularity_never_rescues_a_failed_fit` — for 200 seeded random features with at least one
  False gate, `rank` excludes the candidate even at `attention=1e12`.
- `test_attention_only_orders_the_passing` — 200 seeded random sets; `rank` equals the passing
  subset sorted by `(-attention, source_url)`.
- `test_a_quiet_day_ranks_nothing`
- `test_attention_must_be_finite_and_non_negative` (`-1`, `nan`, `inf`)
- `test_the_scorer_satisfies_its_interface`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/explorer && python -m pytest -q && python -m mypy
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- How features are measured from a real repository (a later lane, after discovery sources, which
  are blocked on #87 open question 2); rate caps and staleness (open question 3); the skip registry
  (`roadmap-87-scoring-skiplist-p2`); learning from outcomes. Docs, CHANGELOG. Do not push; commit
  locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
