# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Root test configuration — per-worker database via PostgreSQL template pattern.

Session startup creates ``vibey_test_template`` (migrated once, reused across
sessions; ``VIBEY_TEST_TEMPLATE_DB`` renames it) and clones it into
``vibey_test_<worker_id>`` for this process.
``VIBEY_TEST_DATABASE_URL`` is repointed so every downstream fixture and test
helper picks up the isolated per-worker database transparently.

The application connects as a restricted role, as a split production install does
(ADR-0055): ``VIBEY_PG_URL`` names ``vibey_test_app`` (``VIBEY_TEST_APP_ROLE``
renames it; an empty value falls back to one role for everything), which holds only
the declared grants. ``VIBEY_PG_MIGRATE_URL`` is never exported. So the whole suite
runs every application path under the grants production runs it under, and a query
that needs a privilege nobody declared fails here, as ``permission denied``.
``VIBEY_TEST_DATABASE_URL`` stays the owner's, for fixtures that set up or inspect
state the application itself never touches.
"""

import asyncio
import contextlib
import faulthandler
import getpass
import os
import signal
import sys
from pathlib import Path

import asyncpg
import pytest
from hypothesis import HealthCheck, settings

from tests.db_reaper import BackgroundReap, HoldMark, TestDatabaseHold, TestDatabaseReaper
from tests.db_roles import TestDatabaseRoles
from vibey.infrastructure.db.migrator import apply_migrations, discover_migrations

# The no-loss lane: `pytest -m noloss --hypothesis-profile=noloss`, the CI job "No-loss
# property suite (10,000 examples)". 10,000 is the definition of done in
# docs/plans/implementation-plan.md, and tests/domain/test_noloss_reference.py (protected)
# pins these values, so lowering them here fails that module instead of shrinking the
# suite. No deadline and no too_slow check: one example builds and gates a ledger of up to
# thirty events, and a slow CI runner is not a property failure. Loaded only when asked
# for -- every other run keeps Hypothesis' default profile. Never shadow it with a per-test
# `@settings(max_examples=...)`, which would override the profile for that test.
settings.register_profile(
    "noloss",
    max_examples=10_000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

# Every other run: Hypothesis' default example count, but no per-example deadline and no
# too_slow check, for the same reason as the no-loss lane -- a loaded machine is not a
# property failure. Under parallel suites (load average 60+) a 22 ms example took 253 ms
# and failed `test_every_dollar_the_budget_brake_sees_is_charged_somewhere` as "flaky"
# (2026-09-24). A test that genuinely needs a time bound declares it with @settings.
settings.register_profile(
    "vibey",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("vibey")

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
# The template is migrated from THIS checkout's migrations and then reused by
# every later session on the same server. Two checkouts whose migrations
# differ -- parallel worktrees, one carrying a migration the other lacks --
# would otherwise leak schema into each other's clones. Name it per checkout
# with VIBEY_TEST_TEMPLATE_DB; the default is the name it has always had.
_TEMPLATE_DB = os.environ.get("VIBEY_TEST_TEMPLATE_DB", "vibey_test_template")
_BASE_DSN: str | None = None
_ROLES = TestDatabaseRoles.from_environ(os.environ)
# This process's hold on its database (tests/db_reaper.py): taken before the database
# exists, released after it is dropped. A killed session's hold ends with its connection,
# which is how the reaper tells a leaked database from one in use. The database's mark names
# this process too, so a hold that ends while the process lives gives nothing away.
_HOLD: TestDatabaseHold | None = None
# The reap of other, dead sessions' databases, run beside this session by its controller.
_REAP: BackgroundReap | None = None


def _resolve_base_dsn() -> str:
    return os.environ.get(
        "_VIBEY_TEST_BASE_DSN",
        os.environ.get(
            "VIBEY_TEST_DATABASE_URL",
            f"postgresql://{getpass.getuser()}@localhost:5432/vibey_test",
        ),
    )


def _replace_dbname(dsn: str, dbname: str) -> str:
    base, _ = dsn.rsplit("/", 1)
    return f"{base}/{dbname}"


def _worker_id() -> str:
    return os.environ.get("PYTEST_XDIST_WORKER", "main")


# Drawn once per process, so _setup and _teardown name the same database; the
# pid says whose it was if a crashed run leaves it behind.
_LOCAL_RUN_ID = f"{os.getpid()}_{os.urandom(4).hex()}"


def _worker_db_name() -> str:
    # xdist hands each worker a per-run id. A serial (-n 0) run and the xdist
    # controller get none, and the old fixed fallback named every such process,
    # in every checkout on the server, vibey_test_main_main -- which each run's
    # startup terminated and dropped from under whichever run was using it.
    run_id = os.environ.get("PYTEST_XDIST_TESTRUNUID") or _LOCAL_RUN_ID
    return f"vibey_test_{_worker_id()}_{run_id}"


async def _setup(base_dsn: str) -> str:
    """Create template (if needed) and per-worker clone; return worker DSN."""
    admin_dsn = _replace_dbname(base_dsn, "postgres")
    wdb = _worker_db_name()

    conn = await asyncpg.connect(admin_dsn)
    try:
        # Serialise template creation + clone so no process connects to the
        # template while another clones from it.
        await conn.execute("SELECT pg_advisory_lock(hashtext($1))", _TEMPLATE_DB)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                _TEMPLATE_DB,
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{_TEMPLATE_DB}"')

            tmpl_conn = await asyncpg.connect(
                _replace_dbname(base_dsn, _TEMPLATE_DB),
            )
            try:
                migrations = discover_migrations(_MIGRATIONS_DIR)
                await apply_migrations(tmpl_conn, migrations)
                # Roles are cluster-wide; grants live in the database, so the clone
                # below inherits them from the template.
                await _ROLES.ensure(conn)
                await _ROLES.grant(tmpl_conn)
            finally:
                await tmpl_conn.close()

            # The hold comes first, so this database never exists unheld while its session
            # is alive. The mark names this process and machine, so a hold that ends while the
            # process lives still gives nothing away: the reaper keeps the database until the
            # process is gone.
            mark = HoldMark.this_process().text()  # before anything exists, so it cannot fail after
            global _HOLD
            _HOLD = TestDatabaseHold(base_dsn, wdb)
            _HOLD.start()
            # Drop-if-exists handles crashed prior runs (AC-14).
            await conn.execute(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = $1 AND pid <> pg_backend_pid()",
                wdb,
            )
            await conn.execute(f'DROP DATABASE IF EXISTS "{wdb}"')
            await conn.execute(
                f'CREATE DATABASE "{wdb}" TEMPLATE "{_TEMPLATE_DB}"',
            )
            await conn.execute(f"COMMENT ON DATABASE \"{wdb}\" IS '{mark}'")
        finally:
            await conn.execute(
                "SELECT pg_advisory_unlock(hashtext($1))",
                _TEMPLATE_DB,
            )
    finally:
        await conn.close()

    return _replace_dbname(base_dsn, wdb)


async def _teardown(base_dsn: str) -> None:
    wdb = _worker_db_name()
    admin_dsn = _replace_dbname(base_dsn, "postgres")
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            wdb,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{wdb}"')
    finally:
        await conn.close()
        if _HOLD is not None:
            _HOLD.release()


# Where SIGUSR1 sends this process's stacks. Kept open for the life of the process: the
# handler writes to the descriptor, and a closed one would dump nothing.
_STACKS_FILE: object = None


# Module-level rather than a class (ADR-0016's written reason): pytest resolves hooks by
# name at conftest scope, and this is called from one and by one meta test.
def _arm_stack_dump() -> None:
    """On SIGUSR1, dump every thread's stack, and keep running.

    The storm's push-gate reaper sends it to a hung suite before it kills the suite, so the
    kill leaves a record of what was stuck (tests/meta/test_a_hung_test_names_itself.py).
    With `VIBEY_PYTEST_STACKS_DIR` set -- `push_gate.py run` sets it -- the dump goes to one
    file per process there, because a worker's stderr is captured by pre-commit, which the
    reaper is about to kill with it. Without it, to stderr.
    """
    global _STACKS_FILE
    where = os.environ.get("VIBEY_PYTEST_STACKS_DIR")
    if where:
        Path(where).mkdir(parents=True, exist_ok=True)
        _STACKS_FILE = open(  # noqa: SIM115 - must outlive this call; see _STACKS_FILE
            Path(where) / f"pytest-{os.getpid()}.stacks", "a", encoding="utf-8"
        )
        faulthandler.register(signal.SIGUSR1, file=_STACKS_FILE, all_threads=True)
    else:
        faulthandler.register(signal.SIGUSR1, all_threads=True)


def pytest_configure(config: pytest.Config) -> None:
    global _BASE_DSN
    # First, so a hang in the database setup below is as legible as one in a test.
    _arm_stack_dump()
    _BASE_DSN = _resolve_base_dsn()
    os.environ["_VIBEY_TEST_BASE_DSN"] = _BASE_DSN
    # Once per session (the controller, or a serial run; never each xdist worker), clear
    # what killed sessions left on this server. In the background, so no run waits for it;
    # VIBEY_TEST_REAP=0 turns it off and VIBEY_TEST_REAP_LIMIT caps one session's drops.
    global _REAP
    if "PYTEST_XDIST_WORKER" not in os.environ and os.environ.get("VIBEY_TEST_REAP", "1") != "0":
        _REAP = BackgroundReap(
            TestDatabaseReaper(_BASE_DSN), limit=int(os.environ.get("VIBEY_TEST_REAP_LIMIT", "200"))
        )
        _REAP.start()
    worker_dsn = asyncio.run(_setup(_BASE_DSN))
    os.environ["VIBEY_TEST_DATABASE_URL"] = worker_dsn
    # Some integration tests exercise the application entry point directly, whose
    # production settings are VIBEY_PG_URL (the application role) and
    # VIBEY_PG_MIGRATE_URL (the owner). Point both at this worker's isolated database
    # so those tests cannot fall through to an unset configuration or a shared one.
    # The owner's DSN is never exported: only `vibey migrate` reads VIBEY_PG_MIGRATE_URL,
    # and the tests that run it set it for that one call.
    app_dsn = _ROLES.app_dsn(worker_dsn)
    os.environ["VIBEY_TEST_APP_DATABASE_URL"] = app_dsn
    os.environ["VIBEY_PG_URL"] = app_dsn
    os.environ.pop("VIBEY_PG_MIGRATE_URL", None)


def pytest_unconfigure(config: pytest.Config) -> None:
    if _BASE_DSN is not None:
        with contextlib.suppress(Exception):
            asyncio.run(_teardown(_BASE_DSN))
    if _REAP is not None:
        report = _REAP.finish()
        if report is not None and (report.dropped or report.errors):
            print(report.line(), file=sys.stderr)
