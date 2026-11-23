# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The port a trusted-config rule reads `vibey.toml` tables through (ADR-0101).

The rule -- the person's own file grants, a project's may only narrow -- is pure and lives in
`application/`; reading a file is infrastructure's (`infrastructure/trusted_table_reader.py`),
wired in `bootstrap.py`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TrustedTableReaderInterface(Protocol):
    def read_table(self, path: Path, table: str) -> Mapping[str, object] | None:
        """`[table]` of the `vibey.toml` at `path`: None when there is no file, an empty
        mapping when the file has no such table. Raises `ConfigError(str(path), …)` for a file
        that cannot be read, is not a regular file, is too large or is not valid TOML, and for
        a `table` that is not a table."""
        ...

    def same_file(self, first: Path, second: Path) -> bool:
        """Whether the two paths name one file once resolved (so the person's own file, opened
        as a project's, is not read as a project)."""
        ...
