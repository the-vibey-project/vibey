## Title
refactor(db): the ledger repository appends and reads through the ORM seam, digests unchanged

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). The ledger moves first because the
no-loss evidence rests on it. Today it is five raw asyncpg statements over a pool:
`src/vibey/infrastructure/db/ledger_repository.py:111-137` (the append:
`SELECT append_event($1…$12)`, then `SELECT * FROM event …`), `:168-178` (`range`),
`:181-185` (`all_for_project`), `:188-192` (`latest_seq`). The append must keep exactly
today's contract: the gapless per-project `seq` is claimed by the `append_event()` function
in the same transaction as the insert (`migrations/0013_ledger_partitioning.sql:88-116`);
the payload is redacted and digested in Python before it is stored (`:103-109`); and the
stored `jsonb` must decode to the same value, so every digest a verifier recomputes is
unchanged (rule R6 of the no-loss gate).

`PostgresProjectRepository.transition` also calls the appender, on its own asyncpg
connection inside its phase-CAS transaction (`project_repository.py:232-263`). That
repository moves in the next lane (`orm-project`). Until then the appender keeps a legacy
branch for an asyncpg connection, and `orm-project` deletes it.

## Required behaviour
1. `EventRowMapper.to_event(self, row: Mapping[str, Any]) -> LedgerEvent`: the same mapping,
   except `payload=JSON_COLUMNS.mapping(row["payload"])` (lane `orm-tables`). It then reads a
   decoded ORM row and a text asyncpg row alike (the search repository still feeds it
   asyncpg rows until `orm-ledger-search`).
2. `ConnectionEventAppender.append(conn, draft)`:
   - Redaction and digest exactly as today (`:108-109`).
   - If `isinstance(conn, (asyncpg.Connection, asyncpg.pool.PoolConnectionProxy))`: today's
     code, unchanged (the legacy branch; comment it `# legacy asyncpg path, removed by orm-project`).
   - Otherwise `return await self._append_through_orm(conn, draft, redacted_payload, digest)`.
3. New method `_append_through_orm(self, conn: AsyncConnection, draft, payload, digest) -> LedgerEvent`:
   - `seq = await conn.scalar(select(func.append_event(*args)))`, where `args` is one
     `literal(value, EVENT.c["<column>"].type)` per argument, in this order:
     `project_id, cycle, phase, kind, engine_id, job_id, causation_id, correlation_id,
     provenance, produced_at, payload, digest`. The values are today's (`:117-128`) except
     the payload is the redacted **dict**; the column's JSONB type serializes it with
     `json.dumps`, the same text today's `json.dumps(redacted_payload)` sends.
     Typing each argument from its column is required: SQLAlchemy's asyncpg dialect renders
     an untyped `str` as `$n::VARCHAR`, and PostgreSQL will not implicitly cast `varchar`
     to the `phase` or `provenance` enum.
   - `row = (await conn.execute(select(EVENT).where(EVENT.c["project_id"] == draft.project_id, EVENT.c["seq"] == seq))).mappings().first()`.
   - `None` raises today's `LookupError(f"append_event returned seq {seq} but no row exists")`.
   - `EVENT = TABLES.table("event")` is a module constant (lane `orm-tables`).
4. `PostgresLedgerRepository.__init__(self, orm: PostgresOrmInterface, *, appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER)`:
   - `append`: `async with self._orm.transaction() as conn: return await self._appender.append(conn, draft)`.
   - `range`: through `self._orm.connect()`,
     `select(EVENT).where(EVENT.c["project_id"] == project_id, EVENT.c["seq"].between(from_seq, to_seq)).order_by(EVENT.c["seq"])`,
     rows from `.mappings().all()`.
   - `all_for_project`: the same without `between`.
   - `latest_seq`: `await conn.scalar(select(func.max(EVENT.c["seq"])).where(EVENT.c["project_id"] == project_id))`; `None` → `0`.
5. `ledger_repository_interface.py` (`src/vibey/infrastructure/db/interfaces/`): the
   `OwnedConnection` alias becomes
   `AsyncConnection | asyncpg.pool.PoolConnectionProxy | asyncpg.Connection` (under
   `TYPE_CHECKING`; comment: "narrowed to AsyncConnection by orm-project"), and
   `EventRowMapperInterface.to_event` takes `Mapping[str, Any]`.
6. `build_app` builds `ledger = PostgresLedgerRepository(orm)` (`src/vibey/bootstrap.py:718`;
   `orm` exists since lane `orm-app-resources`).
7. `to_drafts` (`:195-238`) is unchanged.

## Where to change
- `src/vibey/infrastructure/db/ledger_repository.py`
- `src/vibey/infrastructure/db/interfaces/ledger_repository_interface.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_ledger_repository.py`:
  - rewrite only the body of `test_append_raises_lookup_error_when_fetchrow_returns_none`
    (`:174-207`): delete its three fake classes and use
    `repo = PostgresLedgerRepository(FakeOrm(FakeResult(scalar=42), FakeResult()))`
    (from `tests/infrastructure/orm/fakes.py`, lane `orm-test-harness`); keep the
    `pytest.raises(LookupError, match="append_event returned seq 42")`. The fake connection
    is not an asyncpg connection, so the append takes the ORM path.
  - append the new tests below. Do not change any other existing test.
- New `tests/infrastructure/orm/test_event_row_mapper.py` (no database).
Every other test that builds `PostgresLedgerRepository(migrated_pool)` keeps working: the
fixture is a `MigratedDatabase` (lane `orm-test-harness`).

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] The whole `test_ledger_repository.py` passes, including `test_concurrent_appends_are_gapless_and_have_no_duplicates` and both silent-no-op tests.
- [ ] **Digest pin:** appending the payload `{"note": "ORM pin", "n": 3, "nested": {"b": [1, 2.5, None], "a": True}}` stores `digest == "fbf86dc2c85ebc7755319ebe4d308be9148a8a0f9cae0e54f8b5bf540bab3ed4"` (the value today's code produces, computed 2026-09-22); the event read back through `range` has that digest, `digest_event(event.payload)` equals it, and its payload equals the original dict.
- [ ] `test_project_repository.py` (still on the legacy branch), `test_ledger_search_repository.py`, `test_design_interview_end_to_end.py`, `test_build_implement_end_to_end.py` and `tests/infrastructure/test_correlation_across_phases.py` pass unchanged.
- [ ] Outside the legacy branch, `ledger_repository.py` calls no `fetchval`, `fetchrow`, `fetch` or `execute` with a string.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_ledger_repository.py` (integration):
- `test_the_orm_append_keeps_the_pinned_digest` (the pin above; `from vibey.domain.ledger import digest_event`)
- `test_range_and_all_for_project_read_through_the_seam` (append three drafts, read them back in seq order both ways)
- `test_latest_seq_is_zero_for_an_empty_ledger`

`tests/infrastructure/orm/test_event_row_mapper.py` (no database):
- `test_a_decoded_row_and_a_text_row_map_to_the_same_event` (two dict rows, identical except
  that one payload is `{"a": 1}` and the other the text `'{"a": 1}'`)
- `test_an_unknown_kind_still_reads_back` (kind `"FutureKindX"` comes back as an
  `UnrecognizedEventKind`, as `EventRowMapper` does today)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_ledger_repository.py tests/infrastructure/db/test_project_repository.py tests/infrastructure/db/test_ledger_search_repository.py tests/infrastructure/db/test_design_interview_end_to_end.py tests/infrastructure/db/test_build_implement_end_to_end.py tests/infrastructure/test_correlation_across_phases.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_event_row_mapper.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `PostgresProjectRepository` and the removal of the legacy branch (`orm-project`).
- The search repository (`orm-ledger-search`), the migrations, the append-only guard
  (`orm-ledger-guard`).
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
