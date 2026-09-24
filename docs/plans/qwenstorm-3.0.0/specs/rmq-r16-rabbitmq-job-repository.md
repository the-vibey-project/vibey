## Title
feat(queue): RabbitMqJobRepository, the RabbitMQ backend of the job queue

## Why
ADR-0044 §1, §5, §8 and §11. This lane composes the pieces into the `JobRepository`
Protocol (`src/vibey/application/interfaces/queue.py:89-186`):

- the fenced records (R10, R11);
- the relay (R13);
- the held deliveries (R14);
- the miss policy (R07).

`WorkerLoop` (`application/worker.py:130-312`) must run on it unchanged. That is the
point of the port.

## Required behaviour
1. `class RabbitMqJobRepository` is constructed with:
   - `records: DispatchingJobRecordsInterface`
   - `relay: DispatchRelayInterface`
   - `deliveries: ProjectDeliveriesInterface`
   - `policy: DispatchMissPolicyInterface`
   - `codec: JobDispatchCodecInterface`
   - `client: AmqpClientInterface`, used only to read the dead queue
   - `names: QueueNamesInterface`
   - `settings: QueueRabbitMqConfigInterface`
   - `clock: Clock`
   - `logger: Logger`
2. The read and write methods that involve no broker delegate straight to `records`:
   `enqueue`, `enqueue_batch`, `list_for_cycle`, `heartbeat`, `grant_attempts`,
   `assign_engine`, `count_unsettled`, `queue_depth`, `get` and `recover_leased` (the
   port method `orm-cli-recover` added for `vibey recover`; amended 2026-09-22). `enqueue`
   and `enqueue_batch` then `await relay.flush_soon()`. A recovered job keeps its dispatch
   generation and gets no outbox row; if its message is gone, R11's lost-dispatch sweep
   re-dispatches it after `redispatch_after`.
3. `claim(project_id, *, owner, lease)`:
   - Call `await deliveries.ensure_started(project_id)`. On the **first** claim of
     this instance, if nothing is buffered, `await deliveries.wait_buffered(first_claim_wait_seconds)`.
   - Then loop:
     - `d = deliveries.next_buffered()`; if it is `None`, return `None`.
     - Decode `d.body`. On `MalformedDispatch`, or a dispatch whose `project_id` is not
       `project_id`, call `d.dead_letter()`, log `queue.malformed_dispatch`, and
       continue.
     - `job = records.claim_dispatched(dispatch, owner=owner, lease=lease)`. If there
       is a job: `deliveries.hold(job.id, d)` and return it.
     - Otherwise:
       - Call `decision = policy.decide(await records.snapshot(dispatch.job_id), dispatch.dispatch_seq, clock.now())`.
       - On `REDELAY`, call `relay.publish(replace(dispatch, not_before=decision.not_before))`
         and then `d.complete()`. If the publish raises, call `d.abandon()` instead and
         return `None`, so the message is never lost.
       - On `DROP`, call `d.complete()`.
       - Log `queue.dispatch_missed` with the reason at `info`, and continue.
4. `ack`, `nack`, `defer` and `park` each call the matching `records` method, then
   **always** `await deliveries.settle_held(job_id)`, whether or not the write landed
   (a refused write means the delivery is stale), then `await relay.flush_soon()`.
   Each returns the records method's boolean.
5. `reap()` is the reconciler, and it is throttled to run at most once per
   `reconcile_interval_seconds` by `clock`. When throttled it returns 0. Otherwise it
   runs, in order:
   - `n = records.reap()`
   - `records.sweep_lost(redispatch_after=...)`
   - `relay.drain()`
   - drain up to 100 dead pointers: `d = await client.get(names.dead_queue())` until it
     returns `None`. Decode each one, call
     `records.park_dead_letter(dispatch, delivery_limit=settings.delivery_limit)`, then
     `d.complete()`. A malformed dead pointer is completed and logged at `warning` with
     its first 200 bytes.

   It returns `n`. Every step's exception is logged and does not stop the later steps.
6. `stop()` returns `await deliveries.stop()`, for the drain.

## Where to change
- The new module and its interface. Copy the settle-then-log discipline of
  `WorkerLoop._landed` (`worker.py:425-442`): log refused writes and never raise.

## Acceptance criteria
- [ ] Using a real Postgres and the in-memory broker, one `WorkerLoop` (`application/worker.py`) runs enqueue → claim → handler `Success` → ack. The job is `succeeded` and the delivery acked.
- [ ] A `Park` leaves no delivery. Answering the gate (with R15's writer) makes the job claimable again after `reap()`.
- [ ] A `Defer` re-delays the job, and it is claimable after `expire()` of its tier.
- [ ] A stale-generation delivery is dropped. A live-lease delivery is re-delayed.
- [ ] A malformed delivery is dead-lettered.
- [ ] `reap()` parks a dead-lettered pointer's job as `delivery_exhausted`.
- [ ] `reap()` is throttled.
- [ ] The instance satisfies `JobRepository` (`isinstance`).
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_rabbitmq_job_repository.py`:
  - `test_worker_loop_runs_a_job_end_to_end`
  - `test_park_holds_no_delivery_and_answer_redispatches`
  - `test_defer_redelays_through_a_tier`
  - `test_stale_generation_is_dropped`
  - `test_live_lease_is_redelayed`
  - `test_redelay_publish_failure_abandons_instead_of_losing`
  - `test_malformed_delivery_is_dead_lettered`
  - `test_reap_parks_dead_lettered_jobs`
  - `test_reap_is_throttled`
  - `test_settles_even_when_the_write_was_refused`
  - `test_repository_satisfies_the_port`
  - `test_recover_leased_delegates_to_the_records`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue tests/fakes tests/application/test_worker.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Selecting this backend (R17).
- The contract suite (R18).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R11, R13, R14, R15, and `orm-cli-recover` (amended 2026-09-22: the port gained `recover_leased`).
- **Wave:** 5.
- **Files touched:**
  - `src/vibey/infrastructure/queue/rabbitmq_job_repository.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/rabbitmq_job_repository_interface.py` (new)
  - `tests/infrastructure/queue/test_rabbitmq_job_repository.py` (new)
- **Parallel-safe with:** nothing in `infrastructure/queue` (it imports all of it). The loop-service lanes can run beside it.
- **Must keep passing unchanged:**
  - `tests/fakes/test_port_parity.py`
  - `tests/application/test_worker.py`
  - `tests/infrastructure/db/*`
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
- **Persistence goes through the ORM (amended 2026-09-22):** no new `import asyncpg`,
  `text()`, `exec_driver_sql()` or SQL string in `src/vibey`; statements are SQLAlchemy Core
  over the SQLModel tables (`TABLES.table(...)`), executed on a connection from
  `PostgresOrmInterface` (draft ADR `specs/ADR-orm.md`).

---
