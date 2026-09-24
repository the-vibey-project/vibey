# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""LocalAuthProbe: the role split protects the ledger only while nobody can connect as
the owner or a superuser without a password (ADR-0055).

Found on the operator's own machine: `psql -w -h /tmp -d postgres` connected as the
superuser with no password at all, because the local server trusts its socket. The
probe must say so -- and must never call a server it could not examine a pass."""

import asyncio
from collections.abc import Sequence
from typing import Any

import asyncpg
import pytest

from vibey.infrastructure.db.interfaces import LocalAuthProbeInterface
from vibey.infrastructure.db.local_auth import (
    DEFAULT_SOCKET_DIRS,
    AuthVerdict,
    LocalAuthProbe,
)


class _App:
    """The application's connection: the catalog answers, and pg_hba as configured."""

    def __init__(
        self, roles: Sequence[str], hba: list[dict[str, Any]] | None, database: str = "vibey"
    ) -> None:
        self._roles = roles
        self._hba = hba
        self._database = database

    async def fetch(self, sql: str, *args: object) -> list[dict[str, Any]]:
        if "pg_hba_file_rules" in sql:
            if self._hba is None:
                raise asyncpg.InsufficientPrivilegeError("permission denied for view")
            return self._hba
        return [{"rolname": role} for role in self._roles]

    async def fetchval(self, sql: str, *args: object) -> str:
        return self._database


class _Knocks:
    """A connector that answers every knock the same way, and remembers them."""

    def __init__(self, answer: object) -> None:
        self._answer = answer
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        if isinstance(self._answer, BaseException):
            raise self._answer
        return self._answer


class _Session:
    closed = False

    async def close(self) -> None:
        self.closed = True


def _rule(users: list[str], method: str = "trust", kind: str = "local") -> dict[str, Any]:
    return {
        "line_number": 90,
        "type": kind,
        "database": ["all"],
        "user_name": users,
        "auth_method": method,
    }


def _probe(connect: object, dirs: Sequence[str] = ("/tmp",)) -> LocalAuthProbe:  # nosec B108 - a socket directory name
    return LocalAuthProbe(connect=connect, socket_dirs=dirs)  # type: ignore[arg-type]


def test_a_local_dsn_is_knocked_on_at_its_host_and_every_socket_directory() -> None:
    probe = LocalAuthProbe()
    assert probe.endpoints("postgresql://app@localhost:6543/v") == (
        ("localhost", 6543),
        *((d, 6543) for d in DEFAULT_SOCKET_DIRS),
    )
    assert probe.endpoints("postgresql:///v") == tuple((d, 5432) for d in DEFAULT_SOCKET_DIRS)
    assert probe.endpoints("postgresql://app@db.vibey.svc.cluster.local/v") == (
        ("db.vibey.svc.cluster.local", 5432),
    )


def test_a_password_less_connection_let_in_is_a_failure() -> None:
    session = _Session()
    knocks = _Knocks(session)

    finding = asyncio.run(
        _probe(knocks).probe(_App(["postgres"], hba=[]), "postgresql://app@remote/v")  # type: ignore[arg-type]
    )

    assert finding.verdict is AuthVerdict.FAIL
    assert "accepted a password-less connection as postgres via remote:5432" in finding.detail
    assert session.closed
    assert knocks.calls == [
        {
            "host": "remote",
            "port": 5432,
            "user": "postgres",
            "database": "vibey",
            "password": "",
            "timeout": 5.0,
        }
    ]


@pytest.mark.parametrize(
    "rule",
    [_rule(["all"]), _rule(["owner"], "peer"), _rule(["all"], "ident", "host")],
)
def test_a_password_less_rule_for_them_is_a_failure(rule: dict[str, Any]) -> None:
    refused = _Knocks(asyncpg.InvalidPasswordError("password authentication failed"))

    finding = asyncio.run(
        _probe(refused).probe(_App(["owner"], hba=[rule]), "postgresql://app@localhost/v")  # type: ignore[arg-type]
    )

    assert finding.verdict is AuthVerdict.FAIL
    assert "pg_hba.conf lets these in without a password: line 90" in finding.detail
    assert "scram-sha-256" in finding.detail


def test_a_rule_for_someone_else_is_not_their_problem() -> None:
    refused = _Knocks(asyncpg.InvalidAuthorizationSpecificationError("no pg_hba entry"))

    finding = asyncio.run(
        _probe(refused).probe(
            _App(["owner"], hba=[_rule(["reporting"])]),  # type: ignore[arg-type]
            "postgresql://app@localhost/v",
        )
    )

    assert finding.verdict is AuthVerdict.PASS
    assert "refused without a password on 2 attempt(s)" in finding.detail


def test_refused_everywhere_but_pg_hba_unreadable_is_unknown() -> None:
    refused = _Knocks(asyncpg.InvalidPasswordError("password authentication failed"))

    finding = asyncio.run(
        _probe(refused).probe(_App(["owner"], hba=None), "postgresql://app@localhost/v")  # type: ignore[arg-type]
    )

    assert finding.verdict is AuthVerdict.UNKNOWN
    assert "pg_hba_file_rules is not readable by this role" in finding.detail


@pytest.mark.parametrize(
    "failure",
    [OSError("no such socket"), TimeoutError(), asyncpg.InvalidCatalogNameError("no db")],
)
def test_a_server_no_knock_could_reach_is_unknown(failure: BaseException) -> None:
    finding = asyncio.run(
        _probe(_Knocks(failure)).probe(_App(["owner"], hba=[]), "postgresql://app@localhost/v")  # type: ignore[arg-type]
    )

    assert finding.verdict is AuthVerdict.UNKNOWN
    assert "no password-less attempt could reach the server" in finding.detail


def test_with_no_privileged_role_to_try_nothing_is_confirmed() -> None:
    finding = asyncio.run(
        _probe(_Knocks(_Session())).probe(_App([], hba=None), "postgresql://app@localhost/v")  # type: ignore[arg-type]
    )

    assert finding.verdict is AuthVerdict.UNKNOWN
    assert "the owner" in finding.detail


async def test_against_the_real_server_it_is_never_a_silent_pass(
    migrated_pool: asyncpg.Pool, database_url: str
) -> None:
    """The application role may not read pg_hba, so against a real server it can never
    earn a pass: a developer's trust-configured server fails (the probe gets in), and
    CI's password-only one, seen from outside its container, is unknown."""
    async with migrated_pool.acquire() as conn:
        finding = await LocalAuthProbe().probe(conn, database_url)

    assert finding.verdict is not AuthVerdict.PASS, finding.detail
    assert finding.detail


def test_the_probe_satisfies_its_declared_interface() -> None:
    assert isinstance(LocalAuthProbe(), LocalAuthProbeInterface)
