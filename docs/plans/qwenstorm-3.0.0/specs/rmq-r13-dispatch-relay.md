## Title
feat(queue): the outbox relay publishes each dispatch to the right exchange

## Why
ADR-0044 §4 and §7. The outbox rows R10 and R11 write must reach the broker with
publisher confirms. The relay is what gives at-least-once publish:

- a due dispatch goes straight to the dispatch exchange;
- a future dispatch goes to the largest wait tier no longer than its remaining delay;
- a row is marked sent, and the job's `dispatched_at` stamped, only after the confirm;
- rows a crashed relay left in `sending` are reclaimed through R05's `reclaim_stale`.

*(Amended 2026-09-22 for the ORM wave, draft ADR `specs/ADR-orm.md`: the relay reaches
PostgreSQL through `PostgresOrmInterface`, not an asyncpg pool, and R05's `AsyncOutbox`
takes an SQLAlchemy `AsyncConnection`. Semantics unchanged.)*

## Required behaviour
1. `class DispatchRelay` is constructed with:
   - `orm: PostgresOrmInterface` (`vibey.infrastructure.db.interfaces`)
   - `client: AmqpClientInterface`
   - `names: QueueNamesInterface`
   - `topology: RabbitMqJobTopologyInterface`
   - `tiers: WaitTierPlanInterface`
   - `records: DispatchingJobRecordsInterface`
   - `clock: Clock` (`application/interfaces`)
   - `logger: Logger`
2. `async def publish(self, dispatch: JobDispatch) -> None`:
   - Compute `remaining = dispatch.not_before - clock.now()` and
     `tier = tiers.choose(remaining)`.
   - Call `await topology.declare_project(dispatch.project_id)`.
   - When `tier is None`, publish to `names.jobs_exchange()` with key
     `names.project_key(pid)`. Otherwise publish to `names.wait_exchange()` with key
     `names.wait_key(tier, pid)`.
   - The body is `JobDispatchCodec().to_bytes(dispatch)`. The properties are
     `message_id=dispatch.message_id`, `type="job.dispatch"`,
     `correlation_id=DELIVERY_CORRELATION.for_project(pid).value` (from
     `domain/correlation.py`) and `delivery_mode=2`.
   - It raises `AmqpPublishError` on a failed confirm.
3. `async def drain(self, limit: int = 100) -> int`:
   - Open `async with self._orm.autocommit() as conn:` — an autocommit connection, so the
     claim commits before anything is published and every mark commits on its own, exactly
     as a bare connection behaved.
   - Call `AsyncOutbox(conn, table="job_outbox", track_claims=True).reclaim_stale(60)`.
   - Build an `AsyncOutboxDrainer` whose sender decodes the payload with the codec,
     calls `publish`, then calls `records.mark_dispatched(job_id, seq)`.
   - Return the count sent.
4. `async def flush_soon(self) -> None` calls `drain(20)`. It logs any exception at
   `warning` as `queue.relay_failed` and never raises. It is the best-effort fast path
   that runs after a commit.
5. A publish that fails leaves the row back at `pending` with `attempt_count+1`, via
   R05's `mark_failed`, and `dispatched_at` untouched.

## Where to change
- The new module, beside `rabbitmq_topology.py`, with its interface.

## Acceptance criteria
- [ ] With a real Postgres and the in-memory broker, a claimable enqueue followed by `drain()` puts one message in the project queue. The body decodes to the job's dispatch, and `dispatched_at` is set.
- [ ] A dispatch 90 s in the future goes to the `w30s` tier. After `expire()` it lands in the project queue with the routing key kept.
- [ ] A publish refusal returns the outbox row to `pending` and leaves `dispatched_at` NULL.
- [ ] A stale `sending` row is reclaimed and published.
- [ ] `flush_soon` never raises.
- [ ] Integration, with a real broker: the tier round trip keeps the routing key.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_dispatch_relay.py`:
  - `test_due_dispatch_goes_to_the_project_queue`
  - `test_future_dispatch_goes_to_the_largest_fitting_tier`
  - `test_expired_tier_message_reaches_the_project_queue`
  - `test_failed_publish_leaves_the_row_pending`
  - `test_stale_sending_row_is_reclaimed_and_sent`
  - `test_flush_soon_swallows_and_logs`
  - `test_real_broker_tier_round_trip` (integration)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue tests/infrastructure/db/test_dispatch_records.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Consuming (R14).
- The repository (R16).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R05, R08, R10, R12.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/queue/dispatch_relay.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/dispatch_relay_interface.py` (new)
  - `tests/infrastructure/queue/test_dispatch_relay.py` (new)
- **Parallel-safe with:** R14, R23, R25 and R26.
- **Must keep passing unchanged:**
  - R10, R11 and R12 tests
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
