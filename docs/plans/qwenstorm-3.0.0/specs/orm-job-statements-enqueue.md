## Title
feat(db): the job queue's enqueue-side statements as SQLAlchemy Core, and a job row mapper class

## Why
The job queue is the largest raw-SQL surface in vibey: eighteen asyncpg calls in
`src/vibey/infrastructure/db/job_repository.py`. Moving it to the ORM (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`) happens in four lanes so that each stays
small: two build the statements as Core, with no database and no behaviour change; two
switch the repository onto them. This is the first. Two things here:

1. **The statements.** Enqueue, the dependency rows, the job-ready notification and the
   reads, each a method on one stateless class so the repository, the RabbitMQ lanes that
   extend it (`rmq-r10`, `rmq-r11`) and the unit tests share one definition. Today's text:
   the insert `:79-102` (`ON CONFLICT (project_id, idempotency_key) DO NOTHING RETURNING *`),
   the key lookups `:105-109` and `:150-154`, the dependency insert `:119-127`, the
   `NOTIFY` f-string `:133`, `list_for_cycle` `:166-175`, `count_unsettled` `:339-350`,
   `queue_depth` `:355-358`, `get` `:366`.
2. **The row mapper.** `_row_to_job_record` (`:20-42`) is a bare module function, while its
   interface `JobRowMapperInterface` already exists
   (`src/vibey/infrastructure/db/interfaces/job_repository_interface.py:19-30`) with no
   class implementing it.

## Required behaviour
1. New `class JobStatements` in `src/vibey/infrastructure/db/job_statements.py`, with
   `JOBS = TABLES.table("job")` and `DEPENDENCIES = TABLES.table("job_dependency")`
   (lane `orm-tables`) as module constants, and these methods (columns by `t.c["name"]`):
   - `insert_job(self, request: EnqueueRequest)` →
     `pg_insert(JOBS).values(project_id=…, cycle=…, phase=request.phase.value, kind=…, priority=…, work_item_id=…, payload=dict(request.payload), requirement=dict(request.requirement), idempotency_key=…, max_attempts=…, run_after=func.coalesce(literal(request.run_after, JOBS.c["run_after"].type), func.now())).on_conflict_do_nothing(index_elements=[JOBS.c["project_id"], JOBS.c["idempotency_key"]]).returning(*JOBS.c)`
     (`pg_insert` is `sqlalchemy.dialects.postgresql.insert`).
   - `by_key(self, project_id: UUID, key: str)` → `select(JOBS).where(project_id ==, idempotency_key ==)`.
   - `id_by_key(self, project_id: UUID, key: str)` → `select(JOBS.c["id"]).where(…the same…)`.
   - `insert_dependency(self, job_id: UUID, depends_on: UUID)` →
     `pg_insert(DEPENDENCIES).values(job_id=job_id, depends_on_job_id=depends_on).on_conflict_do_nothing()`.
   - `notify_ready(self, project_id: UUID)` → `select(func.pg_notify("vibey_job_ready", str(project_id)))`.
     Same channel and payload as today's `NOTIFY`; delivered at commit, folded within a
     transaction, and both arguments bound.
   - `list_for_cycle(self, project_id, *, cycle: int, kind: str)` → ordered by
     `created_at ASC, id ASC`.
   - `count_unsettled(self, project_id, *, cycle: int, phase: Phase, exclude: UUID | None)` →
     `select(func.count()).select_from(JOBS).where(project_id ==, cycle ==, phase == phase.value, JOBS.c["state"].not_in(["succeeded", "failed", "cancelled"]))`,
     plus `.where(JOBS.c["id"] != exclude)` only when `exclude is not None`.
   - `depth(self, project_id)` → `select(JOBS.c["state"], func.count().label("count")).where(project_id ==).group_by(JOBS.c["state"])`.
   - `get(self, job_id)` → `select(JOBS).where(JOBS.c["id"] == job_id)`.
   - `JOB_SQL: Final[JobStatementsInterface] = JobStatements()` (stateless; one instance serves).
2. New `JobStatementsInterface` in
   `src/vibey/infrastructure/db/interfaces/job_statements_interface.py` declaring those
   methods (return types under `TYPE_CHECKING` from `sqlalchemy`: `Select[Any]`,
   `ReturningInsert[Any]`, `Insert`), exported from `interfaces/__init__.py`.
3. New `class JobRowMapper` in `job_repository.py`, implementing the existing
   `JobRowMapperInterface`:
   - `state(self, raw: str) -> StoredJobState` returns `JOB_STATE_PARSER.parse(raw)`.
   - `to_record(self, row: Mapping[str, Any]) -> JobRecord`: exactly today's
     `_row_to_job_record` (including the strict `Phase(...)` and `JobState(...)`), except the
     three JSON columns go through `JSON_COLUMNS` (`mapping` for `payload` and
     `requirement`, `optional_mapping` for `last_error`), so it reads an asyncpg row and an
     ORM row alike.
   - `JOB_ROWS: Final[JobRowMapperInterface] = JobRowMapper()`.
4. Every call of `_row_to_job_record` in `job_repository.py` becomes `JOB_ROWS.to_record`,
   `queue_depth` uses `JOB_ROWS.state(str(row["state"]))`, and `_row_to_job_record` is
   deleted. `JobRowMapperInterface.to_record` takes `Mapping[str, Any]`, and
   `job_repository_interface.py` no longer imports `asyncpg` (not even under `TYPE_CHECKING`:
   import-linter counts type-checking imports, and `orm-raw-sql-guard` forbids asyncpg outside
   the notifier).
5. **No behaviour change**: the repository still runs its own SQL on its pool; nothing
   executes a `JobStatements` statement yet (lane `orm-job-enqueue` does).

## Where to change
- `src/vibey/infrastructure/db/job_statements.py` (new)
- `src/vibey/infrastructure/db/interfaces/job_statements_interface.py` (new)
- `src/vibey/infrastructure/db/interfaces/__init__.py`
- `src/vibey/infrastructure/db/job_repository.py` (the mapper only: add the class, replace
  the calls, delete the function)
- `src/vibey/infrastructure/db/interfaces/job_repository_interface.py` (the `row` type)
- New `tests/infrastructure/orm/test_job_statements_enqueue.py` and
  `tests/infrastructure/orm/test_job_row_mapper.py` (no database)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] Compiled with `sqlalchemy.dialects.postgresql.asyncpg.dialect()`, `insert_job` renders `ON CONFLICT (project_id, idempotency_key) DO NOTHING` and `RETURNING`; `insert_dependency` renders `ON CONFLICT DO NOTHING`; `notify_ready` renders `pg_notify(` with `"vibey_job_ready"` and the project id as bound values; `count_unsettled(exclude=None)` has no `job.id !=` and with an id has one.
- [ ] `JOB_ROWS.to_record` returns equal records for an asyncpg-shaped row (JSON text) and an ORM-shaped row (decoded JSON).
- [ ] `grep -n "_row_to_job_record" src tests -r` prints nothing.
- [ ] The whole `tests/infrastructure/db/test_job_repository.py` and `test_chaos.py` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_job_statements_enqueue.py` (no database; compile each
statement with the asyncpg dialect, assert on `str(compiled)` and `compiled.params`):
- `test_insert_is_idempotent_on_project_and_key`
- `test_run_after_defaults_to_now_in_the_database` (`request.run_after=None` → `coalesce(` in the text)
- `test_dependency_rows_ignore_a_duplicate`
- `test_the_ready_notification_binds_channel_and_project`
- `test_count_unsettled_excludes_only_when_asked`
- `test_list_for_cycle_is_oldest_first`
- `test_the_statements_are_their_declared_seam`
`tests/infrastructure/orm/test_job_row_mapper.py` (no database):
- `test_text_and_decoded_json_rows_map_the_same`
- `test_state_reads_an_unknown_state_forward_compatibly` (`JOB_ROWS.state("future_state")` equals `JOB_STATE_PARSER.parse("future_state")` and does not raise; `JOB_ROWS.state("ready") is JobState.READY`)
- `test_the_mapper_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_job_statements_enqueue.py tests/infrastructure/orm/test_job_row_mapper.py
    # Postgres-backed regression (integration tier, must stay green):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_chaos.py tests/infrastructure/db/test_keda_scaler_query.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Executing these statements (lane `orm-job-enqueue`); the claim/settle statements
  (`orm-job-statements-settle`). `orm_models.py`. Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
