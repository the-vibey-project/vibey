# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The local PostgreSQL `vibey acp` may install, only once the client allowed it (SP-ACP).

Implemented by `infrastructure/acp/acp_postgres_installer.py` over `PostgresLocalService`'s
fixed argv. Both calls block (they run commands), so the bootstrap runs them off the event
loop. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import PostgresInstallOutcome, PostgresReadiness


@runtime_checkable
class PostgresInstallerInterface(Protocol):
    def status(self) -> PostgresReadiness:
        """Whether PostgreSQL is ready, and the package manager that would install it. Runs
        only read-only commands."""
        ...

    def install(self) -> PostgresInstallOutcome:
        """Install and start PostgreSQL. Never prompts for a password: `sudo -n` only."""
        ...
