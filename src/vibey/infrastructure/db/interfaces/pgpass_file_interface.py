# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for libpq's password file.

Mirrors `vibey/infrastructure/db/pgpass_file.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class PgPassFileInterface(Protocol):
    def path(self) -> Path:
        """Where libpq looks: `PGPASSFILE`, else `~/.pgpass`."""
        ...

    def read(self) -> str:
        """The file's text; empty when there is no file."""
        ...

    def write(self, text: str) -> None:
        """Replace the file whole, atomically, readable by its owner alone."""
        ...
