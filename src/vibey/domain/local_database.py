# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The names a local vibey database is made with, and the password file that keeps its secrets.

`vibey install --database` makes the two roles ADR-0055 separates -- the schema's owner and the
application role -- and the database the owner owns. Their passwords never appear in a DSN, on
a command line or in vibey's output: they live in libpq's own password file (`~/.pgpass`), which
`psql`, libpq and asyncpg all read, so each role's DSN is password-free and every connection
still proves a password with scram-sha-256 (sub-doctrine 10.j, ADR-0061).

Pure rules only: what a name may be, the DSN each role connects with, and how password-file
lines are read and added. Reading and writing the file is the infrastructure's.

Declared by `interfaces/local_database_interface.py` (ADR-0016).
"""

import re
from dataclasses import dataclass
from typing import Final

from vibey.domain.errors import VibeyError

#: A name PostgreSQL keeps as written without quoting, and no longer than it keeps (63 bytes).
#: Plain lowercase identifiers only, so a name can never change the SQL it is put into.
_IDENTIFIER: Final = re.compile(r"[a-z_][a-z0-9_]{0,62}")
#: Characters that would end or split the host part of a DSN.
_HOST_BREAKERS: Final = frozenset(":/@ ?#")
_MAX_PORT: Final = 65535
#: libpq's password-file format: five `:`-separated fields, `\` escaping `:` and itself.
_FIELDS: Final = 5


class InvalidDatabaseName(VibeyError):
    """A database, role, host or port that `vibey install --database` will not use."""


@dataclass(frozen=True, slots=True)
class LocalDatabaseNames:
    """The database, its two roles, and where the server listens."""

    database: str
    owner_role: str
    app_role: str
    host: str
    port: int

    def __post_init__(self) -> None:
        for label, value in (
            ("database", self.database),
            ("owner role", self.owner_role),
            ("application role", self.app_role),
        ):
            if _IDENTIFIER.fullmatch(value) is None:
                raise InvalidDatabaseName(
                    f"the {label} name {value!r} is not a plain lowercase identifier: use "
                    "letters a-z, digits and _, starting with a letter or _, at most 63"
                )
        if self.owner_role == self.app_role:
            raise InvalidDatabaseName(
                "the owner role and the application role must differ: the application role "
                "may not own the schema (ADR-0055)"
            )
        if not self.host or any(ch in _HOST_BREAKERS for ch in self.host):
            raise InvalidDatabaseName(f"the host {self.host!r} cannot be put in a DSN")
        if not 0 < self.port <= _MAX_PORT:
            raise InvalidDatabaseName(f"the port {self.port} is not a TCP port (1-{_MAX_PORT})")

    @property
    def roles(self) -> tuple[str, str]:
        """The owner, then the application role."""
        return (self.owner_role, self.app_role)

    def dsn(self, role: str) -> str:
        """The DSN `role` connects with. No password: libpq and asyncpg find it in the file."""
        return f"postgresql://{role}@{self.host}:{self.port}/{self.database}"

    @property
    def owner_dsn(self) -> str:
        """For `vibey migrate` alone (`VIBEY_PG_MIGRATE_URL`), never exported."""
        return self.dsn(self.owner_role)

    @property
    def app_dsn(self) -> str:
        """What every other vibey command connects with (`VIBEY_PG_URL`)."""
        return self.dsn(self.app_role)


@dataclass(frozen=True, slots=True)
class PgPassEntry:
    """One password-file line. `*` in any of the first four fields matches anything."""

    host: str
    port: int | str
    database: str
    user: str
    password: str


class PgPass:
    """Reads and adds lines of libpq's password file, in its own format."""

    def entries(self, text: str) -> tuple[PgPassEntry, ...]:
        """Every well-formed line, in order. Comments, blanks and short lines are skipped,
        as libpq skips them."""
        found: list[PgPassEntry] = []
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = self._split(line)
            if len(fields) != _FIELDS:
                continue
            found.append(PgPassEntry(*fields))
        return tuple(found)

    def password_for(self, text: str, host: str, port: int, database: str, user: str) -> str | None:
        """The password libpq would use: the first line that matches, or None."""
        wanted = (host, str(port), database, user)
        for entry in self.entries(text):
            have = (entry.host, str(entry.port), entry.database, entry.user)
            if all(field in ("*", value) for field, value in zip(have, wanted, strict=True)):
                return entry.password
        return None

    def with_entry(self, text: str, entry: PgPassEntry) -> str:
        """`text` with `entry` appended as its last line."""
        line = ":".join(
            self._escape(str(field))
            for field in (entry.host, entry.port, entry.database, entry.user, entry.password)
        )
        if text and not text.endswith("\n"):
            text += "\n"
        return f"{text}{line}\n"

    @staticmethod
    def _escape(field: str) -> str:
        return field.replace("\\", "\\\\").replace(":", "\\:")

    @staticmethod
    def _split(line: str) -> list[str]:
        fields: list[str] = []
        current: list[str] = []
        escaped = False
        for ch in line:
            if escaped:
                current.append(ch)
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == ":" and len(fields) < _FIELDS - 1:
                fields.append("".join(current))
                current = []
            else:
                current.append(ch)
        fields.append("".join(current))
        return fields
