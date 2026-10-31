# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port contracts for the sovereign surfaces: every implementation of a port honours it alike.

`send_email` and `send_sms` take an idempotency key naming one logical message. No backend can
deduplicate it, so each implementation accepts it and still sends; the surface lane guards it
(ADR-0047 §8). The implementations run without a service: the SMTP relay and the HTTP opener
are the adapters' declared seams.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.fakes.recording_opener import RecordingOpener
from tests.fakes.smtp import InMemorySmtpServer
from vibey.application.interfaces.email import EmailPort
from vibey.application.interfaces.sms import SmsPort
from vibey.infrastructure.email.forward_email import ForwardEmailAdapter
from vibey.infrastructure.email.in_memory import InMemoryEmail
from vibey.infrastructure.sms.in_memory import InMemorySms
from vibey.infrastructure.sms.kannel import KannelSmsAdapter


def _in_memory_email() -> tuple[EmailPort, Callable[[], int]]:
    email = InMemoryEmail()
    return email, lambda: len(email.sent)


def _smtp_email() -> tuple[EmailPort, Callable[[], int]]:
    server = InMemorySmtpServer()
    adapter = ForwardEmailAdapter(smtp_host="smtp", smtp_port=587, connector=server)
    return adapter, lambda: len(server.messages)


def _in_memory_sms() -> tuple[SmsPort, Callable[[], int]]:
    sms = InMemorySms()
    return sms, lambda: len(sms.sent_sms)


def _kannel_sms() -> tuple[SmsPort, Callable[[], int]]:
    opener = RecordingOpener(b"0: Accepted", b"0: Accepted")
    adapter = KannelSmsAdapter(url="http://sms.local", username="u", password="p", opener=opener)
    return adapter, lambda: len(opener.timeouts)


_EMAIL: dict[str, Callable[[], tuple[EmailPort, Callable[[], int]]]] = {
    "in-memory": _in_memory_email,
    "smtp": _smtp_email,
}
_SMS: dict[str, Callable[[], tuple[SmsPort, Callable[[], int]]]] = {
    "in-memory": _in_memory_sms,
    "kannel": _kannel_sms,
}


@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(_EMAIL))
async def test_email_send_accepts_an_idempotency_key(name: str) -> None:
    port, sent = _EMAIL[name]()
    await port.send_email("ops@example.org", "s", "b", idempotency_key="k")
    await port.send_email("ops@example.org", "s", "b", idempotency_key="k")
    assert sent() == 2  # accepted, not deduplicated: the guard owns that


@pytest.mark.asyncio
@pytest.mark.parametrize("name", sorted(_SMS))
async def test_sms_send_accepts_an_idempotency_key(name: str) -> None:
    port, sent = _SMS[name]()
    await port.send_sms("+15550100", "hello", idempotency_key="k")
    await port.send_sms("+15550100", "hello", idempotency_key="k")
    assert sent() == 2  # accepted, not deduplicated: the guard owns that
