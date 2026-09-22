## Title
feat(projects): the project repository lists the newest projects, newest first, through the ORM seam and its in-memory twin

## Why
Issue #143 (rewrite: `issue-audit/updates/143.md`, "Proposed child issues" 1: `GET /projects`).
An API that lists projects needs a port that lists them, and none does: the whole-repository port
`ProjectRepository` (added by lane `fakes-projects` to `src/vibey/application/interfaces/projects.py`)
declares `create`, `get`, `get_latest` and `transition`, the exact methods of
`PostgresProjectRepository` (`src/vibey/infrastructure/db/project_repository.py:173-207`), and every
CLI command today reads one project at a time (`get_latest`, `main.py:722`, `:804`, `:845`). Lane
`orm-project` moves that repository onto the ORM seam; this lane adds the one read the API needs
on the same seam, with no raw SQL (operator standard, ADR draft `specs/ADR-orm.md`), and teaches
the in-memory twin the same ordering (sub-doctrine 9.b, `src/vibey_tools/gh/docs/doctrines.md:349`:
"the test double is the second [implementation], and it exists from the first day").
Lands after `orm-project` and `fakes-projects`.

## Required behaviour
1. `ProjectRepository` (`src/vibey/application/interfaces/projects.py`, as `fakes-projects` left it)
   gains, after `get_latest`:
   ```python
   async def list_recent(self, *, limit: int) -> tuple[ProjectRecord, ...]:
       """The newest `limit` projects, newest first: by `created_at`, then by id, both
       descending. `limit` below 1 raises ValueError."""
       ...
   ```
2. `PostgresProjectRepository.list_recent(self, *, limit: int) -> tuple[ProjectRecord, ...]`
   (`src/vibey/infrastructure/db/project_repository.py`, directly after `get_latest`):
   - `limit < 1` raises `ValueError(f"limit must be at least 1, got {limit}")` before any I/O;
   - otherwise, inside `async with self._orm.connect() as conn:` exactly as `get_latest` does after
     `orm-project`, execute
     `select(PROJECT).order_by(PROJECT.c["created_at"].desc(), PROJECT.c["id"].desc()).limit(limit)`
     and return `tuple(self._rows.to_record(row) for row in result.mappings().all())`.
   No `text()`, no SQL string, no `import asyncpg`.
3. `InMemoryProjectRepository.list_recent(self, *, limit: int) -> tuple[ProjectRecord, ...]`
   (`tests/fakes/projects.py`, lane `fakes-projects`): the same `ValueError` for `limit < 1`;
   otherwise the stored records sorted by `(record.created_at, str(record.project_id))` in
   descending order, the first `limit` of them, as a tuple. Append `"list_recent"` to `self.calls`
   like every other method of the fake. (PostgreSQL orders `uuid` bytewise, which is the order of
   its canonical lowercase text, so the two agree.)

## Where to change
- `src/vibey/application/interfaces/projects.py` (one method on `ProjectRepository`).
- `src/vibey/infrastructure/db/project_repository.py` (one method; copy `get_latest`'s body shape).
- `tests/fakes/projects.py` (one method).
- Append tests to `tests/fakes/test_fake_projects.py` and `tests/infrastructure/db/test_project_repository.py`.
Use `edit_file` for every change; the first line of each file stays the provenance header.

## Acceptance criteria
- [ ] `tests/fakes/test_port_parity.py` passes: the fake's `list_recent` signature matches the port's
      (keyword-only `limit`), and it is not a stub.
- [ ] `grep -n "text(\|exec_driver_sql\|import asyncpg" src/vibey/infrastructure/db/project_repository.py` prints nothing.
- [ ] The PostgreSQL test and the fake test assert the same order for the same three projects.
- [ ] 100% branch coverage of `src/vibey/infrastructure/` and `src/vibey/application/`.

## Tests to write first (TDD)
Append to `tests/fakes/test_fake_projects.py` (no database; `FakeClock` from `tests/fakes/system.py`,
lane `fakes-observability`):
- `test_list_recent_is_newest_first_and_bounded` — `clock = FakeClock()`,
  `repo = InMemoryProjectRepository(clock=clock)`; create `a`, `b`, `c` at `tmp_path / "a"`, `/ "b"`,
  `/ "c"`, calling `clock.advance(timedelta(seconds=1))` between creates; `list_recent(limit=2)`
  names `("c", "b")`; `list_recent(limit=10)` names `("c", "b", "a")`.
- `test_list_recent_orders_a_tie_by_id` — two projects created without advancing the clock come back
  ordered by `str(project_id)` descending.
- `test_list_recent_refuses_a_limit_below_one` — `pytest.raises(ValueError, match="limit must be at least 1, got 0")`.
Append to `tests/infrastructure/db/test_project_repository.py` (integration: the `migrated_pool`
fixture; build the repository as the file's other tests do, `PostgresProjectRepository(migrated_pool)`):
- `test_list_recent_reads_newest_first_through_the_seam` — create `first`, `second`, `third` at
  `tmp_path / "a"`, `/ "b"`, `/ "c"`; `[p.name for p in await repo.list_recent(limit=2)] == ["third", "second"]`;
  `await repo.list_recent(limit=5)` has three records.
- `test_list_recent_refuses_a_limit_below_one_before_reading` — `pytest.raises(ValueError)` for `limit=0`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes/test_fake_projects.py tests/fakes/test_port_parity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_project_repository.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/infrastructure tests/application tests/fakes
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- Paging by cursor, filtering by phase, or any other listing; the API itself (`roadmap-143-api-read-projects-p3`, `-p4`).
- The other repositories; the migrations (no schema change: `project.created_at` exists,
  `migrations/0001_project.sql`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the agent-surface trees. Do not
  push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
