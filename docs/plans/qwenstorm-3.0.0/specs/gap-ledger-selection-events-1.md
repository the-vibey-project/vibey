## Title
feat(ledger): every engine selection is an EngineSelected event naming its candidates, weights and winner

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks the ledger for every
"decision" and "capacity signal". Choosing an engine for a BUILD job is the decision the rotation
stack exists for (ADR-0005, ADR-0038), yet today it leaves only an OpenTelemetry counter
(`src/vibey/application/engine_selection.py:244-246`) and a `selected_count` increment:
`SelectingEngineProvider.select_for` (`:206-248`) discards the `Selection` the selector returns
(`_selection`, `:226`) with every candidate's factors and effective weight
(`src/vibey/domain/rotation.py:30-64`), and a refused selection (`NoEligibleEngine` → a
`CapacityDeferred`, `:232-233`) is not recorded at all.

This lane writes `EngineSelected` through the application's `PhaseLedger` port
(`src/vibey/application/interfaces/ledger.py:104-121`), for a selection that found a winner and
for one that did not.

**Both invocation modes.** `select_for` is the one path every BUILD selection takes. ADR-0046
(`specs/ADR-two-loops.md` §3, "Flow for a BUILD job", steps 1–3) keeps it as the outer decision
in service mode too. The ordering rule that keeps the three selection events from double-recording:
- `EngineSelected` (this lane, both modes) records vibey's decision: the candidates offered to
  the round, their weights, and the winner.
- ADR-0046's `LoopRouted` (service mode) records only what the loop adds: seat, model, `switched`
  and the route reason. It must not repeat the candidates or weights.
- ADR-0046's `PaidFallbackDeclared` (both modes) records only why each sovereign adapter could not
  take the job. `EngineSelected` names no refused engine and no refusal reason.
Service mode does not exist at this HEAD, so this lane proves the subprocess path. The ADR-0046
lane that routes `select_for` through a loop keeps this call and passes the routed winner.

Capacity never enters this payload: no `resets_at`, `capacity_state` or `credits` key (the
"Credits ≠ rate limit" non-negotiable; `CreditsExhausted` has no `resets_at` at the type, the
property test and the DB CHECK, and none of the three changes here).

## Required behaviour
1. `src/vibey/domain/ledger.py`: after `DELIVERY_ESTIMATE_RECORDED` (`:70`) add the comment
   `# Engine rotation (7.c): the decision and the health it rests on.` and
   `ENGINE_SELECTED = "EngineSelected"`.
2. `SelectingEngineProvider.__init__` gains a **required** keyword parameter
   `ledger: PhaseLedger` (from `vibey.application.interfaces`), placed after `jobs`, stored as
   `self._ledger`. Required, so no construction can select without ledgering.
3. In `select_for`, rename `_selection` to `selection`, and:
   - in the `except NoEligibleEngine as exc:` branch, first
     `await self._record_selection(job, inputs, winner=None, selection=None, outcome="no_eligible_engine", detail=str(exc))`,
     then raise the same `CapacityDeferred`;
   - when `adapter is None`, first
     `await self._record_selection(job, inputs, winner=engine_id, selection=selection, outcome="no_adapter", detail=f"selected engine {engine_id.value} has no configured adapter")`,
     then raise the same `CapacityDeferred`;
   - after `record_selection` and before the metrics counter,
     `await self._record_selection(job, inputs, winner=engine_id, selection=selection, outcome="selected", detail=None)`.
   (`selection` may be `None` from a misbehaving selector: the existing
   `_SelectsAnEngineWithNoAdapter` in `tests/application/test_engine_selection.py:340-345` returns
   `(EngineId.AGYLOOP, None)`; its candidates are then `[]`.)
4. New method `async def _record_selection(self, job: JobRecord, inputs: SelectionInputs, *, winner: EngineId | None, selection: Selection | None, outcome: str, detail: str | None) -> None`,
   which calls `self._ledger.append_event(job.project_id, job.cycle, job.id, EventKind.ENGINE_SELECTED, payload)` with:
   ```python
   payload = {
       "outcome": outcome,
       "winner": winner.value if winner is not None else None,
       "attempt": job.attempts,
       "effort": inputs.requirement.effort.name,
       "excluded": sorted(e.value for e in inputs.requirement.excluded),
       "affinity": inputs.affinity.value if inputs.affinity is not None else None,
       "independence_waived": inputs.independence_waived,
       "pool": sorted(e.value for e in self._pool),
       "candidates": [
           {"engine_id": c.engine_id.value, "tier": c.tier.value, "base_weight": c.base_weight,
            "health_factor": c.health_factor, "fidelity_factor": c.fidelity_factor,
            "cost_factor": c.cost_factor, "affinity_factor": c.affinity_factor,
            "effective_weight": c.effective_weight, "current": c.current, "order": c.order}
           for c in (selection.candidates if selection is not None else ())
       ],
       "detail": detail,
   }
   ```
   `candidates` are the round SWRR ran over (the preferred tier, `preferred_tier`,
   `rotation.py:89-110`) with `current` after the round. Say so in the docstring.
5. `src/vibey/bootstrap.py:381-391`: the `SelectingEngineProvider(...)` call gains
   `ledger=PostgresReviewLedger(resources.ledger, phase=Phase.BUILD)`; both names are already
   imported (`bootstrap.py:80`, `:96`). The event's actor is vibey (`engine_id` null); the
   winner is in the payload.
6. Every existing construction under `tests/` (run `grep -rn "SelectingEngineProvider(" tests`;
   three at this HEAD, all in `tests/application/test_engine_selection.py`) gains
   `ledger=review_ledger(InMemoryLedger(), phase=Phase.BUILD)` (`tests/fakes/ledger.py`, lane
   `fakes-ledger`), with edit_file. No other existing line changes.

## Where to change
- `src/vibey/domain/ledger.py` (one insertion).
- `src/vibey/application/engine_selection.py` (edit_file only).
- `src/vibey/bootstrap.py` (one keyword).
- `tests/application/test_engine_selection.py` (and any other test file the grep in behaviour 6
  lists): the constructions, then append the tests below to `test_engine_selection.py`.

## Acceptance criteria
- [ ] One `select_for` over two eligible engines ledgers one `EngineSelected` with `outcome:
      "selected"`, the winner the adapter belongs to, both candidates, and each candidate's
      `effective_weight` equal to the domain `Candidate.effective_weight`.
- [ ] An empty eligible set ledgers `outcome: "no_eligible_engine"`, `winner: null`,
      `candidates: []` and the selector's message as `detail`, then raises `CapacityDeferred`.
- [ ] A winner with no adapter ledgers `outcome: "no_adapter"` then raises `CapacityDeferred`.
- [ ] No payload contains the keys `resets_at`, `capacity_state` or `credits` (checked on
      `json.dumps(payload)`).
- [ ] The event has `phase` BUILD, the job's cycle and id, and `engine_id` null.
- [ ] Every existing test in `tests/application/test_engine_selection.py` passes with only the three edits.
- [ ] 100% branch coverage of `src/vibey/application/*` and `src/vibey/domain/*`.

## Tests to write first (TDD)
Append to `tests/application/test_engine_selection.py` (no service; the health and cursor fakes
of `fakes-engines`, `ledger = InMemoryLedger()` and `review_ledger(ledger, phase=Phase.BUILD)`,
assertions on `ledger.events`):
- `test_a_selection_ledgers_its_candidates_weights_and_winner`
- `test_a_selection_weight_is_the_domains_effective_weight`
- `test_no_eligible_engine_ledgers_the_refused_selection_then_defers`
- `test_a_winner_without_an_adapter_ledgers_then_defers`
- `test_a_selection_event_never_carries_a_capacity_deadline`
- `test_a_selection_event_is_vibeys_own_in_the_build_phase`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application tests/domain tests/test_bootstrap.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Health and circuit transitions (`gap-ledger-selection-events-2`).
- `LoopRouted`, `PaidFallbackDeclared`, `LoopSelector` (ADR-0046's lanes).
- `EngineSelector` itself and the rotation domain (unchanged).
- Docs, CHANGELOG.

Commit as `feat(ledger): every engine selection is a ledger event`. Do not push.

## Lane card
- **Depends on:** `fakes-ledger`, `fakes-engines`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
