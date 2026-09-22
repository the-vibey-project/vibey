## Title
feat(qwenloop): record per-turn timing, the server's own timings, and the settings a run used

## Why
Sub-doctrine 8.c runs each loop as one instance fed by a queue "for performance", so qwenloop's
server settings must be tuned by measurement. Today a run cannot be measured:
- `turn.completed` (src/vibey_runners/qwen/src/qwenloop/application/runner.py:249) carries token
  counts but no timestamp or duration;
- `OpenAIServer.chat_stream` (src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py
  ~136-165) keeps only `usage` from the response and drops llama-server's `timings` object
  (`prompt_n` tokens actually processed, `cache_n` reused from cache, `prompt_ms`, `predicted_n`,
  `predicted_ms`, `predicted_per_second`);
- the managed server is launched with stdout and stderr sent to DEVNULL (inference.py ~81-84), so
  its load, memory and slot messages are lost;
- `meta.json` (src/vibey_runners/qwen/src/qwenloop/infrastructure/run_store.py:21) does not say which
  server settings the run used.
On 2026-09-22 the storm had to replay a synthetic session in a separate benchmark to learn anything.

## Required behaviour
1. Every `turn.completed` event adds: `started_at` and `ended_at` (UTC ISO-8601, from an injected
   clock — no direct `datetime.now()` in application code; follow how the runner already gets time,
   or add a clock port with an interface beside it), `duration_ms`, and, when the server returned
   them, `server_timings` with exactly the keys `prompt_n`, `cache_n`, `prompt_ms`, `predicted_n`,
   `predicted_ms`, `predicted_per_second` (absent keys omitted, never invented).
2. `ChatChunk` gains an optional `timings: Mapping[str, float] | None`; `chat_stream` fills it from
   `data.get("timings")` and passes the six keys above through unchanged.
3. The managed server's stdout and stderr go to `<cache_dir>/servers/<profile>/server.log`
   (append; created if missing) instead of DEVNULL. The log path is recorded in the server info.
4. `meta.json` records `server_settings`: the argv the managed server was started with (with the
   `--api-key` value replaced by `<redacted>`), or, for an attached endpoint, `{"endpoint": base_url}`.
5. Nothing else about the event vocabulary changes; existing consumers keep working.

## Where to change
- inference.py: `ChatChunk` (find its dataclass), `chat_stream` (~115-165), the managed start
  (~72-106, the `create_subprocess_exec` call).
- runner.py:190-260 (the turn loop that emits `turn.completed`).
- run_store.py (meta.json writer) and wherever the runner writes meta.

## Acceptance criteria
- [ ] A fake server response with a `timings` object produces a `turn.completed` event carrying
      `server_timings` with the six keys, and `duration_ms` equal to the injected clock's difference.
- [ ] A response without `timings` produces no `server_timings` key.
- [ ] The managed server writes to server.log (test with a fake binary that prints a line).
- [ ] meta.json contains `server_settings` with the api key redacted.
- [ ] The tenant's gates pass at its 100% coverage floor.

## Tests to write first (TDD)
- tests/test_inference.py: timings passed through; missing timings → None; server.log receives output.
- tests/test_runner.py: turn.completed carries started_at/ended_at/duration_ms/server_timings.
- tests/test_runner.py or the run-store tests: meta.json server_settings, api key redacted.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/qwen
    python -m pytest -q -p no:cacheprovider
    python -m mypy --strict src/qwenloop
    cd ../../.. && uv run ruff check . && uv run ruff format --check .

## Out of scope
Changing the server's settings (the tuning issue). Docs, CHANGELOG. Do not push.
Commit as `feat(qwenloop): ...`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
