## Title
feat(ledger): job enqueue, claim and completion are ledger events, written in the job row's transaction

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`): "every job … with its time,
its actor and its evidence, written as it happens rather than reconstructed after". Today the
queue writes only the mutable `job` row (`src/vibey/infrastructure/db/job_repository.py:49-160`
enqueue, `:178` claim, `:223` ack). `gap-ledger-job-events-1` added the kinds and
`JOB_EVENT_DRAFTS`; this lane appends `JobEnqueued`, `JobClaimed` and `JobSucceeded`.

Each event is appended **on the same connection, inside the same transaction as the job
statement**, through `EventAppenderInterface` (`ConnectionEventAppender`,
`ledger_repository.py:87-138`), which exists for exactly this. Replay stays idempotent because
the job statement is itself the guard: a replayed enqueue hits `ON CONFLICT DO NOTHING` and
returns no row; a replayed ack no longer matches `lease_owner = $owner`; in both cases no event
is appended. A failed append rolls the job write back, so no transition lands unledgered.

This lane builds on the ORM wave: after `orm-job-settle`, `PostgresJobRepository` takes
`PostgresOrmInterface`, runs writes in `self._orm.transaction()` and builds statements with
`JOB_SQL` (`src/vibey/infrastructure/db/job_statements.py`). No raw SQL is added. The in-memory
twin (`FakeJobRepository`, `tests/fakes/queue.py`, lane `fakes-queue-gates`) appends the same
drafts to the in-memory ledger (`InMemoryLedger`, `tests/fakes/ledger.py`, lane `fakes-ledger`).

## Required behaviour
1. `PostgresJobRepository.__init__` gains two keyword parameters after `rows`:
   `events: EventAppenderInterface = DEFAULT_EVENT_APPENDER` (from
   `vibey.infrastructure.db.ledger_repository`) and
   `drafts: JobEventDraftBuilderInterface = JOB_EVENT_DRAFTS` (from
   `vibey.infrastructure.db.job_events`), stored as `self._events` and `self._drafts`.
   `build_app` needs no change (defaults).
2. `_enqueue_on`: in the branch where `JOB_SQL.insert_job(request)` returned a row, after the
   dependency inserts and before `JOB_SQL.notify_ready(...)`:
   `record = self._rows.to_record(row)`, then
   `await self._events.append(conn, self._drafts.enqueued(record, depends_on=depends_on))`,
   and return `record`. The existing-row branch (a replay) appends nothing. Because
   `enqueue_batch` calls `_enqueue_on` inside its one transaction, a rolled-back batch leaves no
   event. `rmq-r10`'s `DispatchingJobRecords._enqueue_on` calls `super()._enqueue_on(...)`, so
   it inherits this.
3. `claim`: inside its transaction, when the claim returns a row:
   `record = self._rows.to_record(row)`;
   `await self._events.append(conn, self._drafts.claimed(record))`; return `record`.
   No row → `None` and no event.
4. `ack`: execute `JOB_SQL.ack(job_id, owner=owner).returning(*JOBS.c)` (`JOBS` from
   `vibey.infrastructure.db.job_statements`; `Update.returning` accumulates, so the shared
   statement is not changed). `row = result.mappings().first()`; `None` → `return False`, no
   event. Otherwise append `self._drafts.succeeded(self._rows.to_record(row), owner=owner)` and
   `return True`.
5. **Lock order.** Every event is appended after the job statements of its transaction. The
   append claims the project's `event_seq` row (`append_event`, `migrations/0013_ledger_partitioning.sql:84-114`: `INSERT … ON CONFLICT (project_id) DO UPDATE` on `event_seq`),
   so claims and acks of one project serialize on it until commit; a transaction never waits on
   a job row after holding it, so this adds no deadlock. The one `enqueue_batch` caller
   (`src/vibey/application/build_decompose_handler.py:89`) enqueues a single project.
6. **The fake.** `InMemoryQueueStore.__init__` gains keyword
   `ledger: LedgerRepositoryInterface | None = None` (the interface `fakes-ledger` added to
   `src/vibey/infrastructure/db/interfaces/ledger_repository_interface.py`), stored as
   `self.ledger = ledger if ledger is not None else InMemoryLedger()`, and keyword
   `drafts: JobEventDraftBuilderInterface = JOB_EVENT_DRAFTS`. `FakeJobRepository`:
   - `enqueue`: for a new job only, `await store.ledger.append(store.drafts.enqueued(record, depends_on=<resolved ids>))`
     before storing the job. An existing key appends nothing.
   - `enqueue_batch`: after every key has resolved, append one `enqueued` draft per new job, in
     request order, then store the jobs. (The in-memory ledger has no rollback; a failing append
     part-way is not modelled, and the method docstring says so.)
   - `claim`: build the leased record, append `claimed(record)`, then store it.
   - `ack`: build the succeeded record, append `succeeded(record, owner=owner)`, then store it;
     a refused ack appends nothing.
   An append that raises (`InMemoryLedger.fail_next_append`) leaves the store unchanged.

## Where to change
- `src/vibey/infrastructure/db/job_repository.py` (edit_file only).
- `tests/fakes/queue.py` (`InMemoryQueueStore.__init__`, `FakeJobRepository.enqueue`,
  `enqueue_batch`, `claim`, `ack`).
- Append to `tests/infrastructure/db/test_job_repository.py` (integration by its directory) and
  to `tests/fakes/test_fake_queue.py` (no service). Do not rewrite either.

## Acceptance criteria
- [ ] Enqueue writes one `JobEnqueued` for the job; enqueueing the same key again returns the
      same record and the ledger still holds one (`PostgresLedgerRepository(migrated_pool).all_for_project`).
- [ ] A batch whose third request names an unknown key raises `LookupError` and leaves no job
      and no event.
- [ ] A claim writes one `JobClaimed` whose payload `owner` is the claimant and whose `attempts` is 1.
- [ ] An ack writes one `JobSucceeded`; a replayed ack returns `False` and writes nothing; an ack
      by a stale owner returns `False` and writes nothing.
- [ ] With `events=` an appender whose `append` raises `RuntimeError`, `claim` raises and the
      job is still `ready` with `attempts == 0`.
- [ ] Every fake test below asserts the same outcome as its PostgreSQL twin.
- [ ] `tests/infrastructure/db/test_chaos.py` (protected) passes unchanged with `-s`; if it
      times out, stop and report the tally — never edit it.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_job_repository.py`:
- `test_enqueue_ledgers_one_job_enqueued_and_a_replay_ledgers_none`
- `test_a_rolled_back_batch_ledgers_nothing`
- `test_claim_ledgers_job_claimed_with_owner_and_attempt`
- `test_ack_ledgers_job_succeeded_once`
- `test_a_stale_owner_ack_ledgers_nothing`
- `test_a_failed_append_rolls_the_claim_back` (a small `_FailingAppender` class in the test file
  implementing `EventAppenderInterface`, passed as `events=`)
Append to `tests/fakes/test_fake_queue.py`, with the same names and outcomes. Each test builds
`store = InMemoryQueueStore()` and `repo = FakeJobRepository(store=store)` and reads
`store.ledger.events`; the failing case uses `store.ledger.fail_next_append(RuntimeError("x"))`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/application/test_worker.py tests/infrastructure/orm
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_build_decompose_fan_out.py tests/infrastructure/db/test_keda_scaler_query.py
    uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Heartbeat, nack, defer, park and grant (`gap-ledger-job-events-3`); reap
  (`gap-ledger-job-events-4`); the gate answer (`gap-ledger-job-events-5`); the RabbitMQ
  records (`gap-ledger-job-events-6` … `-8`).
- `assign_engine` writes no job event: the selection is ledgered as `EngineSelected`
  (`gap-ledger-selection-events-1`).
- Docs, CHANGELOG.

Commit as `feat(ledger): job enqueue, claim and completion are ledger events`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-1`, `orm-job-settle`, `orm-ledger`, `fakes-queue-gates`, `fakes-ledger`.
- **Must keep passing unchanged:** the protected tests (`tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
