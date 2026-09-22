## Title
feat(ledger): the RabbitMQ nack, defer and reap that start a new dispatch episode are ledger events

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`). `gap-ledger-job-events-3` and
`-4` ledger nack, defer and reap inside `PostgresJobRepository`. The RabbitMQ records override all
three with their own statements, which also bump the dispatch generation and write an outbox row
(`split-358-2-redispatching-settles`): `nack` runs `DISPATCH_SQL.nack_redispatch`, `defer` runs
`DISPATCH_SQL.defer_redispatch`, and `reap` runs `self._park_exhausted(conn)` then
`DISPATCH_SQL.reap_redispatch()`. None of them reaches the ledger, and the reap loses who held
each expired lease.

This lane appends `JobAttemptFailed`, `JobDeferred` and `JobLeaseExpired`
(`gap-ledger-job-events-1`) on the same connection, in the same transaction. The redispatch
outbox rows are ledgered as `JobDispatched` by the writer decorator (`gap-ledger-job-events-6`),
so the ledger reads, in seq order, the failure and then the new dispatch. The reap reuses the
members `gap-ledger-job-events-4` added to `PostgresJobRepository` (`_lock_expired`,
`_park_exhausted(conn, only=...)`, `_ledger_expired`), so it narrows and ledgers exactly as the
PostgreSQL backend does, including leaving a job in a phase this vibey does not know for a newer
worker.

## Required behaviour
In `src/vibey/infrastructure/db/dispatch_records.py`, class `DispatchingJobRecords`:
1. `nack`: its statement gets `.returning(*JOBS.c)` in addition to the dispatch columns it
   returns today (`Update.returning` accumulates). `None` → `False`, no event, no outbox row, as
   today. Otherwise append `self._drafts.attempt_failed(self._rows.to_record(row), owner=owner, error=error)`
   **before** the outbox write; the rest is unchanged.
2. `defer`: the same, with `self._drafts.deferred(self._rows.to_record(row), owner=owner, error=error)`.
3. `reap`: one `self._orm.transaction()`:
   ```python
   expired = await self._lock_expired(conn)
   if not expired:
       return 0
   ids = tuple(expired)
   parked = await self._park_exhausted(conn, only=ids)
   rows = (await conn.execute(DISPATCH_SQL.reap_redispatch().where(JOBS.c["id"].in_(ids)))).mappings().all()
   await self._ledger_expired(conn, expired)
   # then the outbox write per re-readied row, exactly as split-358-2 wrote it
   return parked + len(rows)
   ```
   The ledger append precedes the outbox writes, so each `JobLeaseExpired` precedes its
   `JobDispatched`. Keep `split-358-2`'s outbox loop and its `not_before` unchanged.
4. **The fake.** `FakeDispatchingJobRecords.nack`, `defer` and `reap` (`tests/fakes/queue.py`,
   `split-358-2`): where an override delegates to `FakeJobRepository`'s method, that method
   already appends since lanes `-3` and `-4`, so change nothing and prove it with a test; where
   it builds the record itself, append the same draft to `store.ledger` before storing the
   record and before writing the dispatch. The reap selects known phases only, in
   `(project_id.int, id.int)` order, as `gap-ledger-job-events-4` behaviour 6 does.

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py` (edit_file only: `nack`, `defer`, `reap`).
- `tests/fakes/queue.py` (the three overrides, only where behaviour 4 requires).
- Append to `tests/infrastructure/db/test_dispatch_records.py` and
  `tests/fakes/test_fake_dispatch_records.py`.

## Acceptance criteria
Each PostgreSQL test builds the records with `writer=LedgeredDispatchOutboxWriter(DispatchOutboxWriter())`.
- [ ] A nack with attempts left ledgers `JobAttemptFailed` (`final: false`) and then `JobDispatched`
      at the next generation; a nack at the bound ledgers `JobAttemptFailed` (`final: true`) and no
      dispatch; a stale owner's nack ledgers nothing.
- [ ] A defer ledgers `JobDeferred` (with `retry_at`) and then `JobDispatched` whose `not_before`
      is that `retry_at`.
- [ ] A reap of one exhausted and one retryable expired lease returns 2 and ledgers two
      `JobLeaseExpired` naming their former owners, the retryable one followed by its `JobDispatched`.
- [ ] A reap with nothing expired returns 0 and ledgers nothing.
- [ ] The fake gives the same events in the same order for each case.
- [ ] `split-358-2`'s tests pass unchanged; `tests/infrastructure/db/test_chaos.py` passes unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_dispatch_records.py`:
- `test_a_retryable_nack_ledgers_the_failure_then_the_redispatch`
- `test_a_final_nack_ledgers_the_failure_and_no_dispatch`
- `test_a_stale_nack_ledgers_nothing`
- `test_a_defer_ledgers_the_defer_then_the_redispatch_at_retry_at`
- `test_a_reap_ledgers_each_expired_owner_before_its_redispatch`
- `test_a_reap_with_nothing_expired_ledgers_nothing`
Append the same six names, with the same outcomes, to `tests/fakes/test_fake_dispatch_records.py`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/infrastructure/orm
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_dispatch_records.py tests/infrastructure/db/test_job_repository.py
    uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The sweep (its dispatches are ledgered by `gap-ledger-job-events-6`; it changes no job state
  but `dispatched_at` and the generation of a sequence-0 row, and that first dispatch is what
  `JobDispatched` records).
- `DISPATCH_SQL` statements themselves (unchanged; `reap_redispatch` is narrowed here only).
- Docs, CHANGELOG.

Commit as `feat(ledger): the RabbitMQ nack, defer and reap are ledger events`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-3`, `gap-ledger-job-events-4`, `gap-ledger-job-events-7`,
  `split-358-2-redispatching-settles`.
- **Must keep passing unchanged:** the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
