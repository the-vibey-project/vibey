## Title
test(fakes): an in-memory unit of work interprets the ORM statements the repositories issue, so the real repositories run in the default tier

## Why
`src/vibey/infrastructure/db/` holds about 3,076 lines. It reaches its 100% floor (ADR-0023)
only because the gates job runs PostgreSQL: 174 tests in `tests/infrastructure/db/` are
`integration`. The operator's standard requires the default run to need no PostgreSQL, and
SQLite is forbidden (ADR-0002). So the repositories must run against a fake **at their
driver seam**.

A parallel effort moves `infrastructure/db` onto SQLAlchemy 2 async behind a unit-of-work
seam. That is lane `orm-unit-of-work`, part of the `orm-*` lanes; `db/orm.py:28-56` is its
start. This lane targets that seam. It deliberately does not target asyncpg's
`Pool`/`Connection`: an asyncpg-shaped seam would be deleted by the ORM lanes.

A unit of work is a small, well-defined surface: a session, statements, commit and
rollback. The repositories issue a bounded set of statement shapes. An interpreter for exactly
those shapes, evaluated over Python rows and enforcing the schema's keys and constraints, is a
real in-memory implementation. It is not a stub. Any shape it does not interpret raises
loudly, naming itself, so a gap can never pass silently.

## Precondition (check before writing anything)
Run `grep -rn "class .*UnitOfWork" src/vibey/infrastructure/db`. The seam `orm-unit-of-work`
landed must exist:
- a UnitOfWork interface under `src/vibey/infrastructure/db/interfaces/`;
- its factory;
- the repositories that take it.
Write down its exact names in the commit body, and use them everywhere below where this spec
says `UnitOfWorkInterface` or `UnitOfWorkFactoryInterface`. If the seam is absent, stop and
report. Do not invent one.

## Required behaviour
1. **`tests/fakes/db.py` — `class InMemoryDatabase`** holds one dict of rows per mapped
   table, keyed by primary key. The tables come from the ORM metadata (`orm_models.py`: the
   SQLModel or declarative `metadata`). It enforces:
   - primary keys, unique constraints and unique indexes, raising
     `sqlalchemy.exc.IntegrityError`, as asyncpg's unique violation surfaces through
     SQLAlchemy;
   - `NOT NULL` columns;
   - column defaults and `server_default`s the models declare, with `now()` from an injected `Clock`;
   - every CHECK constraint that has a predicate in `tests/fakes/db_checks.py`: a
     `dict[str, Callable[[Mapping[str, object]], bool]]` keyed by constraint name.
2. **`class InMemoryUnitOfWork`** implements `UnitOfWorkInterface`, and
   **`InMemoryUnitOfWorkFactory`** implements `UnitOfWorkFactoryInterface`:
   - entering takes a snapshot, which is a deep copy of the tables; commit keeps the working
     copy; rollback and an exception exit restore the snapshot. Nested use behaves like a
     SAVEPOINT;
   - its session supports:
     - `add`, `add_all`, `get(Model, pk)`, `delete`, `flush`, `refresh`, `commit`, `rollback`;
     - `execute(stmt)`, `scalars(stmt)` and `scalar(stmt)` for:
       - `select(Model | columns)`, with `.where(...)`, `.order_by(asc/desc, nulls)`,
         `.limit`, `.offset`, `.group_by` with `func.count()`, and `.with_for_update(skip_locked=...)`.
         The last is a no-op, because a single process is serialised by an `asyncio.Lock` per
         unit of work;
       - `update(Model).where(...).values(...)` with `.returning(...)`;
       - `delete(Model).where(...)`;
       - `sqlalchemy.dialects.postgresql.insert(Model).values(...)`, with
         `.on_conflict_do_nothing(index_elements=...)` and
         `.on_conflict_do_update(index_elements=..., set_=...)`, and `.returning(...)`;
   - the `WHERE` interpreter walks `BinaryExpression`, `BooleanClauseList` (`and_`, `or_`),
     `UnaryExpression` (`not_`), `Null`, `BindParameter` and column references. It supports
     the operators `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `in_op`, `not_in_op`, `is_`, `is_not`,
     `like_op` and `ilike_op`. `func.now()` and `func.coalesce` evaluate in Python.
   - Anything else raises
     `NotImplementedError(f"InMemoryUnitOfWork does not interpret {type(node).__name__}: {node}")`.
     That includes a `text()` statement, which `fakes-db-sql-transcripts` handles.
3. **Which checks are modelled is stated, not guessed.** `tests/fakes/db_checks.py` has one
   predicate per CHECK constraint found in `migrations/*.sql`. It includes
   `project_cycle_bounded` (`migrations/0001_project.sql:15`), `job_lease_consistent`
   (`0003_job.sql:27`), `no_self_dep` (`0003_job.sql:41`), `handoff_range_sane`
   (`0006_handoff.sql:19`) and `credits_never_have_a_deadline` (`0007_engine_health_rotation.sql:21`).
   The last is CLAUDE.md's "Credits ≠ rate limit … a database CHECK constraint". A fake that
   let a credits-exhausted row carry `resets_at` would break a non-negotiable. The meta test
   `test_every_migration_check_is_modelled_or_declared` lists them all. Each must have a
   predicate, or sit in `NOT_MODELLED` with a one-line reason.
4. **Registry.** Register `UnitOfWorkFactoryInterface → InMemoryUnitOfWorkFactory()`, and add
   it to `DRIVER_SEAMS`.
5. **The repositories run in the default tier.** For every repository that `orm-unit-of-work`
   moved onto the unit of work, parametrize its test module in `tests/infrastructure/db/` over
   a `uow_factory` fixture with two parameters:
   - `memory`: `InMemoryUnitOfWorkFactory`, unmarked;
   - `postgres`: the real factory, marked `integration`.
   Change `tests/infrastructure/db/conftest.py` so the directory marker no longer marks every
   item. It marks an item only when the item has no `memory` parameter.
   `test_chaos.py` is protected and has no `memory` parameter, so it stays `integration`,
   unedited.
6. **A test that only PostgreSQL can answer** (real concurrency, `SKIP LOCKED` across
   connections, server-side functions) keeps only the `postgres` parameter. Name it in
   `POSTGRES_ONLY`, a tuple in the conftest with one reason per test.

## Where to change
- New `tests/fakes/db.py`, `tests/fakes/db_checks.py`, `tests/fakes/test_fake_db.py`.
- `tests/infrastructure/db/conftest.py`, and the repository test modules in `tests/infrastructure/db/`
  for the repositories on the unit of work (parametrization only).
- `tests/fakes/registry.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/db` runs
      the repository tests on the `memory` parameter with PostgreSQL stopped, and they pass.
- [ ] With PostgreSQL, the same tests pass on both parameters. Where the two disagree, the
      lane stops and reports: the fake is wrong, or the test is. It never weakens either.
- [ ] `test_chaos.py` is unchanged (`git diff --stat`).
- [ ] The default-tier coverage of `src/vibey/infrastructure/db/*` is reported in the commit
      body (`coverage report --include='src/vibey/infrastructure/db/*'`). The goal is 100% of
      the ORM repositories. Raw-SQL modules are the next lane.

## Tests to write first (TDD)
`tests/fakes/test_fake_db.py`, over a tiny model declared in the test module on its own `MetaData`:
- `test_insert_select_where_order_limit`
- `test_primary_key_and_unique_violations_raise_integrity_error`
- `test_not_null_and_defaults`
- `test_rollback_restores_and_commit_keeps`
- `test_nested_unit_behaves_like_a_savepoint`
- `test_update_returning_and_delete`
- `test_on_conflict_do_nothing_and_do_update`
- `test_group_by_count`
- `test_an_uninterpreted_construct_names_itself`
- `test_every_migration_check_is_modelled_or_declared`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/db
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db
    git diff --stat HEAD~1 -- tests/infrastructure/db/test_chaos.py

## Out of scope
- `text()` SQL, the migrator, advisory locks, `LISTEN`/`NOTIFY`, the KEDA scaler query and
  cluster preflight's version probe (`fakes-db-sql-transcripts`).
- SQLite, or any embedded engine in the default tier (ADR-0002; see `fakes-embedded-postgres`
  for the opt-in tier).
- Production code: `orm-*` owns the repositories.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** **`orm-unit-of-work`**, `fakes-queue-gates`, `fakes-engines`, `fakes-ledger`.
  The in-memory repositories they provide are the behavioural reference when a
  parametrized case disagrees.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_chaos.py` (protected), the
  PostgreSQL 14–18 matrix (`postgres-compatibility`), and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
