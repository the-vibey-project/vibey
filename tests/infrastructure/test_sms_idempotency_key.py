# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SMS port takes an idempotency key that no backend can deduplicate, and the Kannel adapter
bounds its call with a timeout (gap K3, ADR-0047 lane S05; sub-doctrine 12.c: the bound is the
declared `[surfaces]` key). The key names one logical message; the surface lane guards it."""

import urllib.parse
from types import TracebackType
from typing import Any

import pytest

from vibey.application.interfaces.sms import SmsPort
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.sms.in_memory import InMemorySms
from vibey.infrastructure.sms.kannel import KannelSmsAdapter


class _Response:
    def __enter__(self) -> "_Response":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return b"0: Accepted"


class _RecordingOpener:
    """The `opener=` seam: accepts every message and remembers the request and its timeout."""

    def __init__(self) -> None:
        self.urls: list[str] = []
        self.timeouts: list[float | None] = []

    def __call__(self, request: Any, timeout: float | None = None) -> _Response:
        self.urls.append(request.full_url)
        self.timeouts.append(timeout)
        return _Response()


def _kannel(opener: _RecordingOpener, **kwargs: float) -> KannelSmsAdapter:
    return KannelSmsAdapter(
        url="http://sms.local", username="u", password="p", opener=opener, **kwargs
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [({}, DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS), ({"timeout": 2.5}, 2.5)],
)
async def test_kannel_passes_the_timeout(kwargs: dict[str, float], expected: float) -> None:
    opener = _RecordingOpener()
    await _kannel(opener, **kwargs).send_sms("+15550100", "hello")
    assert opener.timeouts == [expected]


@pytest.mark.asyncio
async def test_kannel_keyed_send_is_the_same_request() -> None:
    opener = _RecordingOpener()
    adapter = _kannel(opener)
    await adapter.send_sms("+15550100", "hello")
    await adapter.send_sms("+15550100", "hello", idempotency_key="msg-1")
    unkeyed, keyed = opener.urls
    assert keyed == unkeyed
    assert "msg-1" not in urllib.parse.unquote(keyed)


@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_kannel_refuses_a_non_positive_timeout(bad: float) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"):
        _kannel(_RecordingOpener(), timeout=bad)


@pytest.mark.asyncio
async def test_in_memory_sms_records_every_send_and_its_key() -> None:
    sms = InMemorySms()
    await sms.send_sms("+15550100", "hello", idempotency_key="msg-1")
    await sms.send_sms("+15550100", "hello", idempotency_key="msg-1")
    await sms.send_sms("+15550100", "again")
    assert len(sms.sent_sms) == 3
    assert sms.sent_keys == ["msg-1", "msg-1", None]


@pytest.mark.asyncio
async def test_sms_send_accepts_an_idempotency_key() -> None:
    """The port contract: both implementations take the keyword and still send."""
    kannel_opener = _RecordingOpener()
    memory = InMemorySms()
    ports: list[SmsPort] = [_kannel(kannel_opener), memory]
    for port in ports:
        await port.send_sms("+15550100", "hello", idempotency_key="msg-1")
    assert len(kannel_opener.urls) == 1
    assert len(memory.sent_sms) == 1
