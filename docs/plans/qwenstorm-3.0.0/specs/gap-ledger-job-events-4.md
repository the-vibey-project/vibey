## Title
feat(ledger): every expired lease the reaper takes back is a JobLeaseExpired event naming who held it

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) names lease expiry and reap
among the job facts the ledger must hold. The reaper changes rows and returns only a count
(`src/vibey/infrastructure/db/job_repository.py:311-320`). After `rmq-r09-reap-bound` (#356) it
also parks a job whose every delivery was abandoned (`_park_exhausted`, a `delivery_exhausted`
gate) and re-readies the rest (`JOB_SQL.reap()`); neither statement says whose lease expired,
and that owner is gone from the row once the statement runs.

This lane locks the expiring rows first, remembers who held each lease, runs R09's two
statements narrowed to exactly those rows, and appends one `JobLeaseExpired` per job
(`gap-ledger-job-events-1`) in the same transaction. PostgreSQL's `now()` is fixed for the
transaction and the rows are locked, so the narrowed statements touch exactly the rows the
reap would have touched, with one deliberate exception below.

**A job in a phase this vibey does not know is left for a newer worker.** The row mapper is
strict on `phase` (`orm-job-statements-enqueue`, behaviour 3), and writers stay strict
(vibey#287): this vibey cannot write an event in a phase it does not know. Such a row appears only
during a rolling upgrade; a claim by this vibey already refuses it, and the newer worker that wrote
the phase reaps it and ledgers it. So the lock selects only known phases, and the reap no longer
re-readies unknown-phase rows. That is the one behaviour change, and a test pins it.

## Required behaviour
In `PostgresJobRepository` (after `rmq-r09-reap-bound` and `gap-ledger-job-events-2`):
1. `@staticmethod def expired_leases() -> Select[Any]` returns
   `select(JOBS).where(JOBS.c["state"] == "leased", JOBS.c["lease_expires_at"] < func.now(), JOBS.c["phase"].in_(sorted(p.value for p in Phase))).order_by(JOBS.c["project_id"], JOBS.c["id"]).with_for_update()`.
   It is public so a test can compile it without a database.
2. `async def _lock_expired(self, conn: AsyncConnection) -> dict[UUID, JobRecord]` executes
   `expired_leases()` and returns `{record.id: record}` for every row
   (`self._rows.to_record`), in the statement's order.
3. R09's `_park_exhausted(self, conn)` gains a keyword-only parameter
   `only: Collection[UUID] | None = None`. When it is not `None`, the statement becomes
   `JOB_SQL.reap_exhausted().where(JOBS.c["id"].in_(tuple(only)))`. Called without it (as
   `split-358-2-redispatching-settles` does), nothing changes.
4. `async def _ledger_expired(self, conn: AsyncConnection, expired: Mapping[UUID, JobRecord]) -> None`
   executes `select(JOBS).where(JOBS.c["id"].in_(tuple(expired))).order_by(JOBS.c["project_id"], JOBS.c["id"])`
   and, for each row, with `after = self._rows.to_record(row)` and `before = expired[after.id]`,
   appends `self._drafts.lease_expired(after, expired_owner=before.lease_owner, expired_at=before.lease_expires_at)`.
   Appending in `(project_id, id)` order keeps one lock order on the `event_seq` rows when one
   reap spans projects.
5. `reap()` runs one `self._orm.transaction()`:
   ```python
   expired = await self._lock_expired(conn)
   if not expired:
       return 0
   ids = tuple(expired)
   parked = await self._park_exhausted(conn, only=ids)
   readied = (await conn.execute(JOB_SQL.reap().where(JOBS.c["id"].in_(ids)))).rowcount
   await self._ledger_expired(conn, expired)
   return parked + readied
   ```
   A parked job's event carries `state: "awaiting_human"`; a re-readied job's `state: "ready"`.
   Every locked row is either parked (`attempts >= max_attempts`) or re-readied, so each gets
   exactly one event.
6. **The fake.** `FakeJobRepository.reap` (`tests/fakes/queue.py`, with R09's bound): select
   each `LEASED` job with `lease_expires_at < now` **and** `isinstance(job.phase, Phase)`, in
   `(job.project_id.int, job.id.int)` order; apply R09's park-or-re-ready exactly as today; then,
   per job in that order, `await store.ledger.append(store.drafts.lease_expired(after, expired_owner=before.lease_owner, expired_at=before.lease_expires_at))`.
   A job in an unknown phase is left `LEASED`.

## Where to change
- `src/vibey/infrastructure/db/job_repository.py` (edit_file only: `reap`, `_park_exhausted`'s
  signature and statement line, and the three new members).
- `tests/fakes/queue.py` (`FakeJobRepository.reap`).
- Append to `tests/infrastructure/db/test_job_repository.py`, `tests/fakes/test_fake_queue.py`
  and `tests/infrastructure/orm/test_job_statements_reap.py` (R09's no-database file).

## Acceptance criteria
- [ ] Two expired leases held by `w1` and `w2`, one with attempts left and one at its bound:
      `reap() == 2`, and the ledger holds two `JobLeaseExpired` whose `expired_owner` are `w1` and
      `w2`, one with `state: "ready"` and one with `state: "awaiting_human"` (and R09's gate).
- [ ] A reap with nothing expired returns `0` and writes nothing.
- [ ] A lease that has not expired is neither reaped nor ledgered.
- [ ] `expired_leases()` compiled with `sqlalchemy.dialects.postgresql.asyncpg.dialect()` renders
      `FOR UPDATE`, `ORDER BY job.project_id, job.id` and `job.phase IN`, and binds every `Phase` value.
- [ ] The fake leaves an expired job in `UnrecognizedPhase("FUTURE_PHASE")` leased and ledgers nothing for it.
- [ ] `tests/infrastructure/db/test_chaos.py` (protected: its reaper runs every 50 ms against
      150 ms leases) passes unchanged with `-s`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
- `tests/infrastructure/orm/test_job_statements_reap.py` (append; no database):
  `test_the_expired_lease_lock_names_only_phases_this_vibey_knows`.
- `tests/infrastructure/db/test_job_repository.py` (append; expire a lease by claiming with
  `lease=timedelta(milliseconds=1)` and sleeping 0.05 s):
  - `test_reap_ledgers_who_held_each_expired_lease`
  - `test_reap_ledgers_a_parked_and_a_readied_job_with_their_states`
  - `test_reap_with_nothing_expired_ledgers_nothing`
  - `test_a_live_lease_is_neither_reaped_nor_ledgered`
- `tests/fakes/test_fake_queue.py` (append; advance `store.clock`): the same four names, plus
  `test_reap_leaves_a_job_in_an_unknown_phase_for_a_newer_worker` (write the record straight into
  `store.jobs`, as `fakes-cli-ledger-deploy` behaviour 4 does).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/infrastructure/orm tests/application/test_worker.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_human_gate_repository.py
    uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- `JOB_SQL.reap()` and `JOB_SQL.reap_exhausted()` themselves (unchanged; narrowed here only).
- The RabbitMQ reap override (`gap-ledger-job-events-8`, which reuses `_lock_expired` and
  `_ledger_expired`).
- A ledger event for the `delivery_exhausted` gate itself (gates are not job transitions).
- Docs, CHANGELOG.

Commit as `feat(ledger): every expired lease the reaper takes back is a ledger event`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-2`, `rmq-r09-reap-bound`.
- **Must keep passing unchanged:** the protected tests, R09's tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
