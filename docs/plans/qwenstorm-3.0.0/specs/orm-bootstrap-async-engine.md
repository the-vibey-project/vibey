## Title
feat(bootstrap): the family's database layer builds async SQLAlchemy engines

## Why
vibey's persistence moves onto SQLAlchemy 2 async over the asyncpg driver (draft ADR:
`specs/ADR-orm.md`). The family already owns the relational database layer:
`vibey_bootstrap.db` (`src/vibey_tools/bootstrap/vibey_bootstrap/db/__init__.py:22-60`) builds
**sync** engines only (`create_engine_from_env`, `get_engine`). Sub-doctrine 10.e
(`doctrines.md:417`) says a gap in the family is closed by teaching ours, not by building a
parallel one in vibey — and vibey's own engine builder today is exactly such a parallel
copy (`src/vibey/infrastructure/db/orm.py:23-29`, `_asyncpg_url`, and `:41`,
`create_async_engine`). This lane adds the async half to the family, as a class with its
interface (9.b), without changing the sync API. vibey adopts it in `orm-database-seam`.

## Required behaviour
1. New class `AsyncEngineFactory` in `vibey_bootstrap/db/async_engine.py`:
   - `__init__(self, creator: Callable[..., Any] | None = None) -> None`. `creator` is the
     function that builds the engine. `None` means `sqlalchemy.ext.asyncio.create_async_engine`,
     imported **lazily inside `create`**, in the same style as `create_engine_from_env`
     (`db/__init__.py:24`), so importing the module needs no SQLAlchemy.
   - `url(self, dsn: str) -> str`: `postgres://…` and `postgresql://…` become
     `postgresql+asyncpg://…`; any other string (including one that already names a driver)
     is returned unchanged.
   - `create(self, dsn: str, **options: Any) -> Any`: calls
     `creator(self.url(dsn), **merged)` where `merged` is `{"pool_pre_ping": True}` updated
     with `options` (the caller wins). Returns what the creator returned (an `AsyncEngine`).
     It never connects.
   - `from_env(self, *, dsn_env: str = "DATABASE_URL", **options: Any) -> Any`: reads the DSN
     with `vibey_bootstrap.failclose.require_env(dsn_env)` (so a missing variable raises
     `ConfigurationError`, like the sync builder) and returns `self.create(dsn, **options)`.
2. A module-level default instance `ASYNC_ENGINES = AsyncEngineFactory()`, with a one-line
   comment saying it is stateless so one shared instance serves every caller.
3. New interface `AsyncEngineFactoryInterface` in
   `vibey_bootstrap/db/interfaces/async_engine_interface.py`, an `ABC` with the three
   abstract methods above (the family's interface style: copy
   `vibey_bootstrap/services/interfaces/telemetry_manager_interface.py`). `AsyncEngineFactory`
   subclasses it. `vibey_bootstrap/db/interfaces/__init__.py` re-exports it.
4. `vibey_bootstrap.db.interfaces` is added to `[tool.setuptools] packages` in
   `src/vibey_tools/bootstrap/pyproject.toml`, directly after `"vibey_bootstrap.db.migrations"`.
5. `vibey_bootstrap/db/__init__.py` and `vibey_bootstrap/db/outbox.py` are unchanged.

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/async_engine.py` (new)
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/interfaces/__init__.py` (new)
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/interfaces/async_engine_interface.py` (new)
- `src/vibey_tools/bootstrap/pyproject.toml` (the one `packages` line)
- `src/vibey_tools/bootstrap/test/db/test_async_engine.py` (new)
Do not add or change any dependency or extra: `sqlalchemy>=2.0` is already in the `db`
extra, and vibey's own `pyproject.toml` already carries `sqlalchemy[asyncio]` and `asyncpg`.
Changing an extra would change `uv.lock`.

## Acceptance criteria
- [ ] `AsyncEngineFactory().url("postgresql://u@h/db") == "postgresql+asyncpg://u@h/db"`, and the same for `postgres://`; `"postgresql+asyncpg://u@h/db"` and `"sqlite:///x"` come back unchanged.
- [ ] With a recording creator, `create("postgresql://u@h/db", pool_size=3)` calls it once with `("postgresql+asyncpg://u@h/db", pool_pre_ping=True, pool_size=3)`, and `pool_pre_ping=False` from the caller wins.
- [ ] `from_env(dsn_env="VIBEY_TEST_ASYNC_DSN")` with the variable unset raises `ConfigurationError`.
- [ ] Against a real PostgreSQL (marked `integration`, skipped unless `VIBEY_TEST_DATABASE_URL` is set and `asyncpg` imports), the default factory's engine runs `select(1)` and is disposed.
- [ ] The vibey-bootstrap suite keeps its 100% line floor (`fail_under = 100`, `pyproject.toml:402`) with only the non-integration tests (the recording creator covers every line).

## Tests to write first (TDD)
`src/vibey_tools/bootstrap/test/db/test_async_engine.py`:
- `test_url_names_the_asyncpg_driver_for_both_postgres_schemes`
- `test_url_leaves_any_other_url_alone`
- `test_create_merges_pool_pre_ping_under_the_callers_options` (a creator that records its args and returns a sentinel)
- `test_create_returns_what_the_creator_built`
- `test_from_env_reads_the_named_variable` (monkeypatch.setenv is fine here: it sets data, it does not patch an import)
- `test_from_env_refuses_a_missing_variable`
- `test_the_factory_is_its_declared_seam` (`isinstance(ASYNC_ENGINES, AsyncEngineFactoryInterface)`)
- `test_the_default_engine_talks_to_postgres` (`@pytest.mark.integration`; `pytest.importorskip("asyncpg")`; skip unless `VIBEY_TEST_DATABASE_URL`; `async with engine.connect() as conn: assert (await conn.execute(select(1))).scalar() == 1`; `await engine.dispose()`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/db)
    (cd src/vibey_tools/bootstrap && VIBEY_TEST_DATABASE_URL=${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test} uv run python -m pytest -q -p no:cacheprovider --no-cov -m integration test/db/test_async_engine.py)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
The fourth command is the whole suite: the 100% line floor is enforced by the tenant's own
pytest `addopts`, so a partial run needs `--no-cov`. Formatting is the root `ruff format`
(it covers `src/**`); do not run black on this tenant.

## Out of scope
- vibey (`src/vibey/**`) — `orm-database-seam` adopts this factory.
- The sync API, the outbox (`rmq-r05-async-outbox` owns `outbox.py`), Alembic.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
