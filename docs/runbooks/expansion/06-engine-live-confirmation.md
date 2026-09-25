# Runbook: every engine confirmed live

> **Status (2026-09-15):** open. claudeloop and agyloop are the only
> live-proven engines. codexloop (silent `events.jsonl`) and cursorloop
> (`CURSOR_API_KEY`) were still blocked at the last recorded check
> (2026-08-20). qwenloop, the fifth engine (ADR-0015), has no live row yet;
> since ADR-0062 its runner ships as two engines, gptossloop (the sovereign
> default, GPT-OSS 20B) and qwenloop (opt-in, Qwen), and neither has one.
> All five runners are now in-tree under `src/vibey_runners/` (ADR-0021), so
> runner fixes land in this repository.

## Goal

All engines — claudeloop, agyloop, codexloop, cursorloop, gptossloop (the
sovereign local default) and qwenloop (opt-in, ADR-0062) — hold green 9/9 conformance and at least one paid live work
item each, so rotation runs across the full pool instead of the two
currently proven.

## Current state (verified the week of 2026-08-17)

| Engine | State |
|---|---|
| claudeloop | Fully live-proven (greeter3/greeter4 runs, dozens of sessions) |
| agyloop | Fully live-proven (implement + verify roles, cross-engine) |
| codexloop | **Broken live**: a real `codexloop run` produced 0 `events.jsonl` lines in ~12 minutes; probe killed; no health row → honestly excluded. Its vocabulary in `LOOP_EVENT_MAP` was source-verified (#34) but never validated against captured runtime output. |
| cursorloop | **Blocked on auth**: `doctor` fails wanting `CURSOR_API_KEY`. Untested beyond that. |
| gptossloop | On by default (ADR-0062); the local runner on `gpt-oss:20b` via Ollama (or llama.cpp / vLLM), zero marginal dollars. Its model is the sovereign DESIGN provider (`vibey worker --provider gptossloop`, the default, ADR-0027). No live BUILD row recorded. |
| qwenloop | Opt-in (`[features] qwenloop = true`); the same runner on `qwen3:14b`. No live BUILD row recorded. |

## Plan per engine

### codexloop

1. Reproduce with full stderr capture: `codexloop run <plan> --run-id X
   --cwd <tmp>` on a trivial plan; inspect `.codexloop/runs/X/` for
   meta.json presence vs events absence (is the run alive but silent, or
   dead at spawn?).
2. Root-cause in codexloop's source (`src/vibey_runners/codex`, in this
   repository) — likely suspects:
   event sink never flushed, stdout-vs-file mode flag, or an auth failure
   swallowed before the first event.
3. Fix in codexloop (its own tests, which keep their own gates per
   ADR-0022), then capture a real run's
   `events.jsonl` and reconcile vibey's `LOOP_EVENT_MAP` +
   `capacity fixtures` against **captured** output (replacing
   source-read-only verification).
4. `vibey doctor --conformance` → 9/9; then one paid greeter work item.

### cursorloop

1. Operator provides `CURSOR_API_KEY` (Cursor dashboard → API keys).
2. `cursorloop doctor` green; capture a real run; reconcile event map
   the same way (its map is also source-verified only).
3. Conformance 9/9 + one paid live item.

### gptossloop and qwenloop

1. Operator serves the model — `ollama pull gpt-oss:20b` for gptossloop (on
   by default), `ollama pull qwen3:14b` for qwenloop plus
   `[features] qwenloop = true`; or installs local weights
   (`qwenloop model install --profile portable` for llama.cpp, or the vLLM
   BF16 profile on NVIDIA).
2. `gptossloop doctor` (and `qwenloop doctor`) green; capture a real run of
   each; reconcile the event map against captured output.
3. Conformance 9/9 + one local BUILD work item. It costs no API dollars,
   so its bar is a completed item, not a paid one; its TurnCompleted
   events must still record `cost_usd` (zero) so the brake reads it.

A copilotloop (runbook 02, superseded) would add a sixth row here.

### Pool-level proof

With ≥4 engines healthy: a multi-item BUILD where rotation demonstrably
spreads implements across the pool (selected_count deltas per engine in
`engine_health`), verify always lands on a non-implementer, and one
forced-rotation tier crossing picks a different engine.

## Verification

- `vibey doctor --conformance --record` shows 9/9 for every engine.
- Each engine has ≥1 succeeded paid `build.implement` in a real project
  ledger, with TurnCompleted `cost_usd` recorded (budget brake visibility
  now depends on it — engines whose events omit cost get a runner-side
  work item to emit it).
- Rotation spread proof archived in the validation report.

## Needs from operator

- `CURSOR_API_KEY` exported (or in the env file the worker loads).
- Nothing for codexloop unless root-cause turns out to be its own expired
  auth (`codex login` may need a refresh).
- gptossloop: a local Ollama serving `gpt-oss:20b`; qwenloop: `qwen3:14b`
  (or local weights) and `[features] qwenloop = true`.

## Risks

- Vendor event vocabularies drift — captured-output reconciliation is the
  bar everywhere now, and workstream 04 watches the changelogs after.
- agyloop emits no `cost_usd` today (36/72 TurnCompleted events in
  greeter4 carried cost — the claudeloop half). Turns still count toward
  turn caps, but dollar caps under-read on agyloop-heavy cycles until its
  runner emits cost.
