## Title
build(imports): the ORM and the database drivers are forbidden in domain, application and tui

## Why
The operator's standard is that every persistence access goes through the ORM, behind a
declared interface (ADR-0016; sub-doctrine 9.b in `src/vibey_tools/gh/docs/doctrines.md:349`).
The first half of that is where the ORM may **not** appear. Today `.importlinter` forbids
`asyncpg` and `psycopg` in `vibey.domain` (`.importlinter` contract `domain-independence`)
but says nothing about `sqlalchemy`, `sqlmodel` or `alembic`, and nothing at all stops
`vibey.application` or `vibey.tui` importing any of them. Nothing does today
(`grep -rln "sqlalchemy\|sqlmodel\|asyncpg" src/vibey/application src/vibey/domain src/vibey/tui`
prints nothing), so the contract can be added now and binds every later ORM lane.
This is lane 1 of the ORM wave (draft ADR: `specs/ADR-orm.md`).

## Required behaviour
1. The `[importlinter:contract:domain-independence]` contract's `forbidden_modules` list
   gains three lines, after `asyncpg`: `sqlalchemy`, `sqlmodel`, `alembic`. Nothing else in
   that contract changes.
2. A new contract is added directly after `application-independence`:
   ```ini
   # Persistence is an infrastructure concern (ADR-0016, sub-doctrine 9.b). The application
   # talks to ports; the TUI talks to the application. Neither ever sees the ORM or a driver.
   [importlinter:contract:application-persistence-free]
   name = application and tui import no ORM and no database driver
   type = forbidden
   source_modules =
       vibey.application
       vibey.tui
   forbidden_modules =
       asyncpg
       psycopg
       sqlalchemy
       sqlmodel
       alembic
   ```
3. A new meta test pins both contracts so a later edit cannot silently drop a line.
4. `uv run lint-imports` reports every contract KEPT.

## Where to change
- `.importlinter` only (the two edits above). Keep the existing comment blocks untouched.
- New test file `tests/meta/test_persistence_import_contracts.py`. Copy the configparser
  reading style of `tests/meta/test_import_contracts_bind.py:65-80` (`_root_config`). Use a
  class `PersistenceContracts` with no state for the helpers if you need helpers (ADR-0016:
  pytest `test_*` functions stay module-level, as `test_import_contracts_bind.py` explains).

## Acceptance criteria
- [ ] `uv run lint-imports` passes and lists `application and tui import no ORM and no database driver` as KEPT.
- [ ] Planting `import sqlalchemy` in any module under `src/vibey/application/` makes `uv run lint-imports` fail (check by hand, then revert the plant).
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_persistence_import_contracts.py tests/meta/test_import_contracts_bind.py` passes.

## Tests to write first (TDD)
`tests/meta/test_persistence_import_contracts.py`:
- `test_domain_forbids_the_orm_and_every_driver` — parses `.importlinter`; the
  `domain-independence` contract's forbidden set contains `asyncpg`, `psycopg`,
  `sqlalchemy`, `sqlmodel`, `alembic`.
- `test_application_and_tui_forbid_the_orm_and_every_driver` — the
  `application-persistence-free` contract exists, is `type = forbidden`, its sources are
  exactly `{vibey.application, vibey.tui}` and its forbidden set contains the same five names.
- `test_external_packages_are_in_the_graph` — the `[importlinter]` section sets
  `include_external_packages = True` (without it, forbidding an external package checks nothing).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    # No-services tests (the root conftest still opens a database at startup today, so export it):
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/meta/test_persistence_import_contracts.py tests/meta/test_import_contracts_bind.py

## Out of scope
- `vibey.cli` and `vibey.bootstrap` still import `asyncpg` today; the last ORM lane
  (`orm-raw-sql-guard`) forbids it there. Do not touch them here.
- Any source file. Docs, CHANGELOG, ADRs, CLAUDE.md, skill trees.
Do not push. Commit locally with the Title as a Conventional Commit.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
