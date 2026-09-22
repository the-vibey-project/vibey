## Title
feat(queue): declare the RabbitMQ topology for jobs

## Why
ADR-0044 §2 names every exchange and queue the job backend uses. It also fixes their
arguments:

- quorum work queues with a delivery limit, at-least-once dead-lettering and a
  per-queue consumer timeout;
- TTL wait tiers that dead-letter back into the dispatch exchange;
- one dead queue.

Declaring them in code at start is sub-doctrine 12.c: the topology is declared, not
clicked. This lane also carries the first integration checks of the upstream facts the
ADR says it owes (the pinned `rabbitmq:4-management-alpine`, `values.yaml:434-440`).

## Required behaviour
1. `class RabbitMqJobTopology(client: AmqpClientInterface, names: QueueNamesInterface, settings: QueueRabbitMqConfigInterface)`.
2. `async def declare_base(self) -> None` declares:
   - exchanges `names.jobs_exchange()` (topic), `names.wait_exchange()` (topic) and
     `names.dead_exchange()` (fanout);
   - the queue `names.dead_queue()` with `{"x-queue-type": "quorum"}`, bound to the
     dead exchange with key `""`;
   - for every tier in `settings.wait_tiers_seconds`, the queue
     `names.wait_queue(t)` with `{"x-queue-type": "classic", "x-message-ttl": t*1000, "x-dead-letter-exchange": names.jobs_exchange()}`,
     bound with `names.wait_binding(t)`.

   It is idempotent, and it runs its declarations once per instance.
3. `def project_arguments(self) -> dict[str, object]` returns exactly:
   ```python
   {"x-queue-type": "quorum", "x-delivery-limit": delivery_limit,
    "x-dead-letter-exchange": names.dead_exchange(),
    "x-dead-letter-strategy": "at-least-once", "x-overflow": "reject-publish",
    "x-consumer-timeout": consumer_timeout_seconds * 1000}
   ```
4. `async def declare_project(self, project_id: UUID) -> str` calls `declare_base()`
   if needed. It then declares `names.project_queue(pid)` with `project_arguments()`,
   binds both of `names.project_bindings(pid)` to the jobs exchange, and caches the
   project id. It returns the queue name.
5. `.importlinter`: `vibey.infrastructure.queue.interfaces` joins the
   `source_modules` of `[importlinter:contract:infrastructure-interfaces-declare-only]`
   (`.importlinter:98-120`).
6. `tests/infrastructure/queue/conftest.py` re-exports the database fixtures, so that
   later lanes can use Postgres here:
   `from tests.infrastructure.db.conftest import database_url, pg_pool, migrated_pool, project_id  # noqa: F401`.
   It also provides `amqp_url` (skip unless `VIBEY_TEST_AMQP_URL` is set) and
   `memory_amqp` (a fresh `InMemoryAmqpClient`).

## Where to change
- The new package. Copy the layout of `src/vibey/infrastructure/bus/`
  (`rabbitmq.py` + `interfaces/rabbitmq_interface.py`).
- `.importlinter:98-120`.

## Acceptance criteria
- [ ] Against the in-memory client, every exchange, queue, argument and binding in behaviours 2–4 is declared exactly once, however often it is called.
- [ ] A message published to `job.<pid>` lands in the project queue. A message published to `names.wait_key(1, pid)` lands in `vibey.jobs.wait.w1s`, and after `expire()` it lands in the project queue.
- [ ] Integration, with a real broker: the declarations succeed, including `x-consumer-timeout` and `x-delivery-limit` on a quorum queue; a declaration made twice succeeds; a message sent to the 1 s wait tier reaches the project queue within 3 s.
- [ ] `lint-imports` passes, and so does `test_import_contracts_bind.py`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_rabbitmq_topology.py`:
  - `test_declare_base_declares_exchanges_dead_queue_and_tiers`
  - `test_project_arguments_are_exact`
  - `test_declare_project_binds_both_keys_and_is_idempotent`
  - `test_wait_tier_expiry_routes_back_to_the_project_queue`
  - `test_topology_satisfies_its_interface`
- `tests/infrastructure/queue/test_rabbitmq_topology_integration.py` (integration):
  - `test_real_broker_accepts_every_argument`
  - `test_real_wait_tier_returns_the_message`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue tests/meta/test_import_contracts_bind.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Loop-service topology (R22 and R23).
- Publishing and consuming (R13, R14).
- The chart.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R04, R06.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/queue/__init__.py` (new)
  - `src/vibey/infrastructure/queue/rabbitmq_topology.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/{__init__,rabbitmq_topology_interface}.py` (new)
  - `.importlinter`
  - `tests/infrastructure/queue/{__init__,conftest,test_rabbitmq_topology,test_rabbitmq_topology_integration}.py` (new)
- **Parallel-safe with:** R11, R15, R22 and R24. It is last in the `.importlinter` chain, after R21.
- **Must keep passing unchanged:**
  - `tests/meta/test_import_contracts_bind.py`
  - `tests/infrastructure/test_sovereign_surfaces.py`
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
