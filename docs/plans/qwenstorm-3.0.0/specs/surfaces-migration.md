## Title
feat(db): migration 0015 adds surface_operation and surface_dead_letter, with their ORM models

## Why
Draft ADR-0047 §8–§9 (`specs/ADR-surface-lanes.md`) keep two kinds of operational state in
PostgreSQL:

- **`surface_operation`**: the intent record of a *guarded* operation (`create_page`,
  `send_email`, `send_sms`), written **before** the effect and finished **after** it, so a
  redelivery of a send whose outcome is unknown is parked instead of repeated (§8).
- **`surface_dead_letter`**: every dead letter drained from a lane's dead queue, with its
  evidence and its redacted request, readable while every lane is down (§9, "Why
  PostgreSQL"). A `human_gate` row is impossible, because `human_gate.project_id` is `NOT NULL`
  (`migrations/0008_human_gate_artifact_budget.sql:3`) and a surface operation belongs to no
  project.

Both are "mutable operational state, like `job` and `job_outbox` … not the ledger" (§9). The
migration number is **0015**: 0014 is R08's (`specs/rmq-r08-dispatch-migration.md`).
Migrations stay checksummed, forward-only SQL (draft ADR-ORM §6), on the PostgreSQL 14 floor.
`tests/infrastructure/db/test_orm.py:18` requires every migrated relation to have an ORM
model. ADR-0047 lanes S10–S12 (schema part).

## Required behaviour
1. **`migrations/0015_surface_lanes.sql`**, exactly:
   ```sql
   -- Surface lanes (draft ADR-0047 §8, §9): the intent record of guarded operations and the
   -- parked dead letters. Operational state, like job and job_outbox -- not the ledger.
   CREATE TABLE surface_operation (
       surface         text        NOT NULL,
       op_id           text        NOT NULL,
       operation       text        NOT NULL,
       request_digest  text        NOT NULL,
       state           text        NOT NULL,
       result          jsonb,
       detail          text        NOT NULL DEFAULT '',
       request_id      text        NOT NULL,
       instance        text        NOT NULL,
       attempts        integer     NOT NULL DEFAULT 1,
       created_at      timestamptz NOT NULL DEFAULT now(),
       updated_at      timestamptz NOT NULL DEFAULT now(),
       PRIMARY KEY (surface, op_id),
       CONSTRAINT surface_operation_state CHECK (state IN ('started','done','failed','parked')),
       CONSTRAINT surface_operation_attempts CHECK (attempts >= 1),
       CONSTRAINT surface_operation_detail_bounded CHECK (char_length(detail) <= 2000)
   );
   CREATE TABLE surface_dead_letter (
       id                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
       surface             text        NOT NULL,
       operation           text        NOT NULL,
       op_id               text        NOT NULL,
       request_id          text        NOT NULL,
       dedupe_key          text        NOT NULL,
       reason              text        NOT NULL,
       detail              text        NOT NULL DEFAULT '',
       attempts            integer     NOT NULL DEFAULT 0,
       delivery_count      integer     NOT NULL DEFAULT 0,
       instance            text        NOT NULL,
       dead_lettered_at    timestamptz NOT NULL,
       recorded_at         timestamptz NOT NULL DEFAULT now(),
       request             jsonb       NOT NULL,
       retained            boolean     NOT NULL,
       answered_at         timestamptz,
       answered_by         text,
       requeue_request_id  text,
       CONSTRAINT surface_dead_letter_dedupe UNIQUE (surface, dedupe_key),
       CONSTRAINT surface_dead_letter_reason CHECK (reason IN ('malformed','wrong_surface','delivery_limit','retries_exhausted','failed','expired','outcome_unknown','key_reused')),
       CONSTRAINT surface_dead_letter_detail_bounded CHECK (char_length(detail) <= 2000),
       CONSTRAINT surface_dead_letter_counts CHECK (attempts >= 0 AND delivery_count >= 0),
       CONSTRAINT surface_dead_letter_answer CHECK ((answered_at IS NULL) = (answered_by IS NULL))
   );
   CREATE INDEX surface_dead_letter_open ON surface_dead_letter (surface, dead_lettered_at DESC)
       WHERE answered_at IS NULL;
   ```
   `surface_operation.result` always holds a JSON object, `{"value": <wire result>}`, never a
   bare scalar (`JsonColumn`'s rule, `specs/orm-tables.md` behaviour 2).
2. **`src/vibey/infrastructure/db/orm_models.py`**: `SurfaceOperationOrm` and
   `SurfaceDeadLetterOrm` (`VibeyOrmModel, table=True`), column-for-column with the SQL,
   declaring the three and five constraints and the partial index in `__table_args__`
   (copy `HumanGateOrm`, `:553-598`, and R08's `JobOutboxOrm` if it exists). Add both to
   `ORM_TABLE_MODELS` (`:678`) and to `__all__`, and update the comment's relation count.
3. **`tests/infrastructure/db/test_orm.py`**: `EXPECTED_TABLE_NAMES` (`:18`) gains
   `"surface_operation"` and `"surface_dead_letter"`. That is the only edit to that file.
4. If `tests/fakes/db_checks.py` exists (lane `fakes-db-unit-of-work`), add one predicate per
   new CHECK constraint, keyed by the constraint names above, so its
   `test_every_migration_check_is_modelled_or_declared` stays green.

## Where to change
- New `migrations/0015_surface_lanes.sql`.
- `src/vibey/infrastructure/db/orm_models.py`.
- `tests/infrastructure/db/test_orm.py` (the constant only), `tests/infrastructure/db/test_migrator.py` (append one test), `tests/fakes/db_checks.py` if present.

## Acceptance criteria
- [ ] A fresh database migrates through 0015; a second apply is a no-op; the checksum guard is unchanged.
- [ ] `test_orm_columns_match_every_migrated_relation` passes with both tables.
- [ ] The state CHECK refuses `'bogus'`; the reason CHECK refuses `'nope'`; the answer CHECK refuses `answered_at` without `answered_by`; a second row with the same `(surface, dedupe_key)` is refused.
- [ ] The file applies on PostgreSQL 14 (no `MERGE`, no 15+ syntax).
- [ ] The chaos test and every repository test pass unchanged; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_migrator.py` (integration by that directory's conftest):
- `test_surface_lanes_migration_adds_both_tables_and_their_checks` — insert one valid row in each through a raw connection from the fixture (tests may use asyncpg), then assert each CHECK and the unique constraint refuse a violating row.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Reading or writing either table (`surfaces-operation-repository`,
  `surfaces-dead-letter-repository`). `docs/plans/data-model.md` (`surfaces-docs-wave`).
  CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Do not push, open PRs
  or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `rmq-r08-dispatch-migration` (0014 must exist first; it also edits `orm_models.py` and `EXPECTED_TABLE_NAMES`).
- **Shares a file with:** `src/vibey/infrastructure/db/orm_models.py`, `tests/infrastructure/db/test_orm.py` (R08 and any later migration lane). Keep their models and names.
- **Must keep passing unchanged:** every test in `tests/infrastructure/db/` (the chaos test is protected), the PostgreSQL 14–18 compatibility set, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. `orm_models.py` is long: `edit_file` only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new Python file is the provenance comment, copied byte-for-byte from a sibling (a `.sql` file carries none, like its siblings).
  - Never hand-edit an applied migration; this lane only adds 0015.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
