# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`psql`, run as the local PostgreSQL's administrator, for `vibey install --database`.

Creating a database and its roles needs the server's administrator, and who that is depends on
how the server was installed -- the same split `PostgresLocalService` installs by:

- **Homebrew** (or a server no package manager installed): the person themselves. `initdb`
  made their own account the superuser, so `psql` runs as them.
- **apt-get or dnf**: the `postgres` account, reached with `sudo -u postgres` (or `runuser`
  as root without sudo). sudo asks for the person's password on the terminal; vibey never
  sees it.

`--admin-user` names another account. The SQL goes to `psql` on its standard input, never on
its command line, so nothing about a role is visible in the process list; and the only secret
it ever carries is a SCRAM verifier, which `PostgresAdminFailed` redacts too.

Declared by `interfaces/postgres_admin_interface.py` (ADR-0016).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess  # nosec B404 - fixed argv, never shell=True
from collections.abc import Callable
from typing import Final

from vibey.domain.errors import VibeyError
from vibey.infrastructure.interfaces.postgres_interface import PostgresLocalServiceInterface
from vibey.infrastructure.postgres import PostgresCommandResult

type SqlRunner = Callable[[tuple[str, ...], str], PostgresCommandResult]

#: The account apt-get's and dnf's PostgreSQL packages make the superuser.
PACKAGE_ADMIN: Final = "postgres"
#: `psql` quiet, unaligned, tuples only, no ~/.psqlrc, stopping at the first error.
PSQL_FLAGS: Final = ("-X", "-q", "-t", "-A", "-v", "ON_ERROR_STOP=1")
_TIMEOUT_SECONDS: Final = 120.0
_VERIFIER: Final = re.compile(r"SCRAM-SHA-256\$[^'\s]*")


class PostgresAdminUnavailable(VibeyError):
    """There is no `psql`, or no way to run it as the administrator."""


class PostgresAdminFailed(VibeyError):
    """`psql` ran as the administrator and failed."""


class PostgresAdmin:
    """Declared by `PostgresAdminInterface`. `argv` is the command up to and including
    `psql`; `runner` is a seam for tests."""

    def __init__(self, argv: tuple[str, ...], *, runner: SqlRunner | None = None) -> None:
        self.argv = argv
        self._runner: SqlRunner = runner or self.run

    @classmethod
    def for_local(
        cls,
        service: PostgresLocalServiceInterface,
        *,
        admin_user: str | None,
        current_user: str,
        which: Callable[[str], str | None] = shutil.which,
        effective_uid: Callable[[], int] = os.geteuid,
    ) -> PostgresAdmin:
        psql = service.tool("psql")
        if psql is None:
            raise PostgresAdminUnavailable(
                "psql, PostgreSQL's client, is not installed here: run `vibey install "
                "--postgres` first"
            )
        user = admin_user or (
            current_user if service.package_manager() in (None, "brew") else PACKAGE_ADMIN
        )
        if user == current_user:
            return cls((psql,))
        if which("sudo") is not None:
            return cls(("sudo", "-u", user, psql))
        if effective_uid() == 0 and which("runuser") is not None:
            return cls(("runuser", "-u", user, "--", psql))
        raise PostgresAdminUnavailable(
            f"the PostgreSQL administrator here is the {user!r} account, and running psql as "
            "it needs sudo, which is not installed: install sudo, run this as that account, "
            "or name an account that may administer PostgreSQL with --admin-user"
        )

    def query(self, sql: str, database: str) -> tuple[str, ...]:
        result = self._psql(sql, database)
        return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())

    def execute(self, sql: str, database: str) -> None:
        self._psql(sql, database)

    def _psql(self, sql: str, database: str) -> PostgresCommandResult:
        result = self._runner((*self.argv, *PSQL_FLAGS, "-d", database, "-f", "-"), sql)
        if result.returncode != 0:
            said = _VERIFIER.sub(
                "SCRAM-SHA-256$<redacted>", (result.stderr or result.stdout).strip()
            )
            raise PostgresAdminFailed(
                f"psql as the PostgreSQL administrator failed (exit {result.returncode}): "
                f"{said or 'no output'}"
            )
        return result

    @staticmethod
    def run(argv: tuple[str, ...], stdin: str) -> PostgresCommandResult:
        """Run `argv` with `stdin` as its input, from `/` (an account sudo switches to may not
        read the person's folder). A process that could not run is exit 1, never a raise."""
        try:
            done = subprocess.run(  # nosec B603 - fixed argv, never shell=True
                argv,
                input=stdin,
                capture_output=True,
                text=True,
                cwd="/",
                check=False,
                timeout=_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return PostgresCommandResult(returncode=1, stderr=str(exc))
        return PostgresCommandResult(done.returncode, done.stdout, done.stderr)
