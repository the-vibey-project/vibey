# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Infisical, Garage and RabbitMQ-management adapters bound every call with a timeout, and
refuse one that bounds nothing (gap K3; sub-doctrine 12.c: the bound is the declared key)."""

import json
from types import TracebackType
from typing import Any

import pytest

from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.blob.garage import GarageBlobAdapter
from vibey.infrastructure.bus.management import RabbitMqManagementApi
from vibey.infrastructure.bus.rabbitmq import RabbitMqBusAdapter
from vibey.infrastructure.config_store.infisical import InfisicalConfigStoreAdapter


class _Response:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body

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
        return self._body


class _RecordingOpener:
    """The `opener=` seam: answers every request and remembers the timeout it was given."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self.timeouts: list[float | None] = []

    def __call__(self, request: object, timeout: float | None = None) -> _Response:
        self.timeouts.append(timeout)
        return _Response(self._body)


_CASES = [({}, DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS), ({"timeout": 2.5}, 2.5)]


def _all_carry(opener: _RecordingOpener, expected: float) -> None:
    assert opener.timeouts, "the adapter made no call"
    assert set(opener.timeouts) == {expected}


@pytest.mark.asyncio
@pytest.mark.parametrize(("kwargs", "expected"), _CASES)
async def test_infisical_calls_carry_the_timeout(kwargs: dict[str, Any], expected: float) -> None:
    opener = _RecordingOpener(json.dumps({"secret": {"secretValue": "v"}}).encode())
    adapter = InfisicalConfigStoreAdapter(
        url="http://inf", token="t", project_id="p", opener=opener, **kwargs
    )
    await adapter.create_config("k", "v")
    assert await adapter.get_config("k") == "v"
    assert len(opener.timeouts) == 2
    _all_carry(opener, expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(("kwargs", "expected"), _CASES)
async def test_garage_calls_carry_the_timeout(kwargs: dict[str, Any], expected: float) -> None:
    opener = _RecordingOpener(b"blob")
    adapter = GarageBlobAdapter(
        url="http://garage:3900", access_key="ak", secret_key="sk", opener=opener, **kwargs
    )
    await adapter.put_blob("b", "k", b"blob")
    assert await adapter.get_blob("b", "k") == b"blob"
    assert len(opener.timeouts) == 3  # bucket PUT, object PUT, object GET
    _all_carry(opener, expected)


@pytest.mark.asyncio
@pytest.mark.parametrize(("kwargs", "expected"), _CASES)
async def test_bus_calls_carry_the_timeout(kwargs: dict[str, Any], expected: float) -> None:
    opener = _RecordingOpener(b'{"routed": true}')
    bus = RabbitMqBusAdapter(
        url="http://bus:15672", username="u", password="p", opener=opener, **kwargs
    )
    await bus.declare_queue("q")
    await bus.publish("q", {"a": 1})
    assert len(opener.timeouts) > 2
    _all_carry(opener, expected)

    consume_opener = _RecordingOpener(b"[]")
    consumer = RabbitMqBusAdapter(
        url="http://bus:15672", username="u", password="p", opener=consume_opener, **kwargs
    )
    assert await consumer.consume("q") is None
    _all_carry(consume_opener, expected)


@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_all_three_refuse_a_non_positive_timeout(bad: float) -> None:
    builders: list[Any] = [
        lambda: InfisicalConfigStoreAdapter(
            url="http://inf", token="t", project_id="p", timeout=bad
        ),
        lambda: GarageBlobAdapter(url="http://g", access_key="a", secret_key="s", timeout=bad),
        lambda: RabbitMqBusAdapter(url="http://bus", username="u", password="p", timeout=bad),
        lambda: RabbitMqManagementApi(url="http://bus", username="u", password="p", timeout=bad),
    ]
    for build in builders:
        with pytest.raises(ValueError, match="timeout must be positive"):
            build()
