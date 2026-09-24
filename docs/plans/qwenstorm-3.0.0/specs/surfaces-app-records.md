## Title
feat(bootstrap): AppResources carries the surface-operation and dead-letter stores, PostgreSQL in production and in memory in the test app

## Why
Draft ADR-0047 §9 (`specs/ADR-surface-lanes.md`): `vibey surface dead-letters` "reads PostgreSQL,
so it works while a lane is down", and every lane host needs the two stores
(`surfaces-operation-repository`, `surfaces-dead-letter-repository`). Persistence is built in
one place — the composition root's persistence bundle (`build_app`, and after lane
`fakes-bootstrap-seam` its `PostgresResourcesFactory` and `PersistenceInterface`) — from the ORM
seam `build_app` hands out (lane `orm-app-resources`, `AppResources.orm`). The test app
(`tests/fakes/app.py`, `InMemoryResourcesFactory`) must offer the in-memory stores
(`surfaces-records-fakes`), so the CLI and composition tests need no database (draft amendment
A1). Part of ADR-0047 lanes S26–S28.

## Required behaviour
1. **`AppResources`** (`src/vibey/bootstrap.py`) gains two fields, before any field that has a
   default: `surface_operations: SurfaceOperationRepositoryInterface` and
   `surface_dead_letters: SurfaceDeadLetterRepositoryInterface`.
2. **Production.** Where `build_app` builds its PostgreSQL repositories (inline, or inside
   `PostgresResourcesFactory` when `fakes-bootstrap-seam` has landed), build
   `PostgresSurfaceOperationRepository(orm)` and `PostgresSurfaceDeadLetterRepository(orm)` from
   the same `orm`, and pass them through. With the factory, add both fields to
   `PersistenceInterface` (`src/vibey/bootstrap_interface.py`) and to the factory's bundle.
3. **`AppResourcesInterface`** (`bootstrap_interface.py`) declares both as read-only properties
   typed by their interfaces.
4. **The test app.** In `tests/fakes/app.py`, `InMemoryResourcesFactory` builds one
   `InMemorySurfaceOperationRepository()` and one `InMemorySurfaceDeadLetterRepository()` per
   `InMemoryPersistence`, exposed on `factory.persistence` for seeding and assertions.
5. Nothing else in `build_app` changes.

## Where to change
- `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`, `tests/fakes/app.py`.
- Append to `tests/test_bootstrap.py` and to `tests/fakes/test_fake_app.py`.

## Acceptance criteria
- [ ] `async with InMemoryApp().open_app() as resources:` gives in-memory stores that the test can seed through `factory.persistence` and read back through `resources`.
- [ ] Integration: `async with build_app() as resources:` gives the two PostgreSQL repositories; a dead letter recorded through `resources.surface_dead_letters` is read back by a second `build_app()`.
- [ ] `isinstance(resources, AppResourcesInterface)` still holds for both apps.
- [ ] `mypy --strict src/vibey` clean; the whole CLI and system suites pass unchanged.

## Tests to write first (TDD)
Append to `tests/fakes/test_fake_app.py` (no service):
- `test_the_in_memory_app_offers_the_surface_stores`
Append to `tests/test_bootstrap.py` (integration: it builds the app against PostgreSQL):
- `test_build_app_offers_the_surface_stores_over_the_orm`
- `test_app_resources_still_satisfy_their_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The surface composition (`surfaces-composition`); the CLI (`surfaces-cli-dead-letters`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-records-fakes`, `orm-app-resources` (`AppResources.orm`), `fakes-bootstrap-seam` (`PersistenceInterface`, `InMemoryResourcesFactory`).
- **Shares a file with:** `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py` (R02 → T15 → R17 → T25 → R27 → R28 → T26 and the ORM and fakes lanes), `tests/fakes/app.py`. Keep every field they added.
- **Must keep passing unchanged:** `tests/test_bootstrap.py`, `tests/cli/*`, `tests/system/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. `bootstrap.py` is long: `edit_file` only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Production code reaches PostgreSQL only through `PostgresOrmInterface`.
  - Substitute only at a declared seam (`build_app(resources_factory=...)`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
