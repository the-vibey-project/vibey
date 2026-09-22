## Title
feat(loop-service): control messages, preflight probes and dead-letter replies

## Why
ADR-0044 §13 gives the service three more consumers:

- **Control.** A caller's stop, wind-down or prompt must reach the runner's own inbox
  (`loop_process_adapter.py:591-614`, `:651-658`), whichever replica runs it.
- **Probes.** `--version`, `doctor` and `run --help` must run in the service's
  environment, which is where auth matters. They must not queue behind an hour-long
  run at prefetch 1. Conformance reads `help_text` from them (`application/conformance.py:119`).
- **Dead-letter replies.** A request that dead-letters after crashing its service
  must still be answered, so its caller does not wait for a result that will never
  come.

## Required behaviour
1. `class RunControlConsumer(host, client, names, engine_id)`. `start()` declares a
   server-named, exclusive, auto-delete queue bound to `names.control_exchange()`
   (declared as topic) with key `engine_id`, and consumes it (prefetch 16). Each
   `RunControl` addressed to a run that is active in this host is passed to
   `LocalRun.control(command, text)`. Unknown runs are ignored. Every delivery is
   completed, and a malformed one is completed and logged.
2. `class RunProbeConsumer(executor, client, names, engine_id, clock)`. `start()`
   declares `names.probe_queue(engine_id)`, a classic, non-exclusive queue bound on the
   runs exchange with `names.probe_key(engine_id)`, and consumes it with prefetch 4.
   Each probe `RunRequest` is checked by `executor.reason_to_reject`, run with
   `capture_output`, bounded by `deadline_seconds`, and answered with a `RunResult`
   carrying its `stdout` and `stderr`. Probe results are not persisted.
3. `class RunDeadLetterReplier(client, names, engine_id)`. `start()` consumes
   `names.run_dead_queue(engine_id)`. For each request that has a `reply_to`, it
   publishes `RunResult(status=DEAD_LETTERED, detail="the request crashed its service <delivery_count> times")`,
   then completes the delivery.
4. `LoopServiceHost.start()` also starts these three consumers, and `stop()` cancels
   them.

## Where to change
- The new `control.py`, its interface, and `host.py`'s `start` and `stop`.

## Acceptance criteria
- [ ] A control `STOP` reaches the active run's inbox.
- [ ] A probe `--version` answers with the fake engine's stdout, even while a long run occupies the prefetch-1 run consumer.
- [ ] A dead-lettered request gets a `DEAD_LETTERED` reply.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_control.py`:
  - `test_stop_reaches_the_active_runs_inbox`
  - `test_prompts_reach_the_inbox`
  - `test_control_for_an_unknown_run_is_ignored`
  - `test_probe_runs_beside_a_long_run`
  - `test_unsafe_probe_is_rejected`
  - `test_dead_lettered_request_is_answered`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The caller side (R24–R26).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R22.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/control.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/control_interface.py` (new)
  - `src/vibey/infrastructure/loop_service/host.py` (wire-up only)
  - `tests/infrastructure/loop_service/test_control.py` (new)
- **Parallel-safe with:** R13, R14, R25 and R26.
- **Must keep passing unchanged:**
  - R22 tests
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
