# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads one table of a `vibey.toml` from disk for a trusted-config rule (ADR-0101).

The same reading the `[acp]`, `[web]` and `[hub]` loaders do privately (`tomllib`, a missing file is
no declaration, a table that is not a table is refused naming the file), offered once as the
application port `TrustedTableReaderInterface`, so a trust rule in `application/` reads no file
itself. Nothing but `ConfigError` leaves it: no file is None, and a symlink loop, a folder that
cannot be searched, bytes that are not UTF-8 and nesting deep enough to exhaust `tomllib`'s
recursion are each refused naming the file. Unlike those private readers it is bounded: the file is
opened without blocking, must be a regular file (a FIFO or a folder at the path is refused, never
waited on), and at most `MAX_CONFIG_BYTES` are read. A symlinked config -- dotfiles -- is followed:
the path is the person's choice. Declared by
`application/interfaces/trusted_table_reader_interface.py`.
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
        text = self.read_text(path)
        if text is None:
            return None
        section = self.parse(path, text).get(table, {})
        if not isinstance(section, dict):
            raise ConfigError(str(path), f"[{table}] must be a table")
        return section

    def read_text(self, path: Path) -> str | None:
        """The whole file as text, read the bounded way this class reads every file, or None when
        there is none. Raises `ConfigError` naming the file and nothing else. Not part of the
        application port: `TomlTrustedTableWriter` reads the file it rewrites through it."""
        try:
            descriptor = self._open(path)
        except (FileNotFoundError, NotADirectoryError):
            return None  # no file (a dangling link included): no declaration
        except OSError as exc:  # a symlink loop, a folder that cannot be searched, ...
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ConfigError(str(path), "is not a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            data = handle.read(MAX_CONFIG_BYTES + 1)
        if len(data) > MAX_CONFIG_BYTES:
            raise ConfigError(str(path), f"is larger than {MAX_CONFIG_BYTES} bytes")
        try:
            return data.decode("utf-8")
        except ValueError as exc:  # bytes that are not UTF-8
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc

    @staticmethod
    def parse(path: Path, text: str) -> dict[str, object]:
        """`text` as a TOML document; `ConfigError` naming `path` when it is not one."""
        try:
            return tomllib.loads(text)
        except ValueError as exc:  # a TOMLDecodeError
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        except RecursionError as exc:  # tomllib recurses: ~500 nested `[` is about 1 KB
            raise ConfigError(str(path), "is not valid TOML: nested too deeply") from exc

    def same_file(self, first: Path, second: Path) -> bool:
        try:
            return first.resolve() == second.resolve()
        except (OSError, RuntimeError):  # 3.12 raises RuntimeError for a symlink loop
            return False  # not provably the person's file: it is read, and refused, as a project's

    @staticmethod
    def _open_nonblocking(path: Path) -> int:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
