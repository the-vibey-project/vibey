## Title
feat(preflight): the conductor bridge measures agent load, agent success rate and exhausted paid credit from the engine-health records

## Why
Issue #134, "Proposed child issues" 5 (rewrite `issue-audit/updates/134.md`, Scope 1 "agent:
availability, load and historical success rate from engine health and ledger outcomes";
"agency: … paid credit balance"). This lane is the first of four: agent and paid credit here;
the information coordinates in `-p2` (channel), `-p3` (probe) and `-p4` (wiring).

Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) says a component that
cannot report its measurements is incomplete. 10.f (`:419`) says unmeasured stays unknown.
8.a (`:99-118`): a local engine spends no credit, so exhausted paid credit blocks only a
pool with no sovereign engine in it.

Verified gap: `VibeyGhFeasibilityAdapter.evaluate`
(`src/vibey/infrastructure/preflight_feasibility.py:54-110`) measures three coordinates:
- `software.availability` (`:73-78`);
- `agent.availability` (`:79-84`);
- `agency.availability`, only for a failed engine auth (`:90-98`).

The engine-health records it already receives (`health_records`, `:59`) carry more:
- `circuit`, the breaker state (`src/vibey/domain/circuit.py:19-22`);
- `capacity_state`, written as the text `"CreditsExhausted"`, `"WindowExhausted"` or
  `"AuthenticationFailed"` (`src/vibey/application/engine_health_service.py:186-219`);
- `ewma_failure`, an exponentially weighted failure rate raised by each failure or capacity
  rejection and decayed by each success (`:240`, `:293`, `:334`);
- `selected_count`, how often rotation picked the engine (`record_selection`, `:247-272`).

All of these reach the evaluator today as `unknown` (`StateVector.unknown()`, `:100`).

vibey-gh already accepts this input shape and needs no change. `Coordinate(material, prop,
value | None, source, measured_at=None)` is at `src/vibey_tools/gh/vibey_gh/feasibility.py:122-155`,
and `StateVector.with_measurements` at `:197-200`. `MEASURED_BY` names the rows this lane
fills: agent stability is "turnover, fatigue and load over time" and agent reliability is
"historical success rate when acting" (`:107-109`); "paid credit … is agency" (`:113-116`).

Default stages gate availability only (`:250-253`; docstring `:35-36`). So the new stability
and reliability readings change no verdict. The credit reading is a real, gated shortfall.

## Required behaviour
In `src/vibey/infrastructure/preflight_feasibility.py`:
1. After the `measurements` list (`:72-85`), and before the agency comment (`:86`):
   ```python
   if conformant:
       measurements.append(self._agent_load(conformant, records))
       measurements.append(self._agent_success(conformant, records))
   ```
2. **Agent load: `agent.stability`.** New method
   `_agent_load(self, conformant: Sequence[EngineId], records: Mapping[str, EngineHealthRecord]) -> Coordinate`:
   - `shedding` = the conformant engines whose `records[e.value].circuit is not CircuitState.CLOSED`
     (import `CircuitState` from `vibey.domain.circuit`). An open, half-open or unrecognized
     circuit is not taking full load.
   - `taking = len(conformant) - len(shedding)`; value `round(taking / len(conformant), 4)`.
   - Source: `f"{taking} of {len(conformant)} conformant agent(s) take load (circuit closed); shedding: {detail}"`.
     `detail` is `"; ".join(f"{e.value} ({r.capacity_state or r.circuit.value})" ...)` over
     `shedding` sorted by `e.value`, where `r = records[e.value]`, or the text `none`.
   - Docstring: the circuit breaker summarises each engine's recent failure and capacity
     series, so this reads a series rather than one reading (#134 scope 2).
3. **Success rate: `agent.reliability`.** New method
   `_agent_success(self, conformant: Sequence[EngineId], records: Mapping[str, EngineHealthRecord]) -> Coordinate`:
   - `ran` = the conformant engines with `records[e.value].selected_count > 0`.
   - When `ran` is empty, return
     `Coordinate("agent", "reliability", None, f"unmeasured — no conformant agent has run yet (selected_count is 0 for {self._names(conformant)})")`.
     No history is unknown, not perfect (10.f).
   - Otherwise `selections = sum(r.selected_count for each e in ran)`,
     `rate = sum(r.selected_count * (1.0 - r.ewma_failure) for each e in ran) / selections`.
     Return `Coordinate("agent", "reliability", round(rate, 4), f"selection-weighted success rate 1 - ewma_failure over {selections} selection(s) of {self._names(ran)}")`.
   - Docstring: the reason for weighting. Rotation spreads work by selection, so the expected
     success of the pool is the selection-weighted mean.
4. **Paid credit: `agency.availability`.** Extend the existing `if conformant and not authenticated:`
   block (`:90-98`) with an `elif`:
   ```python
   elif authenticated and all(
       records[engine_id.value].capacity_state == _CREDITS_EXHAUSTED for engine_id in authenticated
   ):
       measurements.append(
           Coordinate(
               "agency",
               "availability",
               0.0,
               "Fund the paid lane or enable a local engine: paid credit is exhausted on "
               f"every authenticated engine: {self._names(authenticated)}.",
           )
       )
   ```
   - Module constant: `_CREDITS_EXHAUSTED: Final = "CreditsExhausted"`, commented "the
     capacity_state text `EngineHealthService.record_capacity_rejection` writes
     (`application/engine_health_service.py:204`)". Import `Final` from `typing`.
   - A successful auth with credit left still leaves agency unknown. The comment at `:86-89`
     stays true: credit is one permission, and merge rights and token scopes are the
     vibey-gh agency probe's (`roadmap-134-agency-probe`).
5. `agent.availability` is unchanged (`:79-84`), and so is everything else in `evaluate`.

## Where to change
- `src/vibey/infrastructure/preflight_feasibility.py` (145 lines; use `edit_file`).
- `tests/infrastructure/test_preflight_feasibility.py`: append the tests below; change no
  existing test. The class contract `VibeyGhFeasibilityAdapterInterface`
  (`src/vibey/infrastructure/interfaces/class_contracts.py:193-195`) is unchanged: `evaluate`
  keeps its signature.
- No other file.

## Acceptance criteria
- [ ] Every existing test in `tests/infrastructure/test_preflight_feasibility.py` passes
      unchanged. `test_usable_engine_leaves_unmeasured_coordinates_unknown` still reports
      `required == 6`, `required_measured == 2`.
- [ ] Two conformant engines, one with an open circuit, give `agent.stability == 0.5`.
- [ ] Engines selected 3 and 1 times with `ewma_failure` 0.1 and 0.5 give
      `agent.reliability == 0.8`. No selections give `None` with the named reason.
- [ ] One authenticated engine with `capacity_state="CreditsExhausted"` is `infeasible` at
      `feature-branch`, first repair `agency.availability — Fund the paid lane …`. Adding an
      authenticated `qwenloop` with no capacity state removes that shortfall.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/test_preflight_feasibility.py`. Add these imports at the top
with `edit_file`:
- `from dataclasses import replace`;
- `StateVector` into the existing `from vibey_gh.feasibility import FeasibilityEvaluator, Pipeline, Stage` (`:5`).
(Imports go at the top because ruff's E402 refuses them mid-file; the tests themselves are appended.)

Add a test-local recording evaluator:

    class _RecordingEvaluator(FeasibilityEvaluator):
        def __init__(self) -> None:
            super().__init__()
            self.states: list[StateVector] = []
        def evaluate(self, state, stages):
            self.states.append(state)
            return super().evaluate(state, stages)

It is substituted through the adapter's declared `evaluator=` seam (`:48`), with no patching.
Build records with `replace(_health(pid, engine, conformant=True), circuit=..., capacity_state=..., selected_count=..., ewma_failure=...)`.
- `test_agent_load_is_the_share_of_conformant_agents_with_a_closed_circuit`: claudeloop is
  closed; codexloop is `CircuitState.OPEN` with `capacity_state="WindowExhausted"`. Then
  `state.get("agent", "stability").value == 0.5`, and its source contains `1 of 2` and
  `codexloop (WindowExhausted)`.
- `test_agent_load_is_full_when_every_circuit_is_closed`: the value is 1.0 and the source
  ends `shedding: none`.
- `test_agent_success_is_selection_weighted`: the 3×0.1 and 1×0.5 case gives 0.8, and the
  source contains `4 selection(s)`.
- `test_an_agent_that_never_ran_leaves_success_unknown`: `selected_count=0`; the value is
  `None`, and the source starts with `unmeasured — no conformant agent has run yet`.
- `test_no_conformant_agent_measures_neither_load_nor_success`: installed but not conformant.
  Both coordinates keep `StateVector.unknown()`'s source, which starts with `unmeasured — would come from`.
- `test_exhausted_paid_credit_is_an_agency_shortfall`: the credit acceptance case, through the
  real evaluator.
- `test_a_local_engine_keeps_agency_when_paid_credit_is_gone`: claudeloop is
  `CreditsExhausted`; qwenloop is authenticated with no capacity state. The status is
  `unknown` and `first_repair is None`.
- `test_load_and_success_change_no_default_verdict`: the conformant case with an open circuit
  and `selected_count=5`, `ewma_failure=1.0`. The status stays `unknown`, and
  `required_measured == 2`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_preflight_feasibility.py tests/application/test_preflight.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure tests/application
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The information coordinates and the probe channel (`roadmap-134-agent-information-probes-p2`
  … `-p4`).
- A success rate from ledger job outcomes. The job-lifecycle kinds are the gaps.md §E3 lanes
  (`gap-ledger-job-events-*`); the engine-health EWMA is the measured series here.
- Merge rights and token scopes (`roadmap-134-agency-probe`). Writing readings to the ledger
  (the gaps.md §D1 measure lanes). Showing all 18 coordinates in the worker's startup line.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
