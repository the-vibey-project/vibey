## Title
feat(opencodeloop): meter OpenCode token usage and cost so the budget brake can see it

## Why
The OPENCODE descriptor charges 0/0 per million tokens "until a provider-specific meter is configured"
(`src/vibey/infrastructure/engines/descriptors.py:279-284`). opencodeloop does not report any cost. It turns
OpenCode's `step_finish` into `{"event_type":"turn.completed","raw":raw}` (`T/infrastructure/opencode_process.py:186-187`),
so vibey's tail builds the payload `{"raw": {...}}` (`loop_process_adapter.py:498-505`). The one spend rule that
the budget brake and the per-engine meter share reads `payload["cost_usd"]` from `TurnCompleted`
(`src/vibey/domain/phase_timing.py:137-140`; `application/budget_source.py:12-19`; `application/engine_selection.py:251-311`).
It reads nothing here, so every OpenCode dollar goes uncounted. That matters more because OPENCODE is in `DEFAULT_DESCRIPTORS`
with `tier=EngineTier.LOCAL` (`descriptors.py:287,409`). LOCAL is preferred first (`src/vibey/domain/engine.py:51`,
`domain/rotation.py:107`), yet OpenCode can call paid providers.

OpenCode already reports usage and cost. Verified in `sst/opencode` `dev` on 2026-09-22:
- `run --format json` writes `{"type","timestamp","sessionID",...data}` (`packages/opencode/src/cli/cmd/run.ts`, `emit`).
- `step_finish` carries `part: {type:"step-finish", reason, cost: number, tokens: {total?, input, output, reasoning, cache: {read, write}}}`
  (`packages/schema/src/v1/session.ts:240-256`).
- OpenCode computes `part.cost` from each model's price. Its own per-provider, per-model config key is
  `provider.<id>.models.<id>.cost.{input,output,cache_read,cache_write}` (`packages/core/src/v1/config/provider.ts:31-45`).

So the per-provider price is configured where the provider is configured, which is OpenCode's own config.
opencodeloop only needs a **fallback** rate for a provider that has no price (`part.cost == 0` with tokens > 0).
It must never make up a price. Sub-doctrine 12.c: a rate is a key, not a constant.

## Required behaviour
1. `step_finish` (and its aliases `message_finish` and `turn_finish`) normalizes to:
   `{"event_type":"turn.completed","payload":{...},"raw":raw}`
   The `payload` holds:
   - `cost_usd` (float);
   - `cost_source`, which is one of `"opencode"`, `"configured_rate"` or `"unpriced"`;
   - `input_tokens`, `output_tokens`, `reasoning_tokens`, `cache_read_tokens` and `cache_write_tokens` (ints).

   A missing, non-numeric or `bool` value counts as 0. The `payload` envelope is the one claudeloop uses for
   its turn events (`claudeloop/application/runner.py:545-555`), and it is what both vibey readers expect:
   `loop_process_adapter.py:498-499` and `opencodeloop_process.py:151-157`.
2. **Which price wins:**
   - if `part.cost > 0`, then `cost_usd = part.cost` and `cost_source = "opencode"`;
   - else if both fallback rates are set, then
     `cost_usd = ((input + cache_read + cache_write) * price_in + (output + reasoning) * price_out) / 1_000_000`
     and `cost_source = "configured_rate"`. Cache tokens are charged at the full input rate on purpose: a brake
     that over-counts stops early, and one that under-counts spends money;
   - else `cost_usd = 0.0` and `cost_source = "unpriced"`.
3. **Fallback rate settings.**
   - `--price-in-per-mtok` / `OPENCODELOOP_PRICE_IN_PER_MTOK`
   - `--price-out-per-mtok` / `OPENCODELOOP_PRICE_OUT_PER_MTOK`

   Both default to unset. Set both or neither. Each must be ≥ 0. Anything else exits 2.
4. **Dollar cap.** `--max-dollars` / `OPENCODELOOP_MAX_DOLLARS` defaults to unset, which means no cap. When it
   is set it must be > 0. After each `turn.completed`, add up `cost_usd`. When the running total is
   `>= max_dollars`, `watchdog.trip(StopReason.MAX_DOLLARS)` and then `_terminate(process)`. The run's status is
   FAILED, with detail `stopped at bound: max_dollars` and exit 1. That matches the family rule that running out
   of budget is exit 1 (`claudeloop/cli/outcome.py:10`).
5. `RunResult` also carries the run's totals: `turns`, `cost_usd`, `input_tokens` and `output_tokens`. `finish()` writes
   them into `meta.json` and `snapshots/latest.json`.
6. **vibey DESIGN path:** `OpenCodeLoopProcess.run` also adds `"--max-dollars", format(self._max_dollars, "g")`.
   This copies `claudeloop_process.py:93-103`.
7. **vibey BUILD path:** no production code changes. A new test proves that an opencodeloop `turn.completed` line
   reaches the ledger as a `TurnCompleted` with the same `cost_usd`, and that `LEDGER_SPEND_RULE` charges it.
8. **Descriptor comment.** In `descriptors.py:279-282`, rewrite the comment to say that the meter is the
   per-turn `cost_usd` that opencodeloop reports. The descriptor's `cost_per_mtok_*` values stay `0.0`,
   because they are only a rotation weighting hint (`domain/rotation.py:143`) and not the meter. Change no values.

## Where to change
Tenant, domain: `T/domain/model.py`
```python
class StopReason(StrEnum): ...; MAX_DOLLARS = "max_dollars"      # add the member
@dataclass(frozen=True, slots=True)
class RunBounds: ...; max_dollars: float | None = None           # validate: None or > 0

@dataclass(frozen=True, slots=True)
class TurnUsage:
    reported_cost: float = 0.0
    input_tokens: int = 0; output_tokens: int = 0; reasoning_tokens: int = 0
    cache_read_tokens: int = 0; cache_write_tokens: int = 0
    @classmethod
    def from_step(cls, part: Mapping[str, object]) -> "TurnUsage": ...   # pure parse of part.cost / part.tokens

@dataclass(frozen=True, slots=True)
class UsagePricing:
    price_in_per_mtok: float | None = None
    price_out_per_mtok: float | None = None
    # __post_init__: both-or-neither, each >= 0, else ValueError
    def price(self, usage: TurnUsage) -> tuple[float, str]: ...          # rule in item 2
```
- Add `turns`, `cost_usd`, `input_tokens` and `output_tokens` to `RunResult` as trailing fields that default to zero.
- Add `TurnUsageInterface` and `UsagePricingInterface` to `T/domain/interfaces/model_interface.py`, and add
  the new `RunResult` properties to `RunResultInterface`.

Tenant, infrastructure: `T/infrastructure/opencode_process.py`
- `_normalize(cls, line, pricing: UsagePricing | None = None)`. The `_STEP_FINISH` branch (`:186-187`) returns
  `{"event_type":"turn.completed","payload":cls._usage_payload(raw, pricing or UsagePricing()),"raw":raw}`.
- `_usage_payload(raw, pricing)` reads `raw["part"]` only when it is a mapping. It builds a `TurnUsage` and prices it.
- `execute(...)` gains `pricing: UsagePricing`. It passes `pricing` to `_normalize` and totals turns, cost and
  tokens from each `turn.completed` payload. If `bounds.max_dollars` is set and the cost total is `>= max_dollars`,
  it trips `MAX_DOLLARS` and calls `_terminate`. It returns the totals in `RunResult`.
- Update `T/application/interfaces/process_interface.py`.

Tenant, application: `T/application/runner.py`. `run(..., pricing: UsagePricing = UsagePricing())` passes it
through. Mirror this in `runner_interface.py`.

Tenant, store: `T/infrastructure/run_store.py`. In `finish()`, add `turns`, `cost_usd`, `input_tokens` and
`output_tokens` to `metadata`.

Tenant, CLI: `T/cli/app.py`. Add `--max-dollars`, `--price-in-per-mtok` and `--price-out-per-mtok`, each with
`envvar=`, to `run` and `resume`. Build `RunBounds(..., max_dollars=...)` and `UsagePricing(...)` inside the
existing `try` blocks.

vibey:
- `src/vibey/infrastructure/engines/opencodeloop_process.py:84` (as Part 1 left it): append
  `"--max-dollars", format(self._max_dollars, "g")`.
- `src/vibey/infrastructure/engines/descriptors.py:279-282`: rewrite the comment only.

## Acceptance criteria
- [ ] The tenant suite passes at 100% branch coverage. `mypy --strict`, `lint-imports` and `bandit` pass.
- [ ] A `step_finish` with `part.cost = 0.0123` normalizes to `payload.cost_usd == 0.0123` and `cost_source == "opencode"`.
- [ ] `part.cost = 0` with tokens and rates of 3.0 in / 15.0 out → `configured_rate` at the computed value.
      With no rates → `0.0` and `"unpriced"`.
- [ ] `--max-dollars 0.05` stops a run whose second turn brings the total to ≥ 0.05. The result is `exit_code == 1`
      and `stop_reason == "max_dollars"`.
- [ ] vibey: `uv run pytest -q -p no:cacheprovider tests/infrastructure/engines/test_loop_process_adapter.py tests/infrastructure/engines/test_opencodeloop_process.py` passes.

## Tests to write first (TDD)
`TT/test_model.py`
- `test_turn_usage_from_step_reads_cost_and_every_token_field`.
- `test_turn_usage_from_step_zeroes_missing_bool_and_non_numeric_fields`.
- `test_usage_pricing_prefers_opencode_reported_cost`.
- `test_usage_pricing_falls_back_to_configured_rates`: input 1000, cache_read 500, output 200, reasoning 100,
  at rates 3.0/15.0 → `(1500*3 + 300*15)/1e6 = 0.009`.
- `test_usage_pricing_marks_unpriced_usage`.
- `test_usage_pricing_requires_both_rates_or_neither_and_non_negative`.
- `test_run_bounds_rejects_non_positive_max_dollars`.

`TT/test_process.py`
- `test_normalize_step_finish_carries_usage_in_a_payload_envelope`.
- `test_execute_totals_turn_usage_into_the_result`.
- `test_execute_stops_at_the_dollar_cap`: fake `killpg` gets SIGTERM, `stop_reason is MAX_DOLLARS`, and exit 1.
- `test_execute_without_a_dollar_cap_never_trips_on_cost`.

`TT/test_store.py`
- `test_finish_records_usage_totals`.

`TT/test_cli.py`
- `test_cli_prices_come_from_flags_or_env`.
- `test_cli_rejects_one_rate_without_the_other_with_exit_2`.
- `test_cli_rejects_non_positive_max_dollars_with_exit_2`.

vibey, `tests/infrastructure/engines/test_loop_process_adapter.py`
- `test_tail_carries_opencodeloop_turn_cost_to_the_spend_rule`:
  - use `LoopProcessAdapter(descriptor=OPENCODE)` and the `_make_handle` helper (`:29-35`);
  - write `events.jsonl` containing
    `{"timestamp":"2026-01-01T00:00:00+00:00","event_type":"turn.completed","payload":{"cost_usd":0.0123,"cost_source":"opencode","input_tokens":1000,"output_tokens":200},"raw":{"type":"step_finish"}}`;
  - write `meta.json` with `{"status":"finished"}`;
  - assert: the event's kind is `"TurnCompleted"`; `payload["cost_usd"] == 0.0123`; and
    `LEDGER_SPEND_RULE.spend_of_payload(kind, payload).dollars == 0.0123`, where `LEDGER_SPEND_RULE` comes from `vibey.domain.phase_timing`.

vibey, `tests/infrastructure/engines/test_opencodeloop_process.py`
- Extend the argv assertion so it ends with `"--max-turns", "1", "--max-dollars", "0.25"`.

## Checks the lane must run (all must pass)
Run the same commands as in Part 1, and add
`tests/infrastructure/engines/test_loop_process_adapter.py` to the focused `uv run pytest` line. Also run
`uv run coverage report --include='src/vibey/infrastructure/engines/opencodeloop_process.py' --fail-under=100`.

## Out of scope
- The OPENCODE descriptor's `tier` (LOCAL, although OpenCode can bill a paid provider), its `cost_per_mtok_*` values,
  and `src/vibey/domain/config.py`. Changing them is a rotation-policy decision for another issue.
- A rate table per provider inside opencodeloop. The run's JSON stream does not say which provider served a step,
  and OpenCode's own `provider.*.models.*.cost` already does per-provider pricing.
- The tenant README. Its line "billing settings remain outside this package" (`src/vibey_runners/opencode/README.md:11-13`) goes
  stale with this part, so pass it to the docs wave. Also out of scope: CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md, skill trees, and version bumps. Do not push, open PRs or change remotes. Commit locally
  with the Title as the Conventional Commit subject.

## Hard repository rules (always)
- domain/ stays pure. `TurnUsage.from_step` and `UsagePricing.price` are pure arithmetic over mappings.
- Dependencies point inward (the import-linter layers contract, in the tenant and in vibey).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim, and Part 1's `TerminalRule` stays as it is.
- Code lives in classes with an interface beside each (ADR-0016). Module functions need a written reason.
- Every job is idempotent under replay, and the ledger is append-only. Cost is recorded only on the turn events
  the run writes, never added up again on a reused result (`opencodeloop_process.py:80-82` returns a reused result
  without calling `_record`; keep it that way).

## Context shared by every part of this work
# opencodeloop parity: bounded runs, marker-derived completion, exit 75, cost metering

This issue is split into two ordered parts. **Part 1 must be merged before Part 2 starts.**
Each part is a separate lane with its own commit. Each part restates what it needs, so a
lane given only one part has enough to implement it.

Evidence cutoff: `develop` at `d47c196d` (checkout `/private/tmp/claude-501/storm/changelog-2.1.0`),
read on 2026-09-22. The OpenCode event and config shapes were read from `sst/opencode`
branch `dev` on the same date (files named in Part 2).

Paths starting `src/vibey_runners/opencode/` belong to the **tenant**. The tenant layout is
`src/vibey_runners/opencode/src/opencodeloop/{domain,application,infrastructure,cli}` and
`src/vibey_runners/opencode/tests/`. Below, `T/` means `src/vibey_runners/opencode/src/opencodeloop/`
and `TT/` means `src/vibey_runners/opencode/tests/`.

---
