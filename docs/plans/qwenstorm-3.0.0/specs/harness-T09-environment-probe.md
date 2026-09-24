## Title
feat(test-harness): probe the environment a test run is keyed by

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:279-282`) keys a run by "the
environment". Draft ADR-0045 §5 names its parts: the interpreter; the installed distributions
(what the run imports; `uv.lock` is tracked, so it is already in the tree, and a stale venv is
caught only here); the test database's server version; and the digests of the pass-through
variables. The probe runs in the *requester's* process, which is the interpreter the tests run
in. A database that cannot be reached is keyed `unreachable`, so the failure it causes stops
matching once the database is back.

The operator's standard (2026-09-22, `STORM-CONTEXT.md`) is **ORM always, behind interfaces**:
no new `import asyncpg` and no new SQL string in `src/vibey`. Lane orm-raw-sql-guard makes that
mechanical: an import-linter contract refuses `asyncpg` outside the notifier, and
`tests/meta/test_raw_sql_budget.py` counts any string starting `SHOW …`. So the database version
is read through the ORM seam, `PostgresOrm.from_dsn(dsn)` and its `connect()` (lane
orm-database-seam, `src/vibey/infrastructure/db/orm.py`), from
`AsyncConnection.dialect.server_version_info`, which SQLAlchemy fills on the first connection. No
SQL text appears in vibey's source. Amendment A6/A7: the one test against a real database is
`integration`, because `tests/conftest.py` no longer exports `VIBEY_TEST_DATABASE_URL` to every
session (lane fakes-harness-decouple).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/environment_probe.py`:
1. **`OrmDatabaseVersionReader(*, orm_factory: Callable[[str], PostgresOrmInterface] | None = None)`**,
   the default factory being `PostgresOrm.from_dsn`.
   `async def version(self, dsn: str) -> str`: `orm = factory(dsn)`; then
   `async with orm.connect() as conn: info = conn.dialect.server_version_info`, with
   `await orm.dispose()` in a `finally`. Return `".".join(str(part) for part in info)` when `info`
   is a non-empty tuple, else `"unknown"`. Exceptions propagate (the probe maps them).
2. **`EnvironmentProbe(*, pass_env: EnvNamePatternsInterface, database_env: str, versions: DatabaseVersionReaderInterface | None = None, distributions: Callable[[], Iterable[importlib.metadata.Distribution]] | None = None, timeout_seconds: float = 2.0)`**.
   Defaults: `OrmDatabaseVersionReader()` and `importlib.metadata.distributions`.
   - `python_identity(self) -> str`:
     `f"{sys.implementation.name}-{platform.python_version()}-{sys.platform}-{platform.machine()}"`.
   - `distributions_digest(self) -> str`: one line per distribution, `f"{name}=={dist.version}"`,
     where `name` is `dist.metadata["Name"]` lower-cased with each run of `-`, `_` and `.` replaced
     by `-`. Skip distributions whose name is missing or empty; de-duplicate and sort the lines;
     return the sha256 hex of `"\n".join(lines)`.
   - `async def database_version(self, environ: Mapping[str, str]) -> str`:
     - `"unset"` when `database_env == ""`, or the variable is missing or blank;
     - otherwise `await asyncio.wait_for(self._versions.version(dsn), self._timeout_seconds)`;
     - any exception, including a timeout, gives `"unreachable"`.
   - `async def probe(self, environ: Mapping[str, str]) -> tuple[TestEnvironment, tuple[tuple[str, str], ...]]`:
     `values = pass_env.select(environ)`, then return
     `(TestEnvironment.from_values(python=self.python_identity(), distributions=self.distributions_digest(), database=await self.database_version(environ), values=values), values)`.
3. **The interface** `src/vibey/infrastructure/test_harness/interfaces/environment_probe_interface.py`
   declares `@runtime_checkable` `EnvironmentProbeInterface` (`python_identity`,
   `distributions_digest`, `database_version`, `probe`) and `DatabaseVersionReaderInterface`
   (`async version(dsn: str) -> str`).
4. **The fake**, new `tests/fakes/harness_environment.py`:
   `ScriptedDatabaseVersionReader(version: str = "17.2", *, fail: BaseException | None = None, delay_seconds: float = 0.0)`
   implements `DatabaseVersionReaderInterface` in memory: `version(dsn)` appends `dsn` to
   `self.dsns`, sleeps `delay_seconds` when positive (`asyncio.sleep`), raises `fail` when set,
   and otherwise returns the scripted version. Its zero-argument construction is valid.
5. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry: `REGISTRY` of
   `FakeRegistration(port, build, note)`, `PENDING`, `DRIVER_SEAMS`), import the interface module
   and the fake module, then:
   - append `FakeRegistration(port=environment_probe_interface.DatabaseVersionReaderInterface, build=harness_environment.ScriptedDatabaseVersionReader, note="a scripted server version, failure or delay")` to `REGISTRY`;
   - append both `EnvironmentProbeInterface` and `DatabaseVersionReaderInterface` to `DRIVER_SEAMS`;
   - add `"EnvironmentProbeInterface": "fakes-test-harness"` to `PENDING` (fakes-test-harness registers `ScriptedEnvironmentProbe`).

## Where to change
- New `src/vibey/infrastructure/test_harness/environment_probe.py` and its interface module.
- New `tests/fakes/harness_environment.py`; `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_environment_probe.py`.

## Acceptance criteria
- [ ] The distributions digest does not depend on iteration order, and changes when one version changes.
- [ ] `unset`, `unreachable` (a failing reader, and a reader slower than `timeout_seconds`) and a version string are each produced.
- [ ] Only `pass_env` names are selected, and the returned values are the raw values.
- [ ] `grep -n "asyncpg\|SHOW" src/vibey/infrastructure/test_harness/environment_probe.py` prints nothing.
- [ ] With `VIBEY_TEST_DATABASE_URL` set, `uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/test_harness/test_environment_probe.py` passes, and the version starts with a digit.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes (the reader fake satisfies its port's signatures and is not a stub).
- [ ] 100% coverage of `src/vibey/infrastructure/` in the default tier (the `OrmDatabaseVersionReader` lines are covered with an injected `orm_factory`, see the tests).

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_environment_probe.py`
(`from vibey.infrastructure.test_harness import environment_probe as ep`,
`from tests.fakes import harness_environment as fake_env`):
- `test_python_identity_format` (a regex)
- `test_distributions_digest_is_order_independent` (a plain `_Dist(name, version)` class with a `metadata` dict and a `version`)
- `test_distributions_digest_changes_with_a_version`
- `test_distributions_without_a_name_are_skipped`
- `test_database_unset` (parametrized: `database_env=""`, variable missing, variable blank)
- `test_database_unreachable_on_error_and_on_timeout` (`ScriptedDatabaseVersionReader(fail=OSError())` and `(delay_seconds=0.5)` with `timeout_seconds=0.1`)
- `test_database_version_from_the_scripted_reader`
- `test_orm_reader_formats_and_disposes`: `OrmDatabaseVersionReader(orm_factory=...)` with a plain
  in-test class that implements `connect()` as an async context manager yielding an object whose
  `dialect.server_version_info` is `(17, 2)`, and records `dispose()`; assert `"17.2"` and one
  dispose. A second case with `server_version_info = None` gives `"unknown"`.
- `test_database_version_against_the_test_database`: `@pytest.mark.integration`, skipped with
  `pytest.skip("VIBEY_TEST_DATABASE_URL is not set")` when the variable is unset; uses the real
  `OrmDatabaseVersionReader`.
- `test_probe_selects_only_pass_env_names`
- `test_probe_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Building requests (harness-T14a). The scripted probe fake (fakes-test-harness).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T01-test-run-key, harness-T05-test-harness-config, fakes-registry, orm-database-seam (`PostgresOrm.from_dsn`, `PostgresOrmInterface.connect`).
- **Files touched:** the two new source files, `tests/fakes/harness_environment.py` (new), `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only); `test_environment_probe.py` is later touched by fakes-harness-degrade, which finds the `integration` mark already present.
- **Must keep passing unchanged:** harness-T05's tests, `tests/fakes/*`, `tests/meta/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam (the constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out). A test that needs PostgreSQL is `integration` and skips without `VIBEY_TEST_DATABASE_URL`.
  - No new raw SQL and no `asyncpg` import in `src/vibey` (the ORM standard).
  - No test waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
