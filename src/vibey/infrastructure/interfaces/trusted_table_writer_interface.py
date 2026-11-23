# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over writing one table of the person's own `vibey.toml` (SP-LOOPS Task 7).

Implemented by `infrastructure/trusted_table_writer.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TrustedTableWriterInterface(Protocol):
    def write_table(self, path: Path, table: str, values: Mapping[str, object]) -> None:
        """Makes `[table]` of the `vibey.toml` at `path` hold exactly `values` (strings,
        booleans, integers, lists and tables) and leaves every other byte of the file as it was.
        The file is replaced atomically and ends mode 0600; a missing file and folder are made
        (the folder 0700); a symlinked file is written where it points. Raises `ConfigError`
        naming the file, writing nothing, for a comment inside the table (a rewrite would drop
        it), a table spelt as dotted keys or inline, a value TOML cannot hold exactly, and a file
        that cannot be read, parsed or written."""
        ...

    def render_table(self, table: str, values: Mapping[str, object]) -> str:
        """`[table]` holding `values` as `write_table` writes it, for a person to paste when
        the file cannot be rewritten. Raises `ConfigError` for a value TOML cannot hold."""
        ...
