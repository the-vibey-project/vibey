## Title
refactor(db): the rotation cursor repository goes through the ORM seam

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `PostgresRotationCursorRepository`
(`src/vibey/infrastructure/db/rotation_cursor_repository.py:49-170`) is six raw asyncpg
statements: `get` (`:73-81`), `list_for_project` (`:86-91`), `upsert` (`:96-111`),
`update_many` (`:123-141`, the same upsert text repeated inside one transaction), and
`initialize_for_project` (`:152-170`). `update_many` is the crash-safety point of SWRR
rotation (ADR-0005): every cursor is refused before the transaction opens, and all of them
commit together or none does.

## Required behaviour
1. `RotationCursorRowMapper.to_cursor(self, row: Mapping[str, Any])`: the same mapping; the
   interface (`interfaces/rotation_cursor_repository_interface.py:23`) takes
   `Mapping[str, Any]` and drops its `asyncpg` import.
2. `PostgresRotationCursorRepository.__init__(self, orm: PostgresOrmInterface, *, rows=CURSOR_ROWS)`.
3. With `CURSORS = TABLES.table("rotation_cursor")` (lane `orm-tables`):
   - a private method `_upsert(self, cursor: RotationCursor, engine_id: EngineId)` returns
     the one statement both writers use:
     ```python
     stmt = pg_insert(CURSORS).values(project_id=cursor.project_id, engine_id=engine_id.value,
                                      current=cursor.current, order=cursor.order)
     return stmt.on_conflict_do_update(
         index_elements=[CURSORS.c["project_id"], CURSORS.c["engine_id"]],
         set_={"current": stmt.excluded["current"], "order": stmt.excluded["order"]},
     ).returning(*CURSORS.c)
     ```
   - `get`: `select(CURSORS).where(project_id ==, engine_id == engine_id.value)` in `connect()`.
   - `list_for_project`: `select(CURSORS).where(project_id ==).order_by(CURSORS.c["order"])`.
   - `upsert`: `_writable` first (unchanged), then `_upsert` in `transaction()`,
     `.mappings().one()`.
   - `update_many`: `writable` computed before the transaction exactly as today (`:122`), then
     one `transaction()` executing `_upsert` per cursor.
   - `initialize_for_project`: in one `transaction()`, per engine
     `pg_insert(CURSORS).values(project_id=…, engine_id=engine_id.value, current=0, order=idx).on_conflict_do_nothing(index_elements=[CURSORS.c["project_id"], CURSORS.c["engine_id"]])`,
     then the ordered `select` of every cursor of the project.
4. `build_app` builds `rotation_cursors = PostgresRotationCursorRepository(orm)`
   (`src/vibey/bootstrap.py:722`).

## Where to change
- `src/vibey/infrastructure/db/rotation_cursor_repository.py`
- `src/vibey/infrastructure/db/interfaces/rotation_cursor_repository_interface.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_rotation_cursor_repository.py` (append only)
- New `tests/infrastructure/orm/test_rotation_cursor_row_mapper.py` (no database)
Existing tests keep constructing the repository from `migrated_pool` (a `MigratedDatabase`,
lane `orm-test-harness`); `tests/contracts/test_rotation_cursor_contract.py` and
`tests/infrastructure/db/test_forward_compatibility_columns.py:108-133` (the `None` seam:
the refusal happens before the seam is used) pass unchanged.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg" src/vibey/infrastructure/db/rotation_cursor_repository.py src/vibey/infrastructure/db/interfaces/rotation_cursor_repository_interface.py` prints nothing.
- [ ] `update_many` with one writable cursor and one for an unknown engine writes neither (the refusal comes before the transaction).
- [ ] `update_many` whose second statement fails leaves the first cursor unchanged (one transaction).
- [ ] Every existing test in `test_rotation_cursor_repository.py`, the contract test, `test_end_to_end_forced_rotation.py` and `test_engine_health_repository.py::test_health_engine_id_survives_rotation_cursor_round_trip` pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_rotation_cursor_repository.py` (integration):
- `test_update_many_refuses_before_writing_anything` (a known and an `UnrecognizedEngineId` cursor → `ValueError`; the known one is unchanged)
- `test_update_many_is_one_transaction` (a cursor for a project id that does not exist violates the foreign key → the earlier cursor in the same call is unchanged; expect `sqlalchemy.exc.IntegrityError`)
- `test_the_order_column_round_trips` (the quoted `"order"` column reads back as written)
`tests/infrastructure/orm/test_rotation_cursor_row_mapper.py` (no database):
- `test_a_known_engine_maps_to_its_member`
- `test_an_unknown_engine_keeps_its_stored_id`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_rotation_cursor_repository.py tests/contracts tests/infrastructure/db/test_end_to_end_forced_rotation.py tests/infrastructure/db/test_engine_health_repository.py tests/infrastructure/db/test_forward_compatibility_columns.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_rotation_cursor_row_mapper.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `EngineSelector`, the SWRR domain (`domain/rotation.py`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
