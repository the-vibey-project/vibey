## Title
feat(ledger): the RabbitMQ claim, the ack that releases dependents, and the dead-letter park are ledger events

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`). `gap-ledger-job-events-2`
ledgers claim and ack inside `PostgresJobRepository`, but the RabbitMQ records replace both
paths with their own statements, so a RabbitMQ worker's claim and completion reach no ledger:
- `DispatchingJobRecords.claim_dispatched(dispatch, *, owner, lease)`, the fenced claim by job id
  and generation (`split-358-1-fenced-claim`, behaviour 2), runs `DISPATCH_SQL.claim_dispatched`
  instead of `JOB_SQL.claim`;
- `ack_and_release(job_id, *, owner)` (`rmq-r10-dispatch-records-enqueue`, behaviour 3) executes
  `JOB_SQL.ack` itself and checks `rowcount`, instead of calling `super().ack`;
- `park_dead_letter(dispatch, *, delivery_limit)` (`split-358-3-sweep-and-park`) parks a poison
  job and raises a `delivery_exhausted` gate, with its own `update`.

This lane appends `JobClaimed` (with the generation), `JobSucceeded` and `JobParked`
(`gap-ledger-job-events-1`) on the same connection, in the same transaction, through the
`self._events` and `self._drafts` that `DispatchingJobRecords` inherits from
`PostgresJobRepository` (`gap-ledger-job-events-2`). Each statement is already fenced, so a
replay that does not land returns no row and appends nothing.

## Required behaviour
In `src/vibey/infrastructure/db/dispatch_records.py`, class `DispatchingJobRecords`:
1. `claim_dispatched`: when the statement returns a row,
   `record = self._rows.to_record(row)`, then
   `await self._events.append(conn, self._drafts.claimed(record, dispatch_seq=dispatch.dispatch_seq))`,
   then return `record`. No row → `None`, no event.
2. `ack_and_release`: the ack statement becomes `JOB_SQL.ack(job_id, owner=owner).returning(*JOBS.c)`;
   `row = result.mappings().first()`; `None` → `return (False, ())` exactly as today (this replaces
   the `rowcount != 1` check with the same meaning). Otherwise append
   `self._drafts.succeeded(self._rows.to_record(row), owner=owner)` **before** executing
   `DISPATCH_SQL.release_dependents(job_id)`, so the completion precedes the released dispatches
   in the ledger's order. Everything after is unchanged.
3. `park_dead_letter`: the park statement gets `.returning(*JOBS.c)` in addition to what it
   returns today (`Update.returning` accumulates). When it returns a row, append
   `self._drafts.parked(self._rows.to_record(row), owner=None, reason="dead_lettered")` before
   the gate insert. No row → `False`, no event, no gate, as today.
4. **The fake.** In `tests/fakes/queue.py`, `FakeDispatchingJobRecords`:
   - `claim_dispatched`: on a hit, build the leased record, append
     `store.drafts.claimed(record, dispatch_seq=dispatch.dispatch_seq)` to `store.ledger`, then
     store it.
   - `ack_and_release` calls the parent's `ack`, which already appends `JobSucceeded` since
     `gap-ledger-job-events-2`: change nothing, and prove it with a test.
   - `park_dead_letter`: on a hit, build the parked record, append
     `store.drafts.parked(record, owner=None, reason="dead_lettered")`, then store it and add the gate.

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py` (edit_file only: the three methods).
- `tests/fakes/queue.py` (`claim_dispatched`, `park_dead_letter`).
- Append to `tests/infrastructure/db/test_dispatch_records.py` and
  `tests/fakes/test_fake_dispatch_records.py`.

## Acceptance criteria
- [ ] A dispatched claim that hits ledgers one `JobClaimed` whose payload has `dispatch_seq` equal
      to the dispatch's and `owner` equal to the claimant; a miss (stale generation) ledgers nothing.
- [ ] `ack_and_release` by the owner ledgers `JobSucceeded` before any `JobDispatched` of a released
      dependent (compare `seq`); by a non-owner it returns `(False, ())` and ledgers nothing.
- [ ] `park_dead_letter` on a claimable row ledgers `JobParked` with `reason: "dead_lettered"`,
      `owner: null` and `state: "awaiting_human"`, and raises the gate; on a stale generation it
      ledgers nothing and raises no gate.
- [ ] The fake gives the same events in the same order for each case.
- [ ] `split-358-1`/`-3`'s and `rmq-r10`'s tests pass unchanged; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_dispatch_records.py` (build the records with
`writer=LedgeredDispatchOutboxWriter(DispatchOutboxWriter())`, as `build_app` does):
- `test_a_dispatched_claim_ledgers_its_generation`
- `test_a_missed_dispatched_claim_ledgers_nothing`
- `test_ack_and_release_ledgers_the_completion_before_the_releases`
- `test_a_non_owner_ack_and_release_ledgers_nothing`
- `test_a_dead_letter_park_ledgers_job_parked`
- `test_a_stale_dead_letter_park_ledgers_nothing`
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
- The dispatch writes themselves (`gap-ledger-job-events-6`); nack, defer and reap
  (`gap-ledger-job-events-8`); `snapshot` and `mark_dispatched` (reads and the relay's stamp,
  not job transitions).
- Docs, CHANGELOG.

Commit as `feat(ledger): the RabbitMQ claim, ack and dead-letter park are ledger events`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-6`, `split-358-1-fenced-claim`, `split-358-3-sweep-and-park`.
- **Must keep passing unchanged:** the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
