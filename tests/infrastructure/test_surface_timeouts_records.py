# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every HTTP call a sovereign-surface adapter makes carries its timeout (#727).

A server that accepts the connection and never answers must not block the caller for ever
(doctrine 10). The opener is a small recording stand-in: it answers each call from a queue of
bodies and keeps the `timeout` it was given.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

import pytest

from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.config_store.infisical import InfisicalConfigStoreAdapter
from vibey.infrastructure.docs.bookstack import BookStackDocsAdapter
from vibey.infrastructure.secrets.openbao import OpenBaoSecretsAdapter
from vibey.infrastructure.tracker.plane import PlaneTrackerAdapter


class _Response:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class _RecordingOpener:
    def __init__(self, *bodies: dict[str, Any]) -> None:
        self._bodies = list(bodies)
        self.timeouts: list[float | None] = []

    def __call__(self, request: object, timeout: float | None = None) -> _Response:
        self.timeouts.append(timeout)
        return _Response(self._bodies.pop(0))


Exercise = Callable[[Any], Any]


async def _plane(adapter: PlaneTrackerAdapter) -> None:
    ticket = await adapter.create_ticket("a", "b")
    assert await adapter.get_ticket_status(ticket) == "Todo"


async def _bookstack(adapter: BookStackDocsAdapter) -> None:
    page = await adapter.create_page("T", "<p>x</p>")
    await adapter.update_page(page, "<p>y</p>")


async def _openbao(adapter: OpenBaoSecretsAdapter) -> None:
    await adapter.set_secret("k", "v")
    assert await adapter.get_secret("k") == "v"


async def _infisical(adapter: InfisicalConfigStoreAdapter) -> None:
    await adapter.create_config("k", "v")
    assert await adapter.get_config("k") == "v"


CASES: dict[
    str, tuple[Callable[..., Any], dict[str, Any], tuple[dict[str, Any], ...], Exercise]
] = {
    "plane": (
        PlaneTrackerAdapter,
        {"url": "https://plane.test", "token": "t", "workspace_slug": "ws", "project_id": "p1"},
        ({"id": "t-1"}, {"state": "Todo"}),
        _plane,
    ),
    "bookstack": (
        BookStackDocsAdapter,
        {"url": "https://docs.test", "token_id": "i", "token_secret": "s"},
        ({"id": 5}, {}),
        _bookstack,
    ),
    "openbao": (
        OpenBaoSecretsAdapter,
        {"url": "https://bao.test", "token": "t"},
        ({}, {"data": {"data": {"value": "v"}}}),
        _openbao,
    ),
    "infisical": (
        InfisicalConfigStoreAdapter,
        {"url": "https://inf.test", "token": "t", "project_id": "p"},
        ({}, {"secret": {"secretValue": "v"}}),
        _infisical,
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_adapter_bounds_every_call_with_its_timeout(name: str) -> None:
    adapter_type, args, bodies, exercise = CASES[name]
    opener = _RecordingOpener(*bodies)
    asyncio.run(exercise(adapter_type(**args, opener=opener, timeout=7)))
    assert opener.timeouts == [7, 7]


@pytest.mark.parametrize("name", sorted(CASES))
def test_each_adapter_defaults_to_the_surface_timeout(name: str) -> None:
    adapter_type, args, bodies, exercise = CASES[name]
    opener = _RecordingOpener(*bodies)
    asyncio.run(exercise(adapter_type(**args, opener=opener)))
    assert opener.timeouts == [DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS] * 2


def test_the_default_bound_is_finite_and_positive() -> None:
    assert 0 < DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS < float("inf")
