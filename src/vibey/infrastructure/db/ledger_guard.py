# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger is append-only by the database, not by convention (ADR-0055).

Two roles, two DSNs:

- **The owner** (`VIBEY_PG_MIGRATE_URL`) runs migrations and owns every table. It is
  only ever used to migrate and to reconcile the application role's grants.
- **The application role** (`VIBEY_PG_URL`) is what every worker, CLI command,
  operator and KEDA scaler connects as. It holds exactly `APP_ROLE_GRANTS` -- the
  privileges the application's own queries need, and on the ledger only `SELECT` and
  `INSERT` -- and owns nothing, so it can neither rewrite the ledger nor disable the
  triggers (migration 0015) that refuse a rewrite.

`DatabaseRoleReconciler` makes the application role's privileges exactly the declared
ones, on every migration run. `LedgerGuardInspector` answers, from the application's own
connection, whether the guard is in force -- and names every reason it is not. A
single-DSN install (the application connecting as the owner or a superuser) still runs,
so upgrading never strands an install; but it is reported loudly at every start and
fails `vibey doctor` until the operator splits the roles (12.e).

Declared by `interfaces/ledger_guard_interface.py` (ADR-0016).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar, Final
from urllib.parse import unquote, urlsplit

from vibey.domain.errors import VibeyError
from vibey.infrastructure.db.migrator import OwnedConnection

LEDGER_TABLE: Final = "event"
ROW_GUARD_TRIGGER: Final = "event_append_only"
TRUNCATE_GUARD_TRIGGER: Final = "event_no_truncate"
REWRITE_PRIVILEGES: Final = ("UPDATE", "DELETE", "TRUNCATE")


class RoleSeparationRefused(VibeyError):
    """The application role cannot be guarded: it is the owner, a member of the owner,
    or a superuser. Granting or revoking anything would change nothing."""

    def __init__(self, app_role: str, reason: str) -> None:
        self.app_role = app_role
        super().__init__(
            f"refusing to reconcile grants for {app_role!r}: {reason}. VIBEY_PG_URL must "
            "name a role that neither owns the schema nor is a superuser "
            "(docs/reference/configuration.md#database-roles)"
        )


class AppRoleMissing(VibeyError):
    """The application role does not exist and nothing supplied a password to create it."""

    def __init__(self, app_role: str) -> None:
        self.app_role = app_role
        super().__init__(
            f"the application role {app_role!r} does not exist; create it as the owner "
            f"(CREATE ROLE {app_role} LOGIN PASSWORD '...') or give VIBEY_PG_URL a "
            "password so `vibey migrate` can create it"
        )


class SchemaNotMigrated(VibeyError):
    """The application role may not migrate, and migrations are pending."""

    def __init__(self, pending: tuple[str, ...]) -> None:
        self.pending = pending
        super().__init__(
            f"{len(pending)} migration(s) pending ({', '.join(pending)}) and VIBEY_PG_URL's "
            "role may not apply them: set VIBEY_PG_MIGRATE_URL to the owner's DSN, or run "
            "`vibey migrate` with it"
        )


@dataclass(frozen=True, slots=True)
class AppRoleGrants:
    """The privileges the application role holds: nothing else, on nothing else.

    Declared once, here, and derived from the application's own queries
    (`infrastructure/db/*_repository.py`, `cli/main.py`, `cluster_preflight.py`).
    A table missing from `tables` is one the application never touches; a privilege
    missing from a table's tuple is one no query of its needs. A new query that needs
    more fails its tests with `permission denied` -- the suite runs as this role --
    and the fix is a line here, in review, never a broader grant.
    """

    tables: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    sequences: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    functions: tuple[str, ...] = ()

    def ledger_privileges(self) -> tuple[str, ...]:
        return self.tables.get(LEDGER_TABLE, ())


APP_ROLE_GRANTS: Final = AppRoleGrants(
    tables=MappingProxyType(
        {
            # The ledger: read and append. Never UPDATE, DELETE or TRUNCATE.
            "event": ("SELECT", "INSERT"),
            # append_event's per-project counter: INSERT ... ON CONFLICT DO UPDATE ... RETURNING.
            "event_seq": ("SELECT", "INSERT", "UPDATE"),
            "project": ("SELECT", "INSERT", "UPDATE"),
            # The claim is SELECT ... FOR UPDATE SKIP LOCKED, which needs UPDATE.
            "job": ("SELECT", "INSERT", "UPDATE"),
            "job_dependency": ("SELECT", "INSERT"),
            "handoff": ("SELECT", "INSERT"),
            # Upserts: INSERT ... ON CONFLICT DO UPDATE.
            "engine_health": ("SELECT", "INSERT", "UPDATE"),
            "rotation_cursor": ("SELECT", "INSERT", "UPDATE"),
            "human_gate": ("SELECT", "INSERT", "UPDATE"),
            # Read by the cluster preflight's migrations check; written only by the owner.
            "schema_migration": ("SELECT",),
        }
    ),
    # `vibey queue bump` draws bump_seq with nextval().
    sequences=MappingProxyType({"job_bump_seq": ("USAGE",)}),
    functions=("append_event",),
)


class RoleIdentifier:
    """Quotes a role or relation name for DDL, which cannot take bind parameters.

    Declared by `interfaces/ledger_guard_interface.py`.
    """

    @staticmethod
    def quote(name: str) -> str:
        if not name or "\x00" in name:
            raise ValueError(f"not a usable identifier: {name!r}")
        return '"' + name.replace('"', '""') + '"'


@dataclass(frozen=True, slots=True)
class DatabaseEndpoints:
    """The two DSNs, read from the environment. Declared by
    `interfaces/ledger_guard_interface.py`.

    `app_url` (`VIBEY_PG_URL`) is the application role's; `migrate_url`
    (`VIBEY_PG_MIGRATE_URL`) is the owner's, and absent on a single-DSN install.
    """

    APP_ENV: ClassVar[str] = "VIBEY_PG_URL"
    MIGRATE_ENV: ClassVar[str] = "VIBEY_PG_MIGRATE_URL"

    app_url: str
    migrate_url: str | None = None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str], *, app_url: str) -> "DatabaseEndpoints":
        """`app_url` is resolved by the caller (bootstrap refuses an unset one); the
        owner's DSN is optional and blank means unset."""
        return cls(app_url=app_url, migrate_url=environ.get(cls.MIGRATE_ENV, "").strip() or None)

    @property
    def app_role(self) -> str | None:
        """The role `app_url` names, when it names one (a DSN may leave it to PGUSER)."""
        user = urlsplit(self.app_url).username
        return unquote(user) if user else None

    @property
    def app_password(self) -> str | None:
        password = urlsplit(self.app_url).password
        return unquote(password) if password else None


@dataclass(frozen=True, slots=True)
class LedgerGuardStatus:
    """Whether the application's connection can rewrite the ledger, and why."""

    role: str
    problems: tuple[str, ...] = ()

    @property
    def in_force(self) -> bool:
        return not self.problems

    def describe(self) -> str:
        if self.in_force:
            return f"in force: {self.role} can read and append to the ledger and nothing more"
        return f"NOT in force for {self.role}: " + "; ".join(self.problems)


_ROLE = """
SELECT current_user AS role,
       (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) AS superuser,
       (SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = to_regclass($1)) AS owner,
       (SELECT pg_has_role(current_user, relowner, 'MEMBER')
          FROM pg_class WHERE oid = to_regclass($1)) AS owns
"""

_PARTITIONS = """
SELECT relid::regclass::text AS name, relid = to_regclass($1) AS is_parent
FROM pg_partition_tree(to_regclass($1))
"""

_TRIGGERS = """
SELECT tgname, tgenabled::text AS tgenabled FROM pg_trigger WHERE tgrelid = to_regclass($1)
"""


class LedgerGuardInspector:
    """Reports, from the application's own connection, whether the guard is in force.

    Declared by `interfaces/ledger_guard_interface.py`. Reads catalogs only, so any role
    can run it. The guard is in force when the connecting role is not a superuser, does
    not own the ledger (directly or through membership), holds none of UPDATE, DELETE
    or TRUNCATE on it or on any of its partitions, and the triggers of migration 0015
    are present and enabled on every one of them.
    """

    async def inspect(self, conn: OwnedConnection) -> LedgerGuardStatus:
        # A select with no FROM: exactly one row, whatever the catalogs hold.
        (row,) = await conn.fetch(_ROLE, LEDGER_TABLE)
        role = str(row["role"])
        if row["owner"] is None:
            return LedgerGuardStatus(role, ("the ledger table does not exist (unmigrated)",))
        problems: list[str] = []
        if row["superuser"]:
            problems.append("it connects as a superuser")
        if row["owns"]:
            problems.append(f"it owns the ledger (as {row['owner']} or a member of it)")
        for part in await conn.fetch(_PARTITIONS, LEDGER_TABLE):
            name = str(part["name"])
            held = [
                privilege
                for privilege in REWRITE_PRIVILEGES
                if await conn.fetchval("SELECT has_table_privilege($1, $2)", name, privilege)
            ]
            if held:
                problems.append(f"it holds {', '.join(held)} on {name}")
            expected = (TRUNCATE_GUARD_TRIGGER, ROW_GUARD_TRIGGER)
            triggers = {
                str(t["tgname"]): str(t["tgenabled"]) for t in await conn.fetch(_TRIGGERS, name)
            }
            for trigger in expected:
                state = triggers.get(trigger)
                if state is None:
                    problems.append(f"{name} has no {trigger} trigger")
                elif state == "D":
                    problems.append(f"{trigger} is disabled on {name}")
        return LedgerGuardStatus(role, tuple(problems))


class DatabaseRoleReconciler:
    """Makes the application role's privileges exactly the declared ones.

    Declared by `interfaces/ledger_guard_interface.py`. Runs on the owner's connection,
    after migrations, on every migration run -- so a table a migration adds is
    reachable by the application only once it is declared, and a grant someone added
    by hand is revoked at the next start. Also attaches the TRUNCATE guard to any
    partition added since the last run.
    """

    def __init__(self, grants: AppRoleGrants = APP_ROLE_GRANTS) -> None:
        self._grants = grants

    @property
    def grants(self) -> AppRoleGrants:
        return self._grants

    async def reconcile(
        self, owner: OwnedConnection, *, app_role: str, app_password: str | None = None
    ) -> None:
        exists = await owner.fetchrow(
            "SELECT rolsuper, pg_has_role($1, current_user, 'MEMBER') AS member "
            "FROM pg_roles WHERE rolname = $1",
            app_role,
        )
        if exists is None:
            if not app_password:
                raise AppRoleMissing(app_role)
            ddl = await owner.fetchval(
                "SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', $1::text, $2::text)",
                app_role,
                app_password,
            )
            await owner.execute(ddl)
        elif exists["rolsuper"]:
            raise RoleSeparationRefused(app_role, "it is a superuser")
        elif exists["member"]:
            raise RoleSeparationRefused(app_role, "it is, or is a member of, the owner")
        role = RoleIdentifier.quote(app_role)
        async with owner.transaction():
            await owner.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
            await owner.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}")
            await owner.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
            for table, privileges in self._grants.tables.items():
                await owner.execute(
                    f"GRANT {', '.join(privileges)} ON TABLE {RoleIdentifier.quote(table)} TO {role}"
                )
            for sequence, privileges in self._grants.sequences.items():
                await owner.execute(
                    f"GRANT {', '.join(privileges)} ON SEQUENCE "
                    f"{RoleIdentifier.quote(sequence)} TO {role}"
                )
            for function in self._grants.functions:
                # Every overload: migrations replaced append_event's signature, and a
                # regprocedure's text form is already a quoted, qualified signature.
                for signature in await owner.fetch(
                    "SELECT oid::regprocedure::text AS sig FROM pg_proc "
                    "WHERE proname = $1 AND pronamespace = 'public'::regnamespace",
                    function,
                ):
                    await owner.execute(f"GRANT EXECUTE ON FUNCTION {signature['sig']} TO {role}")
            await owner.execute("SELECT ledger_guard_partitions()")
