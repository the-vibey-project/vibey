## Title
feat(db): the fenced dispatch claim, redispatching settles, the lost-dispatch sweep and the dead-letter park

## Why
ADR-0044 §4, §5 and §8. Six things are needed:

- a fenced claim by job id **and** generation, which also takes over an expired lease
  (this replaces the `SKIP LOCKED` scan for the RabbitMQ backend);
- every settle that starts a new dispatch episode (nack with attempts left, defer, and
  reap) increments the generation and writes an outbox row in its own transaction;
- a sweep that re-dispatches claimable jobs whose message looks lost, which also
  closes the enqueue-versus-ack race R10 leaves open;
- a dead-letter park that turns a poison pointer into a `delivery_exhausted` gate
  (ADR-0024);
- the fences stay exactly the PostgreSQL backend's (`job_repository.py:223-309`);
- the bounded reap is R09's.

*(Amended 2026-09-22 for the ORM wave, draft ADR `specs/ADR-orm.md`: R10 and R09 land
after the ORM job lanes, so every statement here is SQLAlchemy Core executed on the
`AsyncConnection` of a `PostgresOrmInterface` transaction. The SQL blocks below state each
statement's semantics; item 10 says how each is built. Semantics unchanged.)*

## Required behaviour
1. `claim_dispatched(dispatch: JobDispatch, *, owner: str, lease: timedelta) -> JobRecord | None`:
   ```sql
   UPDATE job SET state='leased', lease_owner=$4, lease_expires_at=now()+$5::interval,
                  attempts=attempts+1, updated_at=now()
   WHERE id=$1 AND project_id=$3 AND dispatch_seq=$2
     AND (state='ready' OR (state='leased' AND lease_expires_at < now()))
     AND run_after <= now()
     AND NOT EXISTS (SELECT 1 FROM job_dependency d JOIN job p ON p.id = d.depends_on_job_id
                     WHERE d.job_id = job.id AND p.state <> 'succeeded')
   RETURNING *
   ```
   Map the row with the same row mapper `PostgresJobRepository` uses.
2. `snapshot(job_id) -> DispatchSnapshot | None` (from R07) selects `state`,
   `dispatch_seq`, `run_after`, `lease_expires_at`, and `deps_met` computed with the
   same `NOT EXISTS`.
3. `nack` is overridden. Use today's NACK SQL (`job_repository.py:241-251`) with two
   changes:
   - `dispatch_seq = CASE WHEN attempts >= max_attempts THEN dispatch_seq ELSE dispatch_seq + 1 END`
   - `dispatched_at = NULL`

   Add `RETURNING id, project_id, state, dispatch_seq, kind, run_after`. When the
   returned state is `ready`, write an outbox row with `not_before = run_after`, in the
   same transaction. Return whether a row was updated.
4. `defer` is overridden the same way from today's DEFER SQL (`:298-303`): always
   `dispatch_seq + 1` and an outbox row with `not_before = retry_at`.
5. `reap` is overridden. Keep R09's parking statement (a) unchanged. Its re-ready
   statement (b) also sets `dispatch_seq = dispatch_seq + 1` and `dispatched_at = NULL`,
   and returns the rows, each of which gets an outbox row. Return the count from (a)
   plus (b).
6. `sweep_lost(*, redispatch_after: timedelta, limit: int = 500) -> int` runs one
   transaction:
   - Select candidate rows:
     ```sql
     SELECT id, project_id, dispatch_seq, kind, run_after FROM job j
     WHERE j.state='ready' AND j.run_after <= now()
       AND (j.dispatch_seq = 0 OR j.dispatched_at < now() - $1::interval)
       AND NOT EXISTS (<deps unmet>)
     ORDER BY j.run_after ASC LIMIT $2 FOR UPDATE SKIP LOCKED
     ```
   - A row at seq 0 is updated to seq 1 and written with the plain key.
   - A row at seq ≥ 1 is written again with the **same** generation and
     `key_suffix=f":sweep:{int(epoch)}"`, where `epoch` is the database's
     `extract(epoch from now())`. This is a harmless duplicate that keeps the job's
     FIFO position.
   - Every swept row gets `dispatched_at = now()`, so the next sweep waits.
   - Return the number of rows written.
7. `mark_dispatched(job_id, dispatch_seq) -> bool` runs
   `UPDATE job SET dispatched_at = now() WHERE id=$1 AND dispatch_seq=$2`.
8. `park_dead_letter(dispatch: JobDispatch, *, delivery_limit: int) -> bool` runs one
   transaction:
   - It first tries:
     ```sql
     UPDATE job SET state='awaiting_human', lease_owner=NULL, lease_expires_at=NULL,
            attempts=greatest(attempts-1,0), updated_at=now()
     WHERE id=$1 AND dispatch_seq=$2
       AND (state='ready' OR (state='leased' AND lease_expires_at < now()))
     RETURNING project_id, kind
     ```
   - If no row comes back, return `False`.
   - Otherwise insert a `human_gate` with `kind='delivery_exhausted'` and the prompt
     `f"job {kind!r} was delivered {delivery_limit} times and every consumer holding it died. Answer anything to retry it with a fresh delivery budget."`,
     send `NOTIFY vibey_gate_raised`, and return `True`.
9. The exactly-once commit fence is unchanged: `ack`, `park`, `heartbeat`,
   `grant_attempts` and `assign_engine` are inherited as they are.
10. **How each statement is built (ORM amendment).** New methods on R10's
    `DispatchStatements` (and `DispatchStatementsInterface`), over `JOBS`, `DEPENDENCIES` and
    `GATES = TABLES.table("human_gate")`, reusing `JOB_SQL.deps_unmet(JOBS)` wherever the
    blocks above say `NOT EXISTS (<deps unmet>)`:
    - `claim_dispatched(dispatch, *, owner, lease)`: `update(JOBS).where(id ==, dispatch_seq ==, project_id ==, or_(JOBS.c["state"] == "ready", and_(JOBS.c["state"] == "leased", JOBS.c["lease_expires_at"] < func.now())), JOBS.c["run_after"] <= func.now(), ~JOB_SQL.deps_unmet(JOBS))`
      with the claim's `values` (`lease_expires_at=func.now() + literal(lease, Interval())`, `attempts + 1`) and `.returning(*JOBS.c)`; map with `JOB_ROWS.to_record`.
    - `snapshot(job_id)`: `select(JOBS.c["state"], JOBS.c["dispatch_seq"], JOBS.c["run_after"], JOBS.c["lease_expires_at"], (~JOB_SQL.deps_unmet(JOBS)).label("deps_met")).where(JOBS.c["id"] == job_id)`.
    - `nack` and `defer`: start from `JOB_SQL.nack(...)` / `JOB_SQL.defer(...)` and add
      `.values(dispatch_seq=…, dispatched_at=None)` and `.returning(...)` (a second
      `.values()` call extends the first); the nack's generation is
      `case((JOBS.c["attempts"] >= JOBS.c["max_attempts"], JOBS.c["dispatch_seq"]), else_=JOBS.c["dispatch_seq"] + 1)`.
    - `reap`: (a) is `JOB_SQL.reap_park_exhausted()` from R09, unchanged; (b) is
      `JOB_SQL.reap()` plus `.values(dispatch_seq=JOBS.c["dispatch_seq"] + 1, dispatched_at=None).returning(id, project_id, dispatch_seq, kind, run_after)`.
    - `sweep_lost`: the candidate `select(...)` with
      `or_(JOBS.c["dispatch_seq"] == 0, JOBS.c["dispatched_at"] < func.now() - literal(redispatch_after, Interval()))`,
      `.order_by(JOBS.c["run_after"].asc()).limit(limit).with_for_update(skip_locked=True)`;
      the epoch is `await conn.scalar(select(func.extract("epoch", func.now())))`.
    - `mark_dispatched`: `update(JOBS).where(id ==, dispatch_seq ==).values(dispatched_at=func.now())`.
    - `park_dead_letter`: the `update(...).returning(JOBS.c["project_id"], JOBS.c["kind"])`,
      then `insert(GATES).values(project_id=…, job_id=…, kind="delivery_exhausted", prompt=…).returning(GATES.c["gate_id"])`,
      then `select(func.pg_notify("vibey_gate_raised", str(gate_id)))` — the payload is the
      gate id, as `raise_gate` sends it.

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py` (append to R10's class).
- Extend its interface.
- Reuse R09's parking statement, `JOB_SQL.reap_park_exhausted()`; do not duplicate it.
- `tests/infrastructure/orm/test_dispatch_statements.py` (append: each new statement
  compiled with `sqlalchemy.dialects.postgresql.asyncpg.dialect()` — the claim's generation
  and lease-takeover predicates, the sweep's `FOR UPDATE SKIP LOCKED`, the nack's `CASE`).

## Acceptance criteria
- [ ] The claim hits for a ready row at a matching generation, takes over an expired lease, and misses on a stale generation, a future `run_after`, an unexpired lease or an unmet dependency.
- [ ] `snapshot` feeds `DispatchMissPolicy` correctly in each miss case.
- [ ] A nack with attempts left bumps the generation and writes an outbox row at `run_after`. A nack at the last attempt fails the job with no outbox row.
- [ ] A defer bumps the generation and writes an outbox row at `retry_at`.
- [ ] A reap re-readies with a bump and an outbox row, and still parks exhausted rows (R09).
- [ ] The sweep dispatches the seq-0 race and old dispatches, skips rows with a pending outbox (`dispatched_at IS NULL` and seq ≥ 1), and throttles itself.
- [ ] `mark_dispatched` ignores a stale generation.
- [ ] `park_dead_letter` parks and raises a gate only when the row is still claimable at that generation.
- [ ] An ack from a stale owner after a reap-redispatch is refused.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
Add to `tests/infrastructure/db/test_dispatch_records.py`:
- `test_claim_dispatched_hits_and_leases`
- `test_claim_dispatched_takes_over_an_expired_lease`
- `test_claim_dispatched_misses_each_way` (parametrized over the five miss causes)
- `test_snapshot_reports_deps_and_lease`
- `test_nack_with_attempts_left_redispatches_at_run_after`
- `test_nack_at_the_last_attempt_fails_without_dispatch`
- `test_defer_redispatches_at_retry_at`
- `test_reap_redispatches_and_still_parks_exhausted`
- `test_sweep_dispatches_the_seq_zero_race`
- `test_sweep_duplicates_an_old_dispatch_at_the_same_generation`
- `test_sweep_skips_a_pending_outbox_row`
- `test_sweep_throttles_itself`
- `test_mark_dispatched_ignores_a_stale_generation`
- `test_park_dead_letter_parks_only_a_claimable_row`
- `test_stale_owner_ack_after_reap_is_refused`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/infrastructure/orm/test_dispatch_statements.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Publishing (R13).
- Consuming (R14).
- The repository that composes these pieces (R16).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R07, R09, R10.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/db/dispatch_records.py`
  - `src/vibey/infrastructure/db/interfaces/dispatch_records_interface.py`
  - `tests/infrastructure/db/test_dispatch_records.py`
  - `tests/infrastructure/orm/test_dispatch_statements.py`
- **Parallel-safe with:** R12, R15, R22 and R24.
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected)
  - R10's tests
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
