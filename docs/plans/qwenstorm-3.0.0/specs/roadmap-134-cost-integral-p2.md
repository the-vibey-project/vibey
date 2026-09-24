## Title
feat(gh): the billing reader measures the local lane in generation-seconds beside the paid lane's dollars

## Why
Issue #134, "Proposed child issues" 7, and Scope 3: cost in both lanes (rewrite
`issue-audit/updates/134.md`). This is lane 2 of 4 of `roadmap-134-cost-integral`. Sub-doctrines:
- 8.a (`src/vibey_tools/gh/docs/doctrines.md:99-118`): the local lane's cost is real.
- 10.f (`:419`): a lane nobody timed stays `unknown`, never zero.
- vibey-gh stays stdlib-only (`src/vibey_tools/gh/pyproject.toml:30`, `dependencies = []`).

The package that reads the billing ledger owns the arithmetic. That is vibey-gh's
`BillingLedgerReader` (`src/vibey_tools/gh/vibey_gh/estimate_ledger.py:51-156`). Today it sums
dollars (`:102-111`) and nothing of the local lane. After `roadmap-134-cost-integral-p1`, each
`TurnCompleted` record in the billing ledger keeps `model_ms` and, when llama-server reported
them, `server_timings` with `prompt_ms` and `predicted_ms` (qwenloop
`src/vibey_runners/qwen/src/qwenloop/application/runner.py:323-335`).

Generation-seconds is defined here as the server's own compute for a turn:
`(prompt_ms + predicted_ms) / 1000`. The other clocks are not used, because each would
measure something else:
- `duration_ms` includes the turn's tool runs;
- `model_ms` stops at the model's first answer chunk.

Ollama's OpenAI-compatible endpoint returns no `timings`
(`src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:237-250` reads llama-server's
only). So a local turn without them is counted and reported as untimed, never guessed.

A local turn is any `TurnCompleted` carrying `model_ms` or `server_timings`. Only a local
runner writes those fields; qwenloop is the one that does today.

The billing dimensions are one list (`BILLING_USAGE_FIELDS`, `vibey_gh/delivery_estimate.py:71-83`),
so the forecast also plans and grades the new dimension, with no special case.

## Required behaviour
1. In `vibey_gh/delivery_estimate.py`:
   - `BILLING_USAGE_FIELDS` (`:71-83`) gains `"generation_seconds"` as its last entry.
   - `BillingUsage` (`:248-265`) gains `generation_seconds: float | None = None` after
     `artifacts_produced` (`:262`). Its docstring says: the local lane's server compute,
     `prompt_ms + predicted_ms`, in seconds.
   - `_planned_usage` keeps the new dimension fractional: the set at `:581` becomes
     `{"elapsed_seconds", "dollars", "generation_seconds"}`.
   - `_usage_from_values` (`:743-756`) gains
     `generation_seconds=_optional_float(values.get("generation_seconds")),`.
2. In `vibey_gh/interfaces/delivery_estimate_interface.py`, `BillingUsageInterface`
   (`:132-168`) gains `@property def generation_seconds(self) -> float | None: ...` after
   `artifacts_produced`.
3. In `vibey_gh/estimate_ledger.py`, `BillingLedgerReader`:
   - New `@staticmethod _generation_ms(value: object) -> float | None`. It returns
     `prompt_ms + predicted_ms` when `value` is a `Mapping` whose `prompt_ms` and
     `predicted_ms` are both `int | float`, not `bool`, finite and `>= 0`; otherwise `None`.
     Use `math.isfinite`.
   - In `_usage` (`:85-140`), inside `if kind == "TurnCompleted":` (`:102-105`), add
     `timed = cls._generation_ms(body.get("server_timings"))`. When it is not `None`, add it
     to a local `generation_ms` (start `0.0`) and add 1 to `timed_turns` (start `0`). Pass
     `generation_seconds=generation_ms / 1000 if timed_turns else None` to `BillingUsage(...)`.
   - New `@classmethod _untimed_local_turns(cls, events: list[Mapping[str, object]]) -> list[str]`:
     - count `local` = the `TurnCompleted` events whose payload is a `Mapping` containing
       `"model_ms"` or `"server_timings"`;
     - count `timed` = those whose `_generation_ms(payload.get("server_timings"))` is not `None`;
     - when `local > timed`, return
       `[f"billing ledger: {local - timed} of {local} local turn(s) carry no server timings (Ollama's OpenAI-compatible endpoint reports none), so generation_seconds covers {timed}"]`;
       otherwise `[]`.
   - In `read` (`:54-83`), after `usage = self._usage(events)` (`:82`), do
     `problems.extend(self._untimed_local_turns(events))` before building the snapshot.
   - Update the module docstring (`:2-10`): the billing source now also carries the local
     lane's generation-seconds.
4. Nothing else changes: `dollars` still sums `cost_usd` and `BudgetSpent.dollars` exactly as
   today, and no exchange rate joins the two lanes.

## Where to change
- `src/vibey_tools/gh/vibey_gh/delivery_estimate.py` (764 lines: `edit_file` only),
  `src/vibey_tools/gh/vibey_gh/interfaces/delivery_estimate_interface.py`,
  `src/vibey_tools/gh/vibey_gh/estimate_ledger.py`.
- `src/vibey_tools/gh/test/test_delivery_estimate.py`, three targeted edits, each
  keeping every line not named:
  - `:202-214`: add `"generation_seconds": 0,` after `"artifacts_produced": 0,`.
  - `:250-262`: add `"generation_seconds",` after `"artifacts_produced",`.
  - `_full_usage` (`:57-69`): add `generation_seconds=30.0,` after `artifacts_produced=1,`.
- Append the new tests to `src/vibey_tools/gh/test/test_estimate_ledger.py` and
  `src/vibey_tools/gh/test/test_delivery_estimate.py`. Do not rewrite either.
- No fake is needed. The reader is a class contract, and the tenant registry covers
  `*Transport`, `*Runner`, `*Opener` and `*Sampler` only (lane `fakes-tenant-gh-1`).

## Acceptance criteria
- [ ] A billing ledger with two timed qwenloop turns (`prompt_ms` 120.5 + `predicted_ms`
      800.0, and 79.5 + 1000.0) and one claudeloop turn (`cost_usd` 2.5) reads
      `generation_seconds == 2.0`, `dollars == 2.5` and `problems == ()`.
- [ ] Adding one untimed qwenloop turn (`model_ms` 900, no `server_timings`) keeps
      `generation_seconds == 2.0` and adds exactly the problem
      `billing ledger: 1 of 3 local turn(s) carry no server timings (Ollama's OpenAI-compatible endpoint reports none), so generation_seconds covers 2`.
- [ ] A ledger with no local turn reads `generation_seconds is None` and adds no problem.
- [ ] `BillingUsage().as_dict()` has the key `generation_seconds`. The whole vibey-gh suite
      passes at its 100% branch floor.

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_estimate_ledger.py`. Records are written with
`json.dumps` in the shard shape of the existing test (`:39-97`): a `{"shard": {...}}` header,
then `{"kind", "produced_at", "payload"}` lines.
- `test_generation_seconds_sum_the_server_timings_of_local_turns`: the first acceptance criterion.
- `test_an_untimed_local_turn_is_counted_and_reported_not_guessed`: the second.
- `test_no_local_turn_leaves_generation_seconds_unknown`: the third, with only a `BudgetSpent`.
- `test_malformed_server_timings_are_untimed`: parametrized over
  - `{"prompt_ms": True, "predicted_ms": 1}`;
  - `{"prompt_ms": -1, "predicted_ms": 1}`;
  - `{"prompt_ms": float("inf"), "predicted_ms": 1}`, written with `json.dumps(..., allow_nan=True)`;
  - `{"predicted_ms": 1}`;
  - `"not-a-mapping"`.

  Each is one `TurnCompleted`. `generation_seconds is None`, and there is one problem naming `1 of 1`.

Append to `src/vibey_tools/gh/test/test_delivery_estimate.py` (it has the `_history` helper,
`:72-`, whose default is 4 remaining and 18 completed units):
- `test_the_forecast_plans_generation_seconds_as_a_fraction`:
  `DeliveryEstimator().calculate(_history(), BillingUsage(generation_seconds=3.0), state=StateVector.unknown(), recorded_at="now", source_fingerprint="gen")`.
  Then `forecast.billing.planned_low.generation_seconds == pytest.approx(3.0 / 18 * 4)` and
  `isinstance(..., float)`: it is not rounded to an int, as the counted dimensions are
  (`delivery_estimate.py:581-582`).

## Checks the lane must run (all must pass)
The focused runs pass `--no-cov`: the tenant's `addopts` (`src/vibey_tools/gh/pyproject.toml:66-71`)
enforce `--cov-fail-under=100`, which only the whole suite can meet.

    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_estimate_ledger.py test/test_delivery_estimate.py test/test_delivery_cli.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The conductor's billing projection (`roadmap-134-cost-integral-p1`).
- `vibey-gh estimate`'s cost report (`-p3`, `-p4`).
- A price for a generation-second or any single-unit total: joining the lanes would need an
  exchange rate nobody has declared.
- A qwenloop change to time Ollama turns. Docs, `docs/estimate.md` (the workflow regenerates
  it), CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
