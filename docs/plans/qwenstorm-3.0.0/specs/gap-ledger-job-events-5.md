## Title
feat(ledger): a gate answer that releases a parked job is a JobReleased event in the answer's transaction

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) names the answer among the job
facts the ledger must hold ("enqueue, claim, lease renewal and expiry, reap, park, answer and
completion", gap E3). Answering a gate re-readies its parked job in the same transaction as the
answer (`src/vibey/infrastructure/db/human_gate_repository.py:61-86`; ADR-0009: never block a
worker on a human), but only the rows change: the ledger never learns that the job went back to
the queue, or which gate and which person released it.

After `orm-human-gate`, `answer` runs in one `self._orm.transaction()`: the gate `update`, then
`update(JOBS).where(JOBS.c["id"] == row["job_id"], JOBS.c["state"] == "awaiting_human").values(state="ready", updated_at=func.now())`,
then `pg_notify`. This lane adds `RETURNING` to the job update and appends `JobReleased`
(`gap-ledger-job-events-1`) on the same connection. Replay is safe: a second answer finds the job
no longer `awaiting_human`, the update returns no row, and nothing is appended.

## Required behaviour
1. `PostgresHumanGateRepository.__init__` gains keyword parameters after `rows`:
   `events: EventAppenderInterface = DEFAULT_EVENT_APPENDER`,
   `drafts: JobEventDraftBuilderInterface = JOB_EVENT_DRAFTS` and
   `jobs: JobRowMapperInterface = JOB_ROWS` (`vibey.infrastructure.db.ledger_repository`,
   `vibey.infrastructure.db.job_events`, `vibey.infrastructure.db.job_repository`), stored as
   `self._events`, `self._drafts`, `self._jobs`. `build_app` needs no change.
2. In `answer`, the job update gets `.returning(*JOBS.c)`. When it returns a row:
   ```python
   released = self._jobs.to_record(job_row)
   await self._events.append(
       conn,
       self._drafts.released(released, gate_id=gate.gate_id, gate_kind=gate.kind, answered_by=gate.answered_by),
   )
   ```
   where `gate` is the answered gate's record (`self._rows.to_record(row)`), before the
   `pg_notify`. No returned row (the job was not `awaiting_human`) appends nothing. A gate with no
   `job_id` appends nothing. The returned `HumanGateRecord` is unchanged.
3. **The fake.** `FakeHumanGateRepository.answer` (`tests/fakes/queue.py`, lane
   `fakes-queue-gates`): build the answered gate record and, when the gate's job is
   `AWAITING_HUMAN`, the `READY` job record; then
   `await store.ledger.append(store.drafts.released(record, gate_id=..., gate_kind=..., answered_by=...))`;
   then store both records and fire `on_ready`, in that order. (`store.ledger` and `store.drafts` exist
   since `gap-ledger-job-events-2`.) An append that raises leaves the job parked and the gate
   unanswered.

## Where to change
- `src/vibey/infrastructure/db/human_gate_repository.py` (edit_file only).
- `tests/fakes/queue.py` (`FakeHumanGateRepository.answer`).
- Append to `tests/infrastructure/db/test_human_gate_repository.py` (integration by its
  directory) and `tests/fakes/test_fake_queue.py`.

## Acceptance criteria
- [ ] Answering a gate whose job is parked writes one `JobReleased` with the job's id, `state:
      "ready"`, the gate's id and kind, and `answered_by`; the job is claimable.
- [ ] Answering the same gate again writes nothing more.
- [ ] Answering a gate with no job, or whose job is not parked, writes nothing.
- [ ] With `events=` an appender whose `append` raises, `answer` raises, the gate stays
      unanswered and the job stays `awaiting_human`.
- [ ] `tests/infrastructure/test_operator_handlers.py` and every existing test in
      `test_human_gate_repository.py` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_human_gate_repository.py` (park a claimed job with
`PostgresJobRepository(migrated_pool).park(...)`, then raise a gate for it):
- `test_answering_a_parked_jobs_gate_ledgers_job_released`
- `test_a_second_answer_ledgers_nothing_more`
- `test_a_gate_without_a_parked_job_ledgers_nothing`
- `test_a_failed_append_leaves_the_gate_unanswered_and_the_job_parked`
Append to `tests/fakes/test_fake_queue.py` the same four names with the same outcomes, the gate
and job fakes sharing one `InMemoryQueueStore`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/application
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_human_gate_repository.py tests/infrastructure/test_operator_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Ledgering gate raises and the answer's content (the gate row holds them): a follow-up gap.
- The RabbitMQ redispatch an answer writes (`rmq-r15-gate-redispatch`), which the dispatch
  writer ledgers (`gap-ledger-job-events-6`).
- Docs, CHANGELOG.

Commit as `feat(ledger): a gate answer that releases a parked job is a ledger event`. Do not push.

## Lane card
- **Depends on:** `gap-ledger-job-events-2`, `orm-human-gate`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
