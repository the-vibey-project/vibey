# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every HTTP call the messaging, SIEM and SMS send adapters make carries its timeout (#729).

A hung send is worse than a failed one: the SIEM port promises that a sink that is down must not
fail the work that produced the event, and a thread blocked for ever on the sink does exactly
that.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from tests.fakes.recording_opener import RecordingOpener
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.messaging.matrix import MatrixMessagingAdapter
from vibey.infrastructure.siem.wazuh import WazuhSiemAdapter
from vibey.infrastructure.sms.kannel import KannelSmsAdapter


async def _matrix(adapter: MatrixMessagingAdapter) -> None:
    await adapter.send_message("!room:test", "hello")


async def _wazuh(adapter: WazuhSiemAdapter) -> None:
    await adapter.send_event("vibey-audit", {"kind": "x"})


async def _kannel(adapter: KannelSmsAdapter) -> None:
    await adapter.send_sms("+15550100", "hello")


Case = tuple[Callable[..., Any], dict[str, Any], bytes, Callable[[Any], Awaitable[None]]]
CASES: dict[str, Case] = {
    "matrix": (
        MatrixMessagingAdapter,
        {"url": "https://matrix.test", "token": "t"},
        b"{}",
        _matrix,
    ),
    "wazuh": (WazuhSiemAdapter, {"url": "https://wazuh.test"}, b"{}", _wazuh),
    # Kannel answers "0: Accepted for delivery"; anything else is a rejection.
    "kannel": (
        KannelSmsAdapter,
        {"url": "https://kannel.test", "username": "u", "password": "p"},
        b"0: Accepted for delivery",
        _kannel,
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_adapter_bounds_its_send_with_its_timeout(name: str) -> None:
    adapter_type, args, reply, exercise = CASES[name]
    opener = RecordingOpener(reply)
    asyncio.run(exercise(adapter_type(**args, opener=opener, timeout=7)))
    assert opener.timeouts == [7]


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_adapter_defaults_to_the_surface_timeout(name: str) -> None:
    adapter_type, args, reply, exercise = CASES[name]
    opener = RecordingOpener(reply)
    asyncio.run(exercise(adapter_type(**args, opener=opener)))
    assert opener.timeouts == [DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS]
