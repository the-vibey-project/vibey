<!-- split of #358: child 3 of 3; audit: issue-audit/updates/358.md -->
## Title
feat(db): the lost-dispatch sweep and the dead-letter park

## Why
ADR-0044 §4 (`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:221`, `:304`) adds a lost-dispatch sweep: a claimable row
whose message looks lost (not dispatched within `redispatch_after`), or one still at generation 0 (the
enqueue-versus-ack race #357 leaves open), is dispatched again — generation 0 moves to 1, an older one
is re-sent at the **same** generation under the key `dispatch:<job_id>:<seq>:sweep:<epoch>`, a harmless
duplicate that keeps its FIFO position. ADR-0044 §8 (`:277-297`) turns a pointer that dead-lettered past
`x-delivery-limit` into a `delivery_exhausted` gate and an `awaiting_human` job in one transaction, only
while the row is still claimable at that generation (ADR-0024: every bounded ladder parks with a grant).
Both run through `PostgresOrmInterface` as SQLAlchemy 2 async Core and reuse `JOB_SQL.deps_unmet`,
`JOB_SQL.notify_gate_raised` (#356) and child 1's `DISPATCH_SQL.mark_dispatched`; every batch size and
bound is a parameter the caller reads from `[queue.rabbitmq]` (#348), so no new hard-coded constant
appears (12.c, `src/vibey_tools/gh/docs/doctrines.md:455`), and the in-memory fake learns both (9.b,
`doctrines.md:349`). Verified at integration `4317cff6`; `dispatch_statements.py`,
`dispatch_records.py`, their interfaces, `tests/fakes/queue.py` and the three test files do not exist
there yet — the dependency lanes create them.

## Required behaviour
1. **Statements** added to `class DispatchStatements` (`src/vibey/infrastructure/db/dispatch_statements.py`),
   each declared on `DispatchStatementsInterface`, plus a module constant `GATES = TABLES.table("human_gate")`
   beside `JOBS`:
   - `sweep_candidates(self, *, redispatch_after: timedelta, limit: int)`:
     ```python
     select(*DISPATCH_COLUMNS)
     .where(
         JOBS.c["state"] == "ready",
         JOBS.c["run_after"] <= func.now(),
         or_(JOBS.c["dispatch_seq"] == 0,
             JOBS.c["dispatched_at"] < func.now() - literal(redispatch_after, Interval())),
         ~JOB_SQL.deps_unmet(JOBS),
     )
     .order_by(JOBS.c["run_after"].asc())
     .limit(limit)
     .with_for_update(skip_locked=True)
     ```
     A row at generation ≥ 1 with `dispatched_at IS NULL` (its outbox row is still pending) is never
     selected: `NULL < x` is not true.
   - `sweep_first_dispatch(self, job_id: UUID)`:
     `update(JOBS).where(JOBS.c["id"] == job_id, JOBS.c["dispatch_seq"] == 0).values(dispatch_seq=1, dispatched_at=func.now())`.
   - `sweep_epoch(self)`: `select(func.extract("epoch", func.now()))` (it renders
     `EXTRACT(epoch FROM now())`).
   - `park_dead_letter(self, dispatch: JobDispatch)`:
     ```python
     update(JOBS)
     .where(
         JOBS.c["id"] == dispatch.job_id,
         JOBS.c["dispatch_seq"] == dispatch.dispatch_seq,
         or_(JOBS.c["state"] == "ready",
             and_(JOBS.c["state"] == "leased", JOBS.c["lease_expires_at"] < func.now())),
     )
     .values(state="awaiting_human", lease_owner=None, lease_expires_at=None,
             attempts=func.greatest(JOBS.c["attempts"] - 1, 0), updated_at=func.now())
     .returning(JOBS.c["project_id"], JOBS.c["kind"])
     ```
   - `dead_letter_prompt(self, kind: str, delivery_limit: int) -> str`:
     `f"job {kind!r} was delivered {delivery_limit} times and every consumer holding it died. Answer anything to retry it with a fresh delivery budget."`
   - `dead_letter_gate(self, project_id: UUID, job_id: UUID, prompt: str)`:
     `insert(GATES).values(project_id=project_id, job_id=job_id, kind="delivery_exhausted", prompt=prompt).returning(GATES.c["gate_id"])`.
   Interface return types, under `TYPE_CHECKING` as the file already does: `Select[Any]`, `Update`,
   `ReturningUpdate[Any]`, `ReturningInsert[Any]` and `str`.
2. **Records** added to `class DispatchingJobRecords` (`src/vibey/infrastructure/db/dispatch_records.py`)
   and declared on `DispatchingJobRecordsInterface`. Build each `JobDispatch` from a returned row with
   the class's private row-to-dispatch helper (`_dispatch_from`, or the one #357 wrote), passing the
   generation explicitly where it changes.
   - `async def sweep_lost(self, *, redispatch_after: timedelta, limit: int) -> int`, one
     `async with self._orm.transaction() as conn:`, in exactly this order:
     1. `rows = (await conn.execute(DISPATCH_SQL.sweep_candidates(redispatch_after=redispatch_after, limit=limit))).mappings().all()`;
        no rows returns `0` (and reads no epoch);
     2. `epoch = int(await conn.scalar(DISPATCH_SQL.sweep_epoch()))`, read once;
     3. for each row, in order: at generation 0, execute `DISPATCH_SQL.sweep_first_dispatch(row["id"])`
        and write the dispatch at generation 1 with the plain key; at generation ≥ 1, execute
        `DISPATCH_SQL.mark_dispatched(row["id"], seq)` (child 1) and write the dispatch at the **same**
        generation with `key_suffix=f":sweep:{epoch}"`. Either way the row's `dispatched_at` becomes
        `now()`, so the next sweep waits `redispatch_after`;
     4. return the number of `write(...)` calls that returned `True`.
     `limit` is required: the caller passes `QueueRabbitMqConfig.sweep_batch` and
     `timedelta(seconds=QueueRabbitMqConfig.redispatch_after_seconds)`.
   - `async def park_dead_letter(self, dispatch: JobDispatch, *, delivery_limit: int) -> bool`, one
     `self._orm.transaction()`: `row = (await conn.execute(DISPATCH_SQL.park_dead_letter(dispatch))).mappings().first()`;
     no row returns `False`; otherwise
     `gate_id = (await conn.execute(DISPATCH_SQL.dead_letter_gate(row["project_id"], dispatch.job_id, DISPATCH_SQL.dead_letter_prompt(str(row["kind"]), delivery_limit)))).scalar_one()`,
     then `await conn.execute(JOB_SQL.notify_gate_raised(gate_id))`, and return `True`. The gate is
     answered through the ordinary gate path; the redispatch on that answer is #362's.
3. Everything else in both classes is unchanged.
4. **The fake.** `FakeDispatchingJobRecords` (`tests/fakes/queue.py`) gains the two methods with the same
   signatures (`tests/fakes/test_port_parity.py` compares them). `store` is the shared
   `InMemoryQueueStore`, `now = store.clock.now()`, `seq(id) = self.dispatch_seq.get(id, 0)`, and
   "deps met" means every id in `store.dependencies.get(id, ())` is a job whose state `is JobState.SUCCEEDED`.
   Write through the fake's writer exactly as the fake's `enqueue` does.
   - `sweep_lost(*, redispatch_after, limit)`: candidates are the jobs with `state is JobState.READY`,
     `run_after <= now`, deps met, and either `seq(id) == 0` or
     (`self.dispatched_at.get(id)` is not `None` and `< now - redispatch_after`), sorted by
     `(run_after, str(id))`, first `limit` of them. `epoch = int(now.timestamp())`. For each: at
     generation 0 set `self.dispatch_seq[id] = 1` and write `JobDispatch(id, project_id, 1, kind, run_after)`;
     otherwise write the dispatch at `seq(id)` with `key_suffix=f":sweep:{epoch}"`; then
     `self.dispatched_at[id] = now`. Return how many writes returned `True`.
   - `park_dead_letter(dispatch, *, delivery_limit)`: `False` when the job is unknown,
     `seq(id) != dispatch.dispatch_seq`, or it is neither `READY` nor (`LEASED` with
     `lease_expires_at is not None and lease_expires_at < now`). Otherwise store
     `dataclasses.replace(job, state=JobState.AWAITING_HUMAN, lease_owner=None, lease_expires_at=None, attempts=max(job.attempts - 1, 0), updated_at=now)`,
     add `HumanGateRecord(gate_id=uuid4(), project_id=job.project_id, job_id=job.id, kind="delivery_exhausted", prompt=DISPATCH_SQL.dead_letter_prompt(job.kind, delivery_limit), options=(), default_answer=None, answer=None, raised_at=now, timeout_at=None, answered_at=None, answered_by=None)`
     to `store.gates` under its `gate_id`, and return `True`. (The in-memory store has no gate-raised
     channel; `FakeHumanGateRepository(store=store).raised` lists the gate.)

## Where to change
- `src/vibey/infrastructure/db/dispatch_statements.py` and
  `src/vibey/infrastructure/db/interfaces/dispatch_statements_interface.py` (`GATES` and six statements)
- `src/vibey/infrastructure/db/dispatch_records.py` and
  `src/vibey/infrastructure/db/interfaces/dispatch_records_interface.py` (two methods)
- `tests/fakes/queue.py` (`FakeDispatchingJobRecords`: two methods)
- Append to `tests/infrastructure/orm/test_dispatch_statements.py`,
  `tests/fakes/test_fake_dispatch_records.py` and `tests/infrastructure/db/test_dispatch_records.py`.
- Why more than one source file: statements live on the stateless statements class with its interface,
  the records class executes them behind its own interface, the fake must follow the port (9.b), and the
  proof runs at three tiers (compiled, fake, PostgreSQL). Nothing else changes.
- Copy the style of `DispatchStatements.release_enqueued` and `DispatchingJobRecords.ack_and_release`.

## Acceptance criteria
- [ ] The sweep dispatches the generation-0 race and old dispatches, skips rows whose outbox row is still
      pending (`dispatched_at IS NULL` at generation ≥ 1), respects `limit`, and throttles itself — on
      PostgreSQL and on the fake (`test_sweep_*` in both files).
- [ ] `park_dead_letter` parks and raises a gate only while the row is claimable at that generation
      (`test_park_dead_letter_parks_only_a_claimable_row`), and a listener on `vibey_gate_raised` receives
      the gate id (`test_park_dead_letter_notifies_the_raised_gate`).
- [ ] The compiled sweep renders `FOR UPDATE SKIP LOCKED`; the park is fenced by generation
      (`tests/infrastructure/orm/test_dispatch_statements.py`).
- [ ] `tests/fakes/test_port_parity.py` passes; 100% branch coverage of `src/vibey/infrastructure/`.
- [ ] `git diff HEAD -- src/` adds no `import asyncpg`, `text(`, `literal_column` or `exec_driver_sql`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_dispatch_statements.py` (append; no service; compile with
`sqlalchemy.dialects.postgresql.asyncpg.dialect()`, assert on `str(compiled)` and `compiled.params.values()`):
- `test_the_sweep_locks_its_candidates_and_skips_locked_rows`: the text has `FOR UPDATE SKIP LOCKED`,
  `ORDER BY job.run_after ASC`, `LIMIT`, `job.dispatched_at < now() -` and `NOT (EXISTS (`; the params
  hold `0`, `timedelta(minutes=15)` and `500`.
- `test_the_first_sweep_dispatch_moves_only_sequence_zero`: the text starts `UPDATE job SET dispatch_seq=`
  and has `dispatched_at=now()` and `job.dispatch_seq =`; the params hold `1` and `0`.
- `test_the_sweep_epoch_is_the_database_clock`: the text has `EXTRACT(epoch FROM now())`.
- `test_the_dead_letter_park_is_fenced_by_generation`: the text has `job.dispatch_seq =`,
  `job.lease_expires_at < now()`, ` OR `, `greatest(` and `RETURNING job.project_id, job.kind`; the
  params hold `"awaiting_human"`, the job id and the generation.
- `test_the_dead_letter_gate_binds_kind_and_prompt`: the text has `INSERT INTO human_gate` and
  `RETURNING human_gate.gate_id`; the params hold `"delivery_exhausted"` and the prompt.
- `test_the_dead_letter_prompt_names_the_kind_and_the_limit`:
  `DISPATCH_SQL.dead_letter_prompt("build.implement", 20) == "job 'build.implement' was delivered 20 times and every consumer holding it died. Answer anything to retry it with a fresh delivery budget."`.
- `test_the_sweep_keys_old_dispatches_by_the_database_epoch` (the records through the seam double
  `FakeOrm`/`FakeResult` from `tests/infrastructure/orm/fakes.py`, and `FakeDispatchOutboxWriter` from
  `tests/fakes/queue.py`): with `due = datetime(2026, 9, 22, 12, tzinfo=UTC)`,
  `orm = FakeOrm(FakeResult([{"id": a, "project_id": p, "dispatch_seq": 0, "kind": "build.implement", "run_after": due}, {"id": b, "project_id": p, "dispatch_seq": 3, "kind": "build.implement", "run_after": due}]), FakeResult(scalar=Decimal("1790000000.75")), FakeResult(rowcount=1), FakeResult(rowcount=1))`,
  `DispatchingJobRecords(orm, writer=writer).sweep_lost(redispatch_after=timedelta(minutes=15), limit=500)`
  returns `2`, `[key for key, _ in writer.written] == [f"dispatch:{a}:1", f"dispatch:{b}:3:sweep:1790000000"]`
  and `len(orm.connection.statements) == 4`; with `FakeOrm(FakeResult([]))` it returns `0` after one statement.

`tests/fakes/test_fake_dispatch_records.py` (append; no service): the six sweep/park names below except
the notification test, same scenarios on `FakeDispatchingJobRecords` over an `InMemoryQueueStore` with
the file's frozen clock and a `FakeDispatchOutboxWriter` passed as `writer=`. Age a dispatch by
advancing the clock; make a dependency succeed without an ack with
`store.jobs[a] = dataclasses.replace(store.jobs[a], state=JobState.SUCCEEDED)`.

`tests/infrastructure/db/test_dispatch_records.py` (append; integration by its directory;
`records = DispatchingJobRecords(migrated_pool, writer=DispatchOutboxWriter())`; SQL in the test goes
through the fixture's asyncpg pass-throughs, e.g. `migrated_pool.execute(...)`/`fetchval(...)`):
- `test_sweep_dispatches_the_seq_zero_race`: enqueue A, then B depending on A (B stays at generation 0);
  set A `succeeded` without an ack (`UPDATE job SET state = 'succeeded' WHERE id = $1`);
  `sweep_lost(redispatch_after=timedelta(minutes=15), limit=500) == 1`; B is at generation 1 with
  `dispatched_at` set and a `f"dispatch:{b}:1"` outbox row.
- `test_sweep_duplicates_an_old_dispatch_at_the_same_generation`: enqueue A (generation 1, one outbox
  row), `mark_dispatched(a, 1)`, then age it (`UPDATE job SET dispatched_at = now() - interval '1 hour' WHERE id = $1`);
  the sweep returns `1`; A is still at generation 1; a second outbox row's key starts
  `f"dispatch:{a}:1:sweep:"` and its payload decodes (`JOB_DISPATCH_CODEC.decode(json.loads(...))`) to
  generation 1; `dispatched_at` is within the last minute.
- `test_sweep_skips_a_pending_outbox_row`: enqueue A (generation 1, `dispatched_at` NULL); the sweep
  returns `0` and A still has exactly one outbox row.
- `test_sweep_throttles_itself`: build the same aged dispatch as the previous test inside this test;
  the first sweep returns `1` and an immediate second sweep returns `0`.
- `test_sweep_takes_at_most_limit_rows`: enqueue A, then B1 with `run_after = datetime.now(UTC) - timedelta(minutes=2)`
  and B2 with `run_after = datetime.now(UTC) - timedelta(minutes=1)`, both depending on A; set A
  `succeeded` without an ack; `sweep_lost(redispatch_after=timedelta(minutes=15), limit=1) == 1`, B1 is
  at generation 1 and B2 still at 0.
- `test_park_dead_letter_parks_only_a_claimable_row`: enqueue A (generation 1).
  `park_dead_letter(JobDispatch(a, p, 2, "build.implement", run_after), delivery_limit=20)` is `False`
  (stale generation); after a claim by `"w1"` at generation 1 it is `False` (live lease); after the lease
  expires (`UPDATE job SET lease_expires_at = now() - interval '1 second' WHERE id = $1`) it is `True`:
  A is `awaiting_human`, lease cleared, `attempts == 0`, with one open `delivery_exhausted` gate whose
  prompt is `"job 'build.implement' was delivered 20 times and every consumer holding it died. Answer anything to retry it with a fresh delivery budget."`;
  a second call is `False`.
- `test_park_dead_letter_notifies_the_raised_gate` (PostgreSQL only): `conn = await migrated_pool.acquire()`,
  `await conn.add_listener("vibey_gate_raised", lambda _c, _pid, _ch, payload: received.put_nowait(payload))`
  with `received: asyncio.Queue[str]`; park an expired lease; `await asyncio.wait_for(received.get(), 5)`
  equals the new gate's id as text; remove the listener and release the connection in `finally`
  (tests may use asyncpg; production code may not).

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
# No-service tests: compiled statements, the records through FakeOrm, and the in-memory fake. (Until lane
# fakes-harness-decouple lands the root tests/conftest.py:146-151 still opens PostgreSQL at session start;
# these tests themselves touch none.)
uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_dispatch_statements.py tests/fakes/test_fake_dispatch_records.py tests/fakes/test_port_parity.py
# PostgreSQL tests (integration tier)
uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/db/test_dispatch_records.py tests/infrastructure/db/test_job_repository.py tests/infrastructure/db/test_human_gate_repository.py
uv run pytest -q -p no:cacheprovider -s tests/infrastructure/db/test_chaos.py
# The whole suite with coverage, then the infrastructure floor
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
# No raw SQL added, no protected test touched
! git diff HEAD -- src/ | grep -nE '^\+.*(import asyncpg|[^A-Za-z_]text\(|literal_column|exec_driver_sql)'
test -z "$(git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live)"
git diff --stat
```

## Out of scope
- The fenced claim and snapshot (child 1); nack, defer and reap (child 2, `split-358-2-redispatching-settles`).
- Draining the dead queue and calling these methods on a schedule (#363's reconcile), reading
  `[queue.rabbitmq]` (#348, #364), publishing (#360), consuming (#361), the gate answer's redispatch (#362).
- `PostgresJobRepository`, `JobStatements`, `tests/fakes/registry.py`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push or change remotes. Commit locally with the Title as the subject.

## Conventions this lane relies on (everything needed is here)
The dependency lanes create these; read each file before editing it. If a name below differs from what
the file says, stop and report the difference instead of renaming anything.
- **Tables and constants** (`dispatch_statements.py`): `JOBS = TABLES.table("job")`,
  `DEPENDENCIES = TABLES.table("job_dependency")`,
  `DISPATCH_COLUMNS = (JOBS.c["id"], JOBS.c["project_id"], JOBS.c["dispatch_seq"], JOBS.c["kind"], JOBS.c["run_after"])`,
  `DISPATCH_SQL: Final[DispatchStatementsInterface] = DispatchStatements()`; `TABLES.table(name)`
  (`src/vibey/infrastructure/db/tables.py`) returns the SQLModel table. `human_gate` has
  `gate_id uuid PRIMARY KEY DEFAULT gen_random_uuid()`, `project_id`, `job_id`, `kind text`,
  `prompt text`, `options jsonb NOT NULL DEFAULT '[]'` (`migrations/0008_human_gate_artifact_budget.sql:1-14`).
  The `job` table has `dispatch_seq bigint NOT NULL DEFAULT 0` and `dispatched_at timestamptz`.
- **Child 1's statements:** `DISPATCH_SQL.mark_dispatched(job_id, dispatch_seq)` is
  `update(JOBS).where(id ==, dispatch_seq ==).values(dispatched_at=func.now())`; records
  `claim_dispatched(dispatch, *, owner, lease)` and `mark_dispatched(job_id, dispatch_seq) -> bool`; the
  fake keeps `dispatched_at: dict[UUID, datetime | None]`.
- **The queue statements** (`job_statements.py`, `JOB_SQL: Final[JobStatementsInterface]`):
  `JOB_SQL.deps_unmet(job: FromClause) -> ColumnElement[bool]` (the unmet-dependency `EXISTS` over an
  alias `p` of `job`); `JOB_SQL.notify_gate_raised(gate_id: UUID)` is
  `select(func.pg_notify("vibey_gate_raised", str(gate_id)))` (#356), delivered at commit.
- **The seam** (`interfaces/orm_interface.py`): `self._orm.transaction()` yields an `AsyncConnection`
  (commit on a clean exit, rollback on raise); `conn.execute(stmt)` returns a result with
  `.mappings().first()/.all()`, `.rowcount` and `.scalar_one()`; `conn.scalar(stmt)` returns the first
  column of the first row.
- **#357's records** (`dispatch_records.py`): `DispatchOutboxWriter.write(conn, dispatch, *, key_suffix="") -> bool`
  inserts one `job_outbox` row keyed `f"dispatch:{dispatch.job_id}:{dispatch.dispatch_seq}{key_suffix}"`
  (payload `JOB_DISPATCH_CODEC.encode(dispatch)`) inside the caller's transaction and returns whether a
  row was inserted. `DispatchingJobRecords(PostgresJobRepository)` takes `orm`, keyword `writer` and
  keyword `rows`; `PostgresJobRepository` keeps `self._orm` and `self._rows`.
  `DispatchingJobRecordsInterface(JobRepository, Protocol)` is in `interfaces/dispatch_records_interface.py`.
- **The seam double** (`tests/infrastructure/orm/fakes.py`): `FakeResult(rows=(), *, rowcount=None, scalar=None)`
  (`mappings()` returns itself; `first()`, `all()`, `scalar()`; `rowcount` defaults to `len(rows)`);
  `FakeOrm(*results)` builds one `FakeConnection` (`orm.connection`) whose `execute` records each
  statement in `statements` and pops the next scripted result, and whose `scalar(stmt)` is
  `(await self.execute(stmt)).scalar()`; `transaction()`/`connect()`/`autocommit()` yield it.
- **The fakes** (`tests/fakes/queue.py`): `InMemoryQueueStore` (`jobs`, `dependencies`, `gates:
  dict[UUID, HumanGateRecord]`, `notified`, `clock` with `now()`); `FakeHumanGateRepository(*, store=None)`
  with a `raised` list property; `FakeDispatchOutboxWriter` keeps `written: list[tuple[str, JobDispatch]]`
  and returns `False` for a key it has seen; `FakeDispatchingJobRecords(FakeJobRepository)` takes keyword
  `writer` and keeps `dispatch_seq: dict[UUID, int]` (absent means 0). `JobRecord` and
  `HumanGateRecord` (`src/vibey/application/dto.py`) are frozen dataclasses; `HumanGateRecord` has
  `gate_id, project_id, job_id, kind, prompt, options, default_answer, answer, raised_at, timeout_at, answered_at, answered_by`.
- **The envelope** (`src/vibey/domain/job_dispatch.py`): `JobDispatch(job_id, project_id, dispatch_seq, kind, not_before)`,
  frozen, `dispatch_seq >= 1`, `not_before` timezone-aware; `JOB_DISPATCH_CODEC.decode(mapping)`.
- **The configuration the caller passes** (`[queue.rabbitmq]`, #348): `sweep_batch` (default 500,
  1–100000), `redispatch_after_seconds` (default 900, ≥ 60), `delivery_limit` (default 20, 1–1000).
- **Test fixtures:** `migrated_pool` is both the ORM seam and an asyncpg pool (`execute`, `fetchval`,
  `fetchrow`, `acquire`/`release` pass through); `project_id` inserts a project and returns its id. An
  enqueued job with no unmet dependency starts at generation 1 with one pending outbox row; one with an
  unmet dependency stays at generation 0.

## Standing constraints
### Lane card
- **Files touched:** the five under *Where to change*, plus the three test files (append only).
- **Parallel-safe with:** #359, #362 and the loop-service lanes. It follows child 1 on the same files;
  never run it at the same time as child 2.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_job_repository.py`,
  `tests/infrastructure/db/test_human_gate_repository.py`, `tests/infrastructure/db/test_chaos.py`
  (protected), #357's and child 1's tests, `tests/fakes/test_port_parity.py`, all protected tests.

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
  `mock.patch`, `MagicMock` or `AsyncMock`. Every new port method has matching behaviour in its
  in-memory fake.
- **Persistence goes through `PostgresOrmInterface`** with SQLAlchemy 2 async Core: no new
  `import asyncpg`, `text()`, `literal_column`, `exec_driver_sql()` or SQL strings in `src/`.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.
- Arch Linux and macOS both: the checks need only `uv`, `git` and a local PostgreSQL.

**Depends on:** rmq-r10-dispatch-records-enqueue, rmq-r09-reap-bound, split-358-1-fenced-claim
- rmq-r10-dispatch-records-enqueue: `DispatchStatements`, `DISPATCH_COLUMNS`, `DispatchingJobRecords`, `DispatchOutboxWriter`, the fakes and the three test files.
- rmq-r09-reap-bound: `JOB_SQL.notify_gate_raised` and the `delivery_exhausted` gate kind the park shares.
- split-358-1-fenced-claim: `DISPATCH_SQL.mark_dispatched` (the sweep's stamp at generation ≥ 1), `claim_dispatched` (used by the park test), and the fake's `dispatched_at` dict.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
