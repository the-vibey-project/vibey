## Title
build(imports): asyncpg is imported only by the notifier, and a meta test fails on any new raw-SQL site

## Why
The ORM wave (draft ADR `specs/ADR-orm.md`) ends with every persistence access in
`src/vibey` going through `PostgresOrmInterface` and SQLAlchemy Core or ORM statements,
with exactly two written, driver-level exemptions: the job-ready `LISTEN` (lane
`orm-notifier`) and the checksummed migration scripts (lane `orm-migrator`). Before the
wave, `src/vibey` held 67 SQL-text sites across 13 modules (counted 2026-09-22 with the
heuristic below). A standard that is not enforced drifts back the first time someone is in
a hurry, so this lane makes both halves mechanical:
- **import-linter** refuses `asyncpg` everywhere in `vibey` except the notifier (the
  `domain-independence` contract already refuses it in `vibey.domain`; this generalizes it);
- **a meta test** counts raw-SQL sites in `src/vibey` and fails when the count differs from
  a small, written budget — so a new `text()`, a new SQL string, a new
  `exec_driver_sql` or a new driver-level connection fails CI with the file and the line.

## Required behaviour
1. `.importlinter` gains, after `application-persistence-free` (lane `orm-import-contracts`):
   ```ini
   # asyncpg is the driver under SQLAlchemy, never an API vibey calls. One module names it:
   # the job-ready notifier, whose LISTEN has no SQLAlchemy form (ADR-orm, the driver-level
   # exemption). Everything else reaches PostgreSQL through the ORM seam.
   [importlinter:contract:asyncpg-only-in-the-notifier]
   name = asyncpg is imported only by the job-ready notifier
   type = forbidden
   source_modules =
       vibey
   forbidden_modules =
       asyncpg
       psycopg
   ignore_imports =
       vibey.infrastructure.db.notifier -> asyncpg
   ```
   If `uv run lint-imports` then names any other module importing asyncpg (a `TYPE_CHECKING`
   import counts), remove that import in this lane; each earlier ORM lane was meant to.
2. New `tests/meta/test_raw_sql_budget.py`. It parses every `src/vibey/**/*.py` with `ast`
   and counts, per file, four kinds of site:
   - `sql_string` — a string constant (or the first literal part of an f-string) that
     matches `^\s*(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|WITH|CREATE|ALTER|DROP|NOTIFY|LISTEN|SHOW|TRUNCATE)\s`
     (case-sensitive), excluding docstrings (the first statement of a module, class or
     function);
   - `text` — a call of `text(...)` where the module imports `text` from `sqlalchemy` or
     `sqlalchemy.sql`, or a call `sqlalchemy.text(...)`; `src/vibey/infrastructure/db/orm_models.py`
     is exempt from this kind only, because its `text(...)` calls are server defaults and
     partial-index predicates in the mapping, never executed as statements;
   - `exec_driver_sql` — any call of an attribute named `exec_driver_sql`;
   - `raw_connection` — any call of an attribute named `get_raw_connection`.
   The budget is a module constant with a one-line reason per entry:
   ```python
   BUDGET: Final = {
       ("src/vibey/infrastructure/db/migrator.py", "sql_string"): 1,      # _ENSURE_SCHEMA_MIGRATION_TABLE, the bootstrap DDL
       ("src/vibey/infrastructure/db/migrator.py", "raw_connection"): 1,  # _run_script: multi-statement files need the simple-query protocol
       ("src/vibey/infrastructure/db/notifier.py", "raw_connection"): 1,  # LISTEN has no SQLAlchemy form
   }
   ```
   and the test asserts the counted mapping equals `BUDGET` exactly. On failure the message
   lists every unexpected `path:line kind` and says: reach PostgreSQL through
   `PostgresOrmInterface` with SQLAlchemy Core or ORM statements; an exemption needs a
   written reason in the ADR and an entry here.
3. The counting helpers live in one stateless class, `RawSqlCensus`, in the test module
   (pytest `test_*` functions stay module-level, as `tests/meta/test_import_contracts_bind.py`
   explains).
4. The second paragraph of the `src/vibey/infrastructure/db/orm_models.py` module docstring
   (`:10-13`, "The live repositories still use asyncpg …") is replaced by two sentences: every
   repository now reaches these tables through `PostgresOrmInterface` with Core or ORM
   statements; the only driver-level paths are the notifier's LISTEN and the migrator's
   scripts. Change nothing else in that file.

## Where to change
- `.importlinter`
- `tests/meta/test_raw_sql_budget.py` (new)
- any `src/vibey` module `lint-imports` names in step 1 (import removal only)
- `src/vibey/infrastructure/db/orm_models.py` (the docstring paragraph only)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `uv run lint-imports` passes and lists `asyncpg is imported only by the job-ready notifier` as KEPT.
- [ ] Planting `import asyncpg` in `src/vibey/cli/main.py` makes `lint-imports` fail; revert the plant.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_raw_sql_budget.py` passes.
- [ ] Planting `x = "SELECT 1"` in any `src/vibey` module makes it fail naming that file and line; planting `from sqlalchemy import text` plus `text("SELECT 1")` makes it fail twice (`sql_string` and `text`); revert both.
- [ ] `tests/meta/test_import_contracts_bind.py` and `tests/meta/test_persistence_import_contracts.py` pass.

## Tests to write first (TDD)
`tests/meta/test_raw_sql_budget.py`:
- `test_raw_sql_sites_match_the_written_budget`
- `test_the_census_sees_a_planted_sql_string` (feed `RawSqlCensus` a source string, not a file)
- `test_the_census_ignores_docstrings`
- `test_the_census_sees_text_only_when_it_is_sqlalchemys` (a local function named `text` is not counted)
- `test_the_census_sees_driver_level_access` (`exec_driver_sql` and `get_raw_connection`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # No-services tests (the root conftest still opens a database at startup today):
    uv run pytest -q -p no:cacheprovider tests/meta
    # The whole suite, once, to prove the wave is closed:
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The tenants under `src/vibey_runners` and `src/vibey_tools` (the family's own outbox is
  moved onto `AsyncConnection` by the amended `rmq-r05-async-outbox`).
- `tests/` (tests may use asyncpg and SQL text to set up and observe the database).
- Docs, the ADR itself (the docs wave files `specs/ADR-orm.md`), CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
