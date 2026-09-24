## Title
feat(db): typed Core tables and one JSON-column decoder for every ORM repository

## Why
The ORM lanes write statements with SQLAlchemy Core over the SQLModel mapping
(`src/vibey/infrastructure/db/orm_models.py`, draft ADR `specs/ADR-orm.md`). Two small
shared pieces are missing, and without them every repository lane would reinvent them:

1. **A typed table.** `JobOrm.__table__` exists at runtime but `mypy --strict` rejects it
   (`"type[JobOrm]" has no attribute "__table__"`, checked 2026-09-22 against the pinned
   sqlmodel 0.0.42). `SQLModel.metadata.tables["job"]` is typed `Table`, but only once
   `orm_models` has been imported, and a typo is a bare `KeyError`. Columns must be read as
   `table.c["name"]`: that form types as `Column[Any]` and compares cleanly under mypy.
2. **One JSON decoder.** Through SQLAlchemy's asyncpg dialect a `jsonb` value arrives
   already decoded (the dialect installs a `json.loads` codec); through a raw asyncpg row it
   arrives as text, which is why every mapper today calls `json.loads(row[...])`
   (`ledger_repository.py:78`, `project_repository.py:54`, `job_repository.py:30-39`,
   `human_gate_repository.py:24-26`, `handoff_repository.py:108-111`). While the lanes move
   one repository at a time, a shared mapper can be fed either shape, so it must accept both.

Both are classes with interfaces beside them (ADR-0016, 9.b).

## Required behaviour
1. `class OrmTables` in `src/vibey/infrastructure/db/tables.py`:
   - `__init__(self, metadata: MetaData = SQLModel.metadata, names: frozenset[str] = ORM_TABLE_NAMES)`.
     Importing `ORM_TABLE_NAMES` from `orm_models` is what registers every model.
   - `table(self, name: str) -> Table`: returns `metadata.tables[name]`; a name not in
     `names` raises `KeyError` whose message says to add the model to
     `orm_models.ORM_TABLE_MODELS`.
   - A module-level `TABLES: Final[OrmTablesInterface] = OrmTables()` with the one-line
     "stateless, one instance serves" comment used by `EVENT_ROWS` (`ledger_repository.py:83-84`).
2. `class JsonColumn` in `src/vibey/infrastructure/db/json_column.py`:
   - `decode(self, value: object) -> Any`: `str`, `bytes` or `bytearray` → `json.loads(value)`;
     anything else is returned as it is (already decoded).
   - `mapping(self, value: object) -> dict[str, Any]`: `decode`, then `TypeError` unless the
     result is a `dict`; returns it.
   - `optional_mapping(self, value: object) -> dict[str, Any] | None`: `None` → `None`, else
     `mapping(value)`.
   - `sequence(self, value: object) -> list[Any]`: `decode`, then `TypeError` unless `list`.
   - A module-level `JSON_COLUMNS: Final[JsonColumnInterface] = JsonColumn()`.
   - The class docstring states the transition reason above and that vibey never stores a
     bare JSON string at the top of any of these columns (every one is an object or an array),
     so decoding a `str` is never ambiguous.
3. Interfaces `OrmTablesInterface` (`interfaces/tables_interface.py`) and
   `JsonColumnInterface` (`interfaces/json_column_interface.py`), `@runtime_checkable`
   Protocols in the style of `interfaces/engine_health_repository_interface.py`
   (driver types under `TYPE_CHECKING` only), both exported from
   `vibey/infrastructure/db/interfaces/__init__.py`.

## Where to change
- `src/vibey/infrastructure/db/tables.py` (new)
- `src/vibey/infrastructure/db/json_column.py` (new)
- `src/vibey/infrastructure/db/interfaces/tables_interface.py` (new)
- `src/vibey/infrastructure/db/interfaces/json_column_interface.py` (new)
- `src/vibey/infrastructure/db/interfaces/__init__.py` (two exports, alphabetical in `__all__`)
- `tests/infrastructure/orm/test_tables_and_json.py` (new; create
  `tests/infrastructure/orm/__init__.py` with only the provenance line if it does not exist yet)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `TABLES.table("job").c["idempotency_key"]` is the `job` table's column; `TABLES.table("jobs")` raises `KeyError` naming `ORM_TABLE_MODELS`.
- [ ] Every name in `ORM_TABLE_NAMES` resolves.
- [ ] `JSON_COLUMNS.mapping('{"a": 1}') == {"a": 1}` and `JSON_COLUMNS.mapping({"a": 1}) == {"a": 1}`; `mapping("[1]")` raises `TypeError`; `optional_mapping(None) is None`; `sequence('["x"]') == ["x"]`; `sequence(["x"]) == ["x"]`; `sequence('{}')` raises `TypeError`; bytes decode.
- [ ] `mypy --strict src/vibey` is clean; 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_tables_and_json.py` (no database):
- `test_every_mapped_relation_resolves_to_its_table`
- `test_an_unmapped_name_is_a_key_error_that_says_what_to_do`
- `test_json_text_and_decoded_json_come_back_the_same` (parametrize str, bytes, dict)
- `test_a_mapping_column_refuses_a_non_object`
- `test_an_optional_mapping_passes_none_through`
- `test_a_sequence_column_refuses_a_non_array`
- `test_both_are_their_declared_seams`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_tables_and_json.py
    # Postgres-backed regression (unchanged, must stay green):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_orm.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Using either class in a repository (each repository lane does that).
- `orm_models.py` (lane `rmq-r08-dispatch-migration` edits it; do not).
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
