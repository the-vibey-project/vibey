## Title
feat(gh): `vibey-gh estimate` reads the forecast's billing ledger and shows the measured cost of both lanes

## Why
Issue #134, "Proposed child issues" 7, and the Acceptance line "Cost shows both lanes.
Dollars reconcile with `vibey cost` for the same cycle" (rewrite `issue-audit/updates/134.md`).
This is lane 4 of 4 of `roadmap-134-cost-integral`:
- `-p1` put the local lane's timings into the conductor's billing projection;
- `-p2` taught `BillingLedgerReader` generation-seconds;
- `-p3` gave `OperationEstimate` a `MeasuredCost`.

Nothing reads the ledger for `estimate` yet. `OperationEstimator.estimate`
(`src/vibey_tools/gh/vibey_gh/operation_estimate.py:119-152`) builds the report with no cost,
and the module docstring still says "Cost is `unknown`. Neither paid-lane spend nor local
generation-seconds reach this command yet" (`:22-23`).

The ledger to read already has one declared home: `[estimate.forecast] billing_ledger`. The
forecast resolves it at `vibey_gh/cli.py:841-844` and reads it with `BillingLedgerReader`
(`:845`). Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) and 12.c (`:455`): the
estimate reads the same key through the same reader, with no second key and no second
reader. The conductor writes that file (`roadmap-134-billing-ledger-export`).

Reading a local file leaves the machine, so the estimate's offline default
(`operation_estimate.py:25-29`) is unchanged. `C(o)` itself stays unknown until T(o) exists
(`-p3`, `roadmap-134-design-phi-gradient`).

## Required behaviour
1. `OperationEstimator.__init__` (`operation_estimate.py:70-104`) gains two last keyword-only
   parameters:
   - `billing_ledger: Path | None = None`, stored as `self.billing_ledger`;
   - `billing_reader: BillingLedgerReaderInterface | None = None`, stored as
     `self._billing_reader: BillingLedgerReaderInterface = BillingLedgerReader() if billing_reader is None else billing_reader`.

   Import them from `vibey_gh.estimate_ledger` and
   `vibey_gh.interfaces.delivery_estimate_interface`.
2. New method `_measured_cost(self) -> MeasuredCost`:
   - `self.billing_ledger is None` returns `NO_MEASURED_COST`;
   - otherwise `snapshot = self._billing_reader.read(self.billing_ledger)` and return
     `MeasuredCost(paid_dollars=snapshot.usage.dollars, generation_seconds=snapshot.usage.generation_seconds, window_seconds=snapshot.usage.elapsed_seconds, ledger=self.billing_ledger, problems=snapshot.problems)`.

   `estimate` passes `cost=self._measured_cost()` to `OperationEstimate(...)` (`:139-152`).
   Import `MeasuredCost` and `NO_MEASURED_COST` beside `OperationEstimate` (`:46`).
3. Rewrite the docstring bullet at `:22-23` to: "**Cost** of the operation, `C(o)`, stays
   `unknown` until T(o) exists. The billing ledger the forecast reads is read here too, and its
   paid-lane dollars and local-lane generation-seconds are shown beside it, each in its own unit."
4. `vibey_gh/cli.py`, `_estimate` (`:774-821`): before `estimator = operation_estimate.OperationEstimator(`
   (`:803`), resolve the path exactly as `_forecast` does (`:841-844`):
   ```python
   billing_reference = Path(args.billing_ledger or cfg.estimate.forecast_billing_ledger)
   billing_ledger = (
       billing_reference if billing_reference.is_absolute() else cfg.root / billing_reference
   )
   ```
   Then pass `billing_ledger=billing_ledger` to the constructor.
5. The `estimate` parser: before `es_journal = es.add_mutually_exclusive_group()` (`:1687`),
   add
   `es.add_argument("--billing-ledger", type=Path, help="the billing ledger whose measured cost is shown beside C(o) (default: [estimate.forecast] billing_ledger, the file vibey-gh forecast reads)")`.
   This mirrors the forecast's flag (`:1711-1715`).

## Where to change
- `src/vibey_tools/gh/vibey_gh/operation_estimate.py` (220 lines; `edit_file` only).
- `src/vibey_tools/gh/vibey_gh/cli.py` (long: `edit_file` only; the two sites above).
- `src/vibey_tools/gh/test/test_operation_estimate.py`: in `_estimator` (`:55-75`), add the
  parameter `billing_ledger: Path | None = None` and pass `billing_ledger=billing_ledger`. Then
  append the tests below. Change no other line.

## Acceptance criteria
- [ ] With a billing ledger holding a claudeloop `TurnCompleted` (`cost_usd` 2.5) at
      `2026-09-18T00:00:00+00:00`, and a qwenloop `TurnCompleted` (`model_ms` 900,
      `server_timings` `prompt_ms` 500.0, `predicted_ms` 1500.0) 60 s later, the estimate's
      cost is `MeasuredCost(2.5, 2.0, 60.0, path, ())`. That is $2.50 in the paid lane and 2.0
      generation-seconds in the local lane.
- [ ] `vibey-gh estimate --operation develop --json` in a repository whose
      `.vibey/billing-ledger.jsonl` holds those records reports
      `cost.measured.paid_dollars == 2.5`, `generation_seconds == 2.0` and `cost.value is None`.
- [ ] An absent ledger is a named problem in the report, never a zero, and the exit code is
      unchanged.
- [ ] Zero new runtime dependencies (`src/vibey_tools/gh/pyproject.toml:30`). The whole suite
      passes at its 100% branch floor.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_operation_estimate.py`. Add a helper
`_billing(path, *records)` that writes `{"shard": {}}` and then one `json.dumps(record)` line
per record. `BillingLedgerReader` skips any line with a `"shard"` key
(`vibey_gh/estimate_ledger.py:72-73`).
- `test_the_estimator_reads_measured_cost_from_the_billing_ledger(tmp_path)`: the first
  acceptance criterion, via `_estimator(billing_ledger=path).estimate("develop").cost`.
- `test_without_a_billing_ledger_nothing_is_read`: `_estimator().estimate("develop").cost == NO_MEASURED_COST`.
- `test_a_missing_billing_ledger_is_a_named_problem(tmp_path)`: both lanes are `None`, and
  `problems[0].startswith("billing ledger unavailable at")`.
- `test_the_command_reads_the_forecasts_billing_ledger(repo, capsys)`: write the two records
  to `root / ".vibey" / "billing-ledger.jsonl"`. `main(["estimate", "--operation", "develop", "--json"]) == 3`.
  The JSON has the second acceptance criterion's values, and `cost.measured.ledger` ends
  with `.vibey/billing-ledger.jsonl`.
- `test_the_command_takes_a_billing_ledger_flag(repo, capsys, tmp_path)`: pass
  `--billing-ledger` with an absolute path elsewhere. `cost.measured.ledger == str(that_path)`.
- `test_the_command_says_when_the_billing_ledger_is_absent(repo, capsys)`: no file. The text
  output contains `cost measured: unknown — billing ledger unavailable at`, and the exit code
  is 3.

## Checks the lane must run (all must pass)
The focused run passes `--no-cov`: the tenant's `addopts` (`src/vibey_tools/gh/pyproject.toml:66-71`)
enforce the 100% floor, which only the whole suite can meet.

    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_operation_estimate.py test/test_estimate_ledger.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports

## Out of scope
- Writing the billing ledger (`roadmap-134-billing-ledger-export`) and the reader's arithmetic
  (`-p2`).
- Computing `C(o)`, T(o) or φ (`roadmap-134-design-phi-gradient`).
- Recording predictions (`roadmap-134-validation-harness-p1`, `-p2`). The coordinate probes
  are `roadmap-134-agency-probe`, `-software-probe`, `-network-probe` and `-hardware-series`.
  Sequence after them, because they change this command's files.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
