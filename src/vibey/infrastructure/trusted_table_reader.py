# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads one table of a `vibey.toml` from disk for a trusted-config rule (ADR-0101).

The same reading the `[acp]`, `[web]` and `[hub]` loaders do privately (`tomllib`, a missing
file is no declaration, a table that is not a table is refused naming the file), offered once as
the application port `TrustedTableReaderInterface`, so a trust rule in `application/` reads no
file itself. Unlike those private readers it is bounded: the file is opened without blocking,
must be a regular file (a FIFO or a folder at the path is refused, never waited on), and at most
`MAX_CONFIG_BYTES` are read. A symlinked config -- dotfiles -- is followed: the path is the
person's choice. Declared by `application/interfaces/trusted_table_reader_interface.py`.
"""

from __future__ import annotations

import os
import stat
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

from vibey.domain.config import ConfigError

MAX_CONFIG_BYTES: Final = 1024 * 1024
"""The largest `vibey.toml` read for a trusted table."""


class TomlTrustedTableReader:
    """Declared by `application/interfaces/trusted_table_reader_interface.py`."""

    def __init__(self, opener: Callable[[Path], int] | None = None) -> None:
        self._open = opener or self._open_nonblocking

    def read_table(self, path: Path, table: str) -> Mapping[str, object] | None:
        if not path.exists():
            return None
        try:
            descriptor = self._open(path)
        except OSError as exc:
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ConfigError(str(path), "is not a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            data = handle.read(MAX_CONFIG_BYTES + 1)
        if len(data) > MAX_CONFIG_BYTES:
            raise ConfigError(str(path), f"is larger than {MAX_CONFIG_BYTES} bytes")
        try:
            document = tomllib.loads(data.decode("utf-8"))
        except ValueError as exc:  # a TOMLDecodeError, or bytes that are not UTF-8
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        section = document.get(table, {})
        if not isinstance(section, dict):
            raise ConfigError(str(path), f"[{table}] must be a table")
        return section

    def same_file(self, first: Path, second: Path) -> bool:
        return first.resolve() == second.resolve()

    @staticmethod
    def _open_nonblocking(path: Path) -> int:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
