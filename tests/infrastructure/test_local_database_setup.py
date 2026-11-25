# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey install --database`, with fakes for psql, the password file and the migration.

What holds above all: a password is written to the password file before the role that uses it
exists (so a crash never strands a role nobody knows the password of), it never reaches psql's
input or any output (only its SCRAM verifier does), a role or database vibey did not make is
never taken over, and running it again changes nothing it already did.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from vibey.domain.local_database import LocalDatabaseNames, PgPass
from vibey.infrastructure.db import local_database_setup as database_setup_module
from vibey.infrastructure.db import postgres_admin as admin_module
from vibey.infrastructure.db.database_setup import MigrationReport, OwnerMigration
from vibey.infrastructure.db.interfaces.local_database_setup_interface import (
    LocalDatabaseSetupInterface,
    PassfileConnectorInterface,
)
from vibey.infrastructure.db.interfaces.pgpass_file_interface import PgPassFileInterface
from vibey.infrastructure.db.interfaces.postgres_admin_interface import PostgresAdminInterface
from vibey.infrastructure.db.ledger_guard import DatabaseEndpoints, LedgerGuardStatus
from vibey.infrastructure.db.local_database_setup import (
    DatabaseSetupRefused,
    LocalDatabaseSetup,
    PassfileConnector,
)
from vibey.infrastructure.db.migrator import Migration
from vibey.infrastructure.db.pgpass_file import PgPassFile
from vibey.infrastructure.db.postgres_admin import (
    PostgresAdmin,
    PostgresAdminFailed,
    PostgresAdminUnavailable,
)
from vibey.infrastructure.postgres import PostgresCommandResult, PostgresLocalService

NAMES = LocalDatabaseNames("vibey", "vibey", "vibey_app", "localhost", 5432)
SECRETS = ("owner-secret-1", "app-secret-2")


# ------------------------------------------------------------------ the password file


def test_the_password_file_is_where_libpq_looks(tmp_path: Path) -> None:
    named = PgPassFile(environ={"PGPASSFILE": "~/elsewhere"}, home=lambda: tmp_path)
    assert named.path() == Path("~/elsewhere").expanduser()
    assert PgPassFile(environ={}, home=lambda: tmp_path).path() == tmp_path / ".pgpass"
    assert PgPassFile(environ={"PGPASSFILE": " "}, home=lambda: tmp_path).path() == (
        tmp_path / ".pgpass"
    )
    assert isinstance(named, PgPassFileInterface)


def test_a_missing_password_file_reads_as_empty_and_is_created_private(tmp_path: Path) -> None:
    pgpass = PgPassFile(environ={}, home=lambda: tmp_path)
    assert pgpass.read() == ""
    pgpass.write("localhost:5432:vibey:vibey:x\n")
    assert pgpass.read() == "localhost:5432:vibey:vibey:x\n"
    assert stat.S_IMODE((tmp_path / ".pgpass").stat().st_mode) == 0o600


def test_rewriting_a_readable_password_file_makes_it_private(tmp_path: Path) -> None:
    path = tmp_path / ".pgpass"
    path.write_text("old\n")
    path.chmod(0o644)
    PgPassFile(environ={}, home=lambda: tmp_path).write("new\n")
    assert path.read_text() == "new\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in tmp_path.iterdir()] == [".pgpass"]  # no temporary file left


def test_a_failed_write_leaves_the_old_file_and_no_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / ".pgpass"
    path.write_text("old\n")

    def refuse(*_args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", refuse)
    with pytest.raises(OSError, match="disk full"):
        PgPassFile(environ={}, home=lambda: tmp_path).write("new\n")
    assert path.read_text() == "old\n"
    assert [p.name for p in tmp_path.iterdir()] == [".pgpass"]


# ------------------------------------------------------------------ psql as the administrator


class _Psql:
    """Records every psql run and answers queries from a script of outputs."""

    def __init__(self, *answers: PostgresCommandResult) -> None:
        self.calls: list[tuple[tuple[str, ...], str]] = []
        self._answers = list(answers)

    def __call__(self, argv: tuple[str, ...], stdin: str) -> PostgresCommandResult:
        self.calls.append((argv, stdin))
        return self._answers.pop(0) if self._answers else PostgresCommandResult(0)


def test_psql_reads_its_sql_from_stdin_and_stops_at_the_first_error() -> None:
    psql = _Psql(PostgresCommandResult(0, stdout="role:vibey\n\n  database:adam \n"))
    admin = PostgresAdmin(("sudo", "-u", "postgres", "/usr/bin/psql"), runner=psql)
    assert admin.query("SELECT 1", "postgres") == ("role:vibey", "database:adam")
    admin.execute("CREATE ROLE x", "vibey")
    argv, stdin = psql.calls[1]
    assert argv == (
        "sudo",
        "-u",
        "postgres",
        "/usr/bin/psql",
        "-X",
        "-q",
        "-t",
        "-A",
        "-v",
        "ON_ERROR_STOP=1",
        "-d",
        "vibey",
        "-f",
        "-",
    )
    assert stdin == "CREATE ROLE x"
    assert isinstance(admin, PostgresAdminInterface)


def test_a_psql_failure_is_reported_with_any_verifier_redacted() -> None:
    psql = _Psql(
        PostgresCommandResult(
            3, stderr="ERROR: bad\nLINE 1: PASSWORD 'SCRAM-SHA-256$4096:abc$def:ghi'\n"
        )
    )
    with pytest.raises(PostgresAdminFailed) as caught:
        PostgresAdmin(("psql",), runner=psql).execute("x", "postgres")
    message = str(caught.value)
    assert "ERROR: bad" in message and "exit 3" in message
    assert "abc$def" not in message and "SCRAM-SHA-256$<redacted>" in message


def test_a_psql_failure_with_no_output_still_says_so() -> None:
    with pytest.raises(PostgresAdminFailed, match="no output"):
        PostgresAdmin(("psql",), runner=_Psql(PostgresCommandResult(1))).query("x", "postgres")


def _service(*, manager: str | None, psql: str | None = "/usr/bin/psql") -> Any:
    class _Service:
        def tool(self, name: str) -> str | None:
            return psql if name == "psql" else None

        def package_manager(self) -> str | None:
            return manager

    return _Service()


def _locate(service: Any, **kwargs: Any) -> PostgresAdmin:
    defaults: dict[str, Any] = {
        "admin_user": None,
        "current_user": "adam",
        "which": lambda name: f"/usr/bin/{name}" if name in ("sudo", "runuser") else None,
        "effective_uid": lambda: 1000,
    }
    defaults.update(kwargs)
    return PostgresAdmin.for_local(service, **defaults)


def test_homebrew_s_administrator_is_the_person_and_needs_no_sudo() -> None:
    assert _locate(_service(manager="brew")).argv == ("/usr/bin/psql",)
    assert _locate(_service(manager=None)).argv == ("/usr/bin/psql",)


def test_a_package_manager_s_administrator_is_postgres_reached_through_sudo() -> None:
    assert _locate(_service(manager="apt-get")).argv == ("sudo", "-u", "postgres", "/usr/bin/psql")
    assert _locate(_service(manager="dnf"), admin_user="pgadmin").argv[:3] == (
        "sudo",
        "-u",
        "pgadmin",
    )
    assert _locate(_service(manager="dnf"), admin_user="adam").argv == ("/usr/bin/psql",)


def test_root_without_sudo_switches_user_with_runuser() -> None:
    located = _locate(
        _service(manager="apt-get"),
        which=lambda name: "/usr/sbin/runuser" if name == "runuser" else None,
        effective_uid=lambda: 0,
    )
    assert located.argv == ("runuser", "-u", "postgres", "--", "/usr/bin/psql")


def test_no_way_to_act_as_the_administrator_is_refused_with_the_next_step() -> None:
    with pytest.raises(PostgresAdminUnavailable, match="sudo") as caught:
        _locate(_service(manager="apt-get"), which=lambda name: None)
    assert "--admin-user" in str(caught.value)
    with pytest.raises(PostgresAdminUnavailable, match="sudo"):
        _locate(_service(manager="apt-get"), which=lambda name: None, effective_uid=lambda: 0)


def test_no_psql_is_refused_with_the_install_command() -> None:
    with pytest.raises(PostgresAdminUnavailable, match="vibey install --postgres"):
        _locate(_service(manager="brew", psql=None))


def test_the_default_runner_feeds_stdin_and_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs, argv=argv)
        return subprocess.CompletedProcess(argv, 0, stdout="out", stderr="err")

    monkeypatch.setattr(admin_module.subprocess, "run", run)
    assert PostgresAdmin.run(("psql",), "SELECT 1") == PostgresCommandResult(0, "out", "err")
    assert seen["input"] == "SELECT 1" and seen["cwd"] == "/" and seen["text"] is True

    def fail(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="psql", timeout=1)

    monkeypatch.setattr(admin_module.subprocess, "run", fail)
    assert PostgresAdmin.run(("psql",), "").returncode == 1


def test_a_real_service_is_located_through_its_own_tool_lookup() -> None:
    service = PostgresLocalService(which=lambda name: "/opt/bin/psql" if name == "psql" else None)
    assert PostgresAdmin.for_local(service, admin_user=None, current_user="adam").argv == (
        "/opt/bin/psql",
    )


# ------------------------------------------------------------------ the setup


class _Admin:
    """psql as the administrator: answers the survey, records every statement."""

    def __init__(self, survey: tuple[str, ...] = (), log: list[str] | None = None) -> None:
        self._survey = survey
        self.executed: list[tuple[str, str]] = []
        self.log = log if log is not None else []

    def query(self, sql: str, database: str) -> tuple[str, ...]:
        self.log.append("survey")
        return self._survey

    def execute(self, sql: str, database: str) -> None:
        self.log.append(f"execute {database}")
        self.executed.append((sql, database))


class _PgPass:
    def __init__(self, text: str = "", log: list[str] | None = None) -> None:
        self.text = text
        self.writes = 0
        self.log = log if log is not None else []

    def path(self) -> Path:
        return Path("/home/adam/.pgpass")

    def read(self) -> str:
        return self.text

    def write(self, text: str) -> None:
        self.log.append("pgpass")
        self.writes += 1
        self.text = text


class _Migration:
    def __init__(self, log: list[str] | None = None, guard: str = "") -> None:
        self.runs: list[dict[str, Any]] = []
        self.log = log if log is not None else []
        self._guard = guard

    async def run(
        self, *, owner_url: str, app: DatabaseEndpoints | None, migrations: tuple[Migration, ...]
    ) -> MigrationReport:
        self.log.append("migrate")
        self.runs.append({"owner_url": owner_url, "app": app, "migrations": migrations})
        problems = (self._guard,) if self._guard else ()
        return MigrationReport(("0001_x",), "vibey_app", LedgerGuardStatus("vibey_app", problems))


class _Catalog:
    directory = Path("/migrations")

    def migrations(self) -> tuple[Migration, ...]:
        return (Migration("0001_x", Path("/migrations/0001_x.sql"), "SELECT 1", "sum"),)


def _setup(
    admin: _Admin, pgpass: _PgPass, migration: _Migration, *, secrets: tuple[str, ...] = SECRETS
) -> LocalDatabaseSetup:
    drawn = list(secrets)
    return LocalDatabaseSetup(
        admin=admin,
        pgpass=pgpass,
        names=NAMES,
        migration=migration,
        catalog=_Catalog(),
        secret=lambda: drawn.pop(0),
    )


def test_a_fresh_server_gets_both_roles_the_database_and_the_migrations() -> None:
    log: list[str] = []
    admin, pgpass, migration = _Admin(log=log), _PgPass(log=log), _Migration(log)
    report = _setup(admin, pgpass, migration).apply()

    # The passwords are kept before the roles that use them exist.
    assert log == ["survey", "pgpass", "execute postgres", "execute vibey", "migrate"]
    assert PgPass().password_for(pgpass.text, "localhost", 5432, "vibey", "vibey") == SECRETS[0]
    assert (
        PgPass().password_for(pgpass.text, "localhost", 5432, "vibey", "vibey_app") == (SECRETS[1])
    )
    roles_sql, _ = admin.executed[0]
    assert 'CREATE ROLE "vibey" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD' in roles_sql
    assert 'CREATE ROLE "vibey_app" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE' in roles_sql
    assert roles_sql.count("'SCRAM-SHA-256$4096:") == 2
    assert 'CREATE DATABASE "vibey" OWNER "vibey"' in roles_sql
    assert admin.executed[1] == ('ALTER SCHEMA public OWNER TO "vibey"', "vibey")
    for sql, _ in admin.executed:  # only verifiers reach psql, never a password
        assert not any(secret in sql for secret in SECRETS)

    assert migration.runs == [
        {
            "owner_url": "postgresql://vibey@localhost:5432/vibey",
            "app": DatabaseEndpoints("postgresql://vibey_app@localhost:5432/vibey"),
            "migrations": _Catalog().migrations(),
        }
    ]
    assert report.created_roles == ("vibey", "vibey_app")
    assert report.database_created is True
    assert report.password_file == Path("/home/adam/.pgpass")
    assert report.migration.guard is not None and report.migration.guard.in_force
    assert report.names == NAMES
    assert isinstance(_setup(admin, pgpass, migration), LocalDatabaseSetupInterface)


def test_running_it_again_keeps_the_passwords_and_creates_nothing() -> None:
    kept = PgPass().with_entry(
        PgPass().with_entry("", _entry("vibey", "kept-owner")), _entry("vibey_app", "kept-app")
    )
    admin = _Admin(survey=("role:vibey", "role:vibey_app", "database:vibey"))
    pgpass, migration = _PgPass(kept), _Migration()
    report = _setup(admin, pgpass, migration, secrets=()).apply()

    assert pgpass.writes == 0
    roles_sql, _ = admin.executed[0]
    assert 'ALTER ROLE "vibey" LOGIN PASSWORD' in roles_sql
    assert 'ALTER ROLE "vibey_app" LOGIN PASSWORD' in roles_sql
    assert "CREATE" not in roles_sql
    assert report.created_roles == () and report.database_created is False
    assert len(migration.runs) == 1


def test_a_role_vibey_has_no_password_for_is_never_taken_over() -> None:
    admin = _Admin(survey=("role:vibey_app",))
    pgpass = _PgPass("localhost:5432:vibey:vibey:owner\n")
    with pytest.raises(DatabaseSetupRefused) as caught:
        _setup(admin, pgpass, _Migration()).apply()
    message = str(caught.value)
    assert "vibey_app" in message and "/home/adam/.pgpass" in message
    assert "--app-role" in message
    assert pgpass.writes == 0 and admin.executed == []


def test_a_database_someone_else_owns_is_never_taken_over() -> None:
    admin = _Admin(survey=("database:adam",))
    pgpass = _PgPass()
    with pytest.raises(DatabaseSetupRefused, match="belongs to adam") as caught:
        _setup(admin, pgpass, _Migration()).apply()
    assert "--db-name" in str(caught.value)
    assert pgpass.writes == 0 and admin.executed == []


def test_an_unrecognised_survey_line_is_ignored() -> None:
    admin = _Admin(survey=("NOTICE: something",))
    report = _setup(admin, _PgPass(), _Migration()).apply()
    assert report.created_roles == ("vibey", "vibey_app")


def _entry(user: str, password: str) -> Any:
    from vibey.domain.local_database import PgPassEntry

    return PgPassEntry("localhost", 5432, "vibey", user, password)


def test_the_default_secret_is_long_and_url_safe() -> None:
    secret = LocalDatabaseSetup.new_password()
    assert len(secret) >= 40 and ":" not in secret and "\\" not in secret


def test_the_default_migration_reads_the_password_file_it_was_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration = LocalDatabaseSetup.owner_migration(Path("/p/.pgpass"), {})
    assert isinstance(migration, OwnerMigration)
    seen: dict[str, Any] = {}

    async def connect(dsn: str, **kwargs: Any) -> str:
        seen.update(kwargs, dsn=dsn)
        return "connection"

    monkeypatch.setattr(database_setup_module.asyncpg, "connect", connect)
    connector = PassfileConnector(Path("/p/.pgpass"))
    assert isinstance(connector, PassfileConnectorInterface)
    import asyncio

    assert asyncio.run(connector("postgresql://vibey@localhost:5432/vibey")) == "connection"
    assert seen == {"dsn": "postgresql://vibey@localhost:5432/vibey", "passfile": "/p/.pgpass"}


def test_the_default_setup_builds_its_own_migration_and_catalog(tmp_path: Path) -> None:
    built = LocalDatabaseSetup(
        admin=_Admin(), pgpass=PgPassFile(environ={}, home=lambda: tmp_path), names=NAMES
    )
    assert isinstance(built, LocalDatabaseSetupInterface)
