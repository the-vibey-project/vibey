## Title
feat(db): enqueue and dependency release record their dispatches

## Why
ADR-0044 §4. When a job becomes claimable it must get a dispatch generation and an
outbox row **in the same transaction** as the state change. There are two such moments:

- it is enqueued with every dependency already met;
- the ack of its last dependency commits.

Otherwise a crash between the commit and the publish could lose the dispatch.
`PostgresJobRepository` already owns the enqueue SQL
(`src/vibey/infrastructure/db/job_repository.py:66-134`) and the fenced ack
(`:223-235`). The RabbitMQ backend reuses both through a subclass and adds only the
dispatch-writing steps. The PostgreSQL backend class is not modified.

*(Amended 2026-09-22 for the ORM wave, draft ADR `specs/ADR-orm.md`: this lane lands after
`orm-job-settle`, so `PostgresJobRepository` takes `PostgresOrmInterface`, its
`_enqueue_on` receives an SQLAlchemy `AsyncConnection`, and its statements are Core
(`JOB_SQL`, `src/vibey/infrastructure/db/job_statements.py`). The SQL blocks below state
each statement's semantics; the code builds them as Core. Semantics unchanged.)*

## Required behaviour
1. `class DispatchOutboxWriter` has one method,
   `async def write(conn: AsyncConnection, dispatch: JobDispatch, *, key_suffix: str = "") -> bool`.
   It builds
   `vibey_bootstrap.db.outbox.AsyncOutbox(conn, table="job_outbox", track_claims=True)`
   (from R05) and enqueues the idempotency key `f"dispatch:{dispatch.job_id}:{dispatch.dispatch_seq}{key_suffix}"`
   with payload `JobDispatchCodec().encode(dispatch)` (from R06). It returns whether a
   row was inserted.
2. `class DispatchingJobRecords(PostgresJobRepository)` takes `orm: PostgresOrmInterface` and
   `writer: DispatchOutboxWriterInterface`.
3. It overrides `_enqueue_on(conn, request, enqueued)` (`conn` is the `AsyncConnection` of
   the caller's transaction). It calls `super()._enqueue_on(...)` first, then executes
   `DISPATCH_SQL.first_dispatch(record.id)` (item 7) in the same transaction. Its semantics:
   ```sql
   UPDATE job SET dispatch_seq = 1, dispatched_at = NULL
   WHERE id = $1 AND state = 'ready' AND dispatch_seq = 0
     AND NOT EXISTS (SELECT 1 FROM job_dependency d JOIN job p ON p.id = d.depends_on_job_id
                     WHERE d.job_id = job.id AND p.state <> 'succeeded')
   RETURNING id, project_id, dispatch_seq, kind, run_after
   ```
   A returned row gets one outbox row with `not_before = run_after`. A replayed
   enqueue, where the row exists and `dispatch_seq` is already ≥ 1, writes nothing.
4. `async def ack_and_release(self, job_id, *, owner) -> tuple[bool, tuple[JobDispatch, ...]]`
   runs one transaction:
   - Execute `JOB_SQL.ack(job_id, owner=owner)` (the Core form of today's fenced ACK). If
     its `rowcount` is not 1, return `(False, ())` and change nothing else.
   - Otherwise execute `DISPATCH_SQL.release_dependents(job_id)` (item 7). Its semantics:
     ```sql
     UPDATE job j SET dispatch_seq = 1, dispatched_at = NULL
     WHERE j.state = 'ready' AND j.dispatch_seq = 0
       AND EXISTS (SELECT 1 FROM job_dependency d WHERE d.job_id = j.id AND d.depends_on_job_id = $1)
       AND NOT EXISTS (SELECT 1 FROM job_dependency d JOIN job p ON p.id = d.depends_on_job_id
                       WHERE d.job_id = j.id AND p.state <> 'succeeded')
     RETURNING j.id, j.project_id, j.dispatch_seq, j.kind, j.run_after
     ```
   - Write one outbox row per released job, and return `(True, dispatches)`.
5. `ack()` is overridden to `return (await self.ack_and_release(job_id, owner=owner))[0]`,
   so the class still satisfies the `JobRepository` Protocol
   (`application/interfaces/queue.py:89`).
6. The class never publishes. Publishing belongs to the relay (R13).
7. `class DispatchStatements` (stateless; `DISPATCH_SQL: Final[DispatchStatementsInterface] = DispatchStatements()`)
   builds both statements in Core over `JOBS = TABLES.table("job")` and
   `DEPENDENCIES = TABLES.table("job_dependency")`, reusing the shared unmet-dependency
   clause `JOB_SQL.deps_unmet(JOBS)` instead of restating it:
   - `first_dispatch(job_id)`: `update(JOBS).where(JOBS.c["id"] == job_id, JOBS.c["state"] == "ready", JOBS.c["dispatch_seq"] == 0, ~JOB_SQL.deps_unmet(JOBS)).values(dispatch_seq=1, dispatched_at=None).returning(JOBS.c["id"], JOBS.c["project_id"], JOBS.c["dispatch_seq"], JOBS.c["kind"], JOBS.c["run_after"])`;
   - `release_dependents(job_id)`: the same `values`/`returning`, where
     `JOBS.c["state"] == "ready", JOBS.c["dispatch_seq"] == 0, exists().where(DEPENDENCIES.c["job_id"] == JOBS.c["id"], DEPENDENCIES.c["depends_on_job_id"] == job_id), ~JOB_SQL.deps_unmet(JOBS)`.
   SQLAlchemy correlates both `EXISTS` subqueries to the updated `job` row (checked against
   SQLAlchemy 2.0.53 on 2026-09-22). A returned row becomes a `JobDispatch` through R06's codec
   types; rows come from `.mappings().all()`.

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py`.
- The interface module declares `DispatchOutboxWriterInterface`,
  `DispatchingJobRecordsInterface` and `DispatchStatementsInterface`. Copy
  `infrastructure/db/interfaces/job_repository_interface.py` for the TYPE_CHECKING-only
  imports.
- `vibey.infrastructure.db.interfaces` is already in `.importlinter`'s
  `infrastructure-interfaces-declare-only` contract.

## Acceptance criteria
- [ ] Enqueueing a job with no dependencies gives `dispatch_seq = 1` and exactly one `pending` `job_outbox` row, whose payload decodes to the `JobDispatch`.
- [ ] Enqueueing again with the same key leaves one outbox row and `dispatch_seq = 1`.
- [ ] A job with an unmet dependency stays at `dispatch_seq = 0` with no outbox row.
- [ ] In a batch where B depends on A: A is at 1 and B at 0. A batch rolled back by a bad dependency key leaves no outbox rows.
- [ ] Acking A releases B (B goes to 1 with an outbox row). An ack by a non-owner releases nothing and returns `(False, ())`.
- [ ] A dependent with two dependencies is released only by the second ack.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_dispatch_records.py` (uses the `migrated_pool` and
  `project_id` fixtures from `tests/infrastructure/db/conftest.py:62-71`):
  - `test_claimable_enqueue_writes_one_dispatch`
  - `test_replayed_enqueue_writes_nothing_more`
  - `test_blocked_enqueue_writes_no_dispatch`
  - `test_batch_dispatches_only_its_claimable_rows`
  - `test_rolled_back_batch_leaves_no_outbox_rows`
  - `test_ack_releases_the_dependents_it_unblocks`
  - `test_non_owner_ack_releases_nothing`
  - `test_second_of_two_dependencies_releases`
  - `test_records_satisfy_the_job_repository_protocol`
- `tests/infrastructure/orm/test_dispatch_statements.py` (no database; compile with
  `sqlalchemy.dialects.postgresql.asyncpg.dialect()`):
  - `test_first_dispatch_requires_seq_zero_and_every_dependency_succeeded`
  - `test_release_names_only_the_dependents_of_the_acked_job`
  - `test_the_statements_are_their_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/infrastructure/orm/test_dispatch_statements.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The claim, nack, defer, reap and sweep transitions (R11).
- Publishing (R13).
- The PostgreSQL backend class.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R05, R06, R08, and `orm-job-settle` (amended 2026-09-22).
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/db/dispatch_records.py` (new)
  - `src/vibey/infrastructure/db/interfaces/dispatch_records_interface.py` (new)
  - `tests/infrastructure/db/test_dispatch_records.py` (new)
  - `tests/infrastructure/orm/test_dispatch_statements.py` (new)
- **Parallel-safe with:** R04, R07, R21 and R29. R11 follows it on the same file.
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected)
  - `tests/infrastructure/db/test_build_decompose_fan_out.py`
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
