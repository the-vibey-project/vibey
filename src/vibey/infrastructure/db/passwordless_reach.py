# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Can the app DSN's database be opened with no password, from the worker's OS user?

vibey keeps `VIBEY_PG_URL` out of every model-driven process (SECURITY.md §5). That
protects the queue and the ledger only while holding the DSN is what it takes to reach
them. A local PostgreSQL commonly accepts `trust` or `peer` authentication on its
socket or on localhost: any process running as the worker's OS user -- every engine
session and gate command is one -- then connects as that user, or as the DSN's own
role, without the DSN and without a password. Review reproduced exactly that, as the
operator's own user, on a development machine.

`PasswordlessReachProbe` finds out the direct way: it tries. For the DSN's role and the
OS user, on the DSN's own host and -- when that host is local -- on each local socket
directory, it attempts a connection to the DSN's database with an empty password
(which also keeps libpq's `PGPASSWORD` and passfile out of it). One that is let in is a
failure; attempts that are all refused are a pass; no attempt reaching the server is
unknown, never a pass. It is a failure, not a warning: sub-doctrine 10.j (ADR-0061) makes
scram-sha-256 the only way any connection the project configures authenticates, local
or remote, so a trusted local database is no longer a choice `vibey doctor` lets pass.

Declared by `interfaces/passwordless_reach_interface.py` (ADR-0016).
"""

import getpass
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit

import asyncpg

type Connector = Callable[..., Awaitable[Any]]

# PostgreSQL's usual socket directories, probed read-only.
DEFAULT_SOCKET_DIRS: Final = ("/tmp", "/var/run/postgresql", "/run/postgresql")  # nosec B108
_LOCAL_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})


class ReachVerdict(StrEnum):
    FAIL = "fail"
    PASS = "pass"  # nosec B105 - a verdict name, not a password
    UNKNOWN = "unknown"

    @property
    def mark(self) -> str:
        """How `vibey doctor` prints it."""
        return self.value.upper()


@dataclass(frozen=True, slots=True)
class PasswordlessReachFinding:
    verdict: ReachVerdict
    detail: str


class PasswordlessReachProbe:
    """Tries the app DSN's database with an empty password. Declared by
    `interfaces/passwordless_reach_interface.py`."""

    __slots__ = ("_connect", "_os_user", "_socket_dirs", "_timeout")

    def __init__(
        self,
        *,
        connect: Connector = asyncpg.connect,
        socket_dirs: Sequence[str] = DEFAULT_SOCKET_DIRS,
        os_user: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._connect = connect
        self._socket_dirs = tuple(socket_dirs)
        self._os_user = getpass.getuser() if os_user is None else os_user
        self._timeout = timeout_seconds

    def endpoints(self, dsn: str) -> tuple[tuple[str, int], ...]:
        parts = urlsplit(dsn)
        port = parts.port or 5432
        host = parts.hostname or parse_qs(parts.query).get("host", [""])[0]
        found: list[tuple[str, int]] = []
        if host:
            found.append((host, port))
        if not host or host in _LOCAL_HOSTS or host.startswith("/"):
            found.extend((directory, port) for directory in self._socket_dirs)
        return tuple(dict.fromkeys(found))

    def roles(self, dsn: str) -> tuple[str, ...]:
        user = urlsplit(dsn).username
        return tuple(dict.fromkeys(role for role in (user, self._os_user) if role))

    def database(self, dsn: str) -> str:
        parts = urlsplit(dsn)
        return parts.path.lstrip("/") or parts.username or self._os_user

    async def probe(self, dsn: str) -> PasswordlessReachFinding:
        database = self.database(dsn)
        admitted: list[str] = []
        refused = 0
        for role in self.roles(dsn):
            for host, port in self.endpoints(dsn):
                outcome = await self._knock(host, port, role, database)
                if outcome is True:
                    admitted.append(f"{role} via {host}:{port}")
                elif outcome is False:
                    refused += 1
        if admitted:
            return PasswordlessReachFinding(
                ReachVerdict.FAIL,
                f"database {database!r} accepts a password-less login as "
                f"{', '.join(admitted)} (trust or peer authentication): any process "
                f"running as OS user {self._os_user!r} -- engine sessions included -- can "
                "open it without VIBEY_PG_URL; sub-doctrine 10.j requires scram-sha-256 "
                "for these connections (SECURITY.md §5, §7)",
            )
        if refused == 0:
            return PasswordlessReachFinding(
                ReachVerdict.UNKNOWN,
                f"could not reach the server to try a password-less login to {database!r}",
            )
        return PasswordlessReachFinding(
            ReachVerdict.PASS,
            f"{refused} password-less attempt(s) refused for {database!r} as "
            f"{', '.join(self.roles(dsn))}",
        )

    async def _knock(self, host: str, port: int, role: str, database: str) -> bool | None:
        """True if let in with an empty password, False if authentication refused it,
        None if it could not tell (unreachable, no such database, anything else)."""
        try:
            conn = await self._connect(
                host=host,
                port=port,
                user=role,
                database=database,
                # The point of the probe: an EMPTY password, which also keeps
                # PGPASSWORD and the passfile out of the attempt.
                password="",  # nosec B106
                timeout=self._timeout,
            )
        except (asyncpg.InvalidAuthorizationSpecificationError, asyncpg.InvalidPasswordError):
            return False
        except Exception:  # noqa: BLE001 - any other outcome says nothing about auth
            return None
        await conn.close()
        return True
