## Title
feat(ledger): every RabbitMQ dispatch written to the outbox is a JobDispatched event in the same transaction

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) asks for every job transition,
"written as it happens". In the RabbitMQ backend (ADR-0044 §4) a job becomes deliverable when a
dispatch generation is written to the `job_outbox` table in the same transaction as the job
change. Every such write goes through one seam, `DispatchOutboxWriterInterface.write(conn,
dispatch, *, key_suffix="") -> bool` (`rmq-r10-dispatch-records-enqueue`, behaviour 1): the
first dispatch at enqueue, the release of dependents on ack, the redispatch after nack, defer and
reap (`split-358-2-redispatching-settles`), the lost-dispatch sweep
(`split-358-3-sweep-and-park`) and the gate-answer redispatch (`rmq-r15-gate-redispatch`). None of
them reaches the ledger.

A decorator on that one seam ledgers them all, and it is composed where `rmq-r17` builds the two
writers. It appends `JobDispatched` (`gap-ledger-job-events-1`) only when the outbox row was
inserted, so a replayed write (the outbox key already exists, `write` returns `False`) appends
nothing: idempotent under replay. The cause needs no field of its own: the transition that
caused the dispatch (`JobEnqueued`, `JobSucceeded` of the dependency, `JobAttemptFailed`,
`JobDeferred`, `JobLeaseExpired`, `JobReleased`) is written in the same transaction, and a sweep's
duplicate carries its `:sweep:` key suffix in `key`.

## Required behaviour
1. In `src/vibey/infrastructure/db/dispatch_records.py`, `class LedgeredDispatchOutboxWriter`,
   declared by the existing `DispatchOutboxWriterInterface` (`interfaces/dispatch_records_interface.py`):
   - `__init__(self, inner: DispatchOutboxWriterInterface, *, events: EventAppenderInterface = DEFAULT_EVENT_APPENDER, drafts: JobEventDraftBuilderInterface = JOB_EVENT_DRAFTS, rows: JobRowMapperInterface = JOB_ROWS) -> None`.
   - `async def write(self, conn: AsyncConnection, dispatch: JobDispatch, *, key_suffix: str = "") -> bool`:
     ```python
     inserted = await self._inner.write(conn, dispatch, key_suffix=key_suffix)
     if not inserted:
         return False
     row = (await conn.execute(JOB_SQL.get(dispatch.job_id))).mappings().first()
     if row is None:
         raise LookupError(f"dispatch written for job {dispatch.job_id}, which has no row")
     await self._events.append(
         conn,
         self._drafts.dispatched(
             self._rows.to_record(row),
             dispatch_seq=dispatch.dispatch_seq,
             not_before=dispatch.not_before,
             key=f"dispatch:{dispatch.job_id}:{dispatch.dispatch_seq}{key_suffix}",
         ),
     )
     return True
     ```
     The key is exactly the outbox idempotency key `DispatchOutboxWriter` writes.
   - Class docstring: one sentence on why it decorates the seam (every dispatch path, one place)
     and one on replay (a duplicate key appends nothing).
2. `src/vibey/bootstrap.py`, in the `rabbitmq` branch `rmq-r17-queue-backend-selection` added to
   `build_app`: both `DispatchOutboxWriter()` constructions (search for `DispatchOutboxWriter()`;
   one is passed to `DispatchingJobRecords(orm, writer=...)`, one to
   `PostgresHumanGateRepository(orm, dispatch_writer=...)`) become
   `LedgeredDispatchOutboxWriter(DispatchOutboxWriter())`. The `postgres` branch is unchanged.
3. **The fake.** `FakeDispatchOutboxWriter` (`tests/fakes/queue.py`, `rmq-r10`) gains keyword
   `store: InMemoryQueueStore | None = None`. When `store` is set and the key is new, it runs
   `await store.ledger.append(store.drafts.dispatched(store.jobs[dispatch.job_id], dispatch_seq=dispatch.dispatch_seq, not_before=dispatch.not_before, key=key))`
   before recording the write. `FakeDispatchingJobRecords` builds its default writer with the
   `InMemoryQueueStore` it holds (the attribute `fakes-queue-gates` gave `FakeJobRepository`; read
   `tests/fakes/queue.py`). A duplicate key appends nothing.

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py` (append the class; edit_file for imports).
- `src/vibey/bootstrap.py` (two expressions, edit_file).
- `tests/fakes/queue.py` (`FakeDispatchOutboxWriter`, and the default writer in
  `FakeDispatchingJobRecords.__init__`).
- Append to `tests/infrastructure/db/test_dispatch_records.py` (integration by its directory)
  and `tests/fakes/test_fake_dispatch_records.py`.

## Acceptance criteria
- [ ] Enqueueing a job with no dependencies through `DispatchingJobRecords(orm, writer=LedgeredDispatchOutboxWriter(DispatchOutboxWriter()))`
      ledgers `JobEnqueued` then `JobDispatched` (`dispatch_seq: 1`, `key: "dispatch:<id>:1"`),
      in that seq order, in one transaction.
- [ ] Replaying that enqueue ledgers nothing more.
- [ ] Acking a dependency ledgers `JobSucceeded` for it and `JobDispatched` for the released dependent.
- [ ] A writer whose `write` returns `False` appends nothing; one whose job row is missing raises `LookupError`.
- [ ] The fake gives the same events in the same order for the same three cases.
- [ ] Under `queue.backend = "rabbitmq"`, `build_app` composes both writers ledgered
      (`isinstance(..., LedgeredDispatchOutboxWriter)` on the records' and the gates' writer,
      through the attribute names `rmq-r10`/`rmq-r15` gave them).
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`; `tests/test_bootstrap.py` passes.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_dispatch_records.py`:
- `test_a_claimable_enqueue_ledgers_its_dispatch_after_the_enqueue`
- `test_a_replayed_enqueue_ledgers_no_second_dispatch`
- `test_an_ack_ledgers_the_released_dependents_dispatch`
- `test_a_missing_job_row_is_refused` (drive `LedgeredDispatchOutboxWriter` directly with an
  inner writer class in the test file whose `write` returns `True`, on a transaction from the
  fixture's seam, for a random job id)
Append to `tests/fakes/test_fake_dispatch_records.py` the first three names with the same
outcomes, plus `test_a_duplicate_dispatch_key_ledgers_nothing`.
Append to `tests/test_bootstrap.py`: `test_the_rabbitmq_backend_ledgers_every_dispatch_writer`
(uses the in-memory app composition `rmq-r17` tests already use; if they need a broker, mark it
`integration` and say so in the commit body).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/infrastructure/orm tests/test_bootstrap.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_dispatch_records.py tests/infrastructure/db/test_job_repository.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The relay's publish and `mark_dispatched` (the relay, `rmq-r13`): publishing is not a job
  transition; a `JobDispatchPublished` kind is a follow-up if the operator wants it.
- The claim, ack and dead-letter park (`gap-ledger-job-events-7`); nack, defer and reap
  (`gap-ledger-job-events-8`).
- Docs, CHANGELOG.

Commit as `feat(ledger): every RabbitMQ dispatch is a ledger event`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-2`, `rmq-r10-dispatch-records-enqueue`,
  `rmq-r15-gate-redispatch`, `rmq-r17-queue-backend-selection`.
- **Must keep passing unchanged:** the protected tests, `rmq-r10`'s and `rmq-r17`'s tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
