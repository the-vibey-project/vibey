## Title
feat(db): migration 0014 adds dispatch generations and the job outbox

## Why
ADR-0044 §4. The RabbitMQ backend needs a **dispatch generation** on every job.
`dispatch_seq = 0` means the job was never dispatched, and every new dispatch episode
increments it. It also needs a transactional outbox table in the family's outbox shape
(`vibey_bootstrap/db/outbox.py:31-42`), plus `claimed_at` so that a dead relay's
claims can be reclaimed.

The PostgreSQL backend ignores both, so this migration changes no behaviour.
Migrations are forward-only and are applied by `build_app()` under the migration lock
(`docs/plans/data-model.md` §7). `test_orm.py` requires every migrated relation to
have an ORM model (`tests/infrastructure/db/test_orm.py:50-53`, `:86-104`).

## Required behaviour
1. `migrations/0014_job_dispatch.sql` must be valid on PostgreSQL 14:
   ```sql
   -- Dispatch generations and the dispatch outbox (ADR-0044 §4).
   ALTER TABLE job ADD COLUMN dispatch_seq bigint NOT NULL DEFAULT 0;
   ALTER TABLE job ADD COLUMN dispatched_at timestamptz;
   CREATE INDEX job_ready_dispatch ON job (dispatched_at) WHERE state = 'ready';
   CREATE TABLE job_outbox (
       id               uuid PRIMARY KEY,
       idempotency_key  text UNIQUE NOT NULL,
       payload          jsonb NOT NULL,
       status           text NOT NULL DEFAULT 'pending',
       attempt_count    integer NOT NULL DEFAULT 0,
       last_error       text,
       created_at       timestamptz NOT NULL DEFAULT now(),
       sent_at          timestamptz,
       claimed_at       timestamptz,
       CONSTRAINT job_outbox_status CHECK (status IN ('pending','sending','sent','failed'))
   );
   CREATE INDEX job_outbox_pending ON job_outbox (created_at) WHERE status = 'pending';
   ```
2. `JobOrm` (`orm_models.py:237`) gains two fields:
   - `dispatch_seq: int` (BigInteger, `server_default=text("0")`, not null)
   - `dispatched_at: datetime | None` (timezone-aware)

   It also declares the `job_ready_dispatch` index. A new `JobOutboxOrm(VibeyOrmModel, table=True)`
   mirrors the table, and it is added to `ORM_TABLE_MODELS` (`:678`).
3. `EXPECTED_TABLE_NAMES` in `tests/infrastructure/db/test_orm.py:18` gains
   `"job_outbox"`. This is the only edit to an existing test file in this lane.
4. `JobRecord` and `PostgresJobRepository` are unchanged. `SELECT *` returning extra
   columns is harmless, because `_row_to_job_record` reads columns by name
   (`job_repository.py:20-42`).

## Where to change
- `migrations/0014_job_dispatch.sql`
- `src/vibey/infrastructure/db/orm_models.py`: copy `HumanGateOrm` (`:553`) for the
  new model, and the `JobOrm` column style for the new columns.
- `tests/infrastructure/db/test_orm.py:18`
- `tests/infrastructure/db/test_migrator.py`: add the new test

## Acceptance criteria
- [ ] A fresh database migrates. A second apply is a no-op. The checksum guard is unchanged.
- [ ] `test_orm_columns_match_every_migrated_relation` passes with the new columns and table.
- [ ] The chaos test and `test_job_repository.py` pass unchanged.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_migrator.py`:
  `test_job_dispatch_migration_adds_generation_and_outbox`. It asserts that
  `job.dispatch_seq` defaults to 0 on an inserted row, that `job_outbox` exists, and
  that the `status` CHECK refuses `'bogus'`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Writing or reading `dispatch_seq` and `job_outbox` (R10, R11).
- `docs/plans/data-model.md` (R35).
- CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `migrations/0014_job_dispatch.sql` (new)
  - `src/vibey/infrastructure/db/orm_models.py`
  - `tests/infrastructure/db/test_orm.py` (the `EXPECTED_TABLE_NAMES` constant only)
  - `tests/infrastructure/db/test_migrator.py` (one new test)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - every existing test in `tests/infrastructure/db/test_migrator.py`
  - `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected)
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - `tests/infrastructure/db/test_forward_compatibility_columns.py`
  - the PostgreSQL 14–18 compatibility set in `ci.yml:188-193`
  - all protected tests
- **Standing constraints:** see the list above.

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
