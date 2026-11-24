# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey install --database` and `vibey install --model`: the two local pieces a first project
needs besides the PostgreSQL server (`--postgres`), each a command of its own so it is useful
alone and `scripts/install.sh --full` only has to call it (ADR-0082).

- **`--database`** makes the database and the two roles of ADR-0055 on the local PostgreSQL,
  keeps their passwords in libpq's password file, and migrates (`LocalDatabaseSetup`). It
  prints the one line a person keeps -- `export VIBEY_PG_URL=...`, password-free -- and the
  one-command form of `vibey migrate`, whose owner DSN is never exported. vibey reads
  `VIBEY_PG_URL` from the environment only, so printing that line is as far as it goes.
- **`--model`** pulls the model the local loop runs -- `VIBEY_OLLAMA_MODEL`, then
  `VIBEY_SOVEREIGN_MODEL`, then the sovereign default (ADR-0099) -- into the Ollama at
  `VIBEY_OLLAMA_URL` (`OllamaModelPuller`), saying its download size first when vibey knows it.

Exit codes: 0 done (or already done), 1 a step failed or the ledger guard is not in force, 2 a
name or URL vibey will not use.

Declared by `interfaces/local_install_interface.py` (ADR-0016).
"""

from __future__ import annotations

import getpass
import os
from collections.abc import Callable, Mapping
from typing import Final

import typer

from vibey.cli.interfaces.local_install_interface import LocalInstallCommandInterface
from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.sovereign_model_interface import SovereignModelsInterface
from vibey.domain.local_database import InvalidDatabaseName, LocalDatabaseNames
from vibey.domain.sovereign_model import SOVEREIGN_CATALOG
from vibey.infrastructure.db.interfaces.local_database_setup_interface import (
    LocalDatabaseSetupInterface,
)
from vibey.infrastructure.db.interfaces.pgpass_file_interface import PgPassFileInterface
from vibey.infrastructure.db.interfaces.postgres_admin_interface import PostgresAdminInterface
from vibey.infrastructure.db.local_database_setup import LocalDatabaseReport, LocalDatabaseSetup
from vibey.infrastructure.db.pgpass_file import PgPassFile
from vibey.infrastructure.db.postgres_admin import PostgresAdmin
from vibey.infrastructure.interfaces.ollama_pull_interface import OllamaModelPullerInterface
from vibey.infrastructure.interfaces.postgres_interface import PostgresLocalServiceInterface
from vibey.infrastructure.ollama_models import DEFAULT_OLLAMA_URL
from vibey.infrastructure.ollama_pull import OLLAMA_URL_ENV, OllamaModelPuller
from vibey.infrastructure.postgres import POSTGRES_LOCAL_PORT, PostgresLocalService

EXIT_FAILED: Final = 1
EXIT_USAGE: Final = 2
LOCAL_HOST: Final = "localhost"
DEFAULT_DATABASE: Final = "vibey"
DEFAULT_OWNER_ROLE: Final = "vibey"
#: The application role's name everywhere else vibey names one (the chart's
#: `postgres.appRole`, the supervisor's environment file).
DEFAULT_APP_ROLE: Final = "vibey_app"
STILL_YOURS: Final = (
    "Still yours: require scram-sha-256 for every connection in pg_hba.conf (SECURITY.md §7, "
    "sub-doctrine 10.j), giving the administrator's role a password first; `vibey doctor` "
    "fails local-auth and db-passwordless until then"
)

type SetupFactory = Callable[
    [PostgresAdminInterface, PgPassFileInterface, LocalDatabaseNames], LocalDatabaseSetupInterface
]
type PullerFactory = Callable[..., OllamaModelPullerInterface]


class LocalInstallCommand:
    """Declared by `LocalInstallCommandInterface`. Every factory is a seam for tests."""

    def __init__(
        self,
        *,
        service_factory: Callable[[], PostgresLocalServiceInterface] = PostgresLocalService,
        setup_factory: SetupFactory | None = None,
        puller_factory: PullerFactory = OllamaModelPuller,
        environ: Mapping[str, str] | None = None,
        current_user: Callable[[], str] = getpass.getuser,
        catalog: SovereignModelsInterface = SOVEREIGN_CATALOG,
    ) -> None:
        self._service_factory = service_factory
        self._setup_factory = setup_factory or self._real_setup
        self._puller_factory = puller_factory
        self._environ = environ
        self._current_user = current_user
        self._catalog = catalog

    def database(
        self, *, db_name: str, owner_role: str, app_role: str, admin_user: str | None
    ) -> int:
        try:
            names = LocalDatabaseNames(
                db_name, owner_role, app_role, LOCAL_HOST, POSTGRES_LOCAL_PORT
            )
        except InvalidDatabaseName as exc:
            typer.echo(f"error: {exc}", err=True)
            return EXIT_USAGE
        service = self._service_factory()
        status = service.status()
        if not status.ready:
            typer.echo(
                f"PostgreSQL is not ready here ({status.detail}): run `vibey install "
                "--postgres` first, then `vibey install --database` again",
                err=True,
            )
            return EXIT_FAILED
        try:
            admin = PostgresAdmin.for_local(
                service, admin_user=admin_user, current_user=self._current_user()
            )
            report = self._setup_factory(admin, PgPassFile(environ=self._env()), names).apply()
        except VibeyError as exc:
            typer.echo(f"error: {exc}", err=True)
            return EXIT_FAILED
        return self._said(report)

    def model(self, *, wait_seconds: float) -> int:
        environ = self._env()
        url = environ.get(OLLAMA_URL_ENV) or DEFAULT_OLLAMA_URL
        tag = self._catalog.from_environment(environ)
        variant = self._catalog.variant_of(tag)
        try:
            puller = self._puller_factory(url, wait_seconds=wait_seconds)
        except ValueError as exc:
            typer.echo(f"error: {exc}", err=True)
            return EXIT_USAGE
        result = puller.install(
            tag, typer.echo, None if variant is None else f"about {variant.download}"
        )
        typer.echo(result.detail, err=not result.ok)
        return 0 if result.ok else EXIT_FAILED

    def _env(self) -> Mapping[str, str]:
        return os.environ if self._environ is None else self._environ

    @staticmethod
    def _real_setup(
        admin: PostgresAdminInterface, pgpass: PgPassFileInterface, names: LocalDatabaseNames
    ) -> LocalDatabaseSetupInterface:
        return LocalDatabaseSetup(admin=admin, pgpass=pgpass, names=names)

    @staticmethod
    def _said(report: LocalDatabaseReport) -> int:
        names = report.names
        made = []
        if report.created_roles:
            plural = "s" if len(report.created_roles) > 1 else ""
            made.append(f"the role{plural} {' and '.join(report.created_roles)}")
        if report.database_created:
            made.append(f"the database {names.database}")
        if made:
            typer.echo(f"created {' and '.join(made)}")
        else:
            typer.echo(
                f"the roles {' and '.join(names.roles)} and the database {names.database} "
                "were already there"
            )
        typer.echo(
            f"their passwords are in {report.password_file}, readable by you alone; vibey "
            "never prints them"
        )
        applied = report.migration.applied
        typer.echo(
            f"applied {len(applied)} migration(s)" + (f": {', '.join(applied)}" if applied else "")
        )
        guard = report.migration.guard
        if guard is None:
            typer.echo("the ledger guard was not checked", err=True)
            return EXIT_FAILED
        typer.echo(f"ledger guard {guard.describe()}")
        typer.echo(
            "Add this line to your shell profile (~/.zshrc, ~/.bashrc or ~/.profile) and open "
            "a new terminal, so every vibey command finds the database:"
        )
        typer.echo(f"  export VIBEY_PG_URL={names.app_dsn}")
        typer.echo(
            "To migrate after an upgrade, give the owner's DSN to that one command, never exported:"
        )
        typer.echo(f"  VIBEY_PG_MIGRATE_URL={names.owner_dsn} vibey migrate")
        typer.echo(STILL_YOURS)
        return 0 if guard.in_force else EXIT_FAILED


LOCAL_INSTALL: Final[LocalInstallCommandInterface] = LocalInstallCommand()
"""The command `vibey install --database` and `--model` run, annotated with its interface so
`mypy --strict` checks the class against its declared seam."""
