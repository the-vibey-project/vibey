# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SMTP adapter, through its `connector` seam (ADR-0047 lane S05, gap K3).

The key names one logical message and fixes its Message-ID, "a courtesy to receivers, not a
guarantee"; SMTP cannot deduplicate, so the surface lane guards it. Every connection is bounded
by the timeout, and a bound that bounds nothing is refused. Tests use `InMemorySmtpServer`; one
test sends over a real loopback socket to prove the stdlib connector carries the Message-ID.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import socket
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager
from typing import Any

import pytest

from tests.fakes.smtp import InMemorySmtpServer
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.email.forward_email import STDLIB_SMTP, ForwardEmailAdapter
from vibey.infrastructure.email.in_memory import InMemoryEmail
from vibey.infrastructure.email.interfaces.forward_email_interface import SmtpConnectorInterface


def _adapter(server: InMemorySmtpServer, **kwargs: Any) -> ForwardEmailAdapter:
    return ForwardEmailAdapter(smtp_host="smtp", smtp_port=587, connector=server, **kwargs)


def test_the_in_memory_server_and_the_stdlib_connector_satisfy_the_seam() -> None:
    assert isinstance(InMemorySmtpServer(), SmtpConnectorInterface)
    assert isinstance(STDLIB_SMTP, SmtpConnectorInterface)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("port", "kind"), [(587, "plain"), (465, "implicit_tls")], ids=["submission", "implicit-tls"]
)
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [({}, DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS), ({"timeout": 2.5}, 2.5)],
    ids=["default", "configured"],
)
async def test_smtp_connections_carry_the_timeout(
    port: int, kind: str, kwargs: dict[str, Any], expected: float
) -> None:
    server = InMemorySmtpServer()
    adapter = ForwardEmailAdapter(smtp_host="smtp", smtp_port=port, connector=server, **kwargs)
    await adapter.send_email("ops@example.org", "s", "b")
    assert server.connections == [(kind, "smtp", port)]
    assert server.timeouts == [expected]


@pytest.mark.asyncio
async def test_a_submission_port_says_hello_upgrades_and_logs_in_before_it_sends() -> None:
    server = InMemorySmtpServer()
    await _adapter(server, username="u", password="pw").send_email("ops@example.org", "s", "b")
    assert server.commands == ["ehlo", "starttls", "ehlo", "login:u", "send"]


@pytest.mark.asyncio
async def test_a_submission_port_without_a_password_sends_anonymously_in_the_clear() -> None:
    server = InMemorySmtpServer()
    await _adapter(server).send_email("ops@example.org", "s", "b")
    assert server.commands == ["ehlo", "send"]


@pytest.mark.asyncio
async def test_implicit_tls_logs_in_and_sends_without_starttls() -> None:
    server = InMemorySmtpServer()
    adapter = ForwardEmailAdapter(
        smtp_host="smtp", smtp_port=465, username="u", password="pw", connector=server
    )
    await adapter.send_email("ops@example.org", "s", "b")
    assert server.commands == ["login:u", "send"]


@pytest.mark.asyncio
async def test_a_key_fixes_the_message_id_on_the_from_domain() -> None:
    server = InMemorySmtpServer()
    adapter = _adapter(server, from_email="vibey@example.org")
    await adapter.send_email("ops@example.org", "s", "one", idempotency_key="k")
    await adapter.send_email("ops@example.org", "s", "two", idempotency_key="k")
    await adapter.send_email("ops@example.org", "s", "three", idempotency_key="other")
    first, second, third = (message["Message-ID"] for message in server.messages)
    assert first == second == f"<vibey.{hashlib.sha256(b'k').hexdigest()[:32]}@example.org>"
    assert third != first


@pytest.mark.asyncio
async def test_a_from_address_without_a_domain_falls_back_to_localhost() -> None:
    server = InMemorySmtpServer()
    await _adapter(server, from_email="vibey").send_email(
        "ops@example.org", "s", "b", idempotency_key="k"
    )
    assert server.messages[0]["Message-ID"].endswith("@localhost>")


@pytest.mark.asyncio
async def test_without_a_key_no_message_id_is_set() -> None:
    server = InMemorySmtpServer()
    adapter = _adapter(server, from_email="vibey@example.org")
    await adapter.send_email("ops@example.org", "s", "one")
    await adapter.send_email("ops@example.org", "s", "two")
    assert [message["Message-ID"] for message in server.messages] == [None, None]


@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_forward_email_refuses_a_non_positive_timeout(bad: float) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        ForwardEmailAdapter(smtp_host="smtp", smtp_port=25, timeout=bad)


@pytest.mark.asyncio
async def test_in_memory_email_records_every_send_and_its_key() -> None:
    email = InMemoryEmail()
    await email.send_email("a@example.org", "s", "b", idempotency_key="k")
    await email.send_email("a@example.org", "s", "b", idempotency_key="k")
    await email.send_email("a@example.org", "s", "b")
    assert len(email.sent) == 3
    assert email.sent_keys == ["k", "k", None]


class _SmtpResponder:
    """Accepts one submission at a time on loopback and keeps the DATA of each message."""

    def __init__(self, server: socket.socket) -> None:
        self.messages: list[str] = []
        self._server = server
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            with closing(conn):
                self._session(conn)

    def _session(self, conn: socket.socket) -> None:
        stream = conn.makefile("rwb")
        stream.write(b"220 responder ready\r\n")
        stream.flush()
        for raw in stream:
            verb = raw.decode().split(" ", 1)[0].strip().upper()
            if verb == "DATA":
                stream.write(b"354 go ahead\r\n")
                stream.flush()
                lines: list[str] = []
                for line in stream:
                    if line == b".\r\n":
                        break
                    lines.append(line.decode())
                self.messages.append("".join(lines))
                stream.write(b"250 queued\r\n")
            elif verb == "QUIT":
                stream.write(b"221 bye\r\n")
                stream.flush()
                return
            else:
                stream.write(b"250 ok\r\n")
            stream.flush()


@contextmanager
def _relay() -> Iterator[tuple[int, _SmtpResponder]]:
    with closing(socket.socket()) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(4)
        yield int(server.getsockname()[1]), _SmtpResponder(server)


def test_the_stdlib_connector_puts_the_message_id_on_the_wire() -> None:
    with _relay() as (port, relay):
        adapter = ForwardEmailAdapter(
            smtp_host="127.0.0.1", smtp_port=port, from_email="vibey@example.org"
        )
        asyncio.run(adapter.send_email("ops@example.org", "s", "b", idempotency_key="k"))
    found = re.search(r"^Message-ID: (.+)$", relay.messages[0], re.MULTILINE | re.IGNORECASE)
    assert found is not None
    assert found.group(1).strip() == f"<vibey.{hashlib.sha256(b'k').hexdigest()[:32]}@example.org>"
