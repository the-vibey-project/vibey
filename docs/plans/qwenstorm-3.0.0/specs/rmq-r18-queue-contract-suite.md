## Title
test(queue): one contract suite and a chaos twin prove both queue backends

## Why
ADR-0044 §16. A port with two implementations is only a port if one suite binds both.
`tests/contracts/` already runs a contract against more than one implementation
(`tests/contracts/test_rotation_cursor_contract.py`).

The protected chaos test (`tests/infrastructure/db/test_chaos.py:49-170`) pins the
PostgreSQL backend's tally: zero double commits, zero lost jobs, every job terminal.
The RabbitMQ backend needs the same tally with **channels killed**, not tasks
abandoned. It goes in a new file, because the protected one is never edited.

## Required behaviour
1. In `tests/contracts/test_job_queue_contract.py`, a fixture `queue` is parametrized
   over three backends:
   - `"postgres"`: `PostgresJobRepository`;
   - `"rabbitmq-memory"`: `RabbitMqJobRepository` over Postgres and
     `InMemoryAmqpClient`, which always runs;
   - `"rabbitmq"`: a real broker, skipped unless `VIBEY_TEST_AMQP_URL` is set.

   Each yields a `QueueHarness` with `repo`, `gates` and an `async def settle()`
   helper. For the RabbitMQ backends, `settle()` runs the relay's drain and, on the
   memory broker, `expire()` of every wait tier. For PostgreSQL it does nothing.
2. The contract tests assert identical observable behaviour across all three
   backends:
   - enqueue is idempotent;
   - an empty queue claims `None`;
   - a dependency blocks the claim until it succeeds;
   - a future `run_after` blocks the claim;
   - `ack` is fenced (a second owner is refused);
   - `defer(retry_at=now)` makes the job claimable again after `settle()`;
   - `park` holds the job, and `answer` makes it claimable again;
   - an expired lease is claimable again after `reap()` (and, on RabbitMQ, after `settle()`);
   - `grant_attempts` widens and never narrows;
   - `count_unsettled` and `queue_depth` agree across backends for the same script.
3. `tests/infrastructure/queue/test_rabbitmq_chaos.py`
   (`@pytest.mark.slow @pytest.mark.integration`, real broker only):
   - 8 workers, each with its own `ProjectDeliveries` and channel;
   - 300 jobs with `max_attempts=1000`;
   - with probability 0.2 a worker "crashes": it closes its consumer channel without
     settling;
   - a concurrent `reap()` loop runs every 50 ms with `reconcile_interval_seconds=0`.

   The asserted tally has the same shape as `test_chaos.py:136-170`: executions equal
   commits plus refused, no double commit, no lost job, every job `succeeded`. It also
   prints the tally.

## Where to change
- The two new test files only. Reuse the fixtures from `tests/contracts/conftest.py`
  and `tests/infrastructure/queue/conftest.py`.
- *(Amended 2026-09-22 for the ORM wave, draft ADR `specs/ADR-orm.md`.)* Build every
  backend on the contracts fixture `migrated_pool`: since lane `orm-test-harness` it is a
  `MigratedDatabase`, which is the ORM seam (`PostgresOrmInterface`) the repositories take
  and still an asyncpg pool for the tests' own observations. Test code may read and seed the
  database through that asyncpg side; nothing under `src/` may.

## Acceptance criteria
- [ ] The contract suite passes on `postgres` and `rabbitmq-memory` locally, and on all three in CI (R32).
- [ ] The chaos twin passes against a real broker.
- [ ] `git diff --stat develop -- tests/infrastructure/db/test_chaos.py` is empty.

## Tests to write first (TDD)
This lane is tests. Write the contract tests one by one against `postgres` first, then
enable the other parameters.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/contracts tests/infrastructure/queue tests/infrastructure/db/test_chaos.py
    git diff --stat HEAD~1 -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- CI wiring (R32).
- Production code. If a contract test exposes a backend difference, stop and report
  which backend is wrong. Do not weaken the test.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R17.
- **Wave:** 7.
- **Files touched:**
  - `tests/contracts/test_job_queue_contract.py` (new)
  - `tests/infrastructure/queue/test_rabbitmq_chaos.py` (new)
- **Parallel-safe with:** R27.
- **Must keep passing unchanged:**
  - `tests/contracts/test_rotation_cursor_contract.py`
  - `tests/infrastructure/db/test_chaos.py` (**protected; never edit it**)
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
