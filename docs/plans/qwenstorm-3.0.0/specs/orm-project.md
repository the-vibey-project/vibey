## Title
refactor(db): the project repository and its phase-CAS go through the ORM seam, in one transaction with the ledger event

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `PostgresProjectRepository`
(`src/vibey/infrastructure/db/project_repository.py:140-298`) is five raw asyncpg statements:
`create` (`:181-195`), `get` (`:197-200`), `get_latest` (`:202-205`), and the two branches of
the phase compare-and-set in `transition` (`:232-263`). `transition` is the one that matters:
the CAS and the `PhaseTransitioned` event are written in **one** transaction, so a worker
that dies between them can neither lose the event nor write it twice (docstring `:216-231`,
pinned by `test_project_repository.py:185-205`). Lane `orm-ledger` taught the appender the
ORM path and left a legacy asyncpg branch only for this caller; this lane moves the caller
and deletes that branch, so the ledger module no longer imports asyncpg.

## Required behaviour
1. `ProjectRowMapper.to_record(self, row: Mapping[str, Any])`: the same mapping, except
   `config=JSON_COLUMNS.mapping(row["config"])` (lane `orm-tables`).
2. `PostgresProjectRepository.__init__(self, orm: PostgresOrmInterface, *, appender=…, drafts=…, rows=…, notifications=None)`
   — only the first parameter changes (from `pool: asyncpg.Pool`).
3. With `PROJECT = TABLES.table("project")` as a module constant:
   - `create`: in `self._orm.transaction()`,
     `insert(PROJECT).values(name=name, repo_path=str(repo_path.resolve()), max_cycles=max_cycles, config=dict(config)).returning(*PROJECT.c)`;
     `.mappings().first()`; `None` raises today's `LookupError("project insert returned no row")`.
   - `get`: in `self._orm.connect()`, `select(PROJECT).where(PROJECT.c["id"] == project_id)`.
   - `get_latest`: `select(PROJECT).order_by(PROJECT.c["created_at"].desc()).limit(1)`.
   - `transition`: in `self._orm.transaction()`, **one** statement for both cases:
     `values: dict[str, object] = {"phase": to.value, "updated_at": func.now()}`, plus
     `values["cycle"] = cycle` when `cycle is not None`;
     `update(PROJECT).where(PROJECT.c["id"] == project_id, PROJECT.c["phase"] == expected.value).values(values).returning(*PROJECT.c)`.
     No row raises today's `ValueError(f"project {project_id} is not in expected phase {expected.value!r}")`.
     Then `await self._events.append(conn, self._drafts.build(settled, expected, guard))` on
     the **same** `conn`, inside the same `transaction()` block. The notification code after
     the block is unchanged.
4. In `ledger_repository.py`, delete the legacy asyncpg branch of
   `ConnectionEventAppender.append` (added by `orm-ledger`) and `import asyncpg`:
   `append(self, conn: AsyncConnection, draft)` now always calls `_append_through_orm`. In
   `ledger_repository_interface.py` the `OwnedConnection` alias becomes `AsyncConnection`
   and the `asyncpg` import goes.
5. `ProjectRowMapperInterface.to_record` takes `Mapping[str, Any]`
   (`src/vibey/infrastructure/db/interfaces/project_repository_interface.py`); its `asyncpg`
   import goes.
6. `build_app` builds `PostgresProjectRepository(orm, notifications=notifications)`
   (`src/vibey/bootstrap.py:714-717`).

## Where to change
- `src/vibey/infrastructure/db/project_repository.py`
- `src/vibey/infrastructure/db/ledger_repository.py` (the legacy branch only)
- `src/vibey/infrastructure/db/interfaces/project_repository_interface.py`
- `src/vibey/infrastructure/db/interfaces/ledger_repository_interface.py`
- `src/vibey/bootstrap.py` (the one construction)
- `tests/infrastructure/db/test_project_repository.py`: rewrite only the body of
  `test_create_raises_lookup_error_when_fetchrow_returns_none` (`:232-249`) to
  `repo = PostgresProjectRepository(FakeOrm(FakeResult()))` (from
  `tests/infrastructure/orm/fakes.py`), keeping its `pytest.raises`. Append the new tests.
- New `tests/infrastructure/orm/test_project_row_mapper.py` (no database).
`test_a_failed_append_rolls_the_phase_change_back` (`:185-205`) must pass **unchanged**: it
is the proof that the CAS and the event share one transaction.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg" src/vibey/infrastructure/db/project_repository.py src/vibey/infrastructure/db/ledger_repository.py src/vibey/infrastructure/db/interfaces/project_repository_interface.py src/vibey/infrastructure/db/interfaces/ledger_repository_interface.py` prints nothing.
- [ ] Every test in `test_project_repository.py` passes; the rolled-back-append test is unchanged.
- [ ] A cycle-bumping transition and a plain one both land exactly one `PhaseTransitioned` event (`:54-102` unchanged).
- [ ] `tests/cli/test_forward_compatibility_columns.py`, `tests/infrastructure/db/test_design_interview_end_to_end.py` and `tests/infrastructure/db/test_forward_compatibility_columns.py` pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_project_repository.py` (integration):
- `test_create_stores_config_as_jsonb_and_reads_it_back` (a nested config round-trips equal)
- `test_a_transition_and_its_event_commit_together_through_the_seam` (after `transition`, the
  project is in `to`, and `PostgresLedgerRepository(migrated_pool).all_for_project(project_id)`
  ends with one `PhaseTransitioned` event whose `produced_at` equals the returned record's
  `updated_at`)
`tests/infrastructure/orm/test_project_row_mapper.py` (no database):
- `test_a_decoded_config_and_a_text_config_map_the_same`
- `test_an_unknown_phase_reads_back_as_unrecognized` (`"future_phase"` → `UnrecognizedPhase`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_project_repository.py tests/infrastructure/db/test_ledger_repository.py tests/infrastructure/db/test_design_interview_end_to_end.py tests/infrastructure/db/test_forward_compatibility_columns.py tests/cli/test_forward_compatibility_columns.py tests/cli/test_main_integration.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_project_row_mapper.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The phase-guard call sites (the `guard` parameter stays exactly as documented `:90-103`).
- Notifications. The search repository. Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
