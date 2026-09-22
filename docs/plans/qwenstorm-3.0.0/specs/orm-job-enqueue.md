## Title
refactor(db): job enqueue, batch enqueue and the queue reads go through the ORM seam

## Why
Third of four job-queue lanes (draft ADR `specs/ADR-orm.md`). The enqueue-side statements
exist as Core (`JOB_SQL`, lane `orm-job-statements-enqueue`); this lane makes
`PostgresJobRepository` execute them through the ORM seam (`PostgresOrmInterface`). The
contract that must not move: `enqueue` is idempotent on `(project_id, idempotency_key)`;
`enqueue_batch` is **one** transaction, so a bad `depends_on_keys` entry, a constraint or a
killed worker rolls back every row the batch wrote (`job_repository.py:53-64`); the
`vibey_job_ready` notification is delivered at commit and not at all for a rolled-back
batch (`:129-133`). The claim and settle methods move in the next lane
(`orm-job-settle`); until then they keep running their own SQL on a pool the constructor
still accepts, and that lane removes it.

## Required behaviour
1. `PostgresJobRepository.__init__(self, orm: PostgresOrmInterface, *, pool: Any = None, rows: JobRowMapperInterface = JOB_ROWS)`:
   `self._orm = orm`; `self._rows = rows`; and, **transitionally**,
   `self._pool = pool if pool is not None else orm` with the comment
   `# transitional: the claim/settle methods still use a pool; orm-job-settle removes this`.
   (In tests the `migrated_pool` fixture is a `MigratedDatabase`, which is both the seam and
   a pool, lane `orm-test-harness`; in `build_app` the pool is passed explicitly.)
2. These methods go through `self._orm` and `JOB_SQL`, and nothing else in the class changes:
   - `enqueue`: `async with self._orm.transaction() as conn: return await self._enqueue_on(conn, request, {})`.
   - `enqueue_batch`: the same loop as `:57-64`, inside **one** `self._orm.transaction()`.
   - `_enqueue_on(self, conn: AsyncConnection, request, enqueued)`:
     ```python
     depends_on = [*request.depends_on]
     for key in request.depends_on_keys:
         depends_on.append(await self._job_id(conn, request.project_id, key, enqueued))
     row = (await conn.execute(JOB_SQL.insert_job(request))).mappings().first()
     if row is None:
         row = (await conn.execute(JOB_SQL.by_key(request.project_id, request.idempotency_key))).mappings().first()
         if row is None:
             raise LookupError(...)  # today's message, :111-114
         return self._rows.to_record(row)
     for dep_id in depends_on:
         await conn.execute(JOB_SQL.insert_dependency(row["id"], dep_id))
     await conn.execute(JOB_SQL.notify_ready(request.project_id))
     return self._rows.to_record(row)
     ```
     Keep the docstring and the comment about when the notification is delivered (reword
     "NOTIFY's payload cannot be a bind parameter…" to say `pg_notify` binds both).
   - `_job_id(self, conn: AsyncConnection, ...)`: `existing = await conn.scalar(JOB_SQL.id_by_key(project_id, key))`;
     the rest unchanged (`:147-160`).
   - `list_for_cycle`, `count_unsettled` (`int(await conn.scalar(...))`), `queue_depth`
     (rows from `.mappings().all()`, counts exactly as `:359-362`), `get`: through
     `self._orm.connect()`.
3. `build_app` builds `jobs=PostgresJobRepository(orm, pool=pool)` (`src/vibey/bootstrap.py:918`).
4. `claim`, `heartbeat`, `ack`, `nack`, `park`, `grant_attempts`, `defer`, `reap`,
   `assign_engine` and `_rowcount` are **unchanged**.

## Where to change
- `src/vibey/infrastructure/db/job_repository.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_job_repository.py`: rewrite only the body of
  `test_enqueue_raises_lookup_error_when_both_fetchrows_return_none` (`:329-359`):
  delete its fake classes and use
  `repo = PostgresJobRepository(FakeOrm(FakeResult(), FakeResult()))` (from
  `tests/infrastructure/orm/fakes.py`): the insert returns no row and neither does the
  lookup. Append the new tests below. No other existing test changes.
Every other test — `test_chaos.py` (protected, `PostgresJobRepository(migrated_pool)` at
`:53`), `test_keda_scaler_query.py`, `test_build_decompose_fan_out.py` — passes unchanged.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `enqueue` twice with one key returns the same id and writes one row.
- [ ] A batch whose third request names an unknown dependency key raises `LookupError` and leaves **no** row of the batch and **no** notification.
- [ ] A listener on `vibey_job_ready` receives the project id once per committed enqueue transaction (duplicates in one batch fold).
- [ ] `test_job_repository.py`, `test_chaos.py` (protected, unchanged), `test_keda_scaler_query.py`, `test_build_decompose_fan_out.py`, `tests/application/test_worker.py` pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_job_repository.py` (integration):
- `test_a_rolled_back_batch_notifies_nobody` (listen on a raw connection from
  `await migrated_pool.acquire()` with `add_listener("vibey_job_ready", ...)`; a batch that
  raises `LookupError`; wait 0.2 s; nothing arrived; release the connection in `finally`)
- `test_a_committed_batch_notifies_once` (three requests for one project → exactly one payload arrives within 1 s)
- `test_enqueue_stores_payload_and_requirement_as_jsonb` (nested dicts round-trip equal through `get`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_chaos.py tests/infrastructure/db/test_keda_scaler_query.py tests/infrastructure/db/test_build_decompose_fan_out.py
    # No-services tests that must stay green:
    uv run pytest -q -p no:cacheprovider tests/application/test_worker.py tests/infrastructure/orm
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py

## Out of scope
- The claim/settle methods and removing the transitional pool (`orm-job-settle`).
- `rmq-r10` (it overrides `_enqueue_on` and lands after the job lanes). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
