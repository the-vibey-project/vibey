# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger is append-only by the database, not by convention (ADR-0055).

Two roles, two DSNs:

- **The owner** (`VIBEY_PG_MIGRATE_URL`) runs migrations and owns every table. It is
  only ever used to migrate and to reconcile the application role's grants.
- **The application role** (`VIBEY_PG_URL`) is what every worker, CLI command,
  operator and KEDA scaler connects as. It holds exactly `APP_ROLE_GRANTS` -- the
  privileges the application's own queries need, and on the ledger only `SELECT` and
  `INSERT` -- and owns nothing, so it can neither rewrite the ledger nor disable the
  triggers (migration 0016) that refuse a rewrite.

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
            "role may not apply them: run `VIBEY_PG_MIGRATE_URL=<the owner's DSN> vibey "
            "migrate` (never exported: only that command may hold the owner's DSN)"
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
    """The application role's DSN. Declared by `interfaces/ledger_guard_interface.py`.

    Deliberately nothing of the owner's: only `vibey migrate` reads
    `VIBEY_PG_MIGRATE_URL` (`MIGRATE_ENV`), so no process that runs engine sessions or
    gate commands -- model-chosen shell commands -- ever holds it (review of #1100).
    """

    APP_ENV: ClassVar[str] = "VIBEY_PG_URL"
    MIGRATE_ENV: ClassVar[str] = "VIBEY_PG_MIGRATE_URL"

    app_url: str

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


# Every catalog query below runs with `search_path = pg_catalog, pg_temp` and names its
# operators by schema: nothing another role created in `public` can be resolved in their
# place (review of #1100, finding 1).
SAFE_SEARCH_PATH: Final = "SET LOCAL search_path = pg_catalog, pg_temp"

_ROLE = """
SELECT CURRENT_USER AS role,
       (SELECT r.rolsuper FROM pg_catalog.pg_roles r
         WHERE r.rolname OPERATOR(pg_catalog.=) CURRENT_USER) AS superuser,
       (SELECT pg_catalog.pg_get_userbyid(c.relowner) FROM pg_catalog.pg_class c
         WHERE c.oid OPERATOR(pg_catalog.=) pg_catalog.to_regclass($1)) AS owner,
       (SELECT pg_catalog.pg_has_role(CURRENT_USER, c.relowner, 'MEMBER')
          FROM pg_catalog.pg_class c
         WHERE c.oid OPERATOR(pg_catalog.=) pg_catalog.to_regclass($1)) AS owns,
       pg_catalog.has_schema_privilege('public', 'CREATE') AS create_in_public,
       pg_catalog.has_database_privilege(pg_catalog.current_database(), 'CREATE')
           AS create_in_database
"""

_PARTITIONS = """
SELECT t.relid::pg_catalog.regclass::pg_catalog.text AS name
FROM pg_catalog.pg_partition_tree(pg_catalog.to_regclass($1)) t
"""

_TRIGGERS = """
SELECT g.tgname::pg_catalog.text AS tgname, g.tgenabled::pg_catalog.text AS tgenabled
FROM pg_catalog.pg_trigger g
WHERE g.tgrelid OPERATOR(pg_catalog.=) pg_catalog.to_regclass($1)
"""

# What the connecting role owns outside its own temporary schemas. It should own
# nothing: an object it owns in `public` (an operator, a function) is something the
# owner could resolve by accident.
_OWNED = """
WITH me AS (
    SELECT r.oid FROM pg_catalog.pg_roles r
    WHERE r.rolname OPERATOR(pg_catalog.=) CURRENT_USER
), spaces AS (
    SELECT n.oid FROM pg_catalog.pg_namespace n
    WHERE n.nspname OPERATOR(pg_catalog.!~) '^pg_(toast_)?temp_'
      AND n.nspname OPERATOR(pg_catalog.<>) ALL (ARRAY['pg_catalog', 'information_schema', 'pg_toast'])
)
SELECT c.oid::pg_catalog.regclass::pg_catalog.text AS name, 'relation' AS kind
  FROM pg_catalog.pg_class c
 WHERE c.relowner OPERATOR(pg_catalog.=) (SELECT oid FROM me)
   AND c.relnamespace IN (SELECT oid FROM spaces)
UNION ALL
SELECT p.oid::pg_catalog.regprocedure::pg_catalog.text, 'function'
  FROM pg_catalog.pg_proc p
 WHERE p.proowner OPERATOR(pg_catalog.=) (SELECT oid FROM me)
   AND p.pronamespace IN (SELECT oid FROM spaces)
UNION ALL
SELECT o.oid::pg_catalog.regoperator::pg_catalog.text, 'operator'
  FROM pg_catalog.pg_operator o
 WHERE o.oprowner OPERATOR(pg_catalog.=) (SELECT oid FROM me)
   AND o.oprnamespace IN (SELECT oid FROM spaces)
UNION ALL
SELECT n.nspname::pg_catalog.text, 'schema'
  FROM pg_catalog.pg_namespace n
 WHERE n.nspowner OPERATOR(pg_catalog.=) (SELECT oid FROM me)
   AND n.oid IN (SELECT oid FROM spaces)
ORDER BY 1
"""

# SECURITY DEFINER functions the connecting role may call that run as the ledger's
# owner or as a superuser: each is a way to act as them.
_DEFINERS = """
SELECT p.oid::pg_catalog.regprocedure::pg_catalog.text AS name,
       pg_catalog.pg_get_userbyid(p.proowner) AS runs_as
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid OPERATOR(pg_catalog.=) p.pronamespace
 WHERE p.prosecdef
   AND n.nspname OPERATOR(pg_catalog.<>) ALL (ARRAY['pg_catalog', 'information_schema'])
   AND pg_catalog.has_function_privilege(p.oid, 'EXECUTE')
   AND (p.proowner OPERATOR(pg_catalog.=) (
            SELECT c.relowner FROM pg_catalog.pg_class c
             WHERE c.oid OPERATOR(pg_catalog.=) pg_catalog.to_regclass($1))
        OR (SELECT r.rolsuper FROM pg_catalog.pg_roles r
             WHERE r.oid OPERATOR(pg_catalog.=) p.proowner))
 ORDER BY 1
"""

# SECURITY DEFINER functions the application role may call. None today; one added here
# is a reviewed decision, not an accident the inspector has to be told to ignore.
ALLOWED_SECURITY_DEFINERS: Final[frozenset[str]] = frozenset()

# How many owned objects a report names before it counts the rest.
_OWNED_SHOWN: Final = 5


class LedgerGuardInspector:
    """Reports, from the application's own connection, whether the guard is in force.

    Declared by `interfaces/ledger_guard_interface.py`. Reads catalogs only, so any role
    can run it. The guard is in force when the connecting role is not a superuser, does
    not own the ledger (directly or through membership), holds none of UPDATE, DELETE
    or TRUNCATE on it or on any of its partitions, and the triggers of migrations 0016/0017
    are present and enabled on every one of them.
    """

    async def inspect(self, conn: OwnedConnection) -> LedgerGuardStatus:
        async with conn.transaction():
            await conn.execute(SAFE_SEARCH_PATH)
            return await self._inspect(conn)

    async def _inspect(self, conn: OwnedConnection) -> LedgerGuardStatus:
        ledger = f"public.{LEDGER_TABLE}"
        # A select with no FROM: exactly one row, whatever the catalogs hold.
        (row,) = await conn.fetch(_ROLE, ledger)
        role = str(row["role"])
        if row["owner"] is None:
            return LedgerGuardStatus(role, ("the ledger table does not exist (unmigrated)",))
        problems: list[str] = []
        if row["superuser"]:
            problems.append("it connects as a superuser")
        if row["owns"]:
            problems.append(f"it owns the ledger (as {row['owner']} or a member of it)")
        if row["create_in_public"]:
            problems.append("it may CREATE in schema public")
        if row["create_in_database"]:
            problems.append("it may CREATE schemas in this database")
        owned = [f"{o['name']} ({o['kind']})" for o in await conn.fetch(_OWNED)]
        if owned:
            shown = ", ".join(owned[:_OWNED_SHOWN])
            more = len(owned) - _OWNED_SHOWN
            problems.append(f"it owns {shown}" + (f" and {more} more" if more > 0 else ""))
        for definer in await conn.fetch(_DEFINERS, ledger):
            if definer["name"] not in ALLOWED_SECURITY_DEFINERS:
                problems.append(
                    f"it may call SECURITY DEFINER {definer['name']}, "
                    f"which runs as {definer['runs_as']}"
                )
        for part in await conn.fetch(_PARTITIONS, ledger):
            name = str(part["name"])
            held = [
                privilege
                for privilege in REWRITE_PRIVILEGES
                if await conn.fetchval(
                    "SELECT pg_catalog.has_table_privilege($1, $2)", name, privilege
                )
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

    async def close_schema(self, owner: OwnedConnection) -> None:
        """Take CREATE on `public` away from every role but its owner, before any
        migration runs: a role that can create there can plant an operator or function
        that an unqualified name in the owner's SQL resolves to (review of #1100)."""
        async with owner.transaction():
            await owner.execute(SAFE_SEARCH_PATH)
            await owner.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")

    async def reconcile(
        self, owner: OwnedConnection, *, app_role: str, app_password: str | None = None
    ) -> None:
        async with owner.transaction():
            # Nothing another role created in `public` can be resolved in place of a
            # pg_catalog object for the rest of this transaction (review of #1100).
            await owner.execute(SAFE_SEARCH_PATH)
            await self._reconcile(owner, app_role=app_role, app_password=app_password)

    async def _reconcile(
        self, owner: OwnedConnection, *, app_role: str, app_password: str | None
    ) -> None:
        exists = await owner.fetchrow(
            "SELECT r.rolsuper, "
            "pg_catalog.pg_has_role($1, CURRENT_USER, 'MEMBER') AS member "
            "FROM pg_catalog.pg_roles r WHERE r.rolname OPERATOR(pg_catalog.=) $1",
            app_role,
        )
        if exists is None:
            if not app_password:
                raise AppRoleMissing(app_role)
            ddl = await owner.fetchval(
                "SELECT pg_catalog.format('CREATE ROLE %I LOGIN PASSWORD %L', $1::text, $2::text)",
                app_role,
                app_password,
            )
            await owner.execute(ddl)
        elif exists["rolsuper"]:
            raise RoleSeparationRefused(app_role, "it is a superuser")
        elif exists["member"]:
            raise RoleSeparationRefused(app_role, "it is, or is a member of, the owner")
        role = RoleIdentifier.quote(app_role)
        database = RoleIdentifier.quote(
            str(await owner.fetchval("SELECT pg_catalog.current_database()"))
        )
        # The application role creates nothing: not in `public` (the PostgreSQL 14
        # default grants every role CREATE there), not a schema of its own.
        await owner.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        await owner.execute(f"REVOKE CREATE ON SCHEMA public FROM {role}")
        await owner.execute(f"REVOKE CREATE ON DATABASE {database} FROM {role}")
        await owner.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
        await owner.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {role}")
        await owner.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        for table, privileges in self._grants.tables.items():
            await owner.execute(
                f"GRANT {', '.join(privileges)} ON TABLE public.{RoleIdentifier.quote(table)} "
                f"TO {role}"
            )
        for sequence, privileges in self._grants.sequences.items():
            await owner.execute(
                f"GRANT {', '.join(privileges)} ON SEQUENCE "
                f"public.{RoleIdentifier.quote(sequence)} TO {role}"
            )
        for function in self._grants.functions:
            # Every overload: migrations replaced append_event's signature. With this
            # search_path a regprocedure prints schema-qualified.
            for signature in await owner.fetch(
                "SELECT p.oid::pg_catalog.regprocedure::pg_catalog.text AS sig "
                "FROM pg_catalog.pg_proc p "
                "WHERE p.proname OPERATOR(pg_catalog.=) $1 "
                "AND p.pronamespace OPERATOR(pg_catalog.=) 'public'::pg_catalog.regnamespace",
                function,
            ):
                await owner.execute(f"GRANT EXECUTE ON FUNCTION {signature['sig']} TO {role}")
        await owner.execute("SELECT public.ledger_guard_partitions()")
