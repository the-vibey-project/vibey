# NNNN — Every persistence access goes through the ORM, behind a declared interface

**Status:** proposed · **Date:** 2026-09-22 · **Applies:** ADR-0016 (sub-doctrine 9.b, the declared seam), ADR-0017 (sub-doctrine 10.e, the family first) · **Restates:** ADR-0002 (PostgreSQL, never SQLite) · **Related:** ADR-0005, ADR-0009, ADR-0018, ADR-0020, ADR-0023, ADR-0024, ADR-0029, ADR-0044 · **Evidence:** the storm integration checkout (`storm/integration` at `c91561f4`), read 2026-09-22; every `file:line` below is at that commit. Statement shapes were checked by compiling them with SQLAlchemy 2.0.53 and sqlmodel 0.0.42 (the versions `uv.lock` pins) on 2026-09-22; none has yet run against PostgreSQL through the new code — the lanes' integration tests are what establish that.

**Owes:** nothing new as conduct — this record is mechanism (ADR-0020). It is how the code
meets the operator's standard, "the system always needs to use ORM as well as interfaces
always", under two ratified sub-doctrines: 9.b (code lives in classes with a declared seam;
substitution happens at the seam, never by patching an import) and 10.e (a capability the
family ships is used, and a gap in it is closed by teaching the family). Whether
"persistence goes through the ORM" should itself become a sub-doctrine is the operator's
call under Article II.3; this record neither assumes nor drafts that. It owes the docs
wave: `docs/plans/data-model.md` §3–§7 (how statements are written), the
`orm_models.py` and `orm.py` module docstrings where a lane has not already rewritten them,
the CLAUDE.md "Queue backend" and layer facts, the four agent-surface trees, and the
advertised ADR count (`tests/meta/test_adr_counts.py`).

## Context

### Two ways to PostgreSQL, and only one of them used

vibey reaches PostgreSQL through raw asyncpg. `build_app` opens one pool
(`src/vibey/bootstrap.py:700`) and hands it to nine adapters, each of which writes `$n`
SQL strings: the job queue (`infrastructure/db/job_repository.py`, 18 calls), the ledger
(`ledger_repository.py`, 5), project lifecycle (`project_repository.py`, 5), rotation
cursors (6), engine health (3), handoffs (3), human gates (8, two of them `NOTIFY`
f-strings), the integration advisory lock (2), the ledger search (1, through a hand-rolled
`$n` compiler, `ledger_search_repository.py:59-115`). Around them: the migrator
(`migrator.py`, 8), `vibey doctor --cluster` (`cluster_preflight.py:244-286`, 2, by opening
its own asyncpg connection), `vibey recover` (`cli/main.py:661-706`, an `UPDATE job` string
and a regex over asyncpg's command tag), and `build_app`'s version probe (`bootstrap.py:705`).
A heuristic count of SQL-text sites (the one `orm-raw-sql-guard` pins) finds 67 across 13
modules.

An ORM layer already exists beside them and nothing in production uses it:
`infrastructure/db/orm.py` (`PostgresOrm`, sessions only), `orm_models.py` (SQLModel
models for every migrated relation, pinned column-for-column to the live schema by
`tests/infrastructure/db/test_orm.py`), and `interfaces/orm_interface.py`. Its docstrings
say the queue and the ledger "keep driver-level SQL where their locking and transaction
contracts are explicit" (`orm.py:4-8`, `orm_models.py:10-13`).

### Where the seams are missing

Four adapters have no declared contract beside them: `PostgresAdvisoryLock`,
`PostgresHandoffRepository`, `PostgresHumanGateRepository`, `PostgresJobReadyNotifier`
(`src/vibey/infrastructure/interfaces/class_contracts.py` declares the others). Several
row mappers are bare module functions (`_row_to_job_record`, `_row_to_record`,
`_row_to_dict`), and every mapper interface is declared over `asyncpg.Record`. Tests reach
the database checks by patching `asyncpg.connect` (`tests/infrastructure/test_cluster_preflight.py:287`,
`:309`, `:333`) and `asyncpg.create_pool` (`tests/test_bootstrap.py:107`,
`tests/infrastructure/test_sovereign_surfaces.py:636`, `:703`) — substitution by import, which
9.b forbids. `.importlinter` keeps asyncpg out of `vibey.domain` but says nothing about
`sqlalchemy` or `sqlmodel`, or about `vibey.application`.

### The family

`vibey_bootstrap.db` (`src/vibey_tools/bootstrap/vibey_bootstrap/db/`) is the family's
relational layer: a sync SQLAlchemy engine singleton, a transactional outbox written as
f-string `text()` over a sync session, and an Alembic harness. It has no async engine and
no interfaces. vibey's `orm.py` built its own async engine and its own URL rewrite beside
it.

### What cannot change

The queue's claim is `FOR UPDATE SKIP LOCKED`, strict priority then `run_after` then id,
never a job with an unsucceeded dependency; every settle is fenced on `lease_owner`
(pinned by the protected `tests/infrastructure/db/test_chaos.py` and by
`test_job_repository.py`). The ledger's `seq` is claimed by `append_event()` inside the
insert's transaction (`migrations/0013_ledger_partitioning.sql:88-116`), its payload is
redacted and digested before storage, and UPDATE/DELETE are rules that do nothing
(`:65-66`). "Credits never have a deadline" is a CHECK (`migrations/0007:20-22`), the third
of its three layers. `NOTIFY` in a transaction is delivered at commit. Migrations are
forward-only, checksummed, applied under an advisory lock (`migrator.py:1-18`). Every job is
idempotent under replay.

## Decision

### 1. One seam: `PostgresOrmInterface`

Every read and write in `src/vibey` goes through `PostgresOrmInterface`
(`infrastructure/db/interfaces/orm_interface.py`), implemented by `PostgresOrm`. The seam
hands out, and only hands out:

| way in | what it is | used for |
|---|---|---|
| `transaction()` | the `AsyncConnection` of `engine.begin()` — commit on a clean exit, rollback on raise | every write; the queue's and the ledger's atomic units |
| `connect()` | an `AsyncConnection` with no transaction open | reads; the migrator, which opens its own transactions |
| `autocommit()` | an `AsyncConnection` at `AUTOCOMMIT` | session-level advisory locks; outbox relays — anything a bare connection did |
| `session()` | an `AsyncSession` | low-traffic ORM unit-of-work code |

Repositories take the seam in their constructor; nothing else in `src/vibey` holds a
connection pool or opens a connection. `build_app` builds one `PostgresOrm` and passes it
everywhere; tests substitute it (below). The seam refuses any URL that is not
`postgresql+asyncpg://…` after normalization (`UnsupportedDatabaseUrl`, which names ADR-0002
and never repeats a password): **SQLite stays forbidden**, for ADR-0002's reason — no
`SKIP LOCKED` means no crash-safe claim.

### 2. SQLAlchemy 2 async on the asyncpg driver; SQLModel is the one mapping

The driver stays asyncpg; it moves under SQLAlchemy 2's async engine. The SQLModel models
in `orm_models.py` are the single mapping of the schema: statements are built over their
tables (through `OrmTables.table(name)`, because mypy cannot see SQLModel's `__table__`) or
over the models themselves. There is no second hand-written column list anywhere.

### 3. Core for the hot paths, ORM sessions for the rest

The queue, the ledger, the gates and the locks are written as **SQLAlchemy Core**
statements — `select`, `update`, `postgresql.insert(...).on_conflict_do_nothing/_do_update`,
`.with_for_update(skip_locked=True)`, `exists()`, `case()`, `func.pg_notify`,
`func.append_event`, `func.pg_try_advisory_lock` — each built by a stateless statements
class with an interface beside it (`JobStatements`, and `DispatchStatements` for the
RabbitMQ records), so the repository, the RabbitMQ lanes that extend it and the unit tests
share one definition. Core keeps every statement one statement, as today's SQL is, and
compiles to the same shape: the claim renders `UPDATE job … WHERE job.id = (SELECT j.id
FROM job AS j WHERE … AND NOT (EXISTS (…)) ORDER BY j.priority DESC, j.run_after ASC, j.id
ASC LIMIT … FOR UPDATE SKIP LOCKED) RETURNING …`. ORM sessions (`select(Model)`,
`session.add`) are for low-traffic CRUD where an identity map costs nothing.

Rules the lanes found necessary, and which bind every statement:
- **Bind through the column's type.** SQLAlchemy's asyncpg dialect renders an untyped `str`
  as `$n::VARCHAR` and an untyped `int` as `$n::INTEGER`. PostgreSQL will not implicitly
  cast `varchar` to an enum (`phase`, `provenance`, `job_state`, `circuit_state`), and a
  64-bit advisory key does not fit `int4`. Enum and JSONB values are bound through their
  column's type, `append_event`'s twelve arguments through the `event` columns' types, and
  advisory keys as `BigInteger`.
- **Values, not fragments.** No `text()` fragment and no `literal_column`: an interval is
  `literal(timedelta, Interval())`, an enum literal is `literal(value, column.type)`.
- **`pg_notify(channel, payload)` replaces `NOTIFY` f-strings.** Same delivery (at commit,
  folded within a transaction), and both arguments are bound.
- **CHECK violations surface as `sqlalchemy.exc.IntegrityError`**, the driver's error on
  `.orig` (SQLSTATE `23514` for `credits_never_have_a_deadline`). Repositories neither catch
  nor translate them.

### 4. Row mappers read mappings; JSON arrives decoded

Every row mapper is a class with an interface, declared over `Mapping[str, Any]` rather
than `asyncpg.Record`. Through the dialect, `jsonb` arrives decoded (SQLAlchemy installs a
`json.loads` codec), and a JSONB column is written by passing the Python value (serialized
with `json.dumps`, the text today's code sends). `JsonColumn` decodes either shape, so a
mapper shared by a converted and an unconverted reader works during the transition. **The
ledger's digests do not change**: they are computed in Python over the redacted payload
before storage (`ledger_repository.py:103-109`), and `orm-ledger` pins one —
`{"note": "ORM pin", "n": 3, "nested": {"b": [1, 2.5, None], "a": True}}` digests to
`fbf86dc2c85ebc7755319ebe4d308be9148a8a0f9cae0e54f8b5bf540bab3ed4` before and after, and the
read-back payload re-digests to the same value.

### 5. The ledger stays append-only, loudly

The database rules stay the backstop. The seam adds a guard (`AppendOnlyGuard`, installed
by `PostgresOrm` on its engine's `before_execute`) that refuses any Core or ORM `UPDATE`/
`DELETE` of `event` with `AppendOnlyViolation`, so a mistaken statement fails in the test
that wrote it instead of silently doing nothing.

### 6. Migrations stay checksummed SQL files

No `create_all`, no Alembic autogenerate, no model-derived DDL: the `.sql` files in
`migrations/` remain the authority, forward-only, checksummed, applied under the
migration advisory lock. What changes is the code around them: `PostgresMigrator` takes an
`AsyncConnection`; its lock, unlock, lock-holder lookup, applied-set read and bookkeeping
insert are Core; every caller — `build_app` and the test harness alike — migrates by URL
through `apply_url`, which opens one unpooled connection through the family's engine
factory.

### 7. Two driver-level exemptions, written down and pinned

1. **LISTEN** (`PostgresJobReadyNotifier`). A notification arrives asynchronously on one
   session, whenever the server sends it; SQLAlchemy has no API for receiving one. The
   notifier opens its connection through the family's engine factory, takes the driver
   connection with `AsyncConnection.get_raw_connection()`, and calls asyncpg's
   `add_listener`/`remove_listener`. It sends no SQL. It is the one module allowed to import
   asyncpg.
2. **Migration scripts** (`PostgresMigrator._run_script`). A migration file is a
   multi-statement script. SQLAlchemy's asyncpg dialect prepares every statement it
   executes (`_prepare_and_execute`), and PostgreSQL cannot prepare more than one command,
   so a script needs the simple-query protocol, which only the driver connection offers. The
   migrator runs each checksummed file — and the one `CREATE TABLE IF NOT EXISTS
   schema_migration` bootstrap statement — on the driver connection, inside the
   `AsyncConnection`'s own transaction, after the bookkeeping insert has started it, so the
   file and its row commit together. It imports nothing from the driver.

No other exemption exists. `orm-raw-sql-guard` makes both mechanical: an import-linter
contract (`asyncpg-only-in-the-notifier`) forbids asyncpg in every module of `vibey`
except the notifier, and `tests/meta/test_raw_sql_budget.py` counts SQL strings, `text()`,
`exec_driver_sql` and `get_raw_connection` in `src/vibey` against a three-entry budget
(the bootstrap DDL, and the two raw connections) and fails on any difference.

### 8. The family carries the engine

`vibey_bootstrap.db.async_engine.AsyncEngineFactory` (with
`AsyncEngineFactoryInterface`) builds async engines: it normalizes `postgres://` and
`postgresql://` to the asyncpg driver, defaults `pool_pre_ping`, and imports SQLAlchemy
lazily, as the sync builder does. `PostgresOrm.from_dsn`, the notifier, the migrator and
the cluster preflight all build through it; vibey's own URL helper is deleted. No written
reason exists for a parallel engine in vibey, so there is none (10.e). The sync API is
unchanged.

### 9. Import contracts

`sqlalchemy`, `sqlmodel` and `alembic` join `asyncpg` and `psycopg` among the modules
`vibey.domain` may not import, and a new contract (`application-persistence-free`) forbids
all five in `vibey.application` and `vibey.tui`. Persistence is an infrastructure concern;
the application talks to ports.

### 10. Tests substitute at the seam

Repository tests stay in the integration tier (`tests/infrastructure/db`, real
PostgreSQL). The `migrated_pool` fixture becomes a `MigratedDatabase`: a `PostgresOrm`
over the migrated test database that also passes the asyncpg pool API through, so the
protected chaos test (`PostgresJobRepository(migrated_pool)`, `migrated_pool.acquire()`)
runs unedited, and test code may still observe the database through the driver. Unit tests
that need no database use `FakeOrm`, a `PostgresOrmInterface` double with scripted results.
No lane adds a patch of an import; several remove one (`build_app` takes an optional `orm`,
and `DatabaseCheck` takes an engine factory). This is compatible with the in-memory-fakes
effort that is making the default suite run without PostgreSQL: the ORM lanes' database
tests are integration tests either way.

### 11. Relation to ADR-0044

ADR-0044 §4 writes each dispatch to a transactional outbox **in the same transaction** as
the job's state change. Under this record, that transaction is an SQLAlchemy
`AsyncConnection` from `PostgresOrmInterface.transaction()`, and the outbox is the family's
(`vibey_bootstrap.db.outbox.AsyncOutbox`, amended in `rmq-r05-async-outbox` to take an
`AsyncConnection` and to write Core over a `Table` — no longer "any asyncpg-shaped
executor"). The writer joins the caller's transaction and never commits; the relay drains on
an `autocommit()` connection, so a claim commits before anything is published. The
RabbitMQ records (`rmq-r09`, `rmq-r10`, `rmq-r11`, `rmq-r15`) are amended to build their
statements as Core on `JobStatements`/`DispatchStatements`, reusing the one unmet-dependency
clause, and they are ordered after the ORM job and gate lanes; `rmq-r13` and `rmq-r17` take
the seam instead of a pool; `rmq-r16` implements the port's new `recover_leased`. ADR-0044's
semantics — generations, fences, the sweep, dead-letter parks — are unchanged.

## How each non-negotiable still holds

- **Never block a worker on a human.** Gates are still parked jobs plus a `human_gate` row;
  the answer re-readies the job in the answer's transaction (`orm-human-gate`).
- **Credits ≠ rate limit.** The CHECK is untouched; its violation is now an
  `IntegrityError`, pinned with SQLSTATE and constraint name (`orm-engine-health`).
- **`domain/` stays pure.** It may not import the ORM or any driver (`orm-import-contracts`).
- **Dogfood the family.** The async engine and the async outbox are the family's.
- **Everything configurable, never less.** Pool sizing stays today's ceiling (10) as
  defaults on `PostgresOrm.from_dsn`; making it `vibey.toml` keys is owed (12.c) and not
  done here, which leaves nothing less configurable than it was.
- **Code lives in classes behind interfaces.** Every new class has its interface; the four
  missing contracts and the module-function mappers are closed.
- **Every job idempotent under replay; the ledger append-only.** The same statements, now
  Core; the ledger gains a loud guard in front of its silent rules.
- **100% branch floors.** Every lane runs the per-layer gates.

## Migration

Twenty-six QwenStorm lanes, one module and its interface and its tests each
(`specs/orm-*.md`, order and dependencies in `specs/orm-queue.txt`): import contracts; the
family's async engine; typed tables and the JSON decoder; the seam; the test harness;
`build_app` handing out the seam; the ledger guard; then one lane per repository (ledger,
project, ledger search, engine health, rotation cursor, handoff, human gate, advisory
lock), the job queue in four (enqueue statements, settle statements, enqueue, settle), the
notifier, the migrator in two (callers by URL, then the migrator itself), the cluster
preflight, `vibey recover` through `JobRepository.recover_leased`, `build_app` without a
pool, and the guard that closes the wave. Until the last repository lane, `build_app`
holds the old pool beside the seam; `orm-bootstrap-engine` removes it.

## Consequences

**Good.** One way to PostgreSQL, declared and substitutable. Statements are typed and
composable, so the RabbitMQ records extend the queue's statements instead of restating
their SQL. No identifier is ever formatted into SQL text; the search compiler no longer
needs its own placeholder counter or a `nosec`. The notifier and the doctor stop opening
connections behind every seam. Tests stop patching imports.

**Bad.** A second abstraction over the driver: statement shapes now depend on SQLAlchemy's
compiler, which the lanes pin by compiling statements in unit tests and running them in
integration tests. The asyncpg dialect's typed binds are a trap the lanes had to learn
(enums, 64-bit keys). The migration scripts need a driver-level path, and LISTEN keeps one.
During the wave, a transitional pool and a transitional appender branch exist for a few
lanes.

## Alternatives rejected

- **Keep raw asyncpg for the queue and the ledger** (today's `orm.py` docstring). Every
  contract it cites — `SKIP LOCKED`, the append-only rules, transactional notification — is
  expressible in Core, as the compiled statements show; keeping two ways in is what left the
  ORM unused.
- **ORM sessions everywhere.** The identity map and unit-of-work flush add nothing to a
  single-statement claim or fence and hide the one statement the chaos test relies on.
- **Alembic autogenerate or `create_all`.** It would make the models the schema's authority
  and end the checksummed, forward-only record; migrations stay hand-written.
- **Split migration files into statements.** `DO $$ … $$` bodies and function definitions
  contain semicolons; a splitter would be a SQL parser, and a wrong split is a half-applied
  migration.
- **psycopg 3 under SQLAlchemy.** It would change the driver the whole family and every
  deployment already carries, for no capability the queue lacks.
- **A parallel async engine in vibey.** The family's database layer exists; 10.e closes the
  gap there.

## Evidence flags (10.f)

- The 67-site count is a heuristic (uppercase SQL keyword at the start of a non-docstring
  string constant), taken on `c91561f4`; the operator's survey counted ~64 call sites by a
  different rule. Both describe the same modules.
- Statement shapes are verified by compilation, not yet by execution through the new code;
  each lane's integration tests are the execution evidence, and none has run.
- The claim that SQLAlchemy's asyncpg dialect prepares every statement is read from
  `sqlalchemy/dialects/postgresql/asyncpg.py` (`_prepare_and_execute`) at 2.0.53; a future
  SQLAlchemy that adds a simple-query path would let exemption 2 go, and the budget test
  would say so.
