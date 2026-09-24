# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger is append-only by the database, not by convention (ADR-0055).

Found against the schema migrations 0002 and 0013 left: the `DO INSTEAD NOTHING` rules
on the partitioned parent did not fire for an UPDATE or DELETE addressed to a
partition, never fire on TRUNCATE, and the owner -- which is what the worker connected
as -- could disable them. These tests hold the replacement to account against real
PostgreSQL: as the application role nothing can rewrite the ledger, as the owner the
triggers still refuse, and the application's own paths still work."""

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio

from tests.db_roles import TestDatabaseRoles
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.database_setup import OwnerMigration, SchemaPreparer
from vibey.infrastructure.db.interfaces import (
    DatabaseEndpointsInterface,
    DatabaseRoleReconcilerInterface,
    LedgerGuardInspectorInterface,
    OwnerMigrationInterface,
    RoleIdentifierInterface,
    SchemaPreparerInterface,
)
from vibey.infrastructure.db.ledger_guard import (
    APP_ROLE_GRANTS,
    AppRoleGrants,
    AppRoleMissing,
    DatabaseEndpoints,
    DatabaseRoleReconciler,
    LedgerGuardInspector,
    LedgerGuardStatus,
    RoleIdentifier,
    RoleSeparationRefused,
    SchemaNotMigrated,
)
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.db.migrator import (
    MigrationChecksumError,
    PostgresMigrator,
    discover_migrations,
)
from vibey.infrastructure.engines.tailer import LedgerEventDraft

from .conftest import MIGRATIONS_DIR

ROLES = TestDatabaseRoles.from_environ(os.environ)
split_only = pytest.mark.skipif(not ROLES.split, reason="the suite runs as one role")
PARTITION = "event_partitioned_0013_default"
REFUSED = "the ledger is append-only"


def _draft(project_id: UUID) -> LedgerEventDraft:
    payload = {"prompt_digest": "abc"}
    return LedgerEventDraft(
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        kind=EventKind.TURN_REQUESTED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload=payload,
        digest=digest_event(payload),
    )


@pytest_asyncio.fixture
async def app_conn(migrated_pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    async with migrated_pool.acquire() as conn:
        yield conn  # type: ignore[misc]


@pytest_asyncio.fixture
async def owner_conn(owner_pool: asyncpg.Pool) -> AsyncIterator[asyncpg.Connection]:
    async with owner_pool.acquire() as conn:
        yield conn  # type: ignore[misc]


@pytest_asyncio.fixture
async def appended(migrated_pool: asyncpg.Pool, project_id: UUID) -> UUID:
    """One event, appended through the application's own path, as the application."""
    await PostgresLedgerRepository(migrated_pool).append(_draft(project_id))
    return project_id


# ── as the application role: no rewrite is even permitted ────────────────────────


@split_only
@pytest.mark.parametrize("table", ["event", PARTITION])
@pytest.mark.parametrize(
    "statement",
    ["UPDATE {t} SET digest = 'forged'", "DELETE FROM {t}", "TRUNCATE {t}"],
)
async def test_the_application_role_cannot_rewrite_the_ledger_or_a_partition(
    app_conn: asyncpg.Connection, appended: UUID, table: str, statement: str
) -> None:
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="permission denied"):
        await app_conn.execute(statement.format(t=table))


@split_only
@pytest.mark.parametrize(
    "ddl",
    [
        "ALTER TABLE event DISABLE TRIGGER event_append_only",
        "ALTER TABLE event DISABLE TRIGGER ALL",
        "DROP TRIGGER event_append_only ON event",
    ],
)
async def test_the_application_role_cannot_switch_the_guard_off(
    app_conn: asyncpg.Connection, ddl: str
) -> None:
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="must be owner"):
        await app_conn.execute(ddl)


@split_only
async def test_the_application_can_still_append_and_read(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresLedgerRepository(migrated_pool)
    first = await repo.append(_draft(project_id))
    second = await repo.append(_draft(project_id))

    events = await repo.all_for_project(project_id)
    assert [e.seq for e in events] == [first.seq, second.seq] == [1, 2]


@split_only
async def test_the_guard_is_in_force_for_the_application_role(
    app_conn: asyncpg.Connection,
) -> None:
    status = await LedgerGuardInspector().inspect(app_conn)

    assert status.in_force, status.describe()
    assert status.role == ROLES.app_role
    assert status.describe().startswith(f"in force: {ROLES.app_role}")


@split_only
async def test_the_application_role_holds_exactly_the_declared_grants(
    app_conn: asyncpg.Connection,
) -> None:
    rows = await app_conn.fetch(
        """
        SELECT c.relname AS name, p.privilege
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
        CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE']) p(privilege)
        WHERE c.relkind IN ('r', 'p') AND has_table_privilege(c.oid, p.privilege)
        """
    )
    held: dict[str, set[str]] = {}
    for row in rows:
        held.setdefault(row["name"], set()).add(row["privilege"])

    assert held == {table: set(p) for table, p in APP_ROLE_GRANTS.tables.items()}
    assert await app_conn.fetchval("SELECT has_sequence_privilege('job_bump_seq', 'USAGE')")


# ── as the owner: the triggers still refuse, loudly ─────────────────────────────────


@pytest.mark.parametrize("table", ["event", PARTITION])
@pytest.mark.parametrize(
    "statement",
    ["UPDATE {t} SET digest = 'forged'", "DELETE FROM {t}", "TRUNCATE {t}"],
)
async def test_even_the_owner_is_refused_a_rewrite(
    owner_conn: asyncpg.Connection, appended: UUID, table: str, statement: str
) -> None:
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
        await owner_conn.execute(statement.format(t=table))
    assert await owner_conn.fetchval("SELECT digest FROM event") != "forged"


async def test_deleting_a_project_does_not_cascade_through_its_ledger(
    owner_conn: asyncpg.Connection, appended: UUID
) -> None:
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
        await owner_conn.execute("DELETE FROM project WHERE id = $1", appended)


@split_only
async def test_a_partition_added_later_is_guarded(
    owner_conn: asyncpg.Connection, appended: UUID
) -> None:
    """The row trigger is cloned onto a new partition at once; the TRUNCATE guard,
    which Postgres does not clone, is attached by the next reconcile -- and until
    then the inspector says it is missing."""
    await owner_conn.execute(
        "CREATE TABLE event_later PARTITION OF event FOR VALUES FROM (1000000000) TO (2000000000)"
    )
    await owner_conn.execute(
        "INSERT INTO event (project_id, seq, cycle, phase, kind, correlation_id, payload, digest) "
        "SELECT project_id, 1000000001, cycle, phase, kind, correlation_id, payload, digest "
        "FROM event LIMIT 1"
    )
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
        await owner_conn.execute("UPDATE event_later SET digest = 'x'")
    missing = await LedgerGuardInspector().inspect(owner_conn)
    assert "public.event_later has no event_no_truncate trigger" in missing.problems

    await DatabaseRoleReconciler().reconcile(owner_conn, app_role=ROLES.app_role)

    with pytest.raises(asyncpg.InsufficientPrivilegeError, match=REFUSED):
        await owner_conn.execute("TRUNCATE event_later")
    assert (
        "public.event_later has no event_no_truncate trigger"
        not in (await LedgerGuardInspector().inspect(owner_conn)).problems
    )


async def test_the_guard_is_not_in_force_for_the_owner_and_says_why(
    owner_conn: asyncpg.Connection,
) -> None:
    status = await LedgerGuardInspector().inspect(owner_conn)

    assert not status.in_force
    assert any(p.startswith("it owns the ledger") for p in status.problems)
    assert any("holds UPDATE, DELETE, TRUNCATE on public.event" in p for p in status.problems)
    assert status.describe().startswith("NOT in force for ")


async def test_a_disabled_trigger_is_reported(owner_conn: asyncpg.Connection) -> None:
    await owner_conn.execute("ALTER TABLE event DISABLE TRIGGER event_append_only")

    status = await LedgerGuardInspector().inspect(owner_conn)

    assert "event_append_only is disabled on public.event" in status.problems


async def test_an_unmigrated_database_is_reported(pg_conn: asyncpg.Connection) -> None:
    status = await LedgerGuardInspector().inspect(pg_conn)

    assert status.problems == ("the ledger table does not exist (unmigrated)",)


# ── the reconciler ──────────────────────────────────────────────────────────────


@split_only
async def test_a_grant_added_by_hand_is_revoked_at_the_next_reconcile(
    owner_conn: asyncpg.Connection, app_conn: asyncpg.Connection
) -> None:
    role = RoleIdentifier.quote(ROLES.app_role)
    await owner_conn.execute(f"GRANT DELETE, TRUNCATE ON job, event TO {role}")
    assert await app_conn.fetchval("SELECT has_table_privilege('event', 'DELETE')")

    await DatabaseRoleReconciler().reconcile(owner_conn, app_role=ROLES.app_role)

    assert not await app_conn.fetchval("SELECT has_table_privilege('event', 'DELETE')")
    assert not await app_conn.fetchval("SELECT has_table_privilege('job', 'TRUNCATE')")


async def test_the_owner_itself_is_refused_as_the_application_role(
    owner_conn: asyncpg.Connection,
) -> None:
    owner = await owner_conn.fetchval("SELECT current_user")
    superuser = await owner_conn.fetchval("SELECT rolsuper FROM pg_roles WHERE rolname = $1", owner)

    with pytest.raises(RoleSeparationRefused, match="refusing to reconcile grants"):
        await DatabaseRoleReconciler().reconcile(owner_conn, app_role=owner)
    assert superuser is not None


async def test_a_member_of_the_owner_is_refused(owner_conn: asyncpg.Connection) -> None:
    owner = await owner_conn.fetchval("SELECT current_user")
    member = f"vibey_test_member_{uuid4().hex[:8]}"
    await owner_conn.execute(f"CREATE ROLE {member} NOLOGIN IN ROLE {RoleIdentifier.quote(owner)}")
    try:
        with pytest.raises(RoleSeparationRefused, match="member of, the owner"):
            await DatabaseRoleReconciler().reconcile(owner_conn, app_role=member)
    finally:
        await owner_conn.execute(f"DROP ROLE {member}")


async def test_a_superuser_is_refused(owner_conn: asyncpg.Connection) -> None:
    if not await owner_conn.fetchval("SELECT rolsuper FROM pg_roles WHERE rolname = current_user"):
        pytest.skip("creating a superuser needs one")
    role = f"vibey_test_super_{uuid4().hex[:8]}"
    await owner_conn.execute(f"CREATE ROLE {role} NOLOGIN SUPERUSER")
    try:
        with pytest.raises(RoleSeparationRefused, match="it is a superuser"):
            await DatabaseRoleReconciler().reconcile(owner_conn, app_role=role)
    finally:
        await owner_conn.execute(f"DROP ROLE {role}")


async def test_a_missing_role_is_created_only_when_a_password_is_given(
    owner_conn: asyncpg.Connection,
) -> None:
    role = f"vibey_test_new_{uuid4().hex[:8]}"
    with pytest.raises(AppRoleMissing, match=f"{role!r} does not exist"):
        await DatabaseRoleReconciler().reconcile(owner_conn, app_role=role)
    try:
        await DatabaseRoleReconciler().reconcile(owner_conn, app_role=role, app_password="p'w\"d")
        assert await owner_conn.fetchval("SELECT has_table_privilege($1, 'event', 'INSERT')", role)
        assert not await owner_conn.fetchval(
            "SELECT has_table_privilege($1, 'event', 'UPDATE')", role
        )
    finally:
        await owner_conn.execute(
            f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}; "
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}; "
            f"REVOKE ALL ON SCHEMA public FROM {role}; "
            f"DROP OWNED BY {role}; DROP ROLE {role}"
        )


# ── the migrator's read-only side ───────────────────────────────────────────────


async def test_pending_is_everything_on_a_fresh_database_and_nothing_after(
    pg_conn: asyncpg.Connection,
) -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)
    migrator = PostgresMigrator()

    assert await migrator.pending(pg_conn, migrations) == tuple(m.version for m in migrations)
    assert await migrator.may_migrate(pg_conn)
    await migrator.apply(pg_conn, migrations)
    assert await migrator.pending(pg_conn, migrations) == ()
    assert await migrator.may_migrate(pg_conn)


async def test_pending_refuses_an_edited_migration(pg_conn: asyncpg.Connection) -> None:
    migrations = discover_migrations(MIGRATIONS_DIR)
    await PostgresMigrator().apply(pg_conn, migrations)
    await pg_conn.execute(
        "UPDATE schema_migration SET checksum = 'edited' WHERE version = $1", migrations[0].version
    )

    with pytest.raises(MigrationChecksumError):
        await PostgresMigrator().pending(pg_conn, migrations)


@split_only
async def test_the_application_role_may_not_migrate(app_conn: asyncpg.Connection) -> None:
    assert not await PostgresMigrator().may_migrate(app_conn)


# ── build_app's preparation and `vibey migrate` ─────────────────────────────────


def _preparer() -> SchemaPreparer:
    return SchemaPreparer(migrator=PostgresMigrator(), inspector=LedgerGuardInspector())


def _owner_migration() -> OwnerMigration:
    return OwnerMigration(
        migrator=PostgresMigrator(),
        reconciler=DatabaseRoleReconciler(),
        inspector=LedgerGuardInspector(),
    )


@split_only
async def test_a_split_install_never_migrates_from_build_app_even_with_the_owner_dsn_set(
    pg_conn: asyncpg.Connection, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review of #1100, finding 2: only `vibey migrate` reads VIBEY_PG_MIGRATE_URL. A
    process that starts `build_app` -- a worker whose engine sessions and gates run
    model-chosen commands -- never needs the owner's DSN, so it never reads it."""
    monkeypatch.setenv("VIBEY_PG_MIGRATE_URL", database_url)
    await pg_conn.execute(f"GRANT USAGE ON SCHEMA public TO {ROLES.app_role}")
    app = await asyncpg.connect(ROLES.app_dsn(database_url))
    try:
        endpoints = DatabaseEndpoints(app_url=ROLES.app_dsn(database_url))
        with pytest.raises(SchemaNotMigrated, match="vibey migrate"):
            await _preparer().prepare(app, endpoints, discover_migrations(MIGRATIONS_DIR))
    finally:
        await app.close()
    assert await pg_conn.fetchval("SELECT to_regclass('public.event')") is None


@split_only
async def test_a_split_install_starts_on_a_migrated_schema(
    app_conn: asyncpg.Connection, database_url: str
) -> None:
    endpoints = DatabaseEndpoints(app_url=ROLES.app_dsn(database_url))

    status = await _preparer().prepare(app_conn, endpoints, discover_migrations(MIGRATIONS_DIR))

    assert status.in_force


async def test_a_single_role_install_still_migrates_and_is_reported_unguarded(
    pg_conn: asyncpg.Connection, database_url: str
) -> None:
    endpoints = DatabaseEndpoints(app_url=database_url)

    status = await _preparer().prepare(pg_conn, endpoints, discover_migrations(MIGRATIONS_DIR))

    assert await PostgresMigrator().pending(pg_conn, discover_migrations(MIGRATIONS_DIR)) == ()
    assert not status.in_force


@split_only
async def test_vibey_migrate_reconciles_the_application_role_and_inspects_as_it(
    pg_conn: asyncpg.Connection, database_url: str
) -> None:
    report = await _owner_migration().run(
        owner_url=database_url,
        app=DatabaseEndpoints(app_url=ROLES.app_dsn(database_url)),
        migrations=discover_migrations(MIGRATIONS_DIR),
    )

    assert report.applied == tuple(m.version for m in discover_migrations(MIGRATIONS_DIR))
    assert report.reconciled_role == ROLES.app_role
    assert report.guard is not None and report.guard.in_force


async def test_vibey_migrate_with_one_role_migrates_and_reports_the_guard_absent(
    pg_conn: asyncpg.Connection, database_url: str
) -> None:
    report = await _owner_migration().run(
        owner_url=database_url,
        app=DatabaseEndpoints(app_url=database_url),
        migrations=discover_migrations(MIGRATIONS_DIR),
    )

    assert report.reconciled_role is None
    assert report.guard is not None and not report.guard.in_force


async def test_vibey_migrate_without_an_application_dsn_only_migrates(
    pg_conn: asyncpg.Connection, database_url: str
) -> None:
    report = await _owner_migration().run(
        owner_url=database_url, app=None, migrations=discover_migrations(MIGRATIONS_DIR)
    )

    assert report.applied and report.reconciled_role is None and report.guard is None


# ── plain values ────────────────────────────────────────────────────────────────


def test_the_ledger_grant_is_read_and_append_only() -> None:
    assert APP_ROLE_GRANTS.ledger_privileges() == ("SELECT", "INSERT")
    assert AppRoleGrants().ledger_privileges() == ()
    assert all("DELETE" not in p and "TRUNCATE" not in p for p in APP_ROLE_GRANTS.tables.values())


def test_the_endpoints_read_the_application_credentials_and_nothing_of_the_owner() -> None:
    endpoints = DatabaseEndpoints(app_url="postgresql://vibey%5Fapp:p%40ss@db:5432/vibey")

    assert endpoints.app_role == "vibey_app"
    assert endpoints.app_password == "p@ss"
    assert not hasattr(endpoints, "migrate_url")
    blank = DatabaseEndpoints(app_url="postgresql:///v")
    assert blank.app_role is None and blank.app_password is None


def test_identifiers_are_quoted_and_an_unusable_one_is_refused() -> None:
    assert RoleIdentifier.quote('we"ird') == '"we""ird"'
    for bad in ("", "a\x00b"):
        with pytest.raises(ValueError, match="not a usable identifier"):
            RoleIdentifier.quote(bad)


def test_the_errors_say_what_to_do() -> None:
    assert "VIBEY_PG_MIGRATE_URL" in str(SchemaNotMigrated(("0016",)))
    assert "CREATE ROLE app" in str(AppRoleMissing("app"))
    assert LedgerGuardStatus("r").in_force


def test_every_class_satisfies_its_declared_interface() -> None:
    assert isinstance(RoleIdentifier(), RoleIdentifierInterface)
    assert isinstance(DatabaseEndpoints(app_url="x"), DatabaseEndpointsInterface)
    assert isinstance(LedgerGuardInspector(), LedgerGuardInspectorInterface)
    assert isinstance(DatabaseRoleReconciler(), DatabaseRoleReconcilerInterface)
    assert DatabaseRoleReconciler().grants is APP_ROLE_GRANTS
    assert isinstance(_preparer(), SchemaPreparerInterface)
    assert isinstance(_owner_migration(), OwnerMigrationInterface)


# ── review of #1100: regressions, one per finding ───────────────────────────────


_HIJACK = """
CREATE FUNCTION public.hijack_eq(oid, regnamespace) RETURNS boolean
LANGUAGE plpgsql AS $$
BEGIN
  IF current_user <> '{app}' THEN
    EXECUTE 'CREATE OR REPLACE FUNCTION public.backdoor_wipe() RETURNS bigint '
         || 'LANGUAGE plpgsql SECURITY DEFINER AS $b$ DECLARE n bigint; BEGIN '
         || 'ALTER TABLE event DISABLE TRIGGER event_append_only; '
         || 'DELETE FROM event; GET DIAGNOSTICS n = ROW_COUNT; '
         || 'ALTER TABLE event ENABLE TRIGGER event_append_only; RETURN n; END $b$';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.backdoor_wipe() TO {app}';
  END IF;
  RETURN $1 = $2::oid;
END $$;
CREATE OPERATOR public.= (LEFTARG = oid, RIGHTARG = regnamespace, FUNCTION = public.hijack_eq);
"""


@split_only
async def test_finding_1_an_operator_the_app_planted_never_runs_as_the_owner(
    owner_conn: asyncpg.Connection, app_conn: asyncpg.Connection, appended: UUID
) -> None:
    """PostgreSQL 14's default, and any pg_upgraded database: `public` grants CREATE to
    every role. The app role plants `public.=` on (oid, regnamespace); the owner's
    reconcile must never resolve it, must take CREATE away, and the inspector must
    name what the app role still owns."""
    await owner_conn.execute("GRANT CREATE ON SCHEMA public TO PUBLIC")
    await app_conn.execute(_HIJACK.format(app=ROLES.app_role))
    before = await owner_conn.fetchval("SELECT count(*) FROM event")

    await DatabaseRoleReconciler().reconcile(owner_conn, app_role=ROLES.app_role)

    assert await owner_conn.fetchval("SELECT to_regprocedure('public.backdoor_wipe()')") is None
    assert await owner_conn.fetchval("SELECT count(*) FROM event") == before
    assert not await app_conn.fetchval("SELECT has_schema_privilege('public', 'CREATE')")
    assert not await app_conn.fetchval(
        "SELECT has_database_privilege(current_database(), 'CREATE')"
    )
    status = await LedgerGuardInspector().inspect(app_conn)
    assert any("public.hijack_eq(oid,regnamespace) (function)" in p for p in status.problems), (
        status.problems
    )


@split_only
async def test_finding_1_create_on_public_or_the_database_fails_the_guard(
    owner_conn: asyncpg.Connection, app_conn: asyncpg.Connection
) -> None:
    role = RoleIdentifier.quote(ROLES.app_role)
    database = await owner_conn.fetchval("SELECT current_database()")
    await owner_conn.execute("GRANT CREATE ON SCHEMA public TO PUBLIC")
    await owner_conn.execute(f"GRANT CREATE ON DATABASE {RoleIdentifier.quote(database)} TO {role}")

    problems = (await LedgerGuardInspector().inspect(app_conn)).problems

    assert "it may CREATE in schema public" in problems
    assert "it may CREATE schemas in this database" in problems


@split_only
async def test_finding_1_a_security_definer_function_the_app_can_call_fails_the_guard(
    owner_conn: asyncpg.Connection, app_conn: asyncpg.Connection
) -> None:
    await owner_conn.execute(
        "CREATE FUNCTION public.definer_door() RETURNS int LANGUAGE sql SECURITY DEFINER "
        "AS 'SELECT 1'"
    )

    problems = (await LedgerGuardInspector().inspect(app_conn)).problems

    assert any("SECURITY DEFINER public.definer_door()" in p for p in problems), problems


async def test_finding_1_the_guard_functions_pin_their_search_path(
    owner_conn: asyncpg.Connection,
) -> None:
    rows = await owner_conn.fetch(
        "SELECT proname, proconfig FROM pg_proc WHERE proname IN "
        "('ledger_refuse_rewrite', 'ledger_guard_partitions')"
    )
    assert {r["proname"]: r["proconfig"] for r in rows} == {
        "ledger_refuse_rewrite": ["search_path=pg_catalog, pg_temp"],
        "ledger_guard_partitions": ["search_path=pg_catalog, pg_temp"],
    }


@split_only
async def test_finding_5_concurrent_reconciles_all_succeed(
    owner_pool: asyncpg.Pool, database_url: str
) -> None:
    """Eight `migrate` init containers of a KEDA scale-out, at once: the reconcile
    serializes on the migration lock instead of failing "tuple concurrently updated"."""

    async def one() -> None:
        conn = await asyncpg.connect(database_url)
        try:
            await DatabaseRoleReconciler().reconcile(conn, app_role=ROLES.app_role)
        finally:
            await conn.close()

    results = await asyncio.gather(*(one() for _ in range(8)), return_exceptions=True)

    assert [r for r in results if isinstance(r, BaseException)] == []


@pytest.mark.parametrize(
    ("tamper", "problem"),
    [
        (
            "ALTER TABLE event ENABLE REPLICA TRIGGER event_append_only",
            "event_append_only is not enabled for every session on public.event",
        ),
        (
            "CREATE OR REPLACE FUNCTION public.ledger_refuse_rewrite() RETURNS trigger "
            "LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp "
            "AS $$ BEGIN RETURN OLD; END $$",
            "public.ledger_refuse_rewrite() is not the function the migrations installed",
        ),
        (
            "DROP TRIGGER event_append_only ON event; "
            "CREATE FUNCTION public.no_op() RETURNS trigger LANGUAGE plpgsql "
            "AS $$ BEGIN RETURN OLD; END $$; "
            "CREATE TRIGGER event_append_only BEFORE UPDATE OR DELETE ON event "
            "FOR EACH ROW EXECUTE FUNCTION public.no_op()",
            "event_append_only on public.event does not call public.ledger_refuse_rewrite()",
        ),
        (
            "DROP TRIGGER event_append_only ON event; "
            "CREATE TRIGGER event_append_only AFTER INSERT ON event "
            "FOR EACH ROW EXECUTE FUNCTION public.ledger_refuse_rewrite()",
            "event_append_only on public.event does not fire BEFORE UPDATE OR DELETE",
        ),
    ],
    ids=["replica", "body-replaced", "other-function", "other-events"],
)
async def test_finding_6_a_tampered_trigger_is_not_in_force(
    owner_conn: asyncpg.Connection, tamper: str, problem: str
) -> None:
    await owner_conn.execute(tamper)

    problems = (await LedgerGuardInspector().inspect(owner_conn)).problems

    assert any(problem in p for p in problems), problems


def test_finding_6_the_expected_function_hash_is_the_migrations_body() -> None:
    import hashlib
    import re

    from vibey.infrastructure.db.ledger_guard import REFUSE_REWRITE_SHA256

    sql = (MIGRATIONS_DIR / "0017_ledger_guard_search_path.sql").read_text()
    body = re.search(r"FUNCTION public\.ledger_refuse_rewrite\(\).*?AS \$\$(.*?)\$\$;", sql, re.S)
    assert body is not None
    assert hashlib.sha256(body.group(1).encode()).hexdigest() == REFUSE_REWRITE_SHA256


@split_only
async def test_finding_8_a_role_that_may_create_roles_is_refused(
    owner_conn: asyncpg.Connection,
) -> None:
    role = f"vibey_test_cr_{uuid4().hex[:8]}"
    await owner_conn.execute(f"CREATE ROLE {role} NOLOGIN CREATEROLE")
    try:
        with pytest.raises(RoleSeparationRefused, match="it may create roles"):
            await DatabaseRoleReconciler().reconcile(owner_conn, app_role=role)
    finally:
        await owner_conn.execute(f"DROP ROLE {role}")


async def test_finding_8_membership_is_checked_against_the_ledgers_owner(
    owner_conn: asyncpg.Connection,
) -> None:
    """The ledger's owner need not be the role running the reconcile."""
    owner = f"vibey_test_ledger_owner_{uuid4().hex[:8]}"
    member = f"vibey_test_via_owner_{uuid4().hex[:8]}"
    await owner_conn.execute(f"CREATE ROLE {owner} NOLOGIN")
    await owner_conn.execute(f"CREATE ROLE {member} NOLOGIN IN ROLE {owner}")
    await owner_conn.execute(f"ALTER TABLE event OWNER TO {owner}")
    try:
        with pytest.raises(RoleSeparationRefused, match="member of, the owner"):
            await DatabaseRoleReconciler().reconcile(owner_conn, app_role=member)
    finally:
        await owner_conn.execute("ALTER TABLE event OWNER TO CURRENT_USER")
        await owner_conn.execute(f"DROP ROLE {member}")
        await owner_conn.execute(f"DROP OWNED BY {owner}; DROP ROLE {owner}")


@split_only
async def test_finding_8_default_privileges_and_public_grants_are_reset(
    owner_conn: asyncpg.Connection, app_conn: asyncpg.Connection
) -> None:
    role = RoleIdentifier.quote(ROLES.app_role)
    await owner_conn.execute(f"ALTER DEFAULT PRIVILEGES GRANT ALL ON TABLES TO {role}")
    await owner_conn.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {role}"
    )
    await owner_conn.execute("GRANT UPDATE, DELETE ON event TO PUBLIC")

    await DatabaseRoleReconciler().reconcile(owner_conn, app_role=ROLES.app_role)

    default_acl = await owner_conn.fetchval(
        "SELECT count(*) FROM pg_default_acl, aclexplode(defaclacl) a "
        "WHERE a.grantee = (SELECT oid FROM pg_roles WHERE rolname = $1)",
        ROLES.app_role,
    )
    assert default_acl == 0
    assert not await app_conn.fetchval("SELECT has_table_privilege('event', 'UPDATE')")
    assert not await app_conn.fetchval("SELECT has_table_privilege('event', 'DELETE')")


class _Recording:
    """An owner connection that remembers every statement it was asked to run."""

    def __init__(self, conn: asyncpg.Connection, refuse: str | None = None) -> None:
        self._conn = conn
        self._refuse = refuse
        self.statements: list[str] = []

    def __getattr__(self, name: str) -> object:
        return getattr(self._conn, name)

    async def execute(self, sql: str, *args: object) -> str:
        self.statements.append(sql)
        if self._refuse and sql.startswith(self._refuse):
            raise asyncpg.InsufficientPrivilegeError("permission denied to create role")
        return await self._conn.execute(sql, *args)

    async def fetchval(self, sql: str, *args: object) -> object:
        self.statements.append(sql)
        return await self._conn.fetchval(sql, *args)


async def test_finding_9_a_new_role_gets_a_scram_verifier_never_the_plaintext(
    owner_conn: asyncpg.Connection, database_url: str
) -> None:
    role = f"vibey_test_scram_{uuid4().hex[:8]}"
    password = "correct horse battery staple"
    recording = _Recording(owner_conn)
    try:
        await DatabaseRoleReconciler().reconcile(
            recording,  # type: ignore[arg-type]
            app_role=role,
            app_password=password,
        )
        assert not any(password in sql for sql in recording.statements)
        stored = await owner_conn.fetchval(
            "SELECT rolpassword FROM pg_authid WHERE rolname = $1", role
        )
        assert stored.startswith("SCRAM-SHA-256$4096:")
        parts = ROLES.app_dsn(database_url).split("@", 1)[1]
        conn = await asyncpg.connect(f"postgresql://{role}:{password.replace(' ', '%20')}@{parts}")
        assert await conn.fetchval("SELECT current_user") == role
        await conn.close()
    finally:
        await owner_conn.execute(f"DROP OWNED BY {role}; DROP ROLE IF EXISTS {role}")


async def test_finding_9_an_owner_that_cannot_create_roles_gets_a_clean_error(
    owner_conn: asyncpg.Connection,
) -> None:
    from vibey.infrastructure.db.ledger_guard import OwnerCannotCreateRole

    recording = _Recording(owner_conn, refuse="CREATE ROLE")
    with pytest.raises(OwnerCannotCreateRole, match="CREATEROLE"):
        await DatabaseRoleReconciler().reconcile(
            recording,  # type: ignore[arg-type]
            app_role=f"vibey_test_nocr_{uuid4().hex[:8]}",
            app_password="pw",
        )


def test_finding_9_the_verifier_is_rfc_5803_shaped() -> None:
    import base64
    import hashlib
    import hmac

    from vibey.infrastructure.db.ledger_guard import ScramVerifier

    salt = b"0123456789abcdef"
    verifier = ScramVerifier.compute("pencil", salt=salt, iterations=4096)
    salted = hashlib.pbkdf2_hmac("sha256", b"pencil", salt, 4096)
    client = hmac.new(salted, b"Client Key", "sha256").digest()
    server = hmac.new(salted, b"Server Key", "sha256").digest()
    b64 = base64.b64encode
    assert verifier == (
        f"SCRAM-SHA-256$4096:{b64(salt).decode()}$"
        f"{b64(hashlib.sha256(client).digest()).decode()}:{b64(server).decode()}"
    )
