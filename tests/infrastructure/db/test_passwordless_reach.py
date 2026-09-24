# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""PasswordlessReachProbe: can the app DSN's database be opened with no password at all?

Keeping `VIBEY_PG_URL` out of every model-driven process protects nothing when the
database lets a process in without it. A local PostgreSQL commonly accepts `trust` or
`peer` connections: any process running as the worker's OS user -- an engine session
among them -- then connects as that user, or as the DSN's own role, with no DSN and no
password. Review reproduced exactly that here. `vibey doctor` warns about it.
"""

import getpass
import os
from typing import Any

import asyncpg
import pytest

from vibey.infrastructure.db.interfaces.passwordless_reach_interface import (
    PasswordlessReachProbeInterface,
)
from vibey.infrastructure.db.passwordless_reach import (
    DEFAULT_SOCKET_DIRS,
    PasswordlessReachProbe,
    ReachVerdict,
)


class FakeConnection:
    closed = False

    async def close(self) -> None:
        FakeConnection.closed = True


def _connector(outcomes: dict[tuple[str, str], object], calls: list[dict[str, Any]]):  # type: ignore[no-untyped-def]
    """`outcomes[(host, user)]` is a connection to return or an exception to raise;
    anything unlisted is unreachable."""

    async def connect(**kwargs: Any) -> object:
        calls.append(kwargs)
        outcome = outcomes.get((kwargs["host"], kwargs["user"]), OSError("unreachable"))
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return connect


def _probe(outcomes: dict[tuple[str, str], object], calls: list[dict[str, Any]]):  # type: ignore[no-untyped-def]
    return PasswordlessReachProbe(
        connect=_connector(outcomes, calls), socket_dirs=("/sock",), os_user="adam"
    )


def test_it_knocks_on_the_dsns_host_and_on_the_local_sockets_when_that_host_is_local() -> None:
    probe = PasswordlessReachProbe(socket_dirs=("/sock",), os_user="adam")

    assert probe.endpoints("postgresql://vibey:pw@localhost:5433/app") == (
        ("localhost", 5433),
        ("/sock", 5433),
    )
    assert probe.endpoints("postgresql://vibey@db.internal/app") == (("db.internal", 5432),)
    assert probe.endpoints("postgresql:///app?host=/var/run/postgresql") == (
        ("/var/run/postgresql", 5432),
        ("/sock", 5432),
    )
    # No host at all: libpq's default is the local socket.
    assert probe.endpoints("postgresql:///app") == (("/sock", 5432),)
    assert DEFAULT_SOCKET_DIRS == ("/tmp", "/var/run/postgresql", "/run/postgresql")  # nosec B108


def test_it_tries_the_dsns_role_and_the_os_user_against_the_dsns_database() -> None:
    probe = PasswordlessReachProbe(os_user="adam")

    assert probe.roles("postgresql://vibey:pw@localhost/app") == ("vibey", "adam")
    assert probe.roles("postgresql://adam@localhost/app") == ("adam",)
    assert probe.roles("postgresql://localhost/app") == ("adam",)
    assert probe.database("postgresql://vibey@localhost/app") == "app"
    # libpq's default database is the role's own name.
    assert probe.database("postgresql://vibey@localhost") == "vibey"
    assert probe.database("postgresql://localhost") == "adam"
    assert PasswordlessReachProbe().roles("postgresql://localhost/x") == (getpass.getuser(),)


async def test_a_database_that_lets_the_os_user_in_with_no_password_is_a_warning() -> None:
    calls: list[dict[str, Any]] = []
    probe = _probe(
        {
            ("localhost", "vibey"): asyncpg.InvalidPasswordError("password authentication failed"),
            ("localhost", "adam"): FakeConnection(),
            ("/sock", "vibey"): asyncpg.InvalidAuthorizationSpecificationError("peer failed"),
        },
        calls,
    )

    finding = await probe.probe("postgresql://vibey:secret@localhost:5432/app")

    assert finding.verdict is ReachVerdict.WARN
    assert "adam via localhost:5432" in finding.detail
    assert "'app'" in finding.detail
    assert "without VIBEY_PG_URL" in finding.detail
    assert FakeConnection.closed
    # Never with the DSN's password, never with PGPASSWORD or a passfile.
    assert {c["password"] for c in calls} == {""}
    assert all(c["database"] == "app" for c in calls)


async def test_every_attempt_refused_is_a_pass() -> None:
    probe = _probe(
        {
            ("localhost", "vibey"): asyncpg.InvalidPasswordError("password authentication failed"),
            ("localhost", "adam"): asyncpg.InvalidPasswordError("password authentication failed"),
        },
        [],
    )

    finding = await probe.probe("postgresql://vibey:secret@localhost/app")

    assert finding.verdict is ReachVerdict.PASS
    assert "2 password-less attempt(s) refused" in finding.detail


async def test_nothing_reachable_is_unknown_never_a_pass() -> None:
    finding = await _probe({}, []).probe("postgresql://vibey:secret@localhost/app")

    assert finding.verdict is ReachVerdict.UNKNOWN
    assert "could not reach" in finding.detail


async def test_a_refusal_other_than_authentication_counts_as_unreachable() -> None:
    probe = _probe(
        {("localhost", "vibey"): asyncpg.InvalidCatalogNameError("no such database")}, []
    )

    finding = await probe.probe("postgresql://vibey@localhost/app")

    assert finding.verdict is ReachVerdict.UNKNOWN


def test_the_probe_declares_its_interface() -> None:
    assert isinstance(PasswordlessReachProbe(), PasswordlessReachProbeInterface)


async def test_against_the_real_test_database_the_verdict_is_what_a_connection_shows(
    database_url: str,
) -> None:
    """No fake: probe the lane's own database, then check the verdict against a
    password-less connection made directly."""
    finding = await PasswordlessReachProbe().probe(database_url)

    assert finding.verdict in {ReachVerdict.WARN, ReachVerdict.PASS}, finding.detail
    user = getpass.getuser()
    try:
        conn = await asyncpg.connect(database_url, user=user, password="", passfile=os.devnull)
    except (asyncpg.InvalidPasswordError, asyncpg.InvalidAuthorizationSpecificationError):
        return
    await conn.close()
    assert finding.verdict is ReachVerdict.WARN
    assert user in finding.detail


@pytest.mark.parametrize("verdict", list(ReachVerdict))
def test_each_verdict_prints_as_its_doctor_mark(verdict: ReachVerdict) -> None:
    assert verdict.mark == {"warn": "WARN", "pass": "PASS", "unknown": "UNKNOWN"}[verdict.value]
