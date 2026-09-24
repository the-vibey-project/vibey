## Title
test(preflight): cluster preflight connects through a declared connector, and 33 of its 37 tests leave the integration tier

## Why
`tests/infrastructure/test_cluster_preflight.py` has 37 tests, all marked `integration`
(`pytestmark`, `:31`). Most of them are pure: DSN qualification, workspace writability, and
the engine-auth verdicts (`:72-258`). Only the database checks touch PostgreSQL:
- `check_database` (`src/vibey/infrastructure/cluster_preflight.py:244-268`) calls
  `asyncpg.connect(dsn)` directly. Three tests patch
  `vibey.infrastructure.cluster_preflight.asyncpg.connect` (`:287`, `:309`, `:333`).
- `check_migrations` (`:271-287`) reads `SELECT version FROM schema_migration`.

The database surface is tiny: connect, `SHOW server_version_num`, one `SELECT`, and `close`.
An in-memory probe server can answer it honestly. It holds a server version and a set of
applied migrations, and refuses any statement it does not know.

## Required behaviour
1. **The connector seam.** Add `src/vibey/infrastructure/db/interfaces/connector_interface.py`
   with `@runtime_checkable class PostgresConnectorInterface(Protocol)`:
   `async def connect(self, dsn: str) -> Any`. The production `ASYNCPG_CONNECTOR: Final`
   (`db/connector.py`, a stateless class) calls `asyncpg.connect`. Add it to `DRIVER_SEAMS`.
   If `fakes-db-sql-transcripts` has already added this seam, reuse it unchanged.
2. **`check_database(dsn, *, connector: PostgresConnectorInterface = ASYNCPG_CONNECTOR)`.**
   `ClusterPreflight.__init__(self, *, engine_auth, connector=ASYNCPG_CONNECTOR)` passes it on.
   The messages and the connection hand-back do not change.
3. **`tests/fakes/postgres_probe.py`**:
   - `class InMemoryPostgresServer`:
     - `__init__(self, *, server_version_num: str | int = "170002", applied: Iterable[str] = (), reachable: bool = True, version_error: Exception | None = None, migrations_error: Exception | None = None)`;
     - `connector()` returns a `PostgresConnectorInterface`. When `reachable` is false, it
       raises `OSError("connection refused")`, as asyncpg's connect does;
   - its connection's `fetchval("SHOW server_version_num")` returns the version, or raises
     `version_error`;
   - `fetch("SELECT version FROM schema_migration")` returns `[{"version": v} ...]`, or raises
     `migrations_error`;
   - any other SQL raises `AssertionError(f"probe server does not answer: {sql}")`;
   - `close()` sets `closed`.
   Register it for `PostgresConnectorInterface`.
4. **Split the marks.** Remove the module `pytestmark`:
   - the pure tests (`:72-258`) are unmarked;
   - the database tests use `InMemoryPostgresServer` and are unmarked: unreachable, unsupported,
     unreadable, closes on version failure, pending migrations, no migration files, no
     `schema_migration` table (`migrations_error=asyncpg.UndefinedTableError(...)`). The three
     `monkeypatch.setattr` calls go;
   - `test_full_preflight_against_a_live_database` (`:415`) stays, marked `integration`: it is
     the real thing. Add `test_full_preflight_against_the_probe_server`, which covers the same
     path in the default tier;
   - `test_migrations_report_applied_versions_after_bootstrap` and
     `test_migrations_flag_a_version_the_database_has_not_seen` get `InMemoryPostgresServer`
     twins built from `discover_migrations(migrations_dir())`, and their originals stay
     `integration`.
5. Lower the file's baseline entry.

## Where to change
- New `src/vibey/infrastructure/db/interfaces/connector_interface.py`, `src/vibey/infrastructure/db/connector.py`;
  `src/vibey/infrastructure/db/interfaces/__init__.py`; `src/vibey/infrastructure/cluster_preflight.py`.
- New `tests/fakes/postgres_probe.py`, `tests/fakes/test_fake_postgres_probe.py`.
- `tests/infrastructure/test_cluster_preflight.py`, `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/test_cluster_preflight.py`
      passes with PostgreSQL stopped, and runs at least 33 tests plus the new twins.
- [ ] `grep -c "monkeypatch.setattr" tests/infrastructure/test_cluster_preflight.py` prints `0`.
- [ ] 100% `infrastructure/` coverage from the default tier for `cluster_preflight.py`.

## Tests to write first (TDD)
`tests/fakes/test_fake_postgres_probe.py`:
- `test_probe_answers_version_and_migrations`
- `test_probe_refuses_unknown_sql`
- `test_unreachable_probe_raises_oserror`
- `test_asyncpg_connector_satisfies_the_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/test_cluster_preflight.py tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `vibey doctor --cluster`'s CLI wiring (the CLI lanes). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-bootstrap-seam`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the chart's cluster-smoke contracts (unaffected), and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
