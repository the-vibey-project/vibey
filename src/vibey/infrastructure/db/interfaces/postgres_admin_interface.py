# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for running SQL as the local PostgreSQL's administrator.

Mirrors `vibey/infrastructure/db/postgres_admin.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PostgresAdminInterface(Protocol):
    def query(self, sql: str, database: str) -> tuple[str, ...]:
        """Run `sql` in `database` and return its non-empty output lines."""
        ...

    def execute(self, sql: str, database: str) -> None:
        """Run `sql` in `database`; raises `PostgresAdminFailed` on the first error."""
        ...
