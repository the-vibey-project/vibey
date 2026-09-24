## Title
feat(queue): vibey recover goes through JobRepository.recover_leased instead of its own SQL

## Why
`vibey recover` is the operator's lever for jobs a crashed worker left `leased`. It is the
only command that writes the queue behind the queue's back: it opens its own asyncpg
connection and runs an `UPDATE job …` string (`src/vibey/cli/main.py:661-706`, the SQL at
`:684-694`), then scrapes asyncpg's command tag with a regex (`:696-701`) — the same regex
that once reported `Recovered 0` for every recovery (`tests/cli/test_operational_commands.py:2262-2300`).
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`), and the queue's port is `JobRepository`
(`src/vibey/application/interfaces/queue.py:89-186`). The statement already exists as Core
(`JOB_SQL.recover_leased`, lane `orm-job-statements-settle`). This lane puts it on the port,
so the CLI no longer knows the queue is PostgreSQL — which is also what the RabbitMQ backend
needs (ADR-0044 §1: only the composition root knows the backend).

## Required behaviour
1. `JobRepository` gains
   ```python
   async def recover_leased(self, project_id: UUID | None) -> int:
       """Returns every `leased` job -- of one project, or of every project when
       `project_id` is None -- to `ready`, clearing its lease and its assigned engine,
       whether or not the lease has expired. The operator's `vibey recover`, for jobs a
       crashed worker left behind. Returns how many it put back."""
       ...
   ```
2. `PostgresJobRepository.recover_leased`: in `self._orm.transaction()`,
   `return (await conn.execute(JOB_SQL.recover_leased(project_id))).rowcount`.
3. `FakeJobRepository` (`tests/application/fakes.py:16`) implements it the same way over its
   in-memory rows (state `LEASED` → `READY`, `lease_owner`, `lease_expires_at` and
   `assigned_engine` → `None`, filtered by project when one is given), and appends
   `"recover_leased"` to `self.calls` like its other writers.
4. `recover` in `cli/main.py`:
   ```python
   async def run_recover() -> None:
       if not project_id and not all_projects:
           typer.echo("Must specify either --project <id> or --all")
           raise typer.Exit(1)
       async with build_app() as resources:
           count = await resources.jobs.recover_leased(None if all_projects else project_id)
       typer.echo(f"Recovered {count} stuck job(s).")
   ```
   The local `import re`, `import asyncpg`, `from vibey.bootstrap import database_url` and the
   command-tag comment go. `--all` still wins when both flags are given, as today.
5. Output, exit codes and flags are unchanged.

## Where to change
- `src/vibey/application/interfaces/queue.py` (the port)
- `src/vibey/infrastructure/db/job_repository.py` (one method)
- `src/vibey/cli/main.py` (`recover` only)
- `tests/application/fakes.py` (`FakeJobRepository`)
- `tests/infrastructure/db/test_job_repository.py` (append)
- `tests/application/test_fake_job_repository_recover.py` (new, no database)
The subclasses of `FakeJobRepository` (`tests/application/test_worker.py:730`, `:784`,
`tests/application/test_build_decompose_handler.py:66`) and of `PostgresJobRepository`
(`tests/infrastructure/db/test_build_decompose_fan_out.py:77`) inherit it.
If `rmq-r16-rabbitmq-job-repository` has already landed, `RabbitMqJobRepository` must
implement the method too (delegate to `records.recover_leased`, then `relay.flush_soon()`);
the amended R16 spec already says so.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg\|UPDATE job" src/vibey/cli/main.py` prints nothing.
- [ ] `test_recover_no_args`, `test_recover_all_projects` and `test_recover_counts_the_jobs_it_put_back` pass unchanged.
- [ ] `tests/fakes/test_port_parity.py` passes (the fake still satisfies the port).
- [ ] Against PostgreSQL: two leased jobs in project A and one in B; `recover_leased(A)` returns 2 and leaves B leased; `recover_leased(None)` returns 1; the recovered rows have no lease owner, no expiry and no assigned engine.
- [ ] 100% branch coverage of `src/vibey/cli/`, `src/vibey/application/` and `src/vibey/infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_job_repository.py` (integration, append):
  `test_recover_leased_scopes_to_one_project_or_takes_all`
- `tests/application/test_fake_job_repository_recover.py` (no database):
  `test_the_fake_recovers_like_the_repository` (same scenario on `FakeJobRepository`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed:
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/cli/test_operational_commands.py
    # No-services tests:
    uv run pytest -q -p no:cacheprovider tests/application tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The reaper (`reap` only takes expired leases; `recover` takes every lease, deliberately).
- Docs (the CLI reference is owned by the docs wave), CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
