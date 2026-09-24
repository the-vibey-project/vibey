## Title
feat(bootstrap): an async outbox over SQLAlchemy's AsyncConnection, in Core

## Why
ADR-0044 §4 dispatches jobs through a transactional outbox written **inside the same
transaction** as the job's state change. vibey's persistence goes through SQLAlchemy 2
async over the asyncpg driver, behind its ORM seam (draft ADR `specs/ADR-orm.md`; lanes
`orm-*`), so that transaction is an `sqlalchemy.ext.asyncio.AsyncConnection`.

The family's outbox (`vibey_bootstrap/db/outbox.py:57-183`) has two gaps:

- it is sync SQLAlchemy only, with SQL text built by f-string (`text(f"… {self._table} …")`,
  guarded by `_validate_identifier` and `# nosec B608`);
- a row a relay claimed as `sending` stays `sending` forever if that relay dies before
  `mark_sent` (`:97-112`, `:147-183`).

Sub-doctrine 10.e says to close the gap in the family's package. The sync API stays
exactly as it is. The new async half is written as SQLAlchemy **Core** over a `Table`
object — no SQL strings — so it satisfies the ORM rule vibey holds itself to, and it takes
the caller's `AsyncConnection`, so it joins whatever transaction the caller opened.

*(Amended 2026-09-22 for the ORM wave: the executor Protocol shaped like asyncpg and the
`$n` SQL are replaced by an `AsyncConnection` and Core statements. Semantics unchanged.)*

## Required behaviour
1. `class OutboxSchema` has two methods. The table name is validated by
   `_validate_identifier` (`:24-28`) in both.
   - `ddl(table: str, *, tracked: bool) -> str`: `tracked=False` returns exactly the
     existing `OUTBOX_DDL` text with the table name substituted; `tracked=True` adds a
     column `claimed_at TIMESTAMPTZ` and a constraint
     `CHECK (status IN ('pending','sending','sent','failed'))`.
   - `table(name: str, *, tracked: bool) -> Table`: the same columns as a SQLAlchemy
     `Table` on a private `MetaData()` (`id` UUID primary key, `idempotency_key` Text unique
     not null, `payload` JSONB not null, `status` Text not null, `attempt_count` Integer not
     null, `last_error` Text, `created_at` and `sent_at` `DateTime(timezone=True)`, plus
     `claimed_at` when tracked). It describes an existing table for statements; it is never
     used to create one (no `create_all`).
2. `class AsyncOutbox(conn: AsyncConnection, *, table: str = "outbox", track_claims: bool = False)`.
   It never begins, commits or rolls back: the connection's owner decides — the caller's
   transaction for a writer (R10), an autocommit connection for a relay (R13). Every
   statement is Core over `OutboxSchema().table(table, tracked=track_claims)` (build it once
   in `__init__`); `pg_insert` is `sqlalchemy.dialects.postgresql.insert`.
   - `enqueue(idempotency_key, payload) -> bool`:
     `pg_insert(t).values(id=uuid4(), idempotency_key=…, payload=payload, status="pending", attempt_count=0, created_at=func.now()).on_conflict_do_nothing(index_elements=[t.c["idempotency_key"]]).returning(t.c["id"])`;
     returns `True` when a row came back.
   - `claim_batch(limit, *, max_attempts=5) -> list[OutboxMessage]` is one statement that
     needs no long transaction:
     ```python
     pick = (select(t.c["id"]).where(t.c["status"] == "pending", t.c["attempt_count"] < max_attempts)
             .order_by(t.c["created_at"]).limit(limit).with_for_update(skip_locked=True))
     update(t).where(t.c["id"].in_(pick)).values(status="sending"[, claimed_at=func.now()]).returning(*t.c)
     ```
     Rows map to `OutboxMessage` (`id=str(row["id"])`; `payload` decoded if it arrives as text).
   - `mark_sent(msg_id)` and `mark_failed(msg_id, error, *, max_attempts=5)` behave as the
     sync methods do (`:114-144`), as `update(t)` statements; the failed status is
     `case((t.c["attempt_count"] + 1 >= max_attempts, "failed"), else_="pending")`.
   - `reclaim_stale(older_than_seconds: float) -> int` returns `sending` rows whose
     `claimed_at` is older than `func.now() - literal(timedelta(seconds=older_than_seconds), Interval())`
     to `pending`, and returns `result.rowcount`. It raises `ValueError` unless
     `track_claims=True`.
3. `class AsyncOutboxDrainer(outbox, sender)`, where `sender` is
   `Callable[[OutboxMessage], Awaitable[None]]`. `drain(limit) -> int` claims a batch and
   sends each row: a success is marked sent, and an exception is marked failed and logged,
   never raised. It returns the count sent.
4. The `outbox.*` counters are bumped exactly as the sync class bumps them.
5. Interfaces (family style: `ABC`s, as `vibey_bootstrap/services/interfaces/*`):
   `AsyncOutboxInterface`, `AsyncOutboxDrainerInterface` and `OutboxSchemaInterface` in
   `vibey_bootstrap/db/interfaces/outbox_interface.py`, exported from
   `vibey_bootstrap/db/interfaces/__init__.py` (the package lane `orm-bootstrap-async-engine`
   created). Each class subclasses its interface.
6. `OUTBOX_DDL`, `Outbox`, `OutboxMessage` and `drain_outbox` are unchanged. Add the
   new names to `__all__` (`:186`). SQLAlchemy is imported lazily inside methods, as the
   sync code does, so importing the module still needs no SQLAlchemy.

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/outbox.py`
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/interfaces/outbox_interface.py` (new)
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/interfaces/__init__.py`
- Copy the ordering and filter of `drain_outbox` (`:159-165`) for the claim sub-select.

## Acceptance criteria
- [ ] Every statement, compiled with `sqlalchemy.dialects.postgresql.asyncpg.dialect()`, is asserted: `ON CONFLICT (idempotency_key) DO NOTHING`, `FOR UPDATE SKIP LOCKED` inside the claim's `IN (…)`, `claimed_at` stamped only when tracked, and every value a bound parameter.
- [ ] `grep -n "text(f\|nosec" src/vibey_tools/bootstrap/vibey_bootstrap/db/outbox.py` shows only the unchanged sync code.
- [ ] Against a real PostgreSQL (integration, skipped without `VIBEY_TEST_DATABASE_URL`), two concurrent `claim_batch` calls on two autocommit connections never return the same row.
- [ ] Against a real PostgreSQL, `reclaim_stale` returns a stale `sending` row to `pending`.
- [ ] Against a real PostgreSQL, a duplicate `enqueue` returns `False`, and an `enqueue` inside a transaction that rolls back leaves no row.
- [ ] The existing sync tests pass untouched; the tenant keeps its 100% line floor.

## Tests to write first (TDD)
- `test/db/test_outbox_async.py`:
  - `test_schema_tracked_adds_claimed_at_and_check`
  - `test_schema_untracked_matches_outbox_ddl`
  - `test_schema_table_matches_the_ddl_columns`
  - `test_enqueue_is_idempotent_on_the_key` (compiled)
  - `test_claim_batch_skips_locked_rows_and_stamps_claimed_at` (compiled, tracked and untracked)
  - `test_reclaim_requires_tracking`
  - `test_drainer_marks_sent_and_failed_and_never_raises` (a small fake outbox subclassing `AsyncOutboxInterface`)
  - `test_concurrent_claims_are_disjoint` (integration; engine from `vibey_bootstrap.db.async_engine.ASYNC_ENGINES`)
  - `test_reclaim_returns_stale_rows` (integration)
  - `test_a_rolled_back_enqueue_leaves_nothing` (integration)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/db -m "not integration")
    (cd src/vibey_tools/bootstrap && VIBEY_TEST_DATABASE_URL=${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test} uv run python -m pytest -q -p no:cacheprovider --no-cov test/db/test_outbox_async.py -m integration)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
The third command is the whole suite: the tenant's 100% line floor is in its own pytest
`addopts`, so a partial run needs `--no-cov`.

## Out of scope
- vibey's `job_outbox` table (R08) and its writer (R10).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** `orm-bootstrap-async-engine` (the `vibey_bootstrap.db.interfaces` package and the engine factory the integration tests use).
- **Wave:** 1.
- **Files touched:**
  - `src/vibey_tools/bootstrap/vibey_bootstrap/db/outbox.py`
  - `src/vibey_tools/bootstrap/vibey_bootstrap/db/interfaces/outbox_interface.py` (new)
  - `src/vibey_tools/bootstrap/vibey_bootstrap/db/interfaces/__init__.py`
  - `src/vibey_tools/bootstrap/test/db/test_outbox_async.py` (new)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - `src/vibey_tools/bootstrap/test/db/test_outbox.py` (the sync API must not change)
  - the whole vibey-bootstrap suite
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
- **Persistence goes through the ORM (amended 2026-09-22):** no new `import asyncpg`,
  `text()`, `exec_driver_sql()` or SQL string in `src/vibey`; statements are SQLAlchemy Core
  over the SQLModel tables (`TABLES.table(...)`), executed on a connection from
  `PostgresOrmInterface` (draft ADR `specs/ADR-orm.md`).

---
