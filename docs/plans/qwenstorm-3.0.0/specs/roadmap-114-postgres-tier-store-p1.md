## Title
feat(db): migration 0016 adds the append-only ledger_segment table and its ORM model

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, "Current state" → Tier manager: "**There is
no PostgreSQL tier store**", and "Proposed child issues" 2). The compressed tier has only an
in-memory home (`src/vibey/infrastructure/ledger/tier_store.py:14-40`). A PostgreSQL home needs
a table first: one row per *sealed segment*, a verified copy of a contiguous run of one
project's events, keyed by project and seq range, holding the segment's codec, its digest and
its bytes. Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`: "The ledger stays
append-only") makes the new table append-only exactly as `event` is: the two `DO INSTEAD
NOTHING` rules of `migrations/0013_ledger_partitioning.sql:63-66`, plus the ORM seam's loud
guard (`orm-ledger-guard`: `AppendOnlyGuard`, today guarding only `{"event"}`). Migrations stay
checksummed, forward-only SQL on the PostgreSQL 14 floor (`src/vibey/infrastructure/postgres.py:28`;
draft ADR `specs/ADR-orm.md` §6), and every migrated relation needs an ORM model
(`tests/infrastructure/db/test_orm.py:50-53`, `:86-106`). The number is the next free one:
**0016 at this cutoff** (0014 is `rmq-r08-dispatch-migration`'s `0014_job_dispatch.sql`, 0015
is ADR-0047's `0015_surface_lanes.sql`, `specs/surfaces-migration.md`).

This lane adds the table only. Nothing writes or reads it yet (`roadmap-114-postgres-tier-store-p4`
does), and no row ever leaves `event` because of it (that is the rotation ADR's decision).

## Required behaviour
1. `migrations/0016_ledger_segment.sql`, exactly (like every sibling in `migrations/`, it has no
   provenance line; its first line is the comment):
   ```sql
   -- Sealed ledger segments (vibey#114). One row is a verified copy of a contiguous run of one
   -- project's events, seqs first_seq..last_seq inclusive. A segment is an additional copy:
   -- nothing here removes a row from event. `codec` names the whole encoding of `data`, so a
   -- reader knows how to open it; `digest` is the SHA-256 of `data` exactly as stored, so a
   -- segment is verified without decompressing it.
   CREATE TABLE ledger_segment (
       project_id  uuid        NOT NULL REFERENCES project(id) ON DELETE CASCADE,
       first_seq   bigint      NOT NULL,
       last_seq    bigint      NOT NULL,
       codec       text        NOT NULL,
       digest      text        NOT NULL,
       data        bytea       NOT NULL,
       sealed_at   timestamptz NOT NULL DEFAULT now(),
       PRIMARY KEY (project_id, first_seq),
       CONSTRAINT ledger_segment_range  CHECK (first_seq >= 1 AND last_seq >= first_seq),
       CONSTRAINT ledger_segment_codec  CHECK (codec <> ''),
       CONSTRAINT ledger_segment_digest CHECK (digest ~ '^[0-9a-f]{64}$')
   );

   CREATE INDEX ledger_segment_project_last ON ledger_segment (project_id, last_seq);

   -- Append-only, as event is (0013): a sealed segment is never rewritten or removed.
   CREATE RULE ledger_segment_no_update AS ON UPDATE TO ledger_segment DO INSTEAD NOTHING;
   CREATE RULE ledger_segment_no_delete AS ON DELETE TO ledger_segment DO INSTEAD NOTHING;
   ```
2. `src/vibey/infrastructure/db/orm_models.py`:
   - Add `LargeBinary,` to the `from sqlalchemy import (...)` list (`:21-37`), alphabetically
     after `Integer,`.
   - Add this class immediately after `class SchemaMigrationOrm` (`:664-672`) and before the
     comment block above `ORM_TABLE_MODELS` (copy the `EventOrm` column style, `:192-217`):
     ```python
     class LedgerSegmentOrm(VibeyOrmModel, table=True):
         __tablename__ = "ledger_segment"
         __table_args__ = (
             CheckConstraint(
                 "first_seq >= 1 AND last_seq >= first_seq", name="ledger_segment_range"
             ),
             CheckConstraint("codec <> ''", name="ledger_segment_codec"),
             CheckConstraint("digest ~ '^[0-9a-f]{64}$'", name="ledger_segment_digest"),
             Index("ledger_segment_project_last", "project_id", "last_seq"),
         )

         project_id: UUID = Field(
             sa_column=Column(
                 PostgresUUID(as_uuid=True),
                 ForeignKey("project.id", ondelete="CASCADE"),
                 primary_key=True,
                 nullable=False,
             ),
         )
         first_seq: int = Field(sa_column=Column(BigInteger, primary_key=True, nullable=False))
         last_seq: int = Field(sa_column=Column(BigInteger, nullable=False))
         codec: str = Field(sa_column=Column(Text, nullable=False))
         digest: str = Field(sa_column=Column(Text, nullable=False))
         data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
         sealed_at: datetime = Field(
             default_factory=_utc_now,
             sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
         )
     ```
   - **How a new table joins the registry** (the one `orm-tables`' `OrmTables` reads): append
     `LedgerSegmentOrm,` as the **last** entry of the `ORM_TABLE_MODELS` tuple (`:678-693`).
     `ORM_TABLE_NAMES` (`:694`) is derived from that tuple, and `OrmTables.__init__` defaults
     its `names` to `ORM_TABLE_NAMES`, so after this one line `TABLES.table("ledger_segment")`
     resolves (`orm-tables` Required behaviour 1). Nothing in `tables.py` changes. If the
     comment above the tuple names a count of relations, make the number match
     `len(ORM_TABLE_MODELS)` after your edit.
   - Add `"LedgerSegmentOrm",` to `__all__` (`:697-715`), after `"JobOrm",`.
3. `src/vibey/infrastructure/db/append_only_guard.py` (created by `orm-ledger-guard`): the
   guard's default table set becomes both append-only relations —
   `def __init__(self, tables: frozenset[str] = frozenset({"event", "ledger_segment"})) -> None:`.
   Nothing else in that file changes; `APPEND_ONLY = AppendOnlyGuard()` now guards both, and the
   violation message (`"'ledger_segment' is append-only: vibey never updates or deletes a ledger
   row (corrections are new events)"`) already fits.
4. `tests/infrastructure/db/test_orm.py`: add `"ledger_segment",` to `EXPECTED_TABLE_NAMES`
   (`:18-35`, after `"schema_migration",` or after whatever entry is last when you land). This
   is the only edit to that file.

## Where to change
- `migrations/0016_ledger_segment.sql` (new).
- `src/vibey/infrastructure/db/orm_models.py` (`edit_file`: the import, the class, the tuple, `__all__`).
- `src/vibey/infrastructure/db/append_only_guard.py` (`edit_file`, the default only).
- `tests/infrastructure/db/test_orm.py` (the constant only).
- `tests/infrastructure/db/test_ledger_segment_table.py` (new, integration: the directory's
  conftest marks it).
- `tests/infrastructure/orm/test_append_only_guard_unit.py` (append one test).

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings in
`src/` (the migration file is the one written exemption); substitute at the declared seam, never
by patching an import; never edit a protected test; the first line of every new Python file is
the provenance comment copied byte-for-byte from a sibling (e.g. line 1 of
`tests/infrastructure/db/test_orm.py`).

## Acceptance criteria
- [ ] A fresh database migrates through 0016; a second apply is a no-op; `test_orm_columns_match_every_migrated_relation` passes with `ledger_segment`.
- [ ] `TABLES.table("ledger_segment").c["data"]` is the bytea column.
- [ ] Raw `UPDATE` and `DELETE` of `ledger_segment` change nothing; through the ORM seam both raise `AppendOnlyViolation` naming `ledger_segment`.
- [ ] The range, codec and digest CHECKs, the primary key and the project foreign key each refuse a bad row.
- [ ] `test_chaos.py` (protected), `test_ledger_repository.py`, `test_migrator.py` and `test_append_only_guard.py` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/db/test_ledger_segment_table.py` (integration). Fixtures `migrated_pool`
(a `MigratedDatabase`, lane `orm-test-harness`: an asyncpg pool passthrough **and** the ORM
seam) and `project_id` from `tests/infrastructure/db/conftest.py`. Module constants:
`DATA = b"sealed segment bytes"`, `DIGEST = hashlib.sha256(DATA).hexdigest()`, `CODEC = "jsonl+zlib"`,
and a helper `async def _insert(db, project_id, first_seq, last_seq, *, codec=CODEC, digest=DIGEST, data=DATA) -> None`
that runs `await db.execute("INSERT INTO ledger_segment (project_id, first_seq, last_seq, codec, digest, data) VALUES ($1, $2, $3, $4, $5, $6)", ...)`
(raw SQL in tests is allowed; it is how the rules are proven). Imports: `hashlib`,
`from uuid import UUID, uuid4`, `asyncpg`, `pytest`, `from sqlalchemy import delete, update`,
`from tests.infrastructure.db.migrated_database import MigratedDatabase` (annotate
`migrated_pool: MigratedDatabase`), `from vibey.infrastructure.db.append_only_guard import AppendOnlyViolation`,
`from vibey.infrastructure.db.tables import TABLES`:
- `test_a_segment_row_keeps_its_bytes_exactly` — `_insert(…, 1, 3)`; `fetchrow("SELECT * FROM ledger_segment WHERE project_id = $1", project_id)` has `data == DATA`, `digest == DIGEST`, `codec == CODEC`, `(first_seq, last_seq) == (1, 3)`, `sealed_at is not None`.
- `test_updating_or_deleting_a_segment_changes_nothing` — raw `UPDATE ledger_segment SET codec = 'other' WHERE project_id = $1` and `DELETE FROM ledger_segment WHERE project_id = $1`; afterwards `count(*) == 1` and `codec == CODEC`.
- `test_a_range_below_one_or_running_backwards_is_refused` — parametrize `(0, 1)` and `(5, 4)`; `pytest.raises(asyncpg.exceptions.CheckViolationError)`.
- `test_a_digest_that_is_not_lowercase_sha256_hex_is_refused` — parametrize `"abc"` and `DIGEST.upper()`; `CheckViolationError`.
- `test_an_unnamed_codec_is_refused` — `codec=""`; `CheckViolationError`.
- `test_a_project_holds_one_segment_per_first_seq` — `_insert(…, 1, 3)` twice; the second raises `asyncpg.exceptions.UniqueViolationError`.
- `test_a_segment_belongs_to_an_existing_project` — `_insert(db, uuid4(), 1, 1)`; `asyncpg.exceptions.ForeignKeyViolationError`.
- `test_the_seam_refuses_to_update_a_segment` — `_insert(…, 1, 3)`; with `segments = TABLES.table("ledger_segment")`,
  `pytest.raises(AppendOnlyViolation, match="'ledger_segment' is append-only")` around
  `async with migrated_pool.transaction() as conn: await conn.execute(update(segments).where(segments.c["project_id"] == project_id).values(codec="other"))`;
  afterwards the stored codec is still `CODEC`.
- `test_the_seam_refuses_to_delete_a_segment` — the same with `delete(segments).where(...)`; the row count stays 1.

Append to `tests/infrastructure/orm/test_append_only_guard_unit.py` (no database):
- `test_the_segment_table_is_append_only_by_default` — `with pytest.raises(AppendOnlyViolation) as caught: AppendOnlyGuard()._refuse(None, update(TABLES.table("ledger_segment")).values(codec="x"), (), {}, {})`; `caught.value.table == "ledger_segment"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # A fresh template, so every per-worker clone carries migration 0016:
    export VIBEY_TEST_TEMPLATE_DB=vibey_test_template_seg114
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_ledger_segment_table.py tests/infrastructure/db/test_orm.py tests/infrastructure/db/test_migrator.py tests/infrastructure/db/test_append_only_guard.py tests/infrastructure/db/test_ledger_repository.py tests/infrastructure/db/test_chaos.py
    # No-services unit tests:
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_append_only_guard_unit.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py migrations/0001_project.sql migrations/0013_ledger_partitioning.sql   # must print nothing

## Out of scope
- Any code that writes or reads `ledger_segment` (`roadmap-114-postgres-tier-store-p4`); the
  segment value and port (`-p2`, `-p3`); tier-aware reads (`roadmap-114-tier-aware-reads-*`).
- Chain-link or content-address columns: the codec/chunking ADR (`roadmap-114-design-codec-chunking`)
  decides them, and the table holds no row until a writer is wired, so a later migration can
  add NOT NULL columns.
- Editing any applied migration (the checksum guard exists for that). Wiring anything into
  `bootstrap.py`.
- CHANGELOG.md, docs/ (`docs/plans/data-model.md` is owed by the docs wave), ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the four agent-surface trees. Do not push, no PRs, no remote
  changes; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
