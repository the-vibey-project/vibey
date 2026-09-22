## Title
feat(queue): the composition root selects the queue backend

## Why
ADR-0044 §1: `[queue] backend` chooses the backend in `bootstrap.py`, the one
composition root, and nowhere else. Selecting `rabbitmq` without an AMQP URL fails
loudly, naming the fix. There is no silent fallback, for the same reason ADR-0002
gives for `DatabaseNotConfigured` (`bootstrap.py:641-662`).

The worker learns its prefetch from `-j` only after `build_app` has run
(`cli/main.py:1699`). The drain must also return buffered deliveries on SIGTERM
(ADR-0025, ADR-0026).

## Required behaviour
1. `class QueueBackendSettings` has
   `from_sources(config: VibeyConfig | None, environ: Mapping[str, str]) -> QueueBackendSettings`.
   Its fields are `backend`, `amqp_url`, `vhost`, `prefix` and `rabbitmq`
   (`QueueRabbitMqConfig`). Precedence is: `VIBEY_QUEUE_BACKEND` and
   `VIBEY_BUS_AMQP_URL` first, then `config.queue` and `config.bus`, then the R01
   defaults.
2. `class QueueBackendNotConfigured(VibeyError)`. Its message contains both remedies
   verbatim:
   - `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/`
   - `export VIBEY_QUEUE_BACKEND=postgres`
3. `build_app`:
   - **postgres (the default):** everything as today. `wakeup` is R02's opener, and
     `queue_consumer` is a no-op `PostgresQueueConsumerControl`, whose `set_prefetch`
     and `drain` do nothing.
   - **rabbitmq:** with no `amqp_url`, raise `QueueBackendNotConfigured` before the
     database is used. Otherwise build (on `build_app`'s ORM seam `orm`, a
     `PostgresOrmInterface` — amended 2026-09-22 for the ORM wave; never on an asyncpg
     pool, even while `build_app` still holds one before `orm-bootstrap-engine` lands):
     - `AmqpClient(AmqpSettings(url))`, which connects lazily (R04);
     - `QueueNames(prefix)`, `RabbitMqJobTopology`, `WaitTierPlan`;
     - `DispatchingJobRecords(orm, writer=DispatchOutboxWriter())`;
     - `DispatchRelay` (with `orm`), `ProjectDeliveries`, `DispatchMissPolicy`;
     - `RabbitMqJobRepository` as `jobs`;
     - `PostgresHumanGateRepository(orm, dispatch_writer=DispatchOutboxWriter())` as
       `gates`;
     - a wakeup opener that returns `RabbitMqJobWakeup(deliveries)`;
     - `queue_consumer = RabbitMqQueueConsumerControl(deliveries)`, whose
       `set_prefetch(n)` calls `deliveries.set_prefetch(n)` and whose `drain()` calls
       `await jobs.stop()`.

     The AMQP client is closed in `build_app`'s `finally`.
4. `AppResources` gains `queue_consumer: QueueConsumerControlInterface`, declared in
   `bootstrap_interface.py`.
5. `vibey worker`:
   - After computing `count` (`cli/main.py:1699`), call
     `resources.queue_consumer.set_prefetch(count)`.
   - When the drive loops end, call `await resources.queue_consumer.drain()` in the
     existing `finally`, before closing the notifier.
6. With the default backend, nothing observable changes.

## Where to change
- `src/vibey/bootstrap.py` (`AppResources` `:134-171`, `build_app` `:694-916`).
- `src/vibey/bootstrap_interface.py`.
- `src/vibey/cli/main.py:1699-1760`.
- Put `QueueBackendSettings` and the two consumer-control classes in
  `src/vibey/infrastructure/queue/selection.py`, with their interfaces, so that
  `bootstrap.py` stays wiring.

## Acceptance criteria
- [ ] With no queue keys set, `build_app` yields `PostgresJobRepository`, and the whole existing suite passes unchanged.
- [ ] With `VIBEY_QUEUE_BACKEND=rabbitmq` and no URL, the start fails with `QueueBackendNotConfigured`, and its message holds both remedies.
- [ ] With the backend and a URL set, `build_app` yields `RabbitMqJobRepository`, and the gates carry a dispatch writer. No connection is made until first use.
- [ ] `vibey worker -j 3` calls `set_prefetch(3)`, and it calls `drain()` on exit.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/test_bootstrap.py`:
  - `test_default_backend_is_postgres`
  - `test_rabbitmq_without_url_names_both_remedies`
  - `test_rabbitmq_with_url_composes_the_rabbitmq_backend`
  - `test_env_beats_config_for_the_backend`
- `tests/infrastructure/queue/test_selection.py`:
  - `test_consumer_controls_forward_prefetch_and_drain`
  - `test_postgres_consumer_control_is_a_no_op`
- `tests/cli/test_operational_commands.py` (new tests):
  - `test_worker_sets_prefetch_to_its_parallelism`
  - `test_worker_drains_the_queue_consumer_on_exit`

  Use the existing notifier patch pattern from `:1255`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/queue tests/system/test_full_worker_faked.py tests/infrastructure/test_operator_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Flipping the default (R34).
- The chart (R29–R31).
- Loop services.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R01, R02, R16.
- **Wave:** 6.
- **Files touched:**
  - `src/vibey/bootstrap.py`
  - `src/vibey/bootstrap_interface.py`
  - `src/vibey/cli/main.py`
  - `src/vibey/domain/errors.py` (or `bootstrap.py`, beside `DatabaseNotConfigured`)
  - `tests/test_bootstrap.py`
  - `tests/cli/test_operational_commands.py` (new tests only)
- **Parallel-safe with:** the loop-service lanes, but not with R27 or R28, which share `bootstrap.py` and `cli/main.py`.
- **Must keep passing unchanged:**
  - `tests/cli/*`
  - `tests/test_bootstrap.py`
  - `tests/system/test_full_worker_faked.py`
  - `tests/infrastructure/test_operator_handlers.py`
  - the whole suite, which runs on the default `postgres` backend
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
