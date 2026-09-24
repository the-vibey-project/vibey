## Title
feat(ledger): every lease renewal, failed attempt, defer, park and grant is a ledger event

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks for "every job … decision,
capacity signal … and outcome, with its time, its actor and its evidence". After
`gap-ledger-job-events-2` the ledger holds enqueue, claim and completion; the five lease-fenced
writes that happen in between still change only the mutable row: heartbeat
(`src/vibey/infrastructure/db/job_repository.py:210-221`), nack (`:237-256`), park
(`:258-272`), grant_attempts (`:274-285`) and defer (`:287-309`). This lane ledgers each one in
the same transaction as its row, with the drafts of `gap-ledger-job-events-1`.

**Every lease renewal is recorded, and there is no key to turn that off.** 7.c asks for "as much
of what happened as can be recorded", and a renewal is the evidence that separates "the worker
was alive and the lease expired anyway" from "the worker went silent". Volume is bounded and
small: the worker beats at a third of the lease (`src/vibey/application/worker.py:387-406`), so a
job writes at most three renewals per lease period. With today's leases
(`src/vibey/bootstrap.py:274-287`) a two-hour `build.implement` writes about one renewal per 40
minutes, and a two-minute control-plane job one per 40 seconds for its few minutes — against the
dozens to hundreds of `TurnCompleted`/`TranscriptRecorded` events one engine run already writes.
A switch whose only effect is to drop them would let a deployment hold less than 7.c requires
without the ledger saying so (7.c: "never a silent omission"); the cadence itself already follows
the configured lease. If the operator later wants a volume key, it must record the omission in
the ledger (see the report's operator decisions).

Replay stays idempotent: each write is fenced on `lease_owner` (and `state = 'leased'` for
heartbeat and defer), so a write that did not land returns no row and appends nothing.

## Required behaviour
In `PostgresJobRepository` (after `orm-job-settle` and `gap-ledger-job-events-2`, which added
`self._events` and `self._drafts`), each method below runs its statement with
`.returning(*JOBS.c)` added in the repository (the shared `JOB_SQL` statement is not changed;
`Update.returning` accumulates), inside its existing `self._orm.transaction()`:
`row = result.mappings().first()`; `None` → return `False` and append nothing; otherwise
`record = self._rows.to_record(row)`, append the draft with
`await self._events.append(conn, ...)`, and return `True`.

| method | statement | draft |
|---|---|---|
| `heartbeat(job_id, *, owner, lease)` | `JOB_SQL.heartbeat(job_id, owner=owner, lease=lease)` | `self._drafts.lease_renewed(record, lease=lease)` |
| `nack(job_id, *, owner, error)` | `JOB_SQL.nack(job_id, owner=owner, error=error)` | `self._drafts.attempt_failed(record, owner=owner, error=error)` |
| `defer(job_id, *, owner, retry_at, error)` | `JOB_SQL.defer(job_id, owner=owner, retry_at=retry_at, error=error)` | `self._drafts.deferred(record, owner=owner, error=error)` |
| `park(job_id, *, owner)` | `JOB_SQL.park(job_id, owner=owner)` | `self._drafts.parked(record, owner=owner)` |
| `grant_attempts(job_id, *, owner, max_attempts)` | `JOB_SQL.grant_attempts(job_id, owner=owner, max_attempts=max_attempts)` | `self._drafts.attempts_granted(record, owner=owner)` |

- The return values and every other behaviour are unchanged; `JobRepository`
  (`src/vibey/application/interfaces/queue.py:89-186`) is unchanged.
- `assign_engine` writes no job event: the winner is ledgered by `EngineSelected`
  (`gap-ledger-selection-events-1`). Say so in its docstring, one sentence.
- **The fake.** `FakeJobRepository` (`tests/fakes/queue.py`): `heartbeat`, `nack`, `defer`,
  `park` and `grant_attempts` each build the updated record exactly as today, then
  `await store.ledger.append(<the same draft>)`, then store the record. A refused call appends
  nothing and changes nothing. An append that raises leaves the store unchanged.

## Where to change
- `src/vibey/infrastructure/db/job_repository.py` (edit_file only: the five methods and the
  `assign_engine` docstring).
- `tests/fakes/queue.py` (the five methods).
- Append to `tests/infrastructure/db/test_job_repository.py` and `tests/fakes/test_fake_queue.py`.

## Acceptance criteria
- [ ] A heartbeat by the owner writes one `JobLeaseRenewed` whose `produced_at` equals the row's
      new `lease_expires_at` minus the lease; a heartbeat by another owner writes nothing and
      returns `False`.
- [ ] A nack below the bound writes `JobAttemptFailed` with `final: false`, `state: "ready"` and
      the error; at the bound (`max_attempts=1`) it writes `final: true`, `state: "failed"`.
- [ ] A defer writes `JobDeferred` with `retry_at` equal to the row's `run_after`.
- [ ] A park writes `JobParked` with `state: "awaiting_human"`; a grant writes
      `JobAttemptsGranted` with the new `max_attempts`; a grant that does not widen writes nothing.
- [ ] A replayed nack (same owner, lease already released) writes nothing.
- [ ] `tests/application/test_worker.py` passes; `tests/infrastructure/db/test_chaos.py`
      (protected) passes unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_job_repository.py` (each claims a job first):
- `test_a_heartbeat_ledgers_one_renewal_dated_at_the_renewal`
- `test_a_refused_heartbeat_ledgers_nothing`
- `test_a_nack_below_the_bound_ledgers_a_retryable_failure`
- `test_a_nack_at_the_bound_ledgers_a_final_failure`
- `test_a_replayed_nack_ledgers_nothing`
- `test_a_defer_ledgers_its_retry_time_and_error`
- `test_a_park_ledgers_job_parked`
- `test_a_widening_grant_ledgers_and_a_narrowing_one_does_not`
Append to `tests/fakes/test_fake_queue.py` the same names with the same outcomes, each building
`store = InMemoryQueueStore()` and `FakeJobRepository(store=store)` and reading `store.ledger.events`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/application/test_worker.py tests/infrastructure/orm
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_build_implement_end_to_end.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Reap and lease expiry (`gap-ledger-job-events-4`), the gate answer (`gap-ledger-job-events-5`),
  the RabbitMQ overrides of nack and defer (`gap-ledger-job-events-8`).
- A config key for renewal volume (see Why).
- Docs, CHANGELOG.

Commit as `feat(ledger): lease renewals, failed attempts, defers, parks and grants are ledger events`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-2`.
- **Must keep passing unchanged:** the protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
