## Title
feat(cli): vibey loop-service runs one engine's service, and vibey loop submit publishes a run

## Why
ADR-0044 §13 asks for one long-lived service per engine. That needs an entry point the
chart can run (R30), and one a laptop can run in a terminal. Storms and humans need a
way to publish a run and follow it without spawning the runner: QwenStorm's
`storm-queue.sh` serializes lanes by hand today, and the engine queue should do that.

The qwenloop service must also keep one model resident:

- With an attached endpoint (`QWENLOOP_BASE_URL`, derived from `VIBEY_OLLAMA_URL` by
  `local_engines.py:158-188`), Ollama already keeps it.
- Otherwise the service runs `qwenloop server start` once
  (`qwenloop/cli/app.py:638-660`), so that every run attaches to that healthy server
  (`app.py:269-271`).

The service needs no database. Only the broker and the filesystem are required.

## Required behaviour
1. `bootstrap.py`:
   - `build_loop_service(engine_id: EngineId, *, config: VibeyConfig | None, environ) -> LoopServiceHost`.
     It resolves the binary from `BY_ENGINE_ID` (claudeloop-local uses the claudeloop
     binary), the environment overlay from `LocalEndpointEnvironment(environ).overlay_for(engine_id)`,
     the AMQP URL and prefix from R17's `QueueBackendSettings`, the root from
     `config.loop_services.root`, and the settings from
     `config.loop_services.for_engine(engine_id)`.
   - `build_loop_client(...) -> LoopServiceClient`.
   - With no AMQP URL, both raise `QueueBackendNotConfigured` (R17).
2. `class ModelResidency(engine_id, launcher, environ)` has
   `async def ensure(self) -> str`, which returns a human-readable line:
   - for engines other than `qwenloop`: `"n/a"`;
   - when `QWENLOOP_BASE_URL` is set, after the overlay: `"attached: <url>"`;
   - otherwise it runs `qwenloop server start` through the launcher, bounded by
     600 s, and returns `"managed server started"`, or `"managed server start failed: <tail>"`.
     A failure is a warning, not an exit, because each run can still start its own
     server.
3. `vibey loop-service --engine ID [--prefetch N]`, in the new `cli/loop_service.py`,
   registered in `main.py` the way `ledger_search` is (`main.py:39`, `:88-89`):
   - It builds the host and prints `loop-service started: engine=<id> prefetch=<n> residency=<line>`.
   - It installs the asyncio SIGTERM handler and releases the early latch, copying
     `cli/main.py:1519-1540`.
   - It runs until SIGTERM, then calls `host.stop()` and exits 0.
   - `--prefetch` overrides the config.
   - A missing AMQP URL exits 2 with R17's message.
4. `vibey loop submit --engine ID --plan FILE --cwd DIR [--run-id UUID] [--effort standard] [--isolation worktree] [--follow] [--timeout SECONDS]`:
   - It builds a `LoopServiceAdapter` (R25) for the engine's descriptor and calls
     `start(RunSpec(...))`.
   - With `--follow` it prints each progress line.
   - It awaits the result for up to `--timeout`, prints the `RunResult` as one JSON
     line, and exits with the run's exit code, or 1 when there is none. Saturation
     exits 75, the family's "hand over" code.

## Where to change
- The new CLI module and residency module, `bootstrap.py`, and `main.py` for
  registration.

## Acceptance criteria
- [ ] Using `CliRunner`, and the in-memory client injected through `build_loop_service`'s seam, `vibey loop-service` starts and drains on a simulated SIGTERM.
- [ ] `vibey loop submit` against a stub responder prints the result JSON and returns its exit code.
- [ ] A missing URL exits 2 with both remedies.
- [ ] Residency covers attached, managed-ok, managed-fail and non-qwenloop.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/cli/test_loop_service_cli.py`:
  - `test_loop_service_starts_and_drains`
  - `test_loop_service_without_amqp_url_exits_2`
  - `test_prefetch_flag_overrides_config`
  - `test_loop_submit_prints_the_result_and_returns_its_exit_code`
  - `test_loop_submit_follow_prints_progress`
  - `test_loop_submit_saturated_exits_75`
- `tests/infrastructure/loop_service/test_residency.py`:
  - `test_attached_endpoint_needs_nothing`
  - `test_managed_server_is_started_once`
  - `test_start_failure_is_a_warning`
  - `test_other_engines_are_na`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap.py tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Switching the worker to service invocation (R28).
- The chart (R30).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R17, R23, R24. R25 is needed for `loop submit`: merge it first.
- **Wave:** 7.
- **Files touched:**
  - `src/vibey/cli/loop_service.py` (new)
  - `src/vibey/cli/main.py` (registration only)
  - `src/vibey/bootstrap.py` (`build_loop_service`, `build_loop_client`)
  - `src/vibey/infrastructure/loop_service/residency.py` (new, + interface)
  - `tests/cli/test_loop_service_cli.py` (new)
  - `tests/infrastructure/loop_service/test_residency.py` (new)
- **Parallel-safe with:** R18.
- **Must keep passing unchanged:**
  - `tests/cli/*`
  - `tests/test_bootstrap.py`
  - the image contract "every console script is on PATH" (`ci.yml:822`); no console script is added
  - all protected tests
- **Standing constraints:** see the header list.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
