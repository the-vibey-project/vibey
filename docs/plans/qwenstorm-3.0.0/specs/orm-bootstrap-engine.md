## Title
refactor(bootstrap): build_app opens one AsyncEngine and no asyncpg pool

## Why
By this lane every repository takes the ORM seam (lanes `orm-ledger` … `orm-advisory-lock`)
and migrations run by URL through the family's engine factory (`orm-migrator-callers`,
`orm-migrator`). What is left in the composition root is the pool nobody uses any more
(`src/vibey/bootstrap.py:700-702`, `:953-954`) and the version-floor probe that still runs
`SHOW server_version_num` on it (`:704-708`). This lane removes both, so `build_app` opens
exactly one `AsyncEngine` (inside `PostgresOrm`, lane `orm-database-seam`) and
`bootstrap.py` no longer imports asyncpg (draft ADR `specs/ADR-orm.md`). It also replaces
the tests that fake the pool by patching `asyncpg.create_pool`
(`tests/test_bootstrap.py:79-111`; `tests/infrastructure/test_sovereign_surfaces.py:636`,
`:703`) with a substitution at a declared seam (sub-doctrine 9.b): `build_app` accepts the
ORM seam as an argument.

## Required behaviour
1. `build_app(*, url: str | None = None, config: VibeyConfig | None = None, orm: PostgresOrmInterface | None = None)`.
2. Order inside `build_app`:
   1. `migrator = PostgresMigrator.from_environ(os.environ)` (unchanged: a bad lock-wait
      setting still fails before anything touches the database, `tests/test_bootstrap.py:66-76`);
   2. `dsn = url or database_url()`;
   3. `database = orm if orm is not None else PostgresOrm.from_dsn(dsn)`;
      `owned = orm is None`;
   4. `try:` the version floor —
      `async with database.connect() as conn: server_version_num = await conn.scalar(select(func.current_setting("server_version_num")))`,
      then `parse_postgres_server_version` and `UnsupportedPostgresVersion` exactly as today;
      then `await migrator.apply_url(dsn, discover_migrations(migrations_dir()))`; then
      everything else as it is, every repository built on `database`;
   5. `finally: if owned: await database.dispose()`. An injected seam belongs to its caller.
3. `asyncpg.create_pool`, the `pool` variable, `if pool is None`, `await pool.close()` and
   `import asyncpg` are deleted from `bootstrap.py`. `AppResources.orm` is typed
   `PostgresOrmInterface`.
4. `grep -n "pool" src/vibey/bootstrap.py` shows no database pool (engine-selection "pool"
   words are unrelated and stay).
5. Behaviour is otherwise unchanged.

## Where to change
- `src/vibey/bootstrap.py`
- `tests/test_bootstrap.py`: `test_build_app_rejects_a_postgres_server_below_the_support_floor`
  (`:79-111`) — delete its `Connection`/`Acquire`/`Pool` fakes and the `monkeypatch.setattr`,
  and use `fake = FakeOrm(FakeResult(scalar="130023"))` (from `tests/infrastructure/orm/fakes.py`)
  with `build_app(url="postgresql://old/db", orm=fake)`; keep the `pytest.raises`; replace
  `assert pool.closed is True` with `assert not getattr(fake, "disposed", False)` (the caller
  owns an injected seam).
- `tests/infrastructure/test_sovereign_surfaces.py`, the two `build_app` tests (`:627-660`,
  `:676-720`): delete `_mock_pool()` use and the `patch("asyncpg.create_pool", …)` line, and
  pass `orm=FakeOrm(FakeResult(scalar="170000"))` to `build_app()`. Keep the migrator and
  `database_url` patches and every assertion. Delete `_mock_pool` if nothing else uses it.
- `tests/test_bootstrap.py` (new tests appended)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg" src/vibey/bootstrap.py` prints nothing.
- [ ] `grep -rn "create_pool" tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py` prints nothing.
- [ ] A server below the floor is refused before any migration runs (the fake's script is consumed by the version probe only).
- [ ] `build_app()` against the test database works with no asyncpg pool: the CLI, TUI and system suites pass.
- [ ] An injected seam is not disposed by `build_app`; a built one is.
- [ ] 100% branch coverage of `src/vibey/cli/` and `src/vibey/infrastructure/`; `bootstrap.py`'s new branches are exercised by the tests below.

## Tests to write first (TDD)
Append to `tests/test_bootstrap.py`:
- `test_build_app_probes_the_version_through_the_seam` (injected `FakeOrm(FakeResult(scalar="170000"))`, migrator patched as the sovereign tests patch it; the fake's recorded statement renders `current_setting`)
- `test_build_app_leaves_an_injected_seam_to_its_caller`
- `test_build_app_disposes_the_seam_it_built` (integration: after the context exits,
  `resources.orm.engine.pool.checkedout() == 0`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed: everything that builds the app
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py tests/cli tests/tui tests/system tests/infrastructure/test_cluster_preflight.py tests/infrastructure/test_operator_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- The queue-backend selection (`rmq-r17`); if it has landed, keep its branches and build its
  repositories on `database` too. Engine pool sizing as configuration keys (recorded as owed
  in the ADR). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
