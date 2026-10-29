# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The email port takes an idempotency key that SMTP cannot deduplicate (ADR-0047 lane S05).

The key names one logical message and fixes its Message-ID, "a courtesy to receivers, not a
guarantee"; the surface lane guards it. The adapter tests talk to a real SMTP responder on
loopback, so no import is patched and no outside service is reached.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import socket
import threading
from collections.abc import Iterator
from contextlib import closing, contextmanager

import pytest

from vibey.application.interfaces.email import EmailPort
from vibey.infrastructure.email.forward_email import ForwardEmailAdapter
from vibey.infrastructure.email.in_memory import InMemoryEmail


class _SmtpResponder:
    """Accepts submissions on loopback and keeps the DATA of each message it was handed."""

    def __init__(self, server: socket.socket) -> None:
        self.messages: list[str] = []
        self._server = server
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

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
            elif verb == "EHLO":
                stream.write(b"250 responder\r\n")
            else:
                stream.write(b"250 ok\r\n")
            stream.flush()


@contextmanager
def _relay() -> Iterator[tuple[int, _SmtpResponder]]:
    with closing(socket.socket()) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(4)
        yield int(server.getsockname()[1]), _SmtpResponder(server)


def _message_id(message: str) -> str | None:
    found = re.search(r"^Message-ID: (.+)$", message, re.MULTILINE | re.IGNORECASE)
    return found.group(1).strip() if found else None


def _adapter(port: int, **kwargs: str) -> ForwardEmailAdapter:
    return ForwardEmailAdapter(smtp_host="127.0.0.1", smtp_port=port, **kwargs)


def test_a_key_fixes_the_message_id_on_the_from_domain() -> None:
    digest = hashlib.sha256(b"k").hexdigest()[:32]
    with _relay() as (port, relay):
        adapter = _adapter(port, from_email="vibey@example.org")
        asyncio.run(adapter.send_email("ops@example.org", "s", "one", idempotency_key="k"))
        asyncio.run(adapter.send_email("ops@example.org", "s", "two", idempotency_key="k"))
        asyncio.run(adapter.send_email("ops@example.org", "s", "three", idempotency_key="other"))
    first, second, third = (_message_id(m) for m in relay.messages)
    assert first == second == f"<vibey.{digest}@example.org>"
    assert third != first


def test_a_from_address_without_a_domain_falls_back_to_localhost() -> None:
    with _relay() as (port, relay):
        adapter = _adapter(port, from_email="vibey")
        asyncio.run(adapter.send_email("ops@example.org", "s", "b", idempotency_key="k"))
    assert (_message_id(relay.messages[0]) or "").endswith("@localhost>")


def test_without_a_key_no_message_id_is_set() -> None:
    with _relay() as (port, relay):
        adapter = _adapter(port, from_email="vibey@example.org")
        asyncio.run(adapter.send_email("ops@example.org", "s", "one"))
        asyncio.run(adapter.send_email("ops@example.org", "s", "two"))
    assert [_message_id(m) for m in relay.messages] == [None, None]


@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_forward_email_refuses_a_non_positive_timeout(bad: float) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        ForwardEmailAdapter(smtp_host="127.0.0.1", smtp_port=25, timeout=bad)


@pytest.mark.asyncio
async def test_in_memory_email_records_every_send_and_its_key() -> None:
    email = InMemoryEmail()
    await email.send_email("a@example.org", "s", "b", idempotency_key="k")
    await email.send_email("a@example.org", "s", "b", idempotency_key="k")
    await email.send_email("a@example.org", "s", "b")
    assert len(email.sent) == 3
    assert email.sent_keys == ["k", "k", None]


def test_email_send_accepts_an_idempotency_key() -> None:
    """The port contract: both implementations take the keyword and still send."""
    memory = InMemoryEmail()
    with _relay() as (port, relay):
        ports: list[EmailPort] = [_adapter(port), memory]
        for target in ports:
            asyncio.run(target.send_email("ops@example.org", "s", "b", idempotency_key="k"))
    assert len(relay.messages) == 1
    assert len(memory.sent) == 1
