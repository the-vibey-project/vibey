## Title
feat(db): PostgresSurfaceDeadLetterRepository keeps parked surface dead letters, written once and answered once

## Why
Draft ADR-0047 §9 (`specs/ADR-surface-lanes.md`, "Dead letters are parks"): every
`reconcile_interval_seconds` the lane drains its dead queue into `surface_dead_letter` rows,
"written once, keyed by `(surface, dedupe_key)`". `vibey surface dead-letters` reads them from
PostgreSQL, "so it works while a lane is down", and `vibey surface requeue <id>` "marks the row
answered, once. The dead letter itself is never rewritten." Sub-doctrine 8.f: "an operation the
surface refuses or cannot complete is parked … with its evidence, never retried forever and
never dropped." This lane is that store, on the table migration 0015 created
(`surfaces-migration`), through the ORM seam (draft ADR-ORM `specs/ADR-orm.md` §1–§3). Part of
ADR-0047 lanes S10–S12.

## Required behaviour
In the new `src/vibey/infrastructure/db/surface_dead_letter_repository.py`:

1. Frozen, slotted dataclasses:
   - `SurfaceDeadLetterEntry` (what is written): `surface: str`, `operation: str`, `op_id: str`,
     `request_id: str`, `dedupe_key: str`, `reason: str`, `detail: str`, `attempts: int`,
     `delivery_count: int`, `instance: str`, `dead_lettered_at: datetime`,
     `request: Mapping[str, object]`, `retained: bool`.
   - `SurfaceDeadLetterRecord` (what is read): `id: UUID`, every entry field, `recorded_at:
     datetime`, `answered_at: datetime | None`, `answered_by: str | None`,
     `requeue_request_id: str | None`.
2. `class SurfaceDeadLetterRowMapper.to_record(self, row: Mapping[str, Any]) -> SurfaceDeadLetterRecord`
   (`request` through `JSON_COLUMNS.mapping`). `DEAD_LETTER_ROWS: Final[...] = SurfaceDeadLetterRowMapper()`.
3. `class PostgresSurfaceDeadLetterRepository`,
   `__init__(self, orm: PostgresOrmInterface, *, rows=DEAD_LETTER_ROWS)`, with
   `DEAD = TABLES.table("surface_dead_letter")`:
   - `async record(self, entry: SurfaceDeadLetterEntry) -> bool`: in `orm.transaction()`,
     `postgresql.insert(DEAD).values(<entry fields>, detail=entry.detail[:2000], request=dict(entry.request)).on_conflict_do_nothing(index_elements=[DEAD.c["surface"], DEAD.c["dedupe_key"]]).returning(DEAD.c["id"])`;
     True when written, False when that dead letter was already recorded.
   - `async get(self, dead_letter_id: UUID) -> SurfaceDeadLetterRecord | None`.
   - `async recent(self, *, surface: str | None = None, include_answered: bool = False, limit: int = 100) -> tuple[SurfaceDeadLetterRecord, ...]`:
     newest first (`order_by(DEAD.c["dead_lettered_at"].desc(), DEAD.c["id"].desc())`),
     filtered by surface when given and to `answered_at IS NULL` unless `include_answered`;
     `limit` outside 1–1000 raises `ValueError`.
   - `async mark_answered(self, dead_letter_id: UUID, *, answered_by: str, requeue_request_id: str | None, at: datetime) -> bool`:
     `update(DEAD).where(DEAD.c["id"] == dead_letter_id, DEAD.c["answered_at"].is_(None)).values(answered_at=at, answered_by=answered_by, requeue_request_id=requeue_request_id).returning(DEAD.c["id"])`;
     True exactly once per row. An empty `answered_by` raises `ValueError`.
   No method updates any other column: the evidence is never rewritten.
4. **Interfaces** in the new
   `src/vibey/infrastructure/db/interfaces/surface_dead_letter_repository_interface.py`:
   `SurfaceDeadLetterRowMapperInterface`, `SurfaceDeadLetterRepositoryInterface`
   (`record`, `get`, `recent`, `mark_answered`), `@runtime_checkable`, exported from
   `src/vibey/infrastructure/db/interfaces/__init__.py`.

## Where to change
- New `src/vibey/infrastructure/db/surface_dead_letter_repository.py`,
  `src/vibey/infrastructure/db/interfaces/surface_dead_letter_repository_interface.py`;
  `src/vibey/infrastructure/db/interfaces/__init__.py` (exports).
- New `tests/infrastructure/orm/test_surface_dead_letter_repository.py` (no database) and
  `tests/infrastructure/db/test_surface_dead_letter_repository.py` (integration).

## Acceptance criteria
- [ ] Unit (`FakeOrm`): `record` compiles to `ON CONFLICT (surface, dedupe_key) DO NOTHING RETURNING surface_dead_letter.id`; `mark_answered` filters on `answered_at IS NULL`; `recent` orders newest first and applies both filters; bad `limit` and empty `answered_by` raise.
- [ ] Integration: recording one entry twice writes one row; `recent()` hides an answered row unless `include_answered=True`; `mark_answered` returns True then False, and the row's evidence columns are unchanged afterwards.
- [ ] `grep -n "asyncpg\|text(" src/vibey/infrastructure/db/surface_dead_letter_repository.py` prints nothing.
- [ ] `isinstance(repo, SurfaceDeadLetterRepositoryInterface)`; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_surface_dead_letter_repository.py` (no database):
- `test_record_inserts_once_per_dedupe_key`
- `test_mark_answered_only_touches_an_open_row`
- `test_recent_orders_and_filters`
- `test_arguments_are_validated`
- `test_repository_and_mapper_satisfy_their_interfaces`
`tests/infrastructure/db/test_surface_dead_letter_repository.py` (integration):
- `test_a_dead_letter_is_written_once`
- `test_answering_is_once_and_never_rewrites_the_evidence`
- `test_recent_hides_answered_rows_by_default`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/orm/test_surface_dead_letter_repository.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_surface_dead_letter_repository.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Draining the dead queue (`surfaces-reconcile`), the CLI (`surfaces-cli-dead-letters`), the
  requeue (`surfaces-requeue`), pruning answered rows (a follow-up the ADR names under
  "Security impact"). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill
  trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-migration`, `orm-database-seam`, `orm-tables`, `orm-test-harness`.
- **Shares a file with:** `src/vibey/infrastructure/db/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** every test in `tests/infrastructure/db/` and `tests/infrastructure/orm/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Production code reaches PostgreSQL only through `PostgresOrmInterface`; no new `import asyncpg`, `text()`, `literal_column`, `exec_driver_sql()` or SQL string in `src/`.
  - Substitute only at the declared seam (`FakeOrm`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
