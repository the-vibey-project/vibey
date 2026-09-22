## Title
fix(queue): reaping bounds a job that keeps killing its worker

## Why
ADR-0044 §8, and ADR-0024: every bounded ladder parks with a grant. Neither the claim
nor the reaper bounds a job that takes its worker down:

- the claim increments `attempts` with no upper bound
  (`src/vibey/infrastructure/db/job_repository.py:182-187`);
- `reap()` re-readies every expired lease unconditionally (`:311-320`).

A handler that kills its process on every attempt therefore never reaches
`_settle_failure` (`src/vibey/application/worker.py:224-272`), and it is re-claimed
forever. The RabbitMQ backend bounds the same failure through the broker's delivery
limit. This lane gives the PostgreSQL backend the same bound under the same gate kind,
`delivery_exhausted`.

*(Amended 2026-09-22 for the ORM wave, draft ADR `specs/ADR-orm.md`: this lane lands after
`orm-job-settle`, so the job repository already runs SQLAlchemy Core statements from
`JobStatements` (`src/vibey/infrastructure/db/job_statements.py`) through
`PostgresOrmInterface`. The two statements below are written the same way — no SQL text,
no `NOTIFY` f-string. Semantics unchanged.)*

## Required behaviour
1. `PostgresJobRepository.reap()` runs one transaction with two statements.
   - **(a)** Every row with `state = 'leased' AND lease_expires_at < now() AND attempts >= max_attempts`
     becomes `awaiting_human`: `lease_owner` and `lease_expires_at` are set to NULL,
     `attempts = greatest(attempts - 1, 0)` (one attempt refunded), and
     `updated_at = now()`. One `human_gate` row is inserted per parked job:
     - `kind = 'delivery_exhausted'`
     - its `project_id` and `job_id`
     - `prompt = format('job %L was abandoned mid-run on each of its %s deliveries (its worker died, was killed, or lost its lease every time). Answer anything to retry it once.', kind, max_attempts)`

     Build it as **one** Core statement with a data-modifying CTE, in a new method
     `JobStatements.reap_park_exhausted(self)` (declared on `JobStatementsInterface`), with
     `GATES = TABLES.table("human_gate")`:
     ```python
     exhausted = (
         update(JOBS)
         .where(JOBS.c["state"] == "leased", JOBS.c["lease_expires_at"] < func.now(),
                JOBS.c["attempts"] >= JOBS.c["max_attempts"])
         .values(state="awaiting_human", lease_owner=None, lease_expires_at=None,
                 attempts=func.greatest(JOBS.c["attempts"] - 1, 0), updated_at=func.now())
         .returning(JOBS.c["id"], JOBS.c["project_id"], JOBS.c["kind"], JOBS.c["max_attempts"])
         .cte("exhausted")
     )
     prompt = func.format(literal(REAP_PARK_PROMPT), exhausted.c["kind"], exhausted.c["max_attempts"])
     return (
         insert(GATES)
         .from_select(["project_id", "job_id", "kind", "prompt"],
                      select(exhausted.c["project_id"], exhausted.c["id"],
                             literal("delivery_exhausted"), prompt))
         .returning(GATES.c["gate_id"])
     )
     ```
     (`REAP_PARK_PROMPT` is a module constant holding the `format` string above.) It renders
     `WITH exhausted AS (UPDATE job … RETURNING …) INSERT INTO human_gate … SELECT … FROM
     exhausted RETURNING human_gate.gate_id` (checked against SQLAlchemy 2.0.53 on
     2026-09-22). Then, per returned gate id and in the same transaction,
     `await conn.execute(select(func.pg_notify("vibey_gate_raised", str(gate_id))))`, as
     `raise_gate` does after `orm-human-gate`.
   - **(b)** `JobStatements.reap()` (from `orm-job-statements-settle`) gains the restriction
     `JOBS.c["attempts"] < JOBS.c["max_attempts"]`; that is today's re-ready, restricted.
   - Both run in one `async with self._orm.transaction() as conn:`.
2. It returns the count from (a) (the number of gate ids returned) plus the count from
   (b) (`result.rowcount`).
3. A gate raised by (a) is answered through the ordinary path
   (`human_gate_repository.py:61-86`), which re-readies the job. Each answer therefore
   buys exactly one more delivery.
4. Nothing else in the class changes.
5. **Stop rule:** if an existing test in `test_job_repository.py` asserts that `reap()`
   re-readies a row whose `attempts >= max_attempts`, stop and report. Do not edit
   that test.

## Where to change
- `src/vibey/infrastructure/db/job_statements.py` (`reap_park_exhausted`, the `reap` restriction)
  and `src/vibey/infrastructure/db/interfaces/job_statements_interface.py`.
- `src/vibey/infrastructure/db/job_repository.py` (`reap` only).
- `tests/infrastructure/orm/test_job_statements_settle.py` (append: the compiled CTE renders
  `WITH exhausted AS`, `INSERT INTO human_gate`, `RETURNING human_gate.gate_id`, and binds
  `"delivery_exhausted"`; `reap` has `job.attempts < job.max_attempts`).

## Acceptance criteria
- [ ] A job with `max_attempts=1`, claimed once with an expired lease, is `awaiting_human` after `reap()`, with `attempts = 0` and one open `delivery_exhausted` gate; `reap()` returns 1.
- [ ] A job with attempts left is re-readied as before.
- [ ] Answering the gate re-readies the job, and it can be claimed again.
- [ ] Every existing repository test and the chaos test pass unchanged.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_job_repository.py` (new tests only):
  - `test_reap_parks_a_job_whose_every_delivery_was_abandoned`
  - `test_reap_counts_parked_and_rereadied_together`
  - `test_answering_a_delivery_exhausted_gate_rereadies_the_job`
  - `test_reap_park_notifies_the_raised_gate` (LISTEN on a raw asyncpg connection from
    `await migrated_pool.acquire()` — tests may use the driver — and assert the gate id arrives)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/application/test_worker.py tests/infrastructure/orm/test_job_statements_settle.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The RabbitMQ backend's reap (R11).
- The worker loop.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** `orm-job-settle` (amended 2026-09-22; the repository runs Core statements through the ORM seam).
- **Wave:** 1 of the RabbitMQ lanes, after the ORM job lanes.
- **Files touched:**
  - `src/vibey/infrastructure/db/job_statements.py`
  - `src/vibey/infrastructure/db/interfaces/job_statements_interface.py`
  - `src/vibey/infrastructure/db/job_repository.py` (`reap` only)
  - `tests/infrastructure/orm/test_job_statements_settle.py` (new tests only)
  - `tests/infrastructure/db/test_job_repository.py` (new tests only)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - every existing test in `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected; `max_attempts=1000` keeps it
    clear of the new bound)
  - `tests/infrastructure/db/test_human_gate_repository.py`
  - `tests/application/test_worker.py`
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
