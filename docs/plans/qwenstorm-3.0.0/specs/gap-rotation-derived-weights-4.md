## Title
feat(rotation): engine selection multiplies each candidate's weight by its evidence factor

## Why
`gap-rotation-derived-weights-1..3` made the evidence factor, its band and its derivation. The
selector still builds candidates with health, fidelity, cost and affinity only
(`src/vibey/application/engine_selector.py:185-205`). 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`)
is satisfied only when the factor reaches `select()`. ADR-0038's base weights stay 1, and the
factor is a multiplier like `health_factor`.

## Required behaviour
1. `EngineSelector.__init__` (`engine_selector.py`) gains the keyword
   `evidence: EvidenceWeightsDeriverInterface | None = None`. `None` keeps today's behaviour exactly.
2. Where candidates are built (`:185-205`), when `evidence` is set, call
   `await evidence.factors(job.project_id, tuple(runtime.engine_id for runtime in eligible))`
   **once per selection, before the loop**. Each `Candidate(...)` then gets
   `evidence_factor=factors.get(runtime.engine_id, 1.0)`.
3. `bootstrap.py`: wherever `EngineSelector` is constructed (`grep -n "EngineSelector(" src/vibey/bootstrap.py`),
   pass `evidence=EvidenceWeightsDeriver(ledger=…, recorder=…, config=project_config.engines.evidence, clock=…)`
   using the resources that are already there. If the selector is built without a project
   config in scope, pass `EvidenceConfig()` and write why in a comment.
4. The tier rule is untouched: `preferred_tier` still sees effective weights, so a sovereign
   engine with a low factor still wins over paid while its weight is positive (8.a). The
   rounding floor in `Candidate.effective_weight` guarantees that.

## Where to change
- `src/vibey/application/engine_selector.py` (edit_file).
- `src/vibey/bootstrap.py` (edit_file, one construction site).
- Tests: append to `tests/application/test_engine_selector.py`, with `FixedEvidenceWeights`
  from `tests/fakes/engines.py`.

## Acceptance criteria
- [ ] Two paid candidates of equal weight, with factors 1.5 and 0.5: over 4 selections the
      1.5 engine wins 3 (SWRR with effective weights 2 and 1 after rounding; pin the exact sequence).
- [ ] A sovereign candidate with factor 0.5 still wins over a paid one at 1.5 (the tier rule).
- [ ] `evidence=None` leaves every existing test unchanged.
- [ ] `factors` is called once per selection.
- [ ] 100% branch coverage of `src/vibey/application/*`. The bootstrap tests pass.

## Tests to write first (TDD)
Append to `tests/application/test_engine_selector.py`:
- `test_evidence_factors_shift_the_round_robin`
- `test_evidence_never_overrides_the_sovereign_tier`
- `test_no_evidence_is_todays_selection`
- `test_factors_read_once_per_selection`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- ADR-0046's `LoopSelector` (service mode). When it lands, its `weighted_candidates` extraction
  must keep this factor; say so in a comment at the call site. Docs are also out of scope.

Commit as `feat(rotation): selection uses measured evidence`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
