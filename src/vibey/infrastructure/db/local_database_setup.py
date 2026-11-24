# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey install --database`: a local database, its two roles, and its migrations.

On a local PostgreSQL the administrator can reach (`PostgresAdmin`), this makes what ADR-0055's
two-DSN model needs and then runs `vibey migrate`'s own `OwnerMigration` over it:

1. **Survey**, as the administrator: which of the two roles exist, and who owns the database.
2. **Passwords**, kept in libpq's password file (`PgPassFile`) *before* any role uses them, so
   a run that stops half-way never leaves a role whose password nobody kept. A role the file
   already has a password for keeps it; a new role gets a fresh random one. A role that exists
   and has no password in the file is not vibey's to take over: refused, naming it.
3. **Roles and database**, as the administrator: each role `LOGIN NOSUPERUSER NOCREATEDB
   NOCREATEROLE` with its password stored as a SCRAM verifier computed here
   (`ScramVerifier`), so psql never carries the password itself (sub-doctrine 10.j). The
   database is created owned by the owner role; one that exists and belongs to anyone else is
   refused. `public` is given to the owner, which PostgreSQL 15+ does already and 14 does not,
   so the owner can close it to every other role before migrating.
4. **Migrations**, as the owner, then the application role's grants reconciled and the ledger
   guard inspected from its side -- `OwnerMigration`, unchanged, connecting with
   password-free DSNs that find their passwords in the same file.

Nothing here prints, logs or returns a password. Running it again changes nothing it did: the
passwords are read back, the roles' verifiers are reset to them, and only pending migrations
run.

Declared by `interfaces/local_database_setup_interface.py` (ADR-0016).
"""

from __future__ import annotations

import asyncio
import os
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import asyncpg

from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.local_database_interface import PgPassInterface
from vibey.domain.local_database import LocalDatabaseNames, PgPass, PgPassEntry
from vibey.infrastructure.db.database_setup import MigrationReport, OwnerMigration
from vibey.infrastructure.db.interfaces.database_setup_interface import OwnerMigrationInterface
from vibey.infrastructure.db.interfaces.migration_catalog_interface import (
    MigrationCatalogInterface,
)
from vibey.infrastructure.db.interfaces.pgpass_file_interface import PgPassFileInterface
from vibey.infrastructure.db.interfaces.postgres_admin_interface import PostgresAdminInterface
from vibey.infrastructure.db.ledger_guard import (
    DatabaseEndpoints,
    DatabaseRoleReconciler,
    LedgerGuardInspector,
    RoleIdentifier,
    ScramVerifier,
)
from vibey.infrastructure.db.migration_catalog import MigrationCatalog
from vibey.infrastructure.db.migrator import PostgresMigrator

#: The database the administrator connects to before vibey's own exists.
MAINTENANCE_DATABASE: Final = "postgres"
#: Random bytes in each new password (`secrets.token_urlsafe`): 256 bits.
PASSWORD_BYTES: Final = 32
ROLE_ATTRIBUTES: Final = "LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"


class DatabaseSetupRefused(VibeyError):
    """A role or database is there already and is not vibey's to take over."""


@dataclass(frozen=True, slots=True)
class LocalDatabaseReport:
    """What `vibey install --database` did. Carries no password."""

    names: LocalDatabaseNames
    created_roles: tuple[str, ...]
    database_created: bool
    password_file: Path
    migration: MigrationReport


class PassfileConnector:
    """`asyncpg.connect` that reads one password file, the one vibey just wrote. Declared by
    `PassfileConnectorInterface`."""

    def __init__(self, passfile: Path) -> None:
        self._passfile = passfile

    async def __call__(self, dsn: str) -> asyncpg.Connection:
        return await asyncpg.connect(dsn, passfile=str(self._passfile))


class LocalDatabaseSetup:
    """Declared by `LocalDatabaseSetupInterface`. `migration`, `catalog` and `secret` are seams;
    by default they are `vibey migrate`'s own and `secrets.token_urlsafe`."""

    def __init__(
        self,
        *,
        admin: PostgresAdminInterface,
        pgpass: PgPassFileInterface,
        names: LocalDatabaseNames,
        migration: OwnerMigrationInterface | None = None,
        catalog: MigrationCatalogInterface | None = None,
        secret: Callable[[], str] | None = None,
        password_format: PgPassInterface | None = None,
    ) -> None:
        self._admin = admin
        self._pgpass = pgpass
        self._names = names
        self._migration = migration or self.owner_migration(pgpass.path(), os.environ)
        self._catalog = catalog or MigrationCatalog.packaged()
        self._secret = secret or self.new_password
        self._format = password_format or PgPass()

    @staticmethod
    def new_password() -> str:
        return secrets.token_urlsafe(PASSWORD_BYTES)

    @staticmethod
    def owner_migration(passfile: Path, environ: Mapping[str, str]) -> OwnerMigrationInterface:
        """`vibey migrate`'s runner, connecting with `passfile`'s passwords."""
        return OwnerMigration(
            migrator=PostgresMigrator.from_environ(environ),
            reconciler=DatabaseRoleReconciler(),
            inspector=LedgerGuardInspector(),
            connect=PassfileConnector(passfile),
        )

    def apply(self) -> LocalDatabaseReport:
        names = self._names
        roles, owner_of_database = self._survey()
        if owner_of_database is not None and owner_of_database != names.owner_role:
            raise DatabaseSetupRefused(
                f"the database {names.database!r} already exists and belongs to "
                f"{owner_of_database}, not {names.owner_role}: vibey will not take it over. "
                "Choose another name with --db-name, or --owner-role "
                f"{owner_of_database} if that role is yours to migrate as"
            )
        text = self._pgpass.read()
        kept = text
        passwords: dict[str, str] = {}
        for role, option in zip(names.roles, ("--owner-role", "--app-role"), strict=True):
            known = self._format.password_for(text, names.host, names.port, names.database, role)
            if known is None and role in roles:
                raise DatabaseSetupRefused(
                    f"the role {role!r} already exists and {self._pgpass.path()} has no "
                    f"password for it, so vibey cannot connect as it and will not reset it. "
                    f"Add the line {names.host}:{names.port}:{names.database}:{role}:<its "
                    f"password> to that file (mode 0600), or choose another name with {option}"
                )
            if known is None:
                known = self._secret()
                kept = self._format.with_entry(
                    kept, PgPassEntry(names.host, names.port, names.database, role, known)
                )
            passwords[role] = known
        if kept != text:
            self._pgpass.write(kept)

        created = tuple(role for role in names.roles if role not in roles)
        self._admin.execute(
            self._roles_sql(passwords, roles, create_database=owner_of_database is None),
            MAINTENANCE_DATABASE,
        )
        owner = RoleIdentifier.quote(names.owner_role)
        self._admin.execute(f"ALTER SCHEMA public OWNER TO {owner}", names.database)
        migration = asyncio.run(
            self._migration.run(
                owner_url=names.owner_dsn,
                app=DatabaseEndpoints(app_url=names.app_dsn),
                migrations=self._catalog.migrations(),
            )
        )
        return LocalDatabaseReport(
            names=names,
            created_roles=created,
            database_created=owner_of_database is None,
            password_file=self._pgpass.path(),
            migration=migration,
        )

    def _survey(self) -> tuple[frozenset[str], str | None]:
        """The roles of the two that exist, and the database's owner (None: no database)."""
        names = self._names
        wanted = ", ".join(self._literal(role) for role in names.roles)
        lines = self._admin.query(
            "SELECT 'role:' || rolname FROM pg_catalog.pg_roles "
            f"WHERE rolname IN ({wanted}) "
            "UNION ALL SELECT 'database:' || pg_catalog.pg_get_userbyid(datdba) "
            f"FROM pg_catalog.pg_database WHERE datname = {self._literal(names.database)}",
            MAINTENANCE_DATABASE,
        )
        roles = frozenset(line.removeprefix("role:") for line in lines if line.startswith("role:"))
        owners = [line.removeprefix("database:") for line in lines if line.startswith("database:")]
        return roles, (owners[0] if owners else None)

    def _roles_sql(
        self, passwords: Mapping[str, str], existing: frozenset[str], *, create_database: bool
    ) -> str:
        statements: list[str] = []
        for role, password in passwords.items():
            verifier = self._literal(ScramVerifier.compute(password))
            quoted = RoleIdentifier.quote(role)
            if role in existing:
                statements.append(f"ALTER ROLE {quoted} LOGIN PASSWORD {verifier};")
            else:
                statements.append(f"CREATE ROLE {quoted} {ROLE_ATTRIBUTES} PASSWORD {verifier};")
        if create_database:
            statements.append(
                f"CREATE DATABASE {RoleIdentifier.quote(self._names.database)} "
                f"OWNER {RoleIdentifier.quote(self._names.owner_role)};"
            )
        return "\n".join(statements) + "\n"

    @staticmethod
    def _literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"
