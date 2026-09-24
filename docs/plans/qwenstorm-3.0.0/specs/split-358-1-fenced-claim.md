<!-- split of #358: child 1 of 3; audit: issue-audit/updates/358.md -->
## Title
feat(db): the fenced dispatch claim, the dispatch snapshot and the dispatched stamp

## Why
ADR-0044 §4–§5 (`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:199-221`, `:232-243`): in the RabbitMQ backend a
worker takes a delivery, then claims its row with a fenced compare-and-set **by job id and generation**
that also takes over an expired lease, replacing for that backend the `SKIP LOCKED` scan (today
`src/vibey/infrastructure/db/job_repository.py:178-208`; as Core, `JobStatements.claim`, lane
`orm-job-statements-settle`). When the claim misses, the worker reads a snapshot and asks
`DispatchMissPolicy` (#354, R07) what the miss means; after the relay publishes a dispatch it stamps
`dispatched_at` only for the generation it published, so a stale relay can never mark a newer episode.
The fences stay exactly the PostgreSQL backend's: `ack`, `park`, `heartbeat`, `grant_attempts` and
`assign_engine` are inherited unchanged. Persistence goes through `PostgresOrmInterface` with SQLAlchemy 2
async Core, reusing `JOB_SQL.deps_unmet`, and every new port method gets matching behaviour in its
in-memory fake (the operator's ORM and fakes standards; sub-doctrine 9.b,
`src/vibey_tools/gh/docs/doctrines.md:349`). Verified at integration `4317cff6` (the `job_repository.py`
lines are today's; the ORM lanes move them); `dispatch_statements.py`, `dispatch_records.py`, their
interfaces, `tests/fakes/queue.py` and the three test files below do not exist there yet — the
dependency lanes create them.

## Required behaviour
1. **Statements** added to `class DispatchStatements` (`src/vibey/infrastructure/db/dispatch_statements.py`)
   and declared on `DispatchStatementsInterface`; typed literals only:
   - `claim_dispatched(self, dispatch: JobDispatch, *, owner: str, lease: timedelta)`:
     ```python
     update(JOBS)
     .where(
         JOBS.c["id"] == dispatch.job_id,
         JOBS.c["project_id"] == dispatch.project_id,
         JOBS.c["dispatch_seq"] == dispatch.dispatch_seq,
         or_(JOBS.c["state"] == "ready",
             and_(JOBS.c["state"] == "leased", JOBS.c["lease_expires_at"] < func.now())),
         JOBS.c["run_after"] <= func.now(),
         ~JOB_SQL.deps_unmet(JOBS),
     )
     .values(state="leased", lease_owner=owner,
             lease_expires_at=func.now() + literal(lease, Interval()),
             attempts=JOBS.c["attempts"] + 1, updated_at=func.now())
     .returning(*JOBS.c)
     ```
   - `snapshot(self, job_id: UUID)`:
     `select(JOBS.c["state"], JOBS.c["dispatch_seq"], JOBS.c["run_after"], JOBS.c["lease_expires_at"], (~JOB_SQL.deps_unmet(JOBS)).label("deps_met")).where(JOBS.c["id"] == job_id)`.
   - `mark_dispatched(self, job_id: UUID, dispatch_seq: int)`:
     `update(JOBS).where(JOBS.c["id"] == job_id, JOBS.c["dispatch_seq"] == dispatch_seq).values(dispatched_at=func.now())`.
   Interface return types (under `TYPE_CHECKING`, as `interfaces/job_statements_interface.py` does):
   `ReturningUpdate[Any]` (`sqlalchemy.sql.dml`), `Select[Any]` and `Update` (`sqlalchemy`).
2. **Records** added to `class DispatchingJobRecords` (`src/vibey/infrastructure/db/dispatch_records.py`)
   and declared on `DispatchingJobRecordsInterface`:
   - `async def claim_dispatched(self, dispatch: JobDispatch, *, owner: str, lease: timedelta) -> JobRecord | None`:
     in `async with self._orm.transaction() as conn:`,
     `row = (await conn.execute(DISPATCH_SQL.claim_dispatched(dispatch, owner=owner, lease=lease))).mappings().first()`;
     return `self._rows.to_record(row)` (the mapper `PostgresJobRepository` uses), or `None` when `row is None`.
   - `async def snapshot(self, job_id: UUID) -> DispatchSnapshot | None`: in
     `async with self._orm.connect() as conn:`, `row = (await conn.execute(DISPATCH_SQL.snapshot(job_id))).mappings().first()`;
     `None` for an unknown job, else
     `DispatchSnapshot(state=str(row["state"]), dispatch_seq=int(row["dispatch_seq"]), run_after=row["run_after"], lease_expires_at=row["lease_expires_at"], deps_met=bool(row["deps_met"]))`.
   - `async def mark_dispatched(self, job_id: UUID, dispatch_seq: int) -> bool`: in
     `self._orm.transaction()`, `return (await conn.execute(DISPATCH_SQL.mark_dispatched(job_id, dispatch_seq))).rowcount == 1`.
3. The exactly-once commit fence is unchanged: `ack` (through #357's `ack_and_release`), `park`,
   `heartbeat`, `grant_attempts` and `assign_engine` are inherited as they are. Nothing else in either
   class changes.
4. **The fake.** `FakeDispatchingJobRecords` (`tests/fakes/queue.py`) gains the three methods with the
   same signatures (`tests/fakes/test_port_parity.py` compares them), using `store.clock.now()` wherever
   the SQL says `now()`, and a new `self.dispatched_at: dict[UUID, datetime | None]` (an absent key means
   `None`), created in `__init__`. `store` below is the shared `InMemoryQueueStore` the fake already
   holds; `seq(id)` is `self.dispatch_seq.get(id, 0)`; "deps met" means every id in
   `store.dependencies.get(id, ())` names a job whose `state is JobState.SUCCEEDED`.
   - `claim_dispatched(dispatch, *, owner, lease)`: with `now = store.clock.now()` and
     `job = store.jobs.get(dispatch.job_id)`, return `None` when `job is None`,
     `job.project_id != dispatch.project_id`, `seq(job.id) != dispatch.dispatch_seq`, the job is neither
     `READY` nor (`LEASED` with `lease_expires_at is not None and lease_expires_at < now`),
     `job.run_after > now`, or its deps are not met. Otherwise store and return
     `dataclasses.replace(job, state=JobState.LEASED, lease_owner=owner, lease_expires_at=now + lease, attempts=job.attempts + 1, updated_at=now)`.
   - `snapshot(job_id)`: `None` for an unknown job, else
     `DispatchSnapshot(state=job.state.value, dispatch_seq=seq(job_id), run_after=job.run_after, lease_expires_at=job.lease_expires_at, deps_met=<deps met>)`.
   - `mark_dispatched(job_id, dispatch_seq)`: `False` for an unknown job or `seq(job_id) != dispatch_seq`;
     otherwise `self.dispatched_at[job_id] = store.clock.now()` and `True`.
   No new registry entry: `FakeDispatchingJobRecords` is already registered in `tests/fakes/registry.py`.

## Where to change
- `src/vibey/infrastructure/db/dispatch_statements.py` and
  `src/vibey/infrastructure/db/interfaces/dispatch_statements_interface.py`
- `src/vibey/infrastructure/db/dispatch_records.py` and
  `src/vibey/infrastructure/db/interfaces/dispatch_records_interface.py`
- `tests/fakes/queue.py` (`FakeDispatchingJobRecords` only)
- Append to `tests/infrastructure/orm/test_dispatch_statements.py`,
  `tests/fakes/test_fake_dispatch_records.py` and `tests/infrastructure/db/test_dispatch_records.py`.
- Why more than one source file: the ORM standard puts every statement on the stateless statements
  class and executes it from the records class, each with an interface beside it (ADR-0016); the
  in-memory fake must change with the port (9.b); and the proof runs at three tiers (compiled, fake,
  PostgreSQL). Nothing else changes.
- Copy the claim's Core shape and its lease literal from `JobStatements.claim` in
  `src/vibey/infrastructure/db/job_statements.py`, and the method style of the existing
  `DispatchStatements.release_enqueued` and `DispatchingJobRecords.ack_and_release`.

## Acceptance criteria
- [ ] The claim hits for a ready row at a matching generation, takes over an expired lease, and misses
      on a stale generation, a future `run_after`, an unexpired lease, an unmet dependency and a wrong
      project — on PostgreSQL (`test_claim_dispatched_*` in `tests/infrastructure/db/test_dispatch_records.py`)
      and on the fake (the same names in `tests/fakes/test_fake_dispatch_records.py`).
- [ ] `snapshot` feeds `DispatchMissPolicy.decide` to the expected verdict in each miss case
      (`test_snapshot_feeds_the_miss_policy`).
- [ ] `mark_dispatched` ignores a stale generation (`test_mark_dispatched_ignores_a_stale_generation`).
- [ ] After a takeover of an expired lease, the old owner's `ack` is refused
      (`test_stale_owner_ack_after_a_takeover_is_refused`).
- [ ] `tests/fakes/test_port_parity.py` passes; 100% branch coverage of `src/vibey/infrastructure/`.
- [ ] `git diff HEAD -- src/` adds no `import asyncpg`, `text(`, `literal_column` or `exec_driver_sql`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_dispatch_statements.py` (append; no service; compile each statement with
`sqlalchemy.dialects.postgresql.asyncpg.dialect()` and assert on `str(compiled)` and
`compiled.params.values()`; build the dispatch as
`JobDispatch(job_id=uuid4(), project_id=uuid4(), dispatch_seq=3, kind="build.implement", not_before=datetime(2026, 9, 22, tzinfo=UTC))`):
- `test_the_dispatched_claim_is_fenced_by_job_generation_and_project`: the text has `job.id =`,
  `job.project_id =`, `job.dispatch_seq =`, `job.run_after <= now()`, `NOT (EXISTS (` and `RETURNING`;
  the params hold the job id, the project id, `3`, the owner and the lease `timedelta`.
- `test_the_dispatched_claim_takes_over_only_an_expired_lease`: the text has `job.lease_expires_at < now()`
  and ` OR `; the params hold `"ready"` and `"leased"`.
- `test_the_snapshot_computes_deps_met`: the text has `AS deps_met`, `NOT (EXISTS (` and `job.id =`.
- `test_mark_dispatched_names_the_generation`: the text starts `UPDATE job SET dispatched_at=now()` and
  has `job.dispatch_seq =`; the params hold the id and the sequence.

`tests/fakes/test_fake_dispatch_records.py` (append; no service): the same seven names as the
PostgreSQL list below, same scenarios, driving `FakeDispatchingJobRecords` over an `InMemoryQueueStore`
with a frozen clock (reuse the clock class already in the file; otherwise add
`class _FrozenClock` with `__init__(self, now: datetime)`, `now()` and `advance(delta)`). Expire a lease
by advancing the clock past it; force a generation with `records.dispatch_seq[job_id] = n`; make a
dependency succeed with `store.jobs[a] = dataclasses.replace(store.jobs[a], state=JobState.SUCCEEDED)`.

`tests/infrastructure/db/test_dispatch_records.py` (append; integration by its directory's conftest;
`records = DispatchingJobRecords(migrated_pool, writer=DispatchOutboxWriter())`; enqueue with
`EnqueueRequest(project_id=project_id, cycle=1, phase=Phase.BUILD, kind="build.implement", idempotency_key=f"key-{subject}")`
or the `_request` helper if the file has one; tests may change or read rows through the fixture's
asyncpg pass-throughs, for example
`await migrated_pool.execute("UPDATE job SET lease_expires_at = now() - interval '1 second' WHERE id = $1", job_id)`):
- `test_claim_dispatched_hits_and_leases`: an enqueued job (generation 1) claimed with
  `JobDispatch(job.id, project_id, 1, "build.implement", job.run_after)` as `"w1"` comes back `LEASED`,
  owned by `"w1"`, with `attempts == 1`.
- `test_claim_dispatched_takes_over_an_expired_lease`: claimed by `"w1"`, lease expired, claimed again at
  generation 1 by `"w2"`: a hit with `attempts == 2` and owner `"w2"`.
- `test_claim_dispatched_misses_each_way` (parametrized over five causes): a stale generation (claim at
  2 while the row is at 1); a future `run_after` (enqueue with `run_after = now + 1 h`); an unexpired
  lease (a second claim by `"w2"` while `"w1"` holds it); an unmet dependency (B depends on a ready A;
  force B to generation 1 with `UPDATE job SET dispatch_seq = 1`); a wrong project (`project_id=uuid4()`).
  Each returns `None` and leaves the row unchanged.
- `test_snapshot_reports_deps_and_lease`: for B blocked by A the snapshot is `state == "ready"`,
  `dispatch_seq == 0`, `deps_met is False`, `lease_expires_at is None`; for A after a claim it is
  `"leased"`, generation 1, `deps_met is True`, a lease set; an unknown id gives `None`.
- `test_snapshot_feeds_the_miss_policy`: `DispatchMissPolicy().decide(snapshot, message_seq, now)` with
  `now = datetime.now(UTC)` after the snapshot gives: stale generation → `DROP`, reason
  `"stale generation"`; future `run_after` → `REDELAY`, `not_before == run_after`, reason `"not due"`;
  unexpired lease → `REDELAY`, `not_before == max(lease_expires_at, run_after)`, reason
  `"held by a live lease"`; unmet dependency → `DROP`, reason `"blocked; its release will dispatch it"`;
  an unknown job (`snapshot` returns `None`) → `DROP`, reason `"unknown job"`. (A wrong project is not
  in this table: the snapshot is keyed by job id alone.)
- `test_mark_dispatched_ignores_a_stale_generation`: `mark_dispatched(job.id, 2)` is `False` and leaves
  `dispatched_at` NULL; `mark_dispatched(job.id, 1)` is `True` and sets it.
- `test_stale_owner_ack_after_a_takeover_is_refused`: after the takeover by `"w2"`,
  `ack(job.id, owner="w1")` is `False` and the row is still leased by `"w2"`; `ack(job.id, owner="w2")` is `True`.

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
uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_dispatch_statements.py tests/fakes/test_fake_dispatch_records.py tests/fakes/test_port_parity.py
# PostgreSQL tests (integration tier)
uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/db/test_dispatch_records.py tests/infrastructure/db/test_job_repository.py
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
- nack, defer and reap redispatch (child 2, `split-358-2-redispatching-settles`); the sweep and the
  dead-letter park (child 3, `split-358-3-sweep-and-park`).
- Publishing (#360), consuming (#361), the repository that composes these pieces (#363).
- `PostgresJobRepository`, `JobStatements`, `tests/fakes/registry.py`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push or change remotes. Commit locally with the Title as the subject.

## Conventions this lane relies on (everything needed is here)
The dependency lanes create these; read each file before editing it. If a name below differs from what
the file says, stop and report the difference instead of renaming anything.
- **Tables** (`src/vibey/infrastructure/db/tables.py`): `TABLES.table(name) -> Table`; columns are
  read as `t.c["name"]`. `dispatch_statements.py` already defines `JOBS = TABLES.table("job")`,
  `DEPENDENCIES = TABLES.table("job_dependency")`,
  `DISPATCH_COLUMNS = (JOBS.c["id"], JOBS.c["project_id"], JOBS.c["dispatch_seq"], JOBS.c["kind"], JOBS.c["run_after"])`
  and `DISPATCH_SQL: Final[DispatchStatementsInterface] = DispatchStatements()`. The `job` table has
  `dispatch_seq bigint NOT NULL DEFAULT 0` and `dispatched_at timestamptz` (migration 0014, #355).
- **The queue statements** (`src/vibey/infrastructure/db/job_statements.py`):
  `JOB_SQL: Final[JobStatementsInterface]`; `JOB_SQL.deps_unmet(job: FromClause) -> ColumnElement[bool]`
  is `exists().where(DEPENDENCIES.c["job_id"] == job.c["id"], DEPENDENCIES.c["depends_on_job_id"] == parent.c["id"], parent.c["state"] != "succeeded")`
  over `parent = JOBS.alias("p")`; `JOB_SQL.claim(project_id, *, owner, lease)` is the `SKIP LOCKED`
  claim whose `values(...)` you copy.
- **The seam** (`src/vibey/infrastructure/db/interfaces/orm_interface.py`): `PostgresOrmInterface` hands
  out `transaction()` (commit on a clean exit, rollback on raise), `connect()` (no transaction open) and
  `autocommit()`, each an async context manager yielding an `AsyncConnection`.
- **The repository** (`job_repository.py`): `PostgresJobRepository.__init__(self, orm, *, rows=JOB_ROWS)`
  keeps `self._orm` and `self._rows`; `JOB_ROWS.to_record(row: Mapping[str, Any]) -> JobRecord`.
- **#357's records** (`dispatch_records.py`): `DispatchOutboxWriter.write(conn, dispatch, *, key_suffix="") -> bool`
  writes one `job_outbox` row keyed `f"dispatch:{dispatch.job_id}:{dispatch.dispatch_seq}{key_suffix}"`;
  `DispatchingJobRecords(PostgresJobRepository)` takes `orm`, keyword `writer` and keyword `rows`, has
  `ack_and_release(job_id, *, owner) -> tuple[bool, tuple[JobDispatch, ...]]`, and its `ack` returns
  `ack_and_release(...)[0]`. `DispatchingJobRecordsInterface(JobRepository, Protocol)` and
  `DispatchOutboxWriterInterface` are in `interfaces/dispatch_records_interface.py`;
  `DispatchStatementsInterface` in `interfaces/dispatch_statements_interface.py` (driver types under
  `TYPE_CHECKING` only).
- **The fakes** (`tests/fakes/queue.py`): `InMemoryQueueStore` holds `jobs: dict[UUID, JobRecord]`,
  `dependencies: dict[UUID, tuple[UUID, ...]]`, `gates: dict[UUID, HumanGateRecord]`, `notified` and a
  `clock` with `now()`; `FakeJobRepository(jobs=None, *, store=None)`; `FakeDispatchOutboxWriter` keeps
  `written: list[tuple[str, JobDispatch]]` and returns `False` for a key it has seen;
  `FakeDispatchingJobRecords(FakeJobRepository)` takes keyword `writer` and keeps
  `dispatch_seq: dict[UUID, int]` (absent means 0). `JobRecord` is a frozen dataclass: update it with
  `dataclasses.replace`.
- **The dispatch envelope** (`src/vibey/domain/job_dispatch.py`, R06): `@dataclass(frozen=True, slots=True) class JobDispatch`
  with `job_id: UUID`, `project_id: UUID`, `dispatch_seq: int` (≥ 1), `kind: str` (non-empty) and
  `not_before: datetime` (timezone-aware); a violation raises `ValueError`.
- **The miss policy** (`src/vibey/domain/dispatch_policy.py`, R07): `DispatchSnapshot(state: str, dispatch_seq: int, run_after: datetime, lease_expires_at: datetime | None, deps_met: bool)`;
  `DispatchVerdict.DROP` / `DispatchVerdict.REDELAY`; `DispatchDecision(verdict, not_before, reason)`;
  `DispatchMissPolicy().decide(snapshot, message_seq, now)` applies the first matching rule: no snapshot
  → DROP `"unknown job"`; other generation → DROP `"stale generation"`; state not `ready`/`leased` →
  DROP `"not claimable: <state>"`; `leased` with `lease_expires_at >= now` → REDELAY at
  `max(lease_expires_at, run_after)`, `"held by a live lease"`; `ready` without `deps_met` → DROP
  `"blocked; its release will dispatch it"`; `run_after > now` → REDELAY at `run_after`, `"not due"`;
  otherwise REDELAY at `now`, `"claim raced; retry now"`.
- **Test fixtures:** `migrated_pool` (`tests/infrastructure/db/conftest.py`) is both the ORM seam and an
  asyncpg pool (`execute`, `fetchval`, `fetchrow`, `acquire` pass through); `project_id` inserts a
  project and returns its id.

## Standing constraints
### Lane card
- **Files touched:** the five under *Where to change*, plus the three test files (append only).
- **Parallel-safe with:** #359, #362 and the loop-service lanes. Children 2 and 3 follow this lane on the
  same files; never run two of them at once.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_job_repository.py`,
  `tests/infrastructure/db/test_chaos.py` (protected), #357's tests, `tests/fakes/test_port_parity.py`,
  all protected tests.

### For every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  They must keep passing.
- **The first line of every new source file** is the provenance comment, copied byte-for-byte from line 1
  of a sibling file.
- **The default run needs no outside service.** Until lane `fakes-harness-decouple` lands, the root
  `tests/conftest.py` still opens PostgreSQL at session start (`:146-151`), so "no service" means the
  test itself touches none. PostgreSQL-backed tests are `integration` (every test under
  `tests/infrastructure/db/` is, by its conftest) and are never the lane's only proof.
- **Substitution at a declared seam only:** never `monkeypatch.setattr` on a module attribute,
  `mock.patch`, `MagicMock` or `AsyncMock`. Every new port method has matching behaviour in its
  in-memory fake.
- **Persistence goes through `PostgresOrmInterface`** with SQLAlchemy 2 async Core: no new
  `import asyncpg`, `text()`, `literal_column`, `exec_driver_sql()` or SQL strings in `src/`.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.
- Arch Linux and macOS both: the checks need only `uv`, `git` and a local PostgreSQL.

**Depends on:** rmq-r10-dispatch-records-enqueue, rmq-r07-dispatch-miss-policy
- rmq-r10-dispatch-records-enqueue: `DispatchStatements`, `DispatchingJobRecords`, their interfaces, `DispatchOutboxWriter`, the two fakes, the three test files (and through it the ORM job lanes, `JOB_SQL.deps_unmet` and the `job_outbox`/`dispatch_seq` migration).
- rmq-r07-dispatch-miss-policy: `DispatchSnapshot` (what `snapshot` returns) and `DispatchMissPolicy` (what the snapshot test feeds).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
