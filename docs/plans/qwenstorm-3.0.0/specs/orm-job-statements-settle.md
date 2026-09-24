## Title
feat(db): the job queue's claim and settle statements as SQLAlchemy Core, SKIP LOCKED included

## Why
Second of four job-queue lanes (see `orm-job-statements-enqueue`; draft ADR
`specs/ADR-orm.md`). This one writes the queue's hot path — the claim and every
lease-fenced settle — as SQLAlchemy Core on the stateless `JobStatements` class, with no
database and no behaviour change. The statements must be **semantically identical** to
today's text in `src/vibey/infrastructure/db/job_repository.py`: the claim
`:180-207` (`FOR UPDATE SKIP LOCKED`, strict priority, then `run_after`, then id, never a
job with an unsucceeded dependency — ADR-0002), heartbeat `:212-221`, ack `:225-235`, nack
`:239-256` (the CASE and the capped, jittered backoff), park `:260-272`, grant `:276-285`,
defer `:296-309`, reap `:313-320`, assign `:324-333`. The protected chaos test
(`tests/infrastructure/db/test_chaos.py`) and `test_job_repository.py` pin those semantics;
they run against these statements once `orm-job-settle` switches the repository.

Two shared pieces are added for the RabbitMQ lanes, which reuse them instead of restating
SQL (`rmq-r10`, `rmq-r11`): the unmet-dependency clause and a `recover_leased` statement
for `vibey recover` (lane `orm-cli-recover`).

## Required behaviour
Add to `JobStatements` (`src/vibey/infrastructure/db/job_statements.py`), declaring each on
`JobStatementsInterface`. `JOBS`/`DEPENDENCIES` as in the enqueue lane; `STATE = JOBS.c["state"].type`.
1. `deps_unmet(self, job: FromClause) -> ColumnElement[bool]`:
   `parent = JOBS.alias("p")`;
   `exists().where(DEPENDENCIES.c["job_id"] == job.c["id"], DEPENDENCIES.c["depends_on_job_id"] == parent.c["id"], parent.c["state"] != "succeeded")`.
2. `claim(self, project_id: UUID, *, owner: str, lease: timedelta)`:
   ```python
   j = JOBS.alias("j")
   pick = (
       select(j.c["id"])
       .where(j.c["state"] == "ready", j.c["run_after"] <= func.now(),
              j.c["project_id"] == project_id, ~self.deps_unmet(j))
       .order_by(j.c["priority"].desc(), j.c["run_after"].asc(), j.c["id"].asc())
       .limit(1)
       .with_for_update(skip_locked=True)
       .scalar_subquery()
   )
   return (
       update(JOBS).where(JOBS.c["id"] == pick)
       .values(state="leased", lease_owner=owner,
               lease_expires_at=func.now() + literal(lease, Interval()),
               attempts=JOBS.c["attempts"] + 1, updated_at=func.now())
       .returning(*JOBS.c)
   )
   ```
3. `heartbeat(self, job_id, *, owner, lease)`: `update(JOBS).where(id ==, lease_owner == owner, state == "leased").values(lease_expires_at=func.now() + literal(lease, Interval()))`.
4. `ack(self, job_id, *, owner)`: `.where(id ==, lease_owner == owner).values(state="succeeded", lease_owner=None, lease_expires_at=None, updated_at=func.now())`.
5. `nack(self, job_id, *, owner, error: Mapping[str, object])`: `.where(id ==, lease_owner == owner)` and
   ```python
   backoff = func.least(
       func.power(2, JOBS.c["attempts"]) * literal(timedelta(seconds=2), Interval()),
       literal(timedelta(minutes=15), Interval()),
   )
   values(
       state=case((JOBS.c["attempts"] >= JOBS.c["max_attempts"], literal("failed", STATE)),
                  else_=literal("ready", STATE)),
       lease_owner=None, lease_expires_at=None,
       run_after=func.now() + backoff * func.random(),
       last_error=dict(error), updated_at=func.now(),
   )
   ```
   The two literals are typed with the column's own enum type (`STATE`): an untyped string
   would render `$n::VARCHAR`, which PostgreSQL will not assign to a `job_state` column.
6. `park(self, job_id, *, owner)`: `.where(id ==, lease_owner == owner).values(state="awaiting_human", lease_owner=None, lease_expires_at=None, attempts=func.greatest(JOBS.c["attempts"] - 1, 0), updated_at=func.now())`.
7. `grant_attempts(self, job_id, *, owner, max_attempts: int)`: `.where(id ==, lease_owner == owner, JOBS.c["max_attempts"] < max_attempts).values(max_attempts=max_attempts, updated_at=func.now())`.
8. `defer(self, job_id, *, owner, retry_at: datetime, error)`: `.where(id ==, lease_owner == owner, state == "leased").values(state="ready", lease_owner=None, lease_expires_at=None, attempts=func.greatest(JOBS.c["attempts"] - 1, 0), run_after=retry_at, last_error=dict(error), updated_at=func.now())`.
9. `reap(self)`: `update(JOBS).where(state == "leased", JOBS.c["lease_expires_at"] < func.now()).values(state="ready", lease_owner=None, lease_expires_at=None, updated_at=func.now())`.
10. `assign_engine(self, job_id, *, owner, engine_id: EngineId)`: `.where(id ==, lease_owner == owner, state == "leased").values(assigned_engine=engine_id.value, updated_at=func.now())`.
11. `recover_leased(self, project_id: UUID | None)`: exactly what `vibey recover` runs today
    (`src/vibey/cli/main.py:684-694`): `update(JOBS).where(state == "leased")` plus
    `.where(JOBS.c["project_id"] == project_id)` only when `project_id is not None`,
    `.values(state="ready", lease_owner=None, lease_expires_at=None, assigned_engine=None)`
    (no `updated_at`, as today).
12. Still **no behaviour change**: nothing executes these yet.

## Where to change
- `src/vibey/infrastructure/db/job_statements.py`
- `src/vibey/infrastructure/db/interfaces/job_statements_interface.py`
- New `tests/infrastructure/orm/test_job_statements_settle.py` (no database)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/` (no `text()` fragments and no `literal_column` either — every interval and enum
value is a typed literal); substitute at the declared seam, never by patching an import;
never edit a protected test; the first line of every new file is the provenance comment
copied byte-for-byte from a sibling.

## Acceptance criteria
Each compiled with `sqlalchemy.dialects.postgresql.asyncpg.dialect()`:
- [ ] `claim` renders `FOR UPDATE SKIP LOCKED`, `LIMIT`, `ORDER BY j.priority DESC, j.run_after ASC, j.id ASC`, `NOT (EXISTS (`, and `RETURNING`; binds the owner, the lease and the project.
- [ ] `nack` renders `CASE WHEN`, `least(`, `power(`, `random()`, and binds `"failed"`/`"ready"` with a `job_state` cast.
- [ ] every fenced write (`heartbeat`, `ack`, `nack`, `park`, `grant_attempts`, `defer`, `assign_engine`) has `lease_owner =` in its WHERE.
- [ ] `recover_leased(None)` has no `project_id =`; `recover_leased(pid)` has one.
- [ ] `mypy --strict src/vibey` clean; 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_job_statements_settle.py`:
- `test_the_claim_skips_locked_rows_in_priority_order`
- `test_the_claim_never_takes_a_job_with_an_unsucceeded_dependency`
- `test_nack_fails_at_the_bound_and_backs_off_below_it`
- `test_every_settle_is_fenced_on_the_lease_owner` (parametrized over the seven)
- `test_park_and_defer_refund_one_attempt` (`greatest(` in both)
- `test_recover_is_scoped_only_when_asked`
- `test_deps_unmet_is_reusable_on_any_alias` (build it on `JOBS.alias("x")`; the text names `x.id`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_job_statements_settle.py tests/infrastructure/orm/test_job_statements_enqueue.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The repository (`orm-job-enqueue`, `orm-job-settle`), the CLI (`orm-cli-recover`), the
  RabbitMQ statements (`rmq-r09`, `rmq-r10`, `rmq-r11`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
