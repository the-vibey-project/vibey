# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for local PostgreSQL discovery and installation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.postgres import PostgresInstallResult, PostgresStatus


@runtime_checkable
class PostgresLocalServiceInterface(Protocol):
    """Inspects and, on explicit request, installs a local PostgreSQL service."""

    def status(self) -> PostgresStatus:
        """Return the local PostgreSQL installation and readiness state."""
        ...

    def install(self) -> PostgresInstallResult:
        """Install and start a supported local PostgreSQL service."""
        ...
