# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Bringing a database to the migrated, guarded state, with the right role for each step.

`SchemaPreparer` is what `build_app()` runs on every start, on the application's own
connection:

- **A split install with the owner's DSN** (`VIBEY_PG_MIGRATE_URL`) migrates on a
  separate owner connection, then reconciles the application role's grants.
- **A single-DSN install** (the application role may migrate: a superuser or the
  schema's owner) migrates as today. The guard is not in force, and the returned status
  says why -- `build_app()` logs it at every start and `vibey doctor` fails on it.
- **A split install without it** (the Helm worker, whose migrations ran in its init
  container) migrates nothing and refuses to start on a stale schema.

`OwnerMigration` is `vibey migrate`: the owner's DSN, then the reconcile, then the
guard inspected from the application's side. Declared by
`interfaces/database_setup_interface.py` (ADR-0016).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import asyncpg

from vibey.infrastructure.db.interfaces.ledger_guard_interface import (
    DatabaseRoleReconcilerInterface,
    LedgerGuardInspectorInterface,
)
from vibey.infrastructure.db.interfaces.migrator_interface import MigratorInterface
from vibey.infrastructure.db.ledger_guard import (
    DatabaseEndpoints,
    LedgerGuardStatus,
    SchemaNotMigrated,
)
from vibey.infrastructure.db.migrator import Migration, OwnedConnection

type Connector = Callable[[str], Awaitable[asyncpg.Connection]]


class SchemaPreparer:
    """Migrates (or verifies) and reports the guard, on every start."""

    def __init__(
        self,
        *,
        migrator: MigratorInterface,
        reconciler: DatabaseRoleReconcilerInterface,
        inspector: LedgerGuardInspectorInterface,
        connect: Connector = asyncpg.connect,
    ) -> None:
        self._migrator = migrator
        self._reconciler = reconciler
        self._inspector = inspector
        self._connect = connect

    async def prepare(
        self,
        app: OwnedConnection,
        endpoints: DatabaseEndpoints,
        migrations: tuple[Migration, ...],
    ) -> LedgerGuardStatus:
        if endpoints.migrate_url is not None:
            owner = await self._connect(endpoints.migrate_url)
            try:
                await self._migrator.apply(owner, migrations)
                # A privileged application role (the owner again, or a superuser) has
                # nothing to reconcile; the inspection below reports it instead of the
                # start failing, so a misconfigured split never strands an install.
                if not await self._migrator.may_migrate(app):
                    role = str(await app.fetchval("SELECT current_user"))
                    await self._reconciler.reconcile(owner, app_role=role)
            finally:
                await owner.close()
        elif await self._migrator.may_migrate(app):
            await self._migrator.apply(app, migrations)
        else:
            pending = await self._migrator.pending(app, migrations)
            if pending:
                raise SchemaNotMigrated(pending)
        return await self._inspector.inspect(app)


@dataclass(frozen=True, slots=True)
class MigrationReport:
    """What `vibey migrate` did, and the guard as the application will see it."""

    applied: tuple[str, ...]
    reconciled_role: str | None
    guard: LedgerGuardStatus | None


class OwnerMigration:
    """`vibey migrate`: migrate as the owner, reconcile the application role, inspect."""

    def __init__(
        self,
        *,
        migrator: MigratorInterface,
        reconciler: DatabaseRoleReconcilerInterface,
        inspector: LedgerGuardInspectorInterface,
        connect: Connector = asyncpg.connect,
    ) -> None:
        self._migrator = migrator
        self._reconciler = reconciler
        self._inspector = inspector
        self._connect = connect

    async def run(
        self,
        *,
        owner_url: str,
        app: DatabaseEndpoints | None,
        migrations: tuple[Migration, ...],
    ) -> MigrationReport:
        """Migrate with `owner_url`. With `app`, reconcile the role its DSN names --
        unless that is the owner itself, which no grant can guard -- then connect as it
        and inspect the guard. Without `app`, migrate only."""
        owner = await self._connect(owner_url)
        try:
            applied = await self._migrator.apply(owner, migrations)
            if app is None:
                return MigrationReport(applied, None, None)
            owner_role = str(await owner.fetchval("SELECT current_user"))
            role = app.app_role
            reconciled: str | None = None
            if role is not None and role != owner_role:
                await self._reconciler.reconcile(
                    owner, app_role=role, app_password=app.app_password
                )
                reconciled = role
        finally:
            await owner.close()
        connection = await self._connect(app.app_url)
        try:
            guard = await self._inspector.inspect(connection)
        finally:
            await connection.close()
        return MigrationReport(applied, reconciled, guard)
