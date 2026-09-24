# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Forward-only SQL migrations, applied in lexical order and tracked in
schema_migration(version, applied_at, checksum).

They run as the schema's owner (ADR-0055): `vibey migrate`, or `build_app()` on every
start when it holds the owner's DSN (`VIBEY_PG_MIGRATE_URL`) or its own role may
migrate; otherwise `build_app()` only verifies, with `pending`. Every run also
re-verifies the checksum of each applied migration: an
edited, already-applied migration is a bug, not a convenience, and it fails the
start with `MigrationChecksumError`.

Runs are serialized. Pods that start together (a KEDA scale-out, a Helm
rollout) would otherwise each read the same applied set and race to apply the
same pending migration. `PostgresMigrator.apply` holds a session-level Postgres
advisory lock from before it creates `schema_migration` until the last pending
migration has committed, so one process migrates and the rest wait, then find
nothing left to do. The wait is bounded, so a wedged holder fails its waiters
loudly, naming its backend pid, instead of hanging them.
"""

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import asyncpg

from vibey.domain.errors import VibeyError

type OwnedConnection = asyncpg.pool.PoolConnectionProxy | asyncpg.Connection


class MigrationChecksumError(VibeyError):
    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(
            f"migration {version!r} has changed since it was applied "
            "-- edited migrations are not allowed"
        )


class MigrationLockTimeout(VibeyError):
    """Another process held the migration lock for longer than this one would wait."""

    def __init__(self, key: int, timeout_seconds: float, holders: tuple[int, ...]) -> None:
        self.key = key
        self.timeout_seconds = timeout_seconds
        self.holders = holders
        held_by = ", ".join(str(pid) for pid in holders) or "none (released as this wait gave up)"
        super().__init__(
            f"gave up after {timeout_seconds:g}s waiting for the migration lock "
            f"(advisory key {key}); held by backend pid(s): {held_by}. "
            "Look the holder up by pid in pg_stat_activity, "
            f"or wait longer by raising {PostgresMigrator.LOCK_TIMEOUT_ENV}."
        )


class InvalidMigrationLockTimeout(VibeyError):
    """The configured wait is not a number of seconds Postgres can honour."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(
            f"migration lock timeout {value!r} is not a number of seconds from 0 "
            f"(wait indefinitely) to {PostgresMigrator.MAX_LOCK_TIMEOUT_MS / 1000:g}; "
            f"set {PostgresMigrator.LOCK_TIMEOUT_ENV} to one, or unset it for the "
            f"{PostgresMigrator.DEFAULT_LOCK_TIMEOUT_SECONDS:g}s default"
        )


class MigrationInsideTransaction(VibeyError):
    """apply() was handed a connection with a transaction already open."""

    def __init__(self) -> None:
        super().__init__(
            "migrations must run on a connection with no open transaction: each one "
            "commits on its own while the migration lock is held, and inside an outer "
            "transaction nothing would commit until after the lock was released"
        )


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    path: Path
    sql: str
    checksum: str


def _checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode()).hexdigest()


def discover_migrations(directory: Path) -> tuple[Migration, ...]:
    migrations = []
    for path in sorted(directory.glob("*.sql")):
        sql = path.read_text()
        migrations.append(Migration(version=path.stem, path=path, sql=sql, checksum=_checksum(sql)))
    return tuple(migrations)


_ENSURE_SCHEMA_MIGRATION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migration (
    version     text PRIMARY KEY,
    applied_at  timestamptz NOT NULL DEFAULT now(),
    checksum    text NOT NULL
);
"""

# A bigint advisory key is stored in pg_locks as two oids -- classid holds the
# high 32 bits, objid the low 32, objsubid is 1 -- so the key is reassembled
# before comparing. Filtered to this database: advisory locks are per-database,
# and another database on the same server may be migrating under the same key.
_LOCK_HOLDERS = """
SELECT pid
FROM pg_locks
WHERE locktype = 'advisory'
  AND database = (SELECT oid FROM pg_database WHERE datname = current_database())
  AND objsubid = 1
  AND granted
  AND ((classid::bigint << 32) | objid::bigint) = $1
ORDER BY pid
"""


_MAY_MIGRATE = """
SELECT r.rolsuper
    OR CASE
           WHEN to_regclass('schema_migration') IS NULL
               THEN has_schema_privilege('public', 'CREATE')
           ELSE pg_has_role(
               current_user,
               (SELECT relowner FROM pg_class WHERE oid = to_regclass('schema_migration')),
               'MEMBER'
           )
       END
FROM pg_roles r
WHERE r.rolname = current_user
"""


class PostgresMigrator:
    """Applies pending migrations under the migration advisory lock.

    Blocking here is deliberate, and it is not the wait ADR-0029 forbids. That
    rule governs a worker holding a job, which defers on contention because it
    has other work it can do. `apply` runs inside `build_app()`, before anything
    has been claimed, and a process that cannot see a migrated schema has
    nothing else it could do; the alternative to waiting is exiting and being
    restarted to wait again. The bound keeps the wait honest.
    """

    LOCK_NAMESPACE: Final = "vibey.migrate"
    LOCK_KEY: Final = int.from_bytes(
        hashlib.sha256(LOCK_NAMESPACE.encode()).digest()[:8], "big", signed=True
    )
    """ADR-0029's derivation -- the first eight bytes of a namespaced sha256 as
    a signed bigint -- so it cannot collide with the integrate lock or any
    other advisory-lock use in the database.

    A class constant rather than a setting, and deliberately so. ADR-0018 wants
    a key wherever a value could be one, but this value is the contract between
    every process that migrates one database, the old and new releases of a
    rolling upgrade included: two processes configured with different keys
    would not exclude each other at all, and nothing would say so. Separate
    deployments need no key of their own either, because advisory locks are
    scoped to one database. It must never change between releases."""

    LOCK_TIMEOUT_ENV: Final = "VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS"
    DEFAULT_LOCK_TIMEOUT_SECONDS: Final = 300.0
    """Five minutes: longer than any migration this tree ships takes to apply,
    short enough that a wedged holder surfaces as a failed start rather than a
    pod that looks healthy and never arrives."""

    MAX_LOCK_TIMEOUT_MS: Final = 2_147_483_647
    """Postgres's own ceiling on lock_timeout (INT_MAX milliseconds)."""

    def __init__(self, *, lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS) -> None:
        """`lock_timeout_seconds` bounds the wait for another process's
        migration; 0 waits indefinitely, which is Postgres's own meaning for
        lock_timeout = 0."""
        if not (
            math.isfinite(lock_timeout_seconds)
            and lock_timeout_seconds >= 0
            and math.ceil(lock_timeout_seconds * 1000) <= self.MAX_LOCK_TIMEOUT_MS
        ):
            raise InvalidMigrationLockTimeout(repr(lock_timeout_seconds))
        self._lock_timeout_seconds = lock_timeout_seconds
        # Rounded up: a positive wait must never collapse to 0ms, which Postgres
        # reads as "wait forever" -- the opposite of what was asked for.
        self._lock_timeout_ms = math.ceil(lock_timeout_seconds * 1000)

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> "PostgresMigrator":
        """The migrator `build_app()` wires: the wait comes from
        VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS, and unset or blank means the
        default. A value that is not a usable number of seconds fails here
        rather than falling back -- a silent default is how a misconfiguration
        hides until the day it matters."""
        raw = environ.get(cls.LOCK_TIMEOUT_ENV, "").strip()
        if not raw:
            return cls()
        try:
            seconds = float(raw)
        except ValueError:
            raise InvalidMigrationLockTimeout(raw) from None
        return cls(lock_timeout_seconds=seconds)

    @property
    def lock_timeout_seconds(self) -> float:
        return self._lock_timeout_seconds

    async def apply(
        self,
        conn: OwnedConnection,
        migrations: tuple[Migration, ...],
        *,
        check_only: bool = False,
    ) -> tuple[str, ...]:
        """Applies pending migrations in order, each in its own transaction,
        all under the migration lock. Raises MigrationChecksumError if an
        already-applied migration's file has changed, and MigrationLockTimeout
        if another process held the lock past the configured wait. Returns the
        versions applied this call (empty in check_only mode)."""
        if conn.is_in_transaction():
            raise MigrationInsideTransaction()
        await self._acquire(conn)
        try:
            return await self._apply_locked(conn, migrations, check_only=check_only)
        finally:
            # Released on the way out whatever happened, so a failed migration
            # cannot wedge every later start. A connection that died mid-run
            # took the lock with it: Postgres drops a session's locks when the
            # session ends, and a pool reset unlocks all of them too.
            await conn.execute("SELECT pg_advisory_unlock($1)", self.LOCK_KEY)

    async def may_migrate(self, conn: OwnedConnection) -> bool:
        """Whether `conn`'s role may apply migrations: a superuser, a member of the role
        that owns `schema_migration`, or -- on a database never migrated -- a role that
        may create in `public`. The application role of a split install is none of
        these (ADR-0055), even on PostgreSQL 14, where `public` still grants CREATE to
        every role by default."""
        return bool(await conn.fetchval(_MAY_MIGRATE))

    async def pending(
        self, conn: OwnedConnection, migrations: tuple[Migration, ...]
    ) -> tuple[str, ...]:
        """The versions not yet applied, read without DDL and without the lock, so a
        role that may not migrate can still tell a migrated schema from a stale one.
        An applied migration whose file has changed raises MigrationChecksumError, as
        `apply` does."""
        applied: dict[str, str] = {}
        if await conn.fetchval("SELECT to_regclass('schema_migration') IS NOT NULL"):
            rows = await conn.fetch("SELECT version, checksum FROM schema_migration")
            applied = {row["version"]: row["checksum"] for row in rows}
        pending: list[str] = []
        for migration in migrations:
            checksum = applied.get(migration.version)
            if checksum is None:
                pending.append(migration.version)
            elif checksum != migration.checksum:
                raise MigrationChecksumError(migration.version)
        return tuple(pending)

    async def _acquire(self, conn: OwnedConnection) -> None:
        try:
            async with conn.transaction():
                # is_local: the bound applies to this one statement and is gone
                # at COMMIT, so the migrations never run under it. The advisory
                # lock is session-level, so it outlives the transaction.
                await conn.execute(
                    "SELECT set_config('lock_timeout', $1, true)",
                    f"{self._lock_timeout_ms}ms",
                )
                await conn.execute("SELECT pg_advisory_lock($1)", self.LOCK_KEY)
        except asyncpg.exceptions.LockNotAvailableError as exc:
            holders = await conn.fetch(_LOCK_HOLDERS, self.LOCK_KEY)
            raise MigrationLockTimeout(
                self.LOCK_KEY,
                self._lock_timeout_seconds,
                tuple(row["pid"] for row in holders),
            ) from exc

    async def _apply_locked(
        self,
        conn: OwnedConnection,
        migrations: tuple[Migration, ...],
        *,
        check_only: bool,
    ) -> tuple[str, ...]:
        # Inside the lock too: two sessions racing CREATE TABLE IF NOT EXISTS on
        # a fresh database can still collide on the catalog's unique index.
        await conn.execute(_ENSURE_SCHEMA_MIGRATION_TABLE)

        applied_rows = await conn.fetch("SELECT version, checksum FROM schema_migration")
        applied = {row["version"]: row["checksum"] for row in applied_rows}

        newly_applied = []
        for migration in migrations:
            if migration.version in applied:
                if applied[migration.version] != migration.checksum:
                    raise MigrationChecksumError(migration.version)
                continue

            if check_only:
                continue

            async with conn.transaction():
                await conn.execute(migration.sql)
                await conn.execute(
                    "INSERT INTO schema_migration (version, checksum) VALUES ($1, $2)",
                    migration.version,
                    migration.checksum,
                )
            newly_applied.append(migration.version)

        return tuple(newly_applied)


async def apply_migrations(
    conn: OwnedConnection,
    migrations: tuple[Migration, ...],
    *,
    check_only: bool = False,
) -> tuple[str, ...]:
    """`PostgresMigrator().apply` with the default wait.

    A module-level function because it is this module's public façade (the
    exception ADR-0016 names): the test harness migrates its template database
    through it, as do the contract and repository fixtures, and it predates the
    class. New callers that need a configured wait take a `PostgresMigrator`.
    """
    return await PostgresMigrator().apply(conn, migrations, check_only=check_only)
