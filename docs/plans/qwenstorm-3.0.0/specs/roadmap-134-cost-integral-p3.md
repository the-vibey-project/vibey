## Title
feat(gh): the operation estimate reports the measured cost of both lanes beside `C(o)`, which stays unknown until T(o) exists

## Why
Issue #134, "Proposed child issues" 7, Scope 3 (cost in both lanes, "shown separately and
together"), and the Acceptance line "Cost shows both lanes" (rewrite
`issue-audit/updates/134.md`). This is lane 3 of 4 of `roadmap-134-cost-integral`.

The paper defines the cost of an operation as `C(o) = ∫₀^{T(o)} c(x(t)) dt` over its duration
`T(o) = T₀(o) ∏ φᵢ(dᵢ)` (`docs/paper.md:1254-1256`). φ is unspecified (`src/vibey_tools/gh/vibey_gh/feasibility.py:31-33`),
and it is a separate design spike (`roadmap-134-design-phi-gradient`). So `C(o)` cannot be
computed yet, and sub-doctrine 10.f (`src/vibey_tools/gh/docs/doctrines.md:419`) forbids
inventing it. What can be measured is the integrand's history: what the paid lane spent, and
what the local lane computed, over the billing ledger's window.

Today the report has only `"cost": {"value": None, "reason": COST_REASON}`
(`src/vibey_tools/gh/vibey_gh/estimate_report.py:117`) and one line (`:134`), and COST_REASON
still says nothing reaches the command (`:38-41`). The two lanes are shown apart, each in
its own unit, and never added. No exchange rate between a dollar and a generation-second is
declared, and a default would invent an operator decision (12.c, `doctrines.md:455`). This
lane only holds and renders; the reading is `-p4`. `estimate_report.py` performs no I/O
(`:4-7`), and that stays true.

## Required behaviour
1. In `vibey_gh/estimate_report.py`, after the reason constants (`:38-50`), add
   ```python
   @dataclass(frozen=True)
   class MeasuredCost(MeasuredCostInterface):
       """The cost history C(o) would integrate over (#134 scope 3), both lanes apart:
       paid-lane dollars and local-lane generation-seconds are never summed, because no
       exchange rate between them is declared."""

       paid_dollars: float | None
       generation_seconds: float | None
       window_seconds: float | None
       ledger: Path | None
       problems: tuple[str, ...] = ()
   ```
   with two methods:
   - `as_dict(self) -> dict[str, Any]` returns exactly
     `{"paid_dollars": …, "generation_seconds": …, "window_seconds": …, "ledger": None if self.ledger is None else str(self.ledger), "problems": list(self.problems)}`.
   - `describe(self) -> str`. The first rule that applies decides:
     1. `ledger is None`: `"not read — no billing ledger was given to this estimate"`.
     2. `paid_dollars is None and generation_seconds is None`:
        `f"unknown — {why} ({self.ledger})"`. `why` is `"; ".join(self.problems)`, or, with no
        problems, `"the billing ledger holds no spend and no timed local turn"`.
     3. Otherwise:
        `f"paid lane {paid}, local lane {local}, over {window} of {self.ledger}"`. When there
        are problems, append `f" — {'; '.join(self.problems)}"`. The parts are:
        - `paid` is `f"${paid_dollars:.2f}"`, or `"unknown"`;
        - `local` is `f"{generation_seconds:.1f} generation-seconds"`, or
          `"unknown generation-seconds"`;
        - `window` is `f"{window_seconds:.0f}s"`, or `"an untimed window"`.
   - Add `NO_MEASURED_COST = MeasuredCost(None, None, None, None)`, and add `"MeasuredCost"` and
     `"NO_MEASURED_COST"` to `__all__` (`:21-28`, sorted).
2. `COST_REASON` (`:38-41`) becomes: `"C(o) integrates the cost rate over the operation's
   duration T(o), and T(o) waits on φ, which is not fitted yet — so this operation's cost is
   not computed; each lane's measured history is shown beside it, never summed into one unit
   (doctrine 10)"`.
3. `OperationEstimate` (`:53-68`) gains a last field `cost: MeasuredCost = NO_MEASURED_COST`.
   - `as_dict` (`:117`): `"cost": {"value": None, "reason": COST_REASON, "measured": self.cost.as_dict()}`.
   - `lines` (`:134`): directly after `f"{say} cost: unknown — {COST_REASON}"`, add
     `f"{say} cost measured: {self.cost.describe()}"`.
4. New `vibey_gh/interfaces/estimate_report_interface.py`:
   `@runtime_checkable class MeasuredCostInterface(Protocol)`, with the five fields as
   read-only properties plus `as_dict` and `describe`. `Path` is imported under
   `TYPE_CHECKING` only; copy `vibey_gh/interfaces/operation_estimator_interface.py:13-18`.
   `MeasuredCost` subclasses it, as `BillingUsage` subclasses its interface
   (`vibey_gh/delivery_estimate.py:249`); `estimate_report.py` imports it with
   `from vibey_gh.interfaces.estimate_report_interface import MeasuredCostInterface`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/estimate_report.py` (203 lines: `edit_file` only).
- New `src/vibey_tools/gh/vibey_gh/interfaces/estimate_report_interface.py`. Line 1 is the
  provenance header, copied byte-for-byte from `vibey_gh/interfaces/operation_estimator_interface.py:1`.
- `src/vibey_tools/gh/test/test_operation_estimate.py`:
  - add `NO_MEASURED_COST` and `MeasuredCost` to the import at `:14-20`, and add the imports
    `import dataclasses` and
    `from vibey_gh.interfaces.estimate_report_interface import MeasuredCostInterface`
    at the top (isort places them);
  - change the one assertion at `:293` to
    `assert data["cost"] == {"value": None, "reason": COST_REASON, "measured": NO_MEASURED_COST.as_dict()}`;
  - append the tests below. Change no other line.

## Acceptance criteria
- [ ] `MeasuredCost(2.5, 2.0, 60.0, Path(".vibey/billing-ledger.jsonl")).describe() == "paid lane $2.50, local lane 2.0 generation-seconds, over 60s of .vibey/billing-ledger.jsonl"`.
- [ ] Every estimate carries `"cost": {"value": None, …, "measured": …}`: `C(o)` is never a number.
- [ ] The text report has the line `vibey-gh estimate: cost measured: not read — no billing ledger was given to this estimate` by default.
- [ ] The whole vibey-gh suite passes at its 100% branch floor.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_operation_estimate.py`:
- `test_measured_cost_shows_both_lanes_apart`: the first acceptance criterion.
- `test_measured_cost_says_which_lane_is_unknown`: `MeasuredCost(None, 2.0, None, Path("b.jsonl")).describe()`
  contains `paid lane unknown` and `an untimed window`. `MeasuredCost(2.5, None, 60.0, Path("b.jsonl"))`
  contains `unknown generation-seconds`.
- `test_measured_cost_with_nothing_measured_names_why`: with problems `("billing ledger unavailable at b.jsonl: missing",)`
  the text is `"unknown — billing ledger unavailable at b.jsonl: missing (b.jsonl)"`. With no
  problems it names `holds no spend and no timed local turn`.
- `test_measured_cost_appends_its_problems`: `MeasuredCost(1.0, 2.0, 3.0, Path("b.jsonl"), ("1 of 3 local turn(s) …",))`
  ends with ` — 1 of 3 local turn(s) …`.
- `test_no_measured_cost_is_not_read`: `NO_MEASURED_COST.describe()` starts with `not read`,
  and `NO_MEASURED_COST.as_dict()["ledger"] is None`.
- `test_the_report_shows_measured_cost_under_an_unknown_c_of_o`:
  `dataclasses.replace(_estimator().estimate("develop"), cost=MeasuredCost(2.5, 2.0, 60.0, Path("b.jsonl")))`.
  Its `lines()` holds `cost: unknown — ` + COST_REASON and then the `cost measured: paid lane $2.50` line.
  Its `as_dict()["cost"]["measured"]["paid_dollars"] == 2.5`.
- `test_measured_cost_satisfies_its_seam`: `isinstance(NO_MEASURED_COST, MeasuredCostInterface)`.

## Checks the lane must run (all must pass)
The focused run passes `--no-cov`: the tenant's `addopts` (`src/vibey_tools/gh/pyproject.toml:66-71`)
enforce the 100% floor, which only the whole suite can meet.

    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_operation_estimate.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports

## Out of scope
- Reading the billing ledger in `OperationEstimator` and the CLI (`roadmap-134-cost-integral-p4`).
- Computing T(o), φ or the gradient (`roadmap-134-design-phi-gradient`).
- A price per generation-second. Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
