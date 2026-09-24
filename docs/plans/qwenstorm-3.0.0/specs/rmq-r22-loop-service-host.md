## Title
feat(loop-service): the service host consumes run requests, dedupes, supersedes, replies and acknowledges

## Why
ADR-0044 §13. One long-lived process per engine consumes `vibey.runs.<engine_id>`
with a configured prefetch, so that one loaded model is shared in an orderly way. The
host owns four of the invariants the ADR calls the riskiest:

1. A redelivered request never starts a second process.
2. A result is persisted and published before its request is acknowledged.
3. A request that is superseded, or not started in time, is answered rather than run.
4. No two runs ever share one worktree.

## Required behaviour
1. `class LoopServiceHost` is constructed with:
   - `engine_id: str`
   - `client: AmqpClientInterface`
   - `names: QueueNamesInterface`
   - `executor: LocalRunExecutorInterface`
   - `results: RunResultStoreInterface`
   - `settings: LoopServiceConfigInterface`
   - `delivery_limit: int = 3`
   - `consumer_timeout_seconds: int = 21600`
   - `clock: Clock`
   - `instance_id: str`
   - `logger: Logger`
2. `async def start(self)`:
   - Declare `names.runs_exchange()` (direct) and `names.run_dead_exchange()` (direct).
   - Declare the queue `names.run_queue(engine_id)` with
     `{"x-queue-type":"quorum","x-delivery-limit":delivery_limit,"x-dead-letter-exchange":names.run_dead_exchange(),"x-dead-letter-strategy":"at-least-once","x-overflow":"reject-publish","x-consumer-timeout":consumer_timeout_seconds*1000}`,
     bound with key `engine_id`.
   - Declare `names.run_dead_queue(engine_id)`, bound on the dead exchange with key
     `engine_id`.
   - Consume the run queue with `prefetch=settings.prefetch` and the handler
     `_on_request`.
3. `_on_request(delivery)` checks, in order:
   - **a.** Decode the body. A `MalformedRunMessage`, or a message that is not a
     `RunRequest` or not for this engine, is sent to `dead_letter()`.
   - **b.** The `run_id` is already active in this instance (a redelivery after a
     channel blip): rebind the active run's delivery to this one, and do not start
     anything. vibey_bootstrap's `ReplayGuard` (`servicebus/async_ext.py:26-49`)
     records the run ids seen, for logging.
   - **c.** `results.read(cwd, run_id)` exists: republish that result to `reply_to`,
     then `complete()`.
   - **d.** `run_dir` is given, it exists, and its `meta.json` status is not
     `finished`, `failed` or `stopped`: this is a crashed earlier start. Write, publish
     and complete a result with status `ABANDONED` and detail `"run directory left non-terminal by a previous service instance"`.
   - **e.** `clock.now() > request.start_by`: reply `REJECTED` with
     `"not started before start_by"`, then complete.
   - **f.** `executor.reason_to_reject(request)` is not `None`: reply `REJECTED` with
     that reason, then complete.
   - **g.** An active run on the same `cwd`:
     - with the same `supersedes.key` and a lower `attempt`: call
       `stop(settings.supersede_grace_seconds)` on it, then write, publish and
       complete **its** result as `SUPERSEDED`;
     - with any other key, or none: reply `REJECTED` with `"worktree busy"` and
       complete, without running.
   - **h.** Otherwise start the run:
     - Publish `RunAccepted`.
     - While it runs, publish one `RunProgress` per new `events.jsonl` line, when
       `settings.publish_progress` is on and there is a `run_dir`. Poll every 0.5 s,
       with `seq` starting at 1.
     - Wait for the exit, bounded by `deadline_seconds`. Past the deadline, stop with
       the grace, and the status is `DEADLINE_EXCEEDED`; otherwise it is `EXITED`,
       with `exit_code` and `meta_status`.
     - Write the result through `results.write` (purpose `RUN` only), publish it with
       a confirm, then `complete()` the delivery.
4. Replies go to the default exchange (`""`) with routing key `request.reply_to` and
   `correlation_id = str(run_id)`. A request without `reply_to` is still run and
   persisted, and its replies are skipped.
5. `async def stop(self)` is the drain. It cancels the consumer and lets active runs
   finish for up to `grace_seconds`. It then stops the runs still going; each one's
   result is `ABANDONED`, written, published and completed.
6. The host calls `record_consumer_iteration()` and `record_message_settled()` through
   the amqp client. It never interprets capacity and never reads events for meaning.

## Where to change
- The new module and its interface.

## Acceptance criteria
- [ ] All tests use `InMemoryAmqpClient` and the R21 fake engine script.
- [ ] Each rule 3a–3h has a test. Rule b must show that no second process started.
- [ ] Every completed delivery happened after its result was persisted and published.
- [ ] The drain abandons in-flight runs after the grace period.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_host.py`:
  - `test_runs_a_request_and_replies_accepted_progress_result`
  - `test_malformed_request_is_dead_lettered`
  - `test_redelivery_of_an_active_run_starts_nothing`
  - `test_persisted_result_is_republished_not_rerun`
  - `test_non_terminal_run_dir_is_abandoned`
  - `test_late_request_is_rejected`
  - `test_unsafe_request_is_rejected`
  - `test_higher_attempt_supersedes_the_older_run`
  - `test_different_key_on_a_busy_worktree_is_rejected`
  - `test_deadline_stops_the_run`
  - `test_result_is_persisted_before_ack`
  - `test_drain_abandons_after_grace`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The control, probe and dead-letter consumers (R23).
- The CLI (R27).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R04, R21.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/host.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/host_interface.py` (new)
  - `tests/infrastructure/loop_service/test_host.py` (new)
- **Parallel-safe with:** R11, R12, R15 and R24. R23 extends `host.py` after it.
- **Must keep passing unchanged:**
  - R21 tests
  - the `vibey_bootstrap` amqp tests
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
