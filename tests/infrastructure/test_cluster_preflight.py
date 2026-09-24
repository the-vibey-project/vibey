# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Cluster preflight checks.

The database arms run against real Postgres, never a mock: a check whose
whole job is to notice a misconfigured connection is worthless if the
connection is faked.
"""

import os
from pathlib import Path

import asyncpg
import pytest

from tests.db_roles import TestDatabaseRoles
from vibey.bootstrap import build_app, migrations_dir
from vibey.domain.engine import EngineId
from vibey.infrastructure.cluster_preflight import (
    ENGINE_API_KEY_ENVS,
    ClusterCheck,
    ClusterPreflight,
    EngineAuthCheck,
    all_ok,
    check_database,
    check_dsn_resolves_cluster_wide,
    check_migrations,
    check_not_root,
    check_workspace_writable,
)
from vibey.infrastructure.interfaces import ClusterPreflightInterface, EngineAuthCheckInterface

pytestmark = pytest.mark.integration


def _test_dsn() -> str:
    return os.environ.get(
        "VIBEY_TEST_DATABASE_URL",
        f"postgresql://{os.environ.get('USER', 'postgres')}@localhost:5432/vibey_test",
    )


# An unroutable port on loopback: refused immediately rather than hanging.
_DEAD_DSN = "postgresql://nobody@127.0.0.1:1/nothing"


def _every_binary(binary: str) -> str:
    """The image since ADR-0037: one wheel, every runner's console script on PATH."""
    return f"/app/.venv/bin/{binary}"


def _no_binary(_binary: str) -> None:
    return None


_EVERY_KEY = {
    "ANTHROPIC_API_KEY": "x",
    "OPENAI_API_KEY": "x",
    "CURSOR_API_KEY": "x",
    "GOOGLE_API_KEY": "x",
}


@pytest.mark.parametrize(
    ("dsn", "expected_ok"),
    [
        ("postgresql://u:p@db.ns.svc.cluster.local:5432/vibey", True),
        ("postgresql://u:p@localhost:5432/vibey", True),
        ("postgresql://u:p@10.96.0.10:5432/vibey", True),
        ("postgresql://u:p@[::1]:5432/vibey", True),
        ("postgresql://u:p@vibey-postgres:5432/vibey", False),
    ],
)
def test_dsn_qualification_is_judged_by_cross_namespace_resolvability(
    dsn: str, expected_ok: bool
) -> None:
    """The bare-name case is the one that shipped: it works for the worker,
    which is in the namespace, and fails for KEDA's operator, which is not."""
    assert check_dsn_resolves_cluster_wide(dsn).ok is expected_ok


def test_dsn_without_a_host_is_a_failure_not_a_crash() -> None:
    check = check_dsn_resolves_cluster_wide("postgresql:///vibey")
    assert not check.ok
    assert "no host" in check.detail


def test_bare_host_failure_names_the_fix() -> None:
    check = check_dsn_resolves_cluster_wide("postgresql://u@vibey-postgres:5432/v")
    assert "svc" in check.detail


def test_root_fails_and_any_other_uid_passes() -> None:
    assert not check_not_root(0).ok
    assert check_not_root(10001).ok


def test_workspace_writable(tmp_path: Path) -> None:
    assert check_workspace_writable(tmp_path).ok


def test_workspace_unwritable_reports_the_reason(tmp_path: Path) -> None:
    """A read-only or wrongly-owned volume fails at the first worktree,
    long after the pod reports Ready."""
    check = check_workspace_writable(tmp_path / "does-not-exist")
    assert not check.ok
    assert "does-not-exist" in check.detail


def test_the_default_chart_install_passes_although_every_engine_ships() -> None:
    """The regression this check had after ADR-0037: the one wheel puts all five
    paid engines on PATH, so a default install (`--provider scripted`, no
    `worker.engines`, no keys) -- the install CI deploys -- reported FAIL for
    engines the worker was never asked to use."""
    check = EngineAuthCheck(which=_every_binary).check({})
    assert check.ok, check.detail
    assert "nothing required" in check.detail
    assert "--provider scripted" in check.detail
    assert "5 engine binaries on PATH, none with an API key" in check.detail
    # The one fact a bare PASS would hide: nothing engine-driven can run.
    assert "no engine-driven (BUILD) job can run" in check.detail


def test_an_image_without_engine_binaries_passes_the_same_way() -> None:
    check = EngineAuthCheck(which=_no_binary).check({})
    assert check.ok
    assert "0 engine binaries on PATH" in check.detail


def test_without_an_allow_list_the_verdict_names_what_can_and_cannot_authenticate() -> None:
    check = EngineAuthCheck(which=_every_binary).check({"ANTHROPIC_API_KEY": "x"})
    assert check.ok
    assert "API key present: claudeloop" in check.detail
    assert "without one: agyloop, codexloop, cursorloop" in check.detail
    assert "--engines" in check.detail


def test_without_an_allow_list_every_key_present_names_no_gap() -> None:
    check = EngineAuthCheck(which=_every_binary).check(_EVERY_KEY)
    assert check.ok
    assert "API key present: agyloop, claudeloop, codexloop, cursorloop" in check.detail
    assert "without one: opencode" in check.detail


def test_without_an_allow_list_can_report_every_engine_keyed() -> None:
    """The port remains generic when a deployment supplies an OpenCode config secret."""
    api_key_envs = {**ENGINE_API_KEY_ENVS, EngineId.OPENCODE: ("OPENCODE_CONFIG",)}
    check = EngineAuthCheck(which=_every_binary, api_key_envs=api_key_envs).check(
        {**_EVERY_KEY, "OPENCODE_CONFIG": "mounted"}
    )
    assert check.ok
    assert "without one" not in check.detail


def test_an_allow_listed_engine_without_credentials_fails() -> None:
    """Subscription login is a TTY flow; in a cluster an engine the worker was
    told to use, with no API key, can never authenticate."""
    engines = frozenset({EngineId.CLAUDELOOP})
    check = EngineAuthCheck(which=_every_binary, allow_list=engines).check({})
    assert not check.ok
    assert "installed but unauthenticated: claudeloop" in check.detail
    assert "engineAuth.keys" in check.detail


def test_only_the_allow_list_is_judged() -> None:
    """codexloop has no key either, but the worker was not told to use it."""
    engines = frozenset({EngineId.CLAUDELOOP})
    check = EngineAuthCheck(which=_every_binary, allow_list=engines).check(
        {"ANTHROPIC_AUTH_TOKEN": "x"}
    )
    assert check.ok, check.detail
    assert check.detail == "1 engine(s) this worker uses: claudeloop; every API key present"


def test_an_allow_listed_engine_missing_from_path_fails() -> None:
    engines = frozenset({EngineId.CODEXLOOP})
    check = EngineAuthCheck(which=_no_binary, allow_list=engines).check(_EVERY_KEY)
    assert not check.ok
    assert check.detail == "required but not on PATH: codexloop"


def test_missing_and_unauthenticated_are_reported_together() -> None:
    def only_claude(binary: str) -> str | None:
        return f"/bin/{binary}" if binary == "claudeloop" else None

    engines = frozenset({EngineId.CLAUDELOOP, EngineId.CODEXLOOP})
    check = EngineAuthCheck(which=only_claude, allow_list=engines).check({})
    assert not check.ok
    assert check.detail.startswith("required but not on PATH: codexloop; ")
    assert "installed but unauthenticated: claudeloop" in check.detail


def test_every_allow_listed_engine_authenticated_passes() -> None:
    engines = frozenset(EngineId(e) for e in ("claudeloop", "codexloop", "cursorloop", "agyloop"))
    check = EngineAuthCheck(which=_every_binary, allow_list=engines).check(_EVERY_KEY)
    assert check.ok
    assert "4 engine(s) this worker uses" in check.detail


def test_an_allow_listed_engine_that_takes_no_key_is_judged_on_presence_alone() -> None:
    """qwenloop runs a local model; there is no API key for it to lack."""
    engines = frozenset({EngineId.QWENLOOP})
    check = EngineAuthCheck(which=_every_binary, allow_list=engines).check({})
    assert check.ok, check.detail
    assert "(qwenloop takes no API key)" in check.detail


def test_the_claudeloop_provider_requires_claudeloop_without_an_allow_list() -> None:
    """DESIGN runs claudeloop as a subprocess under `--provider claudeloop`,
    whatever the BUILD allow-list says."""
    check = EngineAuthCheck(which=_every_binary, provider="claudeloop").check({})
    assert not check.ok
    assert "installed but unauthenticated: claudeloop" in check.detail


def test_the_provider_engine_joins_the_allow_list() -> None:
    engines = frozenset({EngineId.CODEXLOOP})
    check = EngineAuthCheck(which=_every_binary, allow_list=engines, provider="claudeloop").check(
        {"ANTHROPIC_API_KEY": "x", "CODEX_API_KEY": "x"}
    )
    assert check.ok
    assert "2 engine(s) this worker uses: claudeloop, codexloop" in check.detail


def test_the_qwenloop_provider_requires_no_engine() -> None:
    """It talks to a local Ollama over HTTP, not through the qwenloop binary."""
    check = EngineAuthCheck(which=_every_binary, provider="qwenloop").check({})
    assert check.ok
    assert "--provider qwenloop: nothing required" in check.detail


def test_an_unknown_provider_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match="provider must be one of"):
        EngineAuthCheck(which=_every_binary, provider="gpt")


def test_built_from_the_workers_flags_spelled_as_the_worker_takes_them() -> None:
    check = EngineAuthCheck.for_worker(
        engines="claudeloop, codexloop", provider=None, which=_every_binary
    ).check({"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x"})
    assert check.detail.startswith("2 engine(s) this worker uses: claudeloop, codexloop")


def test_an_empty_engines_flag_means_no_allow_list_as_it_does_for_the_worker() -> None:
    """The chart omits --engines when worker.engines is "", and the worker
    reads an empty value as unset."""
    check = EngineAuthCheck.for_worker(engines="", provider="scripted", which=_every_binary)
    assert "nothing required" in check.check({}).detail


def test_an_unknown_engine_in_the_flag_is_refused() -> None:
    with pytest.raises(ValueError, match="not a valid EngineId"):
        EngineAuthCheck.for_worker(engines="claudeloop,gpt", provider=None, which=_every_binary)


def test_the_classes_satisfy_their_declared_interfaces() -> None:
    engine_auth = EngineAuthCheck(which=_no_binary)
    assert isinstance(engine_auth, EngineAuthCheckInterface)
    assert isinstance(ClusterPreflight(engine_auth=engine_auth), ClusterPreflightInterface)


async def test_database_check_connects_and_hands_back_the_connection() -> None:
    check, conn = await check_database(_test_dsn())
    assert check.ok
    assert conn is not None
    await conn.close()


async def test_database_check_reports_an_unreachable_host() -> None:
    check, conn = await check_database(_DEAD_DSN)
    assert not check.ok
    assert conn is None
    assert "cannot connect" in check.detail


async def test_database_check_reports_an_unsupported_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OldServer:
        async def fetchval(self, _query: str) -> str:
            return "130023"

        async def close(self) -> None:
            pass

    async def connect(_dsn: str) -> OldServer:
        return OldServer()

    monkeypatch.setattr("vibey.infrastructure.cluster_preflight.asyncpg.connect", connect)

    check, conn = await check_database("postgresql://old/db")

    assert not check.ok
    assert conn is not None
    assert "below" in check.detail


async def test_database_check_reports_an_unreadable_server_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnreadableServer:
        async def fetchval(self, _query: str) -> str:
            return "unknown"

        async def close(self) -> None:
            pass

    async def connect(_dsn: str) -> UnreadableServer:
        return UnreadableServer()

    monkeypatch.setattr("vibey.infrastructure.cluster_preflight.asyncpg.connect", connect)

    check, conn = await check_database("postgresql://unknown/db")

    assert not check.ok
    assert conn is not None
    assert "unreadable" in check.detail


async def test_database_check_closes_when_version_query_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenServer:
        async def fetchval(self, _query: str) -> str:
            raise asyncpg.PostgresError("version query failed")

        async def close(self) -> None:
            self.closed = True

    broken = BrokenServer()

    async def connect(_dsn: str) -> BrokenServer:
        return broken

    monkeypatch.setattr("vibey.infrastructure.cluster_preflight.asyncpg.connect", connect)

    check, conn = await check_database("postgresql://broken/db")

    assert not check.ok
    assert conn is None
    assert "version check failed" in check.detail
    assert broken.closed is True


async def test_migrations_report_applied_versions_after_bootstrap() -> None:
    # Explicit url: build_app() otherwise reads VIBEY_PG_URL, which this
    # module does not set, and the fallback silently targets a database
    # named after the current user -- which happens to work on a dev box
    # with a trusting local Postgres and fails on CI.
    async with build_app(url=_test_dsn()):
        pass
    conn = await asyncpg.connect(_test_dsn())
    try:
        check = await check_migrations(conn, migrations_dir())
    finally:
        await conn.close()
    assert check.ok, check.detail
    assert "applied" in check.detail


async def test_migrations_flag_a_version_the_database_has_not_seen(tmp_path: Path) -> None:
    """An image newer than its database is a real deployment state: the
    worker applies migrations at startup, so a pending one means startup
    did not finish."""
    # Explicit url: build_app() otherwise reads VIBEY_PG_URL, which this
    # module does not set, and the fallback silently targets a database
    # named after the current user -- which happens to work on a dev box
    # with a trusting local Postgres and fails on CI.
    async with build_app(url=_test_dsn()):
        pass
    for sql in sorted(migrations_dir().glob("*.sql")):
        (tmp_path / sql.name).write_text(sql.read_text())
    (tmp_path / "9999_from_a_newer_image.sql").write_text("SELECT 1;")

    conn = await asyncpg.connect(_test_dsn())
    try:
        check = await check_migrations(conn, tmp_path)
    finally:
        await conn.close()
    assert not check.ok
    assert "9999_from_a_newer_image" in check.detail


async def test_migrations_without_any_files_is_a_failure(tmp_path: Path) -> None:
    conn = await asyncpg.connect(_test_dsn())
    try:
        check = await check_migrations(conn, tmp_path)
    finally:
        await conn.close()
    assert not check.ok
    assert "no migrations found" in check.detail


async def test_migrations_on_a_database_with_no_schema_migration_table() -> None:
    """The state a database is in before anything has ever migrated it.

    Staged inside a transaction that is always rolled back: this suite runs
    under xdist against a per-worker database, and dropping the table for
    real would leave every test scheduled after this one on the same worker
    looking at a half-migrated schema.
    """
    conn = await asyncpg.connect(_test_dsn())
    try:
        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute("DROP TABLE IF EXISTS schema_migration")
            check = await check_migrations(conn, migrations_dir())
        finally:
            await tx.rollback()
    finally:
        await conn.close()
    assert not check.ok
    assert "unreadable" in check.detail


async def test_full_preflight_against_a_live_database(tmp_path: Path) -> None:
    # Explicit url: build_app() otherwise reads VIBEY_PG_URL, which this
    # module does not set, and the fallback silently targets a database
    # named after the current user -- which happens to work on a dev box
    # with a trusting local Postgres and fails on CI.
    async with build_app(url=_test_dsn()):
        pass
    # Every engine on PATH and no key: the default chart install on the
    # ADR-0037 image, which must pass the whole sweep. The sweep connects as the
    # application role, as the chart's workloads do (ADR-0055); whether the server
    # admits a password-less owner depends on the machine, so that probe is stubbed.
    from vibey.infrastructure.cluster_preflight import DatabaseSecurityChecks
    from vibey.infrastructure.db.local_auth import AuthVerdict, LocalAuthFinding

    class _Refused:
        def endpoints(self, app_url: str) -> tuple[tuple[str, int], ...]:
            return ()

        async def probe(self, app: object, app_url: str) -> LocalAuthFinding:
            return LocalAuthFinding(AuthVerdict.PASS, "refused")

    # A test earlier on this worker may have dropped `public` and rebuilt it as the owner,
    # which takes the application role's grants with it (tests/db_roles.py, `restore`). This
    # test runs the sweep as that role, so it puts them back first, as every test that runs as
    # the application role after one of those must. Without it, the test passed or failed on
    # which tests xdist happened to schedule before it on the same worker.
    await TestDatabaseRoles.from_environ(os.environ).restore(_test_dsn(), migrations_dir())
    app_dsn = os.environ.get("VIBEY_TEST_APP_DATABASE_URL", _test_dsn())
    preflight = ClusterPreflight(
        engine_auth=EngineAuthCheck(which=_every_binary),
        database_security=DatabaseSecurityChecks(probe=_Refused()),
    )
    checks = await preflight.run(
        dsn=app_dsn,
        workspace=tmp_path,
        migrations_dir=migrations_dir(),
        environ={},
        uid=10001,
    )
    assert all_ok(checks), [c for c in checks if not c.ok]
    assert {c.name for c in checks} == {
        "dsn-host",
        "non-root",
        "workspace-writable",
        "engine-auth",
        "database",
        "migrations",
        "ledger-guard",
        "local-auth",
    }


async def test_preflight_skips_the_migration_check_when_the_database_is_unreachable(
    tmp_path: Path,
) -> None:
    """No connection means no migration verdict -- reporting one anyway
    would be inventing a fact about a database nobody reached."""
    preflight = ClusterPreflight(engine_auth=EngineAuthCheck(which=_no_binary))
    checks = await preflight.run(
        dsn=_DEAD_DSN,
        workspace=tmp_path,
        migrations_dir=migrations_dir(),
        environ={},
        uid=10001,
    )
    assert not all_ok(checks)
    assert "migrations" not in {c.name for c in checks}


def test_all_ok_is_false_when_any_check_failed() -> None:
    assert all_ok([ClusterCheck("a", True), ClusterCheck("b", True)])
    assert not all_ok([ClusterCheck("a", True), ClusterCheck("b", False)])
