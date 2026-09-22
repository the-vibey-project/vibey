## Title
feat(measure): the PostgreSQL job queue reports depth, wait, oldest age and throughput per state

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): every queue records "its
latency, throughput, queue depth and waiting time". The only queue figure vibey has is
`PostgresJobRepository.queue_depth(project_id)` (`src/vibey/infrastructure/db/job_repository.py:353-362`):
per-project counts, read on demand by `vibey status`, never recorded, with no waiting time and no
age. The job table carries everything needed (`migrations/0003_job.sql`: `state`, `run_after`,
`created_at`, `updated_at`). Under ADR-0044's RabbitMQ backend the job rows stay in PostgreSQL
(lane `rmq-r17-queue-backend-selection`: `DispatchingJobRecords(orm, …)`), so this sampler reports
the job queue under both backends; broker-side depth is `gap-measure-queue-sampler-rmq`.
It is a `MeasurementSource` (lane `gap-measure-port`) the worker's ticker (lane
`gap-measure-ticker`) collects on the `[measure]` period, through the ORM seam only.

## Required behaviour
1. New `src/vibey/infrastructure/measure/job_queue_sampler.py`:
   - `JOB = TABLES.table("job")` (lane `orm-tables`); `BACKLOG_STATES: Final = (JobState.READY,
     JobState.LEASED, JobState.AWAITING_HUMAN, JobState.AWAITING_CAPACITY)`;
     `SETTLED_STATES: Final = (JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED)`.
   - `class JobQueueSampler`, `__init__(self, orm: PostgresOrmInterface, *, clock: Clock,
     states: tuple[JobState, ...] = BACKLOG_STATES, ids: Callable[[], UUID] = uuid4)`;
     `name` property returns `"postgres.job"`.
   - `async def collect(self) -> tuple[Measurement, ...]`, with `now = clock.now()`, through one
     `self._orm.connect()`:
     - backlog: `select(JOB.c["state"], func.count().label("depth"),
       func.min(JOB.c["created_at"]).label("oldest"),
       func.min(JOB.c["run_after"]).filter(JOB.c["run_after"] <= now).label("due"))
       .where(JOB.c["state"].in_([s.value for s in self._states])).group_by(JOB.c["state"])`,
       rows from `.mappings().all()`, each state read with `JOB_STATE_PARSER.parse(str(row["state"]))`.
       One measurement per configured state, zero-filled (a drained queue records depth 0, never
       silence): subject `MeasurementSubject(SubjectKind.QUEUE, f"postgres.job.{state.value}")`,
       outcome `SAMPLED`, `started_at = ended_at = now`, readings `DEPTH`; `OLDEST_AGE_SECONDS =
       max(0.0, (now - oldest).total_seconds())` when `oldest` is not `None`; and, for `READY`
       only, `WAIT_SECONDS` from `due` the same way when it is not `None`.
     - throughput, from the second collect on: `select(func.count()).where(JOB.c["state"].in_(
       [s.value for s in SETTLED_STATES]), JOB.c["updated_at"] > previous, JOB.c["updated_at"] <= now)`
       through `conn.scalar`; when `(now - previous).total_seconds() > 0`, one measurement
       subject `postgres.job.settled`, `started_at=previous`, `ended_at=now`, readings `COUNT` and
       `THROUGHPUT_PER_SECOND = count / seconds`. `previous` is the `now` of the last collect
       that succeeded.
2. New `src/vibey/infrastructure/measure/interfaces/job_queue_sampler_interface.py`:
   `JobQueueSamplerInterface` (`name`, `collect`).
3. `src/vibey/bootstrap.py` `build_app`: bind `clock = SystemClock()` once before the yield, pass
   `clock=clock` where the yield passes `clock=SystemClock()` today (`:935`), and pass
   `measurement_sources=(JobQueueSampler(orm, clock=clock),)` (lane `gap-measure-ticker` added
   the field with `()`).

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings in
`src/`; substitute at the declared seam, never by patching an import; the first line of every new
file is the provenance comment copied byte-for-byte from a sibling.

## Where to change
- New `src/vibey/infrastructure/measure/job_queue_sampler.py` and its interface file.
- `src/vibey/bootstrap.py` (`edit_file`).
- New `tests/infrastructure/orm/test_job_queue_sampler.py` (no database; `FakeOrm`/`FakeResult`
  from `tests/infrastructure/orm/fakes.py`) and new
  `tests/infrastructure/db/test_job_queue_sampler.py` (integration).

## Acceptance criteria
- [ ] Scripted rows `ready` (depth 2, oldest 30 s ago, due 10 s ago) and `leased` (depth 1) give
      four measurements: ready depth 2 / age 30 / wait 10, leased depth 1 with its age, and
      depth 0 with no age for `awaiting_human` and `awaiting_capacity`.
- [ ] The first collect records no throughput; a second, 60 s later, with 6 settled jobs,
      records `count 6` and `throughput_per_second 0.1` over that window.
- [ ] The compiled backlog statement (PostgreSQL dialect) contains `FILTER (WHERE` and
      `GROUP BY job.state`.
- [ ] Against a migrated database, two ready jobs enqueued through `PostgresJobRepository`
      (build the request as `tests/infrastructure/db/test_job_repository.py` does) give
      `postgres.job.ready` depth 2.
- [ ] `grep -n "text(\|exec_driver_sql\|asyncpg" src/vibey/infrastructure/measure/job_queue_sampler.py` prints nothing.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_job_queue_sampler.py`:
- `test_backlog_is_measured_per_state_and_zero_filled`
- `test_wait_is_measured_for_ready_jobs_only`
- `test_throughput_needs_a_previous_sample`
- `test_the_backlog_statement_filters_and_groups`
- `test_the_sampler_satisfies_its_interfaces` (`MeasurementSource`, `JobQueueSamplerInterface`)

`tests/infrastructure/db/test_job_queue_sampler.py` (integration):
- `test_ready_jobs_are_counted_against_a_real_queue`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_job_queue_sampler.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_queue_sampler.py tests/cli/test_operational_commands.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- RabbitMQ queues (`gap-measure-queue-sampler-rmq`); changing `JobRepository.queue_depth` or any
  job statement (the `orm-job-*` lanes own them).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): the PostgreSQL job queue reports depth, wait, oldest age and throughput per state`. Do not push.

## Lane card
- **Depends on:** `gap-measure-ticker`, `orm-tables`, `orm-test-harness`, `orm-app-resources`.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_job_repository.py`, the worker
  tests in `tests/cli/test_operational_commands.py`, the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
