# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every HTTP call the file, blob and bus adapters make carries its timeout (#728).

A server that accepts the connection and never answers must not block the caller for ever
(doctrine 10).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from tests.fakes.recording_opener import RecordingOpener
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.blob.garage import GarageBlobAdapter
from vibey.infrastructure.bus.rabbitmq import RabbitMqBusAdapter
from vibey.infrastructure.files.nextcloud import NextcloudFilesAdapter


async def _nextcloud(adapter: NextcloudFilesAdapter) -> None:
    await adapter.upload_file("a.txt", b"x")
    assert await adapter.download_file("a.txt") == b"x"


async def _garage(adapter: GarageBlobAdapter) -> None:
    await adapter.put_blob("b", "k", b"x")
    assert await adapter.get_blob("b", "k") == b"x"


async def _rabbitmq(adapter: RabbitMqBusAdapter) -> None:
    await adapter.declare_queue("q", dead_letter=False)
    assert await adapter.consume("q") is None


Case = tuple[
    Callable[..., Any], dict[str, Any], tuple[bytes, ...], Callable[[Any], Awaitable[None]]
]
CASES: dict[str, Case] = {
    "nextcloud": (
        NextcloudFilesAdapter,
        {"url": "https://cloud.test", "user": "u", "password": "p"},
        (b"", b"x"),
        _nextcloud,
    ),
    # put_blob creates the bucket, then puts the object (three calls with the get).
    "garage": (
        GarageBlobAdapter,
        {"url": "https://garage.test", "access_key": "a", "secret_key": "s"},
        (b"", b"", b"x"),
        _garage,
    ),
    "rabbitmq": (
        RabbitMqBusAdapter,
        {"url": "https://mq.test", "username": "u", "password": "p"},
        (b"", b"[]"),
        _rabbitmq,
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_adapter_bounds_every_call_with_its_timeout(name: str) -> None:
    adapter_type, args, replies, exercise = CASES[name]
    opener = RecordingOpener(*replies)
    asyncio.run(exercise(adapter_type(**args, opener=opener, timeout=7)))
    assert opener.timeouts == [7] * len(replies)


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_adapter_defaults_to_the_surface_timeout(name: str) -> None:
    adapter_type, args, replies, exercise = CASES[name]
    opener = RecordingOpener(*replies)
    asyncio.run(exercise(adapter_type(**args, opener=opener)))
    assert opener.timeouts == [DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS] * len(replies)
