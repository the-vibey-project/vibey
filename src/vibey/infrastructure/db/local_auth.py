# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Does the database let a password-less connection in as a role that could rewrite the
ledger? (ADR-0055)

Splitting the roles keeps the ledger append-only only while nobody can simply connect
as the owner or a superuser. A local PostgreSQL commonly accepts `trust` or `peer`
connections on its socket: any process running as the operator's OS user then connects
as a superuser with no DSN and no password at all, and the split protects nothing.

`LocalAuthProbe` finds out two ways and says which it could not:

1. **It tries.** For the ledger's owner and every login superuser, it attempts a
   connection with an empty password: on the application DSN's own host and, when that
   host is local, on each local socket directory. One that is let in is a failure.
2. **It reads `pg_hba_file_rules`** when the connecting role may (a superuser, or one
   granted it): a `trust`, `peer` or `ident` rule that can match the owner or a
   superuser is a failure.

A pass needs both: every attempt refused, and the rules read and clean. Anything less
is `unknown`, printed as such -- never a pass. Declared by
`interfaces/local_auth_interface.py` (ADR-0016).
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final
from urllib.parse import urlsplit

import asyncpg

from vibey.infrastructure.db.migrator import OwnedConnection

type Connector = Callable[..., Awaitable[Any]]

DEFAULT_SOCKET_DIRS: Final = ("/tmp", "/var/run/postgresql", "/run/postgresql")  # nosec B108 - PostgreSQL's socket directories, probed read-only
PASSWORDLESS_METHODS: Final = ("trust", "peer", "ident")
_LOCAL_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})

_PRIVILEGED_ROLES = """
SELECT DISTINCT rolname FROM (
    SELECT pg_get_userbyid(relowner) AS rolname FROM pg_class WHERE oid = to_regclass('event')
    UNION
    SELECT rolname FROM pg_roles WHERE rolsuper AND rolcanlogin
) roles
WHERE rolname IS NOT NULL
ORDER BY rolname
"""

_HBA = """
SELECT line_number, type, database, user_name, auth_method
FROM pg_hba_file_rules
WHERE error IS NULL AND auth_method = ANY($1::text[])
ORDER BY line_number
"""


class AuthVerdict(StrEnum):
    PASS = "pass"  # nosec B105 - a verdict's name, not a password
    FAIL = "fail"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LocalAuthFinding:
    verdict: AuthVerdict
    detail: str


class LocalAuthProbe:
    """Attempts password-less connections as the privileged roles; reads pg_hba."""

    def __init__(
        self,
        *,
        connect: Connector = asyncpg.connect,
        socket_dirs: Sequence[str] = DEFAULT_SOCKET_DIRS,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._connect = connect
        self._socket_dirs = tuple(socket_dirs)
        self._timeout = timeout_seconds

    def endpoints(self, app_url: str) -> tuple[tuple[str, int], ...]:
        """Where to knock: the DSN's own host, plus the local sockets when it is local."""
        parts = urlsplit(app_url)
        port = parts.port or 5432
        host = parts.hostname
        found: list[tuple[str, int]] = []
        if host:
            found.append((host, port))
        if not host or host in _LOCAL_HOSTS or host.startswith("/"):
            found.extend((directory, port) for directory in self._socket_dirs)
        return tuple(dict.fromkeys(found))

    async def probe(self, app: OwnedConnection, app_url: str) -> LocalAuthFinding:
        roles = [str(r["rolname"]) for r in await app.fetch(_PRIVILEGED_ROLES)]
        database = str(await app.fetchval("SELECT current_database()"))
        admitted: list[str] = []
        refused = 0
        for role in roles:
            for host, port in self.endpoints(app_url):
                outcome = await self._knock(host, port, role, database)
                if outcome is True:
                    admitted.append(f"{role} via {host}:{port}")
                elif outcome is False:
                    refused += 1
        rules = await self._passwordless_rules(app, roles)
        if admitted or rules:
            parts = []
            if admitted:
                parts.append("accepted a password-less connection as " + ", ".join(admitted))
            if rules:
                parts.append("pg_hba.conf lets these in without a password: " + "; ".join(rules))
            return LocalAuthFinding(
                AuthVerdict.FAIL,
                " and ".join(parts)
                + " -- anyone who can reach it as that OS user can rewrite the ledger; "
                "require scram-sha-256 for them (SECURITY.md §7)",
            )
        if rules is None or refused == 0:
            why = []
            if refused == 0:
                why.append("no password-less attempt could reach the server")
            if rules is None:
                why.append("pg_hba_file_rules is not readable by this role")
            return LocalAuthFinding(
                AuthVerdict.UNKNOWN,
                f"could not confirm that {', '.join(roles) or 'the owner'} need a password: "
                + "; ".join(why),
            )
        return LocalAuthFinding(
            AuthVerdict.PASS,
            f"{', '.join(roles)} refused without a password on {refused} attempt(s); "
            "pg_hba.conf has no password-less rule for them",
        )

    async def _knock(self, host: str, port: int, role: str, database: str) -> bool | None:
        """True if let in with an empty password, False if refused, None if unreachable."""
        try:
            conn = await self._connect(
                host=host,
                port=port,
                user=role,
                database=database,
                password="",  # nosec B106 - the probe IS an empty-password attempt
                timeout=self._timeout,
            )
        except (asyncpg.InvalidAuthorizationSpecificationError, asyncpg.InvalidPasswordError):
            return False
        except asyncpg.PostgresError:
            # The server answered but not with a session (no such database, too many
            # connections): not proof either way that a password is required.
            return None
        except (OSError, TimeoutError, asyncpg.InterfaceError):
            return None
        await conn.close()
        return True

    async def _passwordless_rules(
        self, app: OwnedConnection, roles: Sequence[str]
    ) -> list[str] | None:
        try:
            rows = await app.fetch(_HBA, list(PASSWORDLESS_METHODS))
        except asyncpg.InsufficientPrivilegeError:
            return None
        matching = []
        for row in rows:
            users = list(row["user_name"] or [])
            if "all" in users or any(role in users for role in roles):
                matching.append(
                    f"line {row['line_number']}: {row['type']} {','.join(row['database'] or [])} "
                    f"{','.join(users)} {row['auth_method']}"
                )
        return matching
