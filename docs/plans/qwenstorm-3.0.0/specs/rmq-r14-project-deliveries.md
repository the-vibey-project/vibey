## Title
feat(queue): buffer a project's deliveries, hold them as leases, and wake the worker

## Why
ADR-0044 §5 and §11. In the RabbitMQ backend the broker's lease is a *held delivery*:
a message pushed under `basic.qos prefetch = worker parallelism`, kept unacknowledged
while its job runs. Four things follow:

- a worker's `claim()` takes the next *buffered* delivery;
- the same push is the wakeup that replaces `LISTEN vibey_job_ready`
  (`src/vibey/infrastructure/db/notifier.py:16-51`);
- on SIGTERM, deliveries that were buffered but never claimed must go back to the
  queue at once (ADR-0025, ADR-0026);
- held deliveries settle as their jobs finish.

## Required behaviour
1. `class ProjectDeliveries(client, topology, *, prefetch: int = 1)`:
   - `set_prefetch(n: int)` is allowed only before the first `ensure_started`. It
     raises `RuntimeError` afterwards, and `ValueError` for `n < 1`.
   - `async def ensure_started(project_id)` runs once per instance. It calls
     `topology.declare_project` and `client.consume(queue, prefetch=..., handler=...)`.
     The handler appends each delivery to an `asyncio.Queue` and sets an
     `asyncio.Event`. Only one project per instance is allowed; a second project id
     raises `RuntimeError`, because a worker serves one project (`cli/main.py:1549-1566`).
   - `next_buffered() -> AmqpDeliveryInterface | None` takes the next delivery without
     waiting, and clears the event when the buffer empties.
   - `async def wait_buffered(timeout: timedelta) -> bool`.
   - `hold(job_id, delivery)` records the delivery as the job's broker lease.
   - `async def settle_held(job_id) -> bool` completes (acks) the held delivery and
     forgets it. It returns `False` if nothing is held.
   - `async def stop() -> int` cancels the consumer, abandons every buffered-but-unheld
     delivery (`nack(requeue=True)`), and returns how many it returned. Held deliveries
     are left alone; their jobs are still running.
2. `class RabbitMqJobWakeup(deliveries)` implements `JobReadyNotifier`
   (`application/interfaces/queue.py:81-86`).
   `wait_for_job_ready(project_id, *, timeout)` calls `ensure_started` and returns
   `wait_buffered(timeout)`: `True` when a delivery was pushed, `False` on timeout.

## Where to change
- The two new modules and their interfaces.

## Acceptance criteria
- [ ] Using the in-memory client, no more than `prefetch` deliveries are ever unsettled.
- [ ] `hold` and `settle_held` ack exactly the held one.
- [ ] `stop()` returns buffered deliveries with their delivery count incremented, and keeps held ones.
- [ ] A second project id raises.
- [ ] `set_prefetch` after start raises.
- [ ] The wakeup returns `True` on a push and `False` on a timeout.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_project_deliveries.py`:
  - `test_prefetch_bounds_the_buffer`
  - `test_hold_then_settle_acks_that_delivery`
  - `test_stop_returns_unheld_buffered_deliveries`
  - `test_one_project_per_instance`
  - `test_prefetch_is_fixed_once_started`
- `tests/infrastructure/queue/test_rabbitmq_wakeup.py`:
  - `test_wakes_on_push`
  - `test_times_out_without_push`
  - `test_wakeup_satisfies_job_ready_notifier`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The claim logic (R16).
- CLI wiring (R17).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R12.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/queue/{project_deliveries,rabbitmq_wakeup}.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/{project_deliveries_interface,rabbitmq_wakeup_interface}.py` (new)
  - `tests/infrastructure/queue/{test_project_deliveries,test_rabbitmq_wakeup}.py` (new)
- **Parallel-safe with:** R13, R23, R25 and R26.
- **Must keep passing unchanged:**
  - R12 tests
  - `tests/infrastructure/db/test_notifier.py`
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
