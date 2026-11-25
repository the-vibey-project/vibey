# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""libpq's password file, where `vibey install --database` keeps its roles' passwords.

The file libpq, `psql` and asyncpg all read: `PGPASSFILE` when set, else `~/.pgpass`. vibey
writes it whole, through a temporary file in the same folder that is readable by its owner
alone and then renamed over it, so a crash leaves the old file or the new one and never half
of either, and the result is mode 0600 (libpq and asyncpg ignore a file others may read).
`CONTRIBUTING.md` and `vibey-gh`'s contributor setup already keep the contributor's own
password here; this is the same file, for the same reason (sub-doctrine 10.j: a password-free
DSN that still proves a password).

Declared by `interfaces/pgpass_file_interface.py` (ADR-0016).
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

PGPASSFILE_ENV: Final = "PGPASSFILE"
DEFAULT_NAME: Final = ".pgpass"
PRIVATE_MODE: Final = 0o600


class PgPassFile:
    """Declared by `PgPassFileInterface`. `environ` and `home` are seams for tests."""

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        home: Callable[[], Path] = Path.home,
    ) -> None:
        self._environ = os.environ if environ is None else environ
        self._home = home

    def path(self) -> Path:
        named = self._environ.get(PGPASSFILE_ENV, "").strip()
        return Path(named).expanduser() if named else self._home() / DEFAULT_NAME

    def read(self) -> str:
        try:
            return self.path().read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def write(self, text: str) -> None:
        path = self.path()
        # mkstemp creates the file 0600, so no moment exists when another user may read it.
        handle, temporary = tempfile.mkstemp(prefix=f"{DEFAULT_NAME}.", dir=path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, PRIVATE_MODE)
            os.replace(temporary, path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary)
            raise
