## Title
refactor(db): the job claim and every lease-fenced settle go through the ORM seam

## Why
Last of four job-queue lanes (draft ADR `specs/ADR-orm.md`). The claim and settle
statements exist as Core (`JOB_SQL`, lane `orm-job-statements-settle`); the enqueue side
already runs through the seam (`orm-job-enqueue`), which left the other nine methods on a
transitional pool. This lane moves them and deletes the pool, the last `asyncpg` import in
`src/vibey/infrastructure/db/job_repository.py`, and `_rowcount` (`:370-372`), which parsed
asyncpg's command tag (`"UPDATE 3"`); SQLAlchemy reports the same count as
`result.rowcount`. What must not move is pinned by `tests/infrastructure/db/test_job_repository.py`
and by the protected chaos test (`tests/infrastructure/db/test_chaos.py`: 8 workers, no double
commit, no lost job, every job terminal).

## Required behaviour
1. `PostgresJobRepository.__init__(self, orm: PostgresOrmInterface, *, rows: JobRowMapperInterface = JOB_ROWS)`;
   the transitional `pool` parameter and `self._pool` are deleted.
2. Every write runs in `async with self._orm.transaction() as conn:` and the reads in
   `self._orm.connect()`:
   - `claim`: `row = (await conn.execute(JOB_SQL.claim(project_id, owner=owner, lease=lease))).mappings().first()`;
     `self._rows.to_record(row) if row is not None else None`.
   - `heartbeat`, `ack`, `nack`, `park`, `grant_attempts`, `defer`, `assign_engine`:
     `result = await conn.execute(JOB_SQL.<name>(...))`; `return result.rowcount == 1`.
   - `reap`: `return (await conn.execute(JOB_SQL.reap())).rowcount`.
3. `_rowcount` and `import asyncpg` are deleted from the module.
4. `build_app` builds `jobs=PostgresJobRepository(orm)` (`src/vibey/bootstrap.py:918`; drop
   the `pool=` keyword `orm-job-enqueue` added).
5. The `JobRepository` port (`src/vibey/application/interfaces/queue.py:89-186`) and every
   observable behaviour are unchanged.

## Where to change
- `src/vibey/infrastructure/db/job_repository.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_job_repository.py` (append only)
No other test changes: the chaos test builds `PostgresJobRepository(migrated_pool)`, and
the fixture is the seam (lane `orm-test-harness`).

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg\|_rowcount\|_pool\|fetchrow\|fetchval" src/vibey/infrastructure/db/job_repository.py` prints nothing.
- [ ] `test_chaos.py` passes unchanged and prints its tally (`-s`), with zero double commits and zero lost jobs; `git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py` is empty.
- [ ] Every test in `test_job_repository.py`, `test_keda_scaler_query.py`, `test_build_decompose_fan_out.py`, `test_build_implement_end_to_end.py`, `tests/application/test_worker.py`, `tests/system/test_full_worker_faked.py` passes.
- [ ] Two concurrent claims on one ready job: exactly one gets it (SKIP LOCKED through the seam).
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_job_repository.py` (integration):
- `test_two_concurrent_claims_take_one_job_once` (`asyncio.gather` of two `claim`s on a
  one-job project with two repositories over `migrated_pool`; one record and one `None`)
- `test_a_stale_owner_cannot_settle` (claim as A, `ack` as B → `False`, row still `leased` by A)
- `test_nack_at_the_bound_fails_the_job` (`max_attempts=1`, claim, nack → state `failed`)
- `test_reap_counts_the_leases_it_returned` (two expired leases → `reap() == 2`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_keda_scaler_query.py tests/infrastructure/db/test_build_decompose_fan_out.py tests/infrastructure/db/test_build_implement_end_to_end.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
    # No-services tests that must stay green:
    uv run pytest -q -p no:cacheprovider tests/application/test_worker.py tests/infrastructure/orm
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- `vibey recover` (`orm-cli-recover`), the reap bound (`rmq-r09`, which lands after this
  lane and extends `reap`), the RabbitMQ records (`rmq-r10`, `rmq-r11`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
