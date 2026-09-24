<!-- split of #358: child 2 of 3; audit: issue-audit/updates/358.md -->
## Title
feat(db): nack, defer and reap start a new dispatch episode in their own transaction

## Why
ADR-0044 §4 (`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:215-220`): every RabbitMQ-backend settle that starts
a new dispatch episode — a nack with attempts left (outbox row at the new `run_after`), a defer (at
`retry_at`) and a reap of an expired lease (at `run_after`) — increments `dispatch_seq` and writes one
outbox row **in the same transaction** as the state change, while a nack at the last attempt fails the
job with no bump and a reap still parks a spent job as a `delivery_exhausted` gate (§8, `:277-297`; #356).
Today `DispatchingJobRecords` (#357) inherits all three unchanged from `PostgresJobRepository`
(`src/vibey/infrastructure/db/job_repository.py:237-256`, `:287-320` at `4317cff6`; after the ORM wave,
`JOB_SQL.nack`, `JOB_SQL.defer` and `JOB_SQL.reap` through `PostgresOrmInterface`), so a nacked job in
that backend would sit `ready` with no message ever sent for it. Each statement here is the ORM wave's
own with `.values(...)` and `.returning(...)` added, never restated (the operator's ORM standard), and
the in-memory fake learns the same behaviour (sub-doctrine 9.b, `src/vibey_tools/gh/docs/doctrines.md:349`).
Verified at integration `4317cff6`; `dispatch_statements.py`, `dispatch_records.py`, their interfaces,
`tests/fakes/queue.py` and the three test files do not exist there yet — the dependency lanes create them.

## Required behaviour
1. **Statements** added to `class DispatchStatements` (`src/vibey/infrastructure/db/dispatch_statements.py`)
   and declared on `DispatchStatementsInterface` (return type `ReturningUpdate[Any]` from
   `sqlalchemy.sql.dml`, under `TYPE_CHECKING`):
   - `nack_redispatch(self, job_id: UUID, *, owner: str, error: Mapping[str, object])`:
     ```python
     JOB_SQL.nack(job_id, owner=owner, error=error)
     .values(
         dispatch_seq=case(
             (JOBS.c["attempts"] >= JOBS.c["max_attempts"], JOBS.c["dispatch_seq"]),
             else_=JOBS.c["dispatch_seq"] + 1,
         ),
         dispatched_at=None,
     )
     .returning(JOBS.c["id"], JOBS.c["project_id"], JOBS.c["state"],
                JOBS.c["dispatch_seq"], JOBS.c["kind"], JOBS.c["run_after"])
     ```
     A second `.values()` call extends the first; the `CASE` reads the row's old `attempts`, the same
     test the nack's own state `CASE` makes, so the generation moves exactly when the job goes back to
     `ready`.
   - `defer_redispatch(self, job_id: UUID, *, owner: str, retry_at: datetime, error: Mapping[str, object])`:
     `JOB_SQL.defer(job_id, owner=owner, retry_at=retry_at, error=error).values(dispatch_seq=JOBS.c["dispatch_seq"] + 1, dispatched_at=None).returning(*DISPATCH_COLUMNS)`.
   - `reap_redispatch(self)`:
     `JOB_SQL.reap().values(dispatch_seq=JOBS.c["dispatch_seq"] + 1, dispatched_at=None).returning(*DISPATCH_COLUMNS)`.
     (`JOB_SQL.reap()` already re-readies only `attempts < max_attempts`, #356.)
2. **Records.** `DispatchingJobRecords` (`src/vibey/infrastructure/db/dispatch_records.py`) overrides
   the three `JobRepository` methods; each runs one `async with self._orm.transaction() as conn:`. Build
   each `JobDispatch` from a returned row with the private helper the class already uses for
   `_enqueue_on`/`ack_and_release`; if it has none, add one private method
   `_dispatch_from(self, row: Mapping[str, Any]) -> JobDispatch` returning
   `JobDispatch(job_id=row["id"], project_id=row["project_id"], dispatch_seq=int(row["dispatch_seq"]), kind=str(row["kind"]), not_before=row["run_after"])`.
   - `async def nack(self, job_id: UUID, *, owner: str, error: Mapping[str, object]) -> bool`:
     `row = (await conn.execute(DISPATCH_SQL.nack_redispatch(job_id, owner=owner, error=error))).mappings().first()`;
     `None` returns `False`; when `str(row["state"]) == "ready"` write one outbox row through the
     writer the constructor stored (`await <writer>.write(conn, dispatch)`, `not_before = run_after`);
     a `failed` row writes none. Return `True`.
   - `async def defer(self, job_id: UUID, *, owner: str, retry_at: datetime, error: Mapping[str, object]) -> bool`:
     the same with `defer_redispatch`; a returned row always gets one outbox row (its `run_after` is
     `retry_at`). No row returns `False`.
   - `async def reap(self) -> int`: `parked = await self._park_exhausted(conn)` (#356's protected
     method on `PostgresJobRepository`, unchanged and not duplicated), then
     `rows = (await conn.execute(DISPATCH_SQL.reap_redispatch())).mappings().all()`, one outbox row per
     row, and `return parked + len(rows)`.
   - `ack`, `park`, `heartbeat`, `grant_attempts`, `assign_engine`, `claim_dispatched`, `snapshot` and
     `mark_dispatched` are unchanged.
3. **No new port method:** `nack`, `defer` and `reap` are already on the `JobRepository` Protocol
   (`src/vibey/application/interfaces/queue.py:129-162`), so `DispatchingJobRecordsInterface` does not
   change.
4. **The fake.** `FakeDispatchingJobRecords` (`tests/fakes/queue.py`) overrides the same three methods,
   keeping the parent's signatures. `store` is the shared `InMemoryQueueStore`; "redispatch job J"
   means: `n = self.dispatch_seq.get(J.id, 0) + 1`, `self.dispatch_seq[J.id] = n`,
   `self.dispatched_at[J.id] = None`, and write `JobDispatch(J.id, J.project_id, n, J.kind, J.run_after)`
   through the fake's writer exactly as the fake's `enqueue` writes its dispatches.
   - `nack`: `False` when `await super().nack(...)` is `False`; otherwise, if the job is now
     `JobState.READY`, redispatch it; return `True`.
   - `defer`: `False` when `await super().defer(...)` is `False`; otherwise redispatch; return `True`.
   - `reap`: first collect the ids of jobs that are `LEASED` with `lease_expires_at is not None`,
     `lease_expires_at < store.clock.now()` and `attempts < max_attempts`; then `count = await super().reap()` (which re-readies those and
     parks the exhausted ones, #356); redispatch each collected job; return `count`.
5. **Stop rules.** Stop and report, changing nothing, if `JobStatementsInterface.nack`, `.defer` or
   `.reap` are not typed as `Update` (so `.values()`/`.returning()` do not type-check), or if
   `PostgresJobRepository._park_exhausted(self, conn) -> int` does not exist.

## Where to change
- `src/vibey/infrastructure/db/dispatch_statements.py` and
  `src/vibey/infrastructure/db/interfaces/dispatch_statements_interface.py` (three statements)
- `src/vibey/infrastructure/db/dispatch_records.py` (three overrides, and `_dispatch_from` only if no
  such helper exists)
- `tests/fakes/queue.py` (`FakeDispatchingJobRecords`: three overrides)
- Append to `tests/infrastructure/orm/test_dispatch_statements.py`,
  `tests/fakes/test_fake_dispatch_records.py` and `tests/infrastructure/db/test_dispatch_records.py`.
- Why more than one source file: statements live on the stateless statements class with its interface,
  the records class executes them, the fake must follow the port (9.b), and the proof runs at three
  tiers. `interfaces/dispatch_records_interface.py` does not change (item 3).
- Copy the style of `DispatchStatements.release_enqueued` and `DispatchingJobRecords.ack_and_release`.

## Acceptance criteria
- [ ] A nack with attempts left bumps the generation, clears `dispatched_at` and writes an outbox row at
      the new `run_after`; a nack at the last attempt fails the job with no bump and no outbox row
      (`test_nack_with_attempts_left_redispatches_at_run_after`, `test_nack_at_the_last_attempt_fails_without_dispatch`).
- [ ] A defer bumps the generation and writes an outbox row at `retry_at` (`test_defer_redispatches_at_retry_at`).
- [ ] A reap re-readies with a bump and an outbox row and still parks exhausted rows, with no outbox row
      for a park (`test_reap_redispatches_and_still_parks_exhausted`).
- [ ] A refused nack or defer writes nothing (`test_a_refused_settle_writes_no_dispatch`); an ack from a
      stale owner after a reap-redispatch is refused (`test_stale_owner_ack_after_reap_is_refused`).
- [ ] Each of these holds on PostgreSQL and on the fake (same test names in both files).
- [ ] `tests/fakes/test_port_parity.py` passes; 100% branch coverage of `src/vibey/infrastructure/`.
- [ ] `git diff HEAD -- src/` adds no `import asyncpg`, `text(`, `literal_column` or `exec_driver_sql`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_dispatch_statements.py` (append; no service; compile with
`sqlalchemy.dialects.postgresql.asyncpg.dialect()`, assert on `str(compiled)` and `compiled.params`):
- `test_nack_redispatch_bumps_below_the_bound_and_clears_the_stamp`: the text has
  `THEN job.dispatch_seq ELSE job.dispatch_seq +`, `dispatched_at=`, `job.lease_owner =` and
  `RETURNING job.id, job.project_id, job.state, job.dispatch_seq, job.kind, job.run_after`;
  `compiled.params["dispatched_at"] is None`.
- `test_nack_redispatch_keeps_the_queue_backoff`: the text still has
  `CASE WHEN (job.attempts >= job.max_attempts)`, `least(`, `power(` and `random()`.
- `test_defer_redispatch_always_bumps`: the text has `dispatch_seq=(job.dispatch_seq +`,
  `job.lease_owner =`, `job.state =` and `RETURNING job.id, job.project_id, job.dispatch_seq, job.kind, job.run_after`;
  the params hold the `retry_at` datetime.
- `test_reap_redispatch_bumps_only_below_the_bound`: the text has `job.attempts < job.max_attempts`,
  `job.lease_expires_at < now()`, `dispatch_seq=(job.dispatch_seq +` and
  `RETURNING job.id, job.project_id, job.dispatch_seq, job.kind, job.run_after`.

`tests/fakes/test_fake_dispatch_records.py` (append; no service): the six names below, the same
scenarios on `FakeDispatchingJobRecords` over an `InMemoryQueueStore` with the file's frozen clock, a
`FakeDispatchOutboxWriter` passed as `writer=`, and assertions on `writer.written`,
`records.dispatch_seq`, `records.dispatched_at` and `store.jobs`/`store.gates`. Expire a lease by
advancing the clock past it.

`tests/infrastructure/db/test_dispatch_records.py` (append; integration by its directory;
`records = DispatchingJobRecords(migrated_pool, writer=DispatchOutboxWriter())`; claim with
`records.claim_dispatched(JobDispatch(job.id, project_id, seq, job.kind, job.run_after), owner=..., lease=timedelta(seconds=30))`;
expire a lease with `await migrated_pool.execute("UPDATE job SET lease_expires_at = now() - interval '1 second' WHERE id = $1", job_id)`;
read an outbox payload with `json.loads(await migrated_pool.fetchval("SELECT payload FROM job_outbox WHERE idempotency_key = $1", key))`
and decode it with `JOB_DISPATCH_CODEC.decode(...)`):
- `test_nack_with_attempts_left_redispatches_at_run_after`: `max_attempts=3`, claimed at generation 1
  by `"w1"`, `nack(job.id, owner="w1", error={"reason": "boom"})` is `True`; the row is `ready` at
  generation 2 with `dispatched_at` NULL; the row keyed `f"dispatch:{job.id}:2"` decodes to generation 2
  with `not_before` equal to the row's `run_after`.
- `test_nack_at_the_last_attempt_fails_without_dispatch`: `max_attempts=1`; after the nack the row is
  `failed` at generation 1 and no `f"dispatch:{job.id}:2"` row exists.
- `test_defer_redispatches_at_retry_at`: `retry_at = datetime.now(UTC) + timedelta(hours=1)`;
  `defer(job.id, owner="w1", retry_at=retry_at, error={"reason": "capacity"})` is `True`; generation 2;
  the new outbox row's `not_before == retry_at`.
- `test_reap_redispatches_and_still_parks_exhausted`: `reap()` is `0` while nothing has expired. Then A
  (`max_attempts=3`) and B (`max_attempts=1`), each claimed once, both leases expired: `reap() == 2`; A
  is `ready` at generation 2 with a `f"dispatch:{a}:2"` row; B is `awaiting_human` with `attempts == 0`,
  one open `delivery_exhausted` gate (`SELECT count(*) FROM human_gate WHERE job_id = $1 AND kind = 'delivery_exhausted' AND answered_at IS NULL` is 1)
  and no `f"dispatch:{b}:2"` row.
- `test_a_refused_settle_writes_no_dispatch`: claimed by `"w1"`; `nack(owner="w2")` and
  `defer(owner="w2", ...)` are both `False`; the row is still leased by `"w1"` at generation 1 and has
  exactly one outbox row.
- `test_stale_owner_ack_after_reap_is_refused`: claimed by `"w1"`, lease expired, `reap()` redispatches
  it at generation 2, `claim_dispatched` at generation 2 by `"w2"` hits; `ack(job.id, owner="w1")` is
  `False`; `ack(job.id, owner="w2")` is `True`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
# No-service tests: compiled statements and the in-memory fake. (Until lane fakes-harness-decouple lands the
# root tests/conftest.py:146-151 still opens PostgreSQL at session start; these tests themselves touch none.)
uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_dispatch_statements.py tests/fakes/test_fake_dispatch_records.py tests/fakes/test_fake_queue.py tests/fakes/test_port_parity.py
# PostgreSQL tests (integration tier)
uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/db/test_dispatch_records.py tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_human_gate_repository.py
uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
uv run pytest -q -p no:cacheprovider tests/application/test_worker.py
# The whole suite with coverage, then the infrastructure floor
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# No raw SQL added, no protected test touched
! git diff HEAD -- src/ | grep -nE '^\+.*(import asyncpg|[^A-Za-z_]text\(|literal_column|exec_driver_sql)'
test -z "$(git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live)"
git diff --stat
```

## Out of scope
- The fenced claim, the snapshot and `mark_dispatched` (child 1); the sweep and the dead-letter park
  (child 3, `split-358-3-sweep-and-park`).
- `PostgresJobRepository` and `JobStatements` (including `_park_exhausted` and `JOB_SQL.reap`), the
  gate answer's redispatch (#362), publishing (#360), consuming (#361), the composed repository (#363).
- `tests/fakes/registry.py`; `interfaces/dispatch_records_interface.py`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push or change remotes. Commit locally with the Title as the subject.

## Conventions this lane relies on (everything needed is here)
The dependency lanes create these; read each file before editing it. If a name below differs from what
the file says, stop and report the difference instead of renaming anything.
- **Tables and constants** (`dispatch_statements.py`): `JOBS = TABLES.table("job")`,
  `DEPENDENCIES = TABLES.table("job_dependency")`,
  `DISPATCH_COLUMNS = (JOBS.c["id"], JOBS.c["project_id"], JOBS.c["dispatch_seq"], JOBS.c["kind"], JOBS.c["run_after"])`,
  `DISPATCH_SQL: Final[DispatchStatementsInterface] = DispatchStatements()`. Columns are read as
  `JOBS.c["name"]`. The `job` table has `dispatch_seq bigint NOT NULL DEFAULT 0` and
  `dispatched_at timestamptz` (migration 0014, #355).
- **The queue statements** (`src/vibey/infrastructure/db/job_statements.py`, `JOB_SQL: Final[JobStatementsInterface]`):
  - `JOB_SQL.nack(job_id, *, owner, error)`: `update(JOBS).where(id ==, lease_owner == owner)` setting
    `state = CASE WHEN attempts >= max_attempts THEN 'failed' ELSE 'ready'` (typed `job_state` literals),
    the lease cleared, `run_after = now() + least(power(2, attempts) * 2 s, 15 min) * random()`,
    `last_error`, `updated_at`.
  - `JOB_SQL.defer(job_id, *, owner, retry_at, error)`: `.where(id ==, lease_owner == owner, state == "leased")`
    setting `state='ready'`, the lease cleared, `attempts = greatest(attempts - 1, 0)`,
    `run_after = retry_at`, `last_error`, `updated_at`.
  - `JOB_SQL.reap()`: `update(JOBS).where(state == "leased", lease_expires_at < now(), attempts < max_attempts)`
    setting `state='ready'`, the lease cleared, `updated_at` (#356 added the `attempts` bound).
  - `JOB_SQL.notify_gate_raised(gate_id)` and `JOB_SQL.reap_exhausted()` exist (#356); this lane reaches
    them only through `_park_exhausted`.
- **The repository** (`job_repository.py`): `PostgresJobRepository.__init__(self, orm, *, rows=JOB_ROWS)`
  keeps `self._orm` and `self._rows`; `async def _park_exhausted(self, conn: AsyncConnection) -> int`
  (#356) parks every expired lease whose attempts are spent as `awaiting_human` (one attempt refunded),
  inserts one `delivery_exhausted` gate per parked job, notifies `vibey_gate_raised` per gate, and
  returns how many it parked. `self._orm.transaction()` yields an `AsyncConnection` that commits on a
  clean exit and rolls back on raise.
- **#357's records** (`dispatch_records.py`): `DispatchOutboxWriter.write(conn, dispatch, *, key_suffix="") -> bool`
  inserts one `job_outbox` row keyed `f"dispatch:{dispatch.job_id}:{dispatch.dispatch_seq}{key_suffix}"`
  with payload `JOB_DISPATCH_CODEC.encode(dispatch)`, inside the caller's transaction, and returns
  whether a row was inserted. `DispatchingJobRecords(PostgresJobRepository)` takes `orm`, keyword
  `writer` and keyword `rows`; its `ack` returns `ack_and_release(job_id, owner=owner)[0]`. Child 1 added
  `claim_dispatched(dispatch, *, owner, lease) -> JobRecord | None`, `snapshot` and
  `mark_dispatched(job_id, dispatch_seq) -> bool`.
- **The fakes** (`tests/fakes/queue.py`): `InMemoryQueueStore` (`jobs`, `dependencies`, `gates`,
  `notified`, `clock` with `now()`); `FakeJobRepository(jobs=None, *, store=None)` whose `nack`, `defer`
  and `reap` follow PostgreSQL (its `reap` parks spent jobs with a `delivery_exhausted` gate in
  `store.gates` and returns parked plus re-readied, #356); `FakeDispatchOutboxWriter` keeps
  `written: list[tuple[str, JobDispatch]]`; `FakeDispatchingJobRecords(FakeJobRepository)` takes keyword
  `writer` and keeps `dispatch_seq: dict[UUID, int]` and (child 1) `dispatched_at: dict[UUID, datetime | None]`.
  `JobRecord` is a frozen dataclass.
- **The envelope** (`src/vibey/domain/job_dispatch.py`): `JobDispatch(job_id: UUID, project_id: UUID, dispatch_seq: int, kind: str, not_before: datetime)`,
  frozen, `dispatch_seq >= 1`, `not_before` timezone-aware; `JOB_DISPATCH_CODEC.encode(d)` /
  `.decode(mapping)` (keys `schema`, `job_id`, `project_id`, `dispatch_seq`, `kind`, `not_before`).
- **Test fixtures:** `migrated_pool` is both the ORM seam and an asyncpg pool (`execute`, `fetchval`,
  `fetchrow`, `acquire` pass through); `project_id` inserts a project and returns its id. Enqueue with
  `EnqueueRequest(project_id=project_id, cycle=1, phase=Phase.BUILD, kind="build.implement", idempotency_key=f"key-{subject}", max_attempts=...)`
  or the file's `_request` helper; an enqueued job with no dependencies starts at generation 1 with one
  outbox row.

## Standing constraints
### Lane card
- **Files touched:** the four under *Where to change*, plus the three test files (append only).
- **Parallel-safe with:** #359, #362 and the loop-service lanes. It follows child 1 on the same files;
  never run it at the same time as child 3.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_job_repository.py`,
  `tests/infrastructure/db/test_human_gate_repository.py`, `tests/infrastructure/db/test_chaos.py`
  (protected), `tests/fakes/test_fake_queue.py`, `tests/application/test_worker.py`, #357's and child 1's
  tests, `tests/fakes/test_port_parity.py`, all protected tests.

### For every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  They must keep passing.
- **The first line of every new source file** is the provenance comment, copied byte-for-byte from line 1
  of a sibling file.
- **The default run needs no outside service.** Until lane `fakes-harness-decouple` lands, the root
  `tests/conftest.py` still opens PostgreSQL at session start (`:146-151`), so "no service" means the
  test itself touches none. PostgreSQL-backed tests are `integration` and are never the lane's only proof.
- **Substitution at a declared seam only:** never `monkeypatch.setattr` on a module attribute,
  `mock.patch`, `MagicMock` or `AsyncMock`. Every changed port method has matching behaviour in its
  in-memory fake.
- **Persistence goes through `PostgresOrmInterface`** with SQLAlchemy 2 async Core: no new
  `import asyncpg`, `text()`, `literal_column`, `exec_driver_sql()` or SQL strings in `src/`.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.
- Arch Linux and macOS both: the checks need only `uv`, `git` and a local PostgreSQL.

**Depends on:** rmq-r10-dispatch-records-enqueue, rmq-r09-reap-bound, split-358-1-fenced-claim
- rmq-r10-dispatch-records-enqueue: `DispatchStatements`, `DISPATCH_COLUMNS`, `DispatchingJobRecords`, `DispatchOutboxWriter`, the fakes and the three test files.
- rmq-r09-reap-bound: `PostgresJobRepository._park_exhausted`, the `attempts < max_attempts` bound in `JOB_SQL.reap()`, and the fake's parking `reap`.
- split-358-1-fenced-claim: `claim_dispatched` (used by the tests), the fake's `dispatched_at` dict, and the same files in their child-1 state.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
