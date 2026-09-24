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

import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final
from urllib.parse import parse_qs, unquote, urlsplit

import asyncpg

from vibey.infrastructure.db.migrator import OwnedConnection

type Connector = Callable[..., Awaitable[Any]]

DEFAULT_SOCKET_DIRS: Final = ("/tmp", "/var/run/postgresql", "/run/postgresql")  # nosec B108 - PostgreSQL's socket directories, probed read-only
PASSWORDLESS_METHODS: Final = ("trust", "peer", "ident")
_LOCAL_HOSTS: Final = frozenset({"localhost", "127.0.0.1", "::1"})

# The ledger's owner, every login role that is a member of it, and every login superuser.
_PRIVILEGED_ROLES = """
SELECT DISTINCT rolname FROM (
    SELECT pg_get_userbyid(relowner) AS rolname FROM pg_class WHERE oid = to_regclass('event')
    UNION
    SELECT r.rolname FROM pg_roles r, pg_class c
     WHERE c.oid = to_regclass('event') AND r.rolcanlogin
       AND pg_has_role(r.oid, c.relowner, 'MEMBER')
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


# A `+group` naming a role that does not exist matches nobody (pg_has_role would raise).
_MEMBER_OF = """
SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $2)
            THEN pg_has_role($1, $2, 'MEMBER') ELSE false END
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
        """Where to knock: the DSN's own host, plus the local sockets when it is local.

        The host is read raw and URL-unquoted -- `%2Ftmp` is the socket directory
        `/tmp`, which `urlsplit().hostname` would lower-case and leave encoded -- and a
        libpq `?host=` parameter counts too."""
        parts = urlsplit(app_url)
        port = parts.port or 5432
        hostport = parts.netloc.rsplit("@", 1)[-1]
        if hostport.startswith("["):
            raw = hostport[1 : hostport.index("]")]
        else:
            raw = hostport.split(":", 1)[0]
        host = unquote(raw) or next(iter(parse_qs(parts.query).get("host", [])), "")
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
        rules, undecidable = await self._passwordless_rules(app, roles)
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
        if rules is None or refused == 0 or undecidable:
            why = []
            if refused == 0:
                why.append("no password-less attempt could reach the server")
            if rules is None:
                why.append("pg_hba_file_rules is not readable by this role")
            if undecidable:
                why.append("these rules name users in a file: " + "; ".join(undecidable))
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
    ) -> tuple[list[str] | None, list[str]]:
        """(rules that let one of `roles` in without a password, rules that cannot be
        decided) -- (None, []) when pg_hba_file_rules is not readable."""
        try:
            rows = await app.fetch(_HBA, list(PASSWORDLESS_METHODS))
        except asyncpg.InsufficientPrivilegeError:
            return None, []
        matching: list[str] = []
        undecidable: list[str] = []
        for row in rows:
            users = list(row["user_name"] or [])
            line = (
                f"line {row['line_number']}: {row['type']} {','.join(row['database'] or [])} "
                f"{','.join(users)} {row['auth_method']}"
            )
            verdicts = [await self._matches(app, spec, roles) for spec in users]
            if True in verdicts:
                matching.append(line)
            elif None in verdicts:
                undecidable.append(line)
        return matching, undecidable

    @staticmethod
    async def _matches(app: OwnedConnection, spec: str, roles: Sequence[str]) -> bool | None:
        """Whether a pg_hba user spec can match one of `roles`: `all`, a name, `+group`
        (membership), `/regex`, or `@file` (None: the file is not readable from here)."""
        if spec == "all":
            return True
        if spec.startswith("@"):
            return None
        if spec.startswith("+"):
            for role in roles:
                if await app.fetchval(_MEMBER_OF, role, spec[1:]):
                    return True
            return False
        if spec.startswith("/"):
            pattern = re.compile(spec[1:])
            return any(pattern.search(role) for role in roles)
        return spec in roles
