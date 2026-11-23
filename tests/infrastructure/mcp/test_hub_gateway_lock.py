# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The agent token goes only to the hub holding its lock (SP-ACP Task 11b, review 1 S-5).

On loopback over plain http nothing else proves the listener is the hub: when the hub has died
and left its record, another account can bind the recorded port. So `HubGateway` reads the agent
token, and sends anything, only while the process the record names holds `serve.lock` -- the
same check `vibey hub pair` makes for the host token. The real lock probe throughout, against a
real flock this process holds (`hub_lock`): no thread, no sleep, no signal. Module-level test
functions (ADR-0016)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.fakes.hub_lock import HubLockHolder
from vibey.domain.host_tools import HubCall
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.mcp.hub_gateway import HubGateway, HubGatewayError

CALL = HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects")
RECORD = ServingRecord(host="127.0.0.1", port=8765, pid=4242)


class _Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def factory(self, **kwargs: Any) -> _Client:
        self._kwargs = kwargs
        return self

    def __enter__(self) -> _Client:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def request(self, method: str, route: str, **_: Any) -> httpx.Response:
        self.calls.append({**self._kwargs, "method": method, "route": route})
        return httpx.Response(200, text="{}")


def _setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, starter: Any = None
) -> tuple[HubGateway, _Client, Path, list[bool]]:
    state = tmp_path / "state"
    config = tmp_path / "vibey.toml"
    config.write_text(f"[hub]\nstate_dir = '{state}'\n")
    LocalTokenStore(state).agent_token()
    read: list[bool] = []
    real = LocalTokenStore.agent_token

    def counted(self: LocalTokenStore) -> str:
        read.append(True)
        return real(self)

    monkeypatch.setattr(LocalTokenStore, "agent_token", counted)
    client = _Client()
    gateway = HubGateway(
        config_path=lambda: config,
        project_config=lambda: tmp_path / "absent.toml",
        client=client.factory,
        starter=starter or (lambda: False),
    )
    return gateway, client, state, read


def test_a_stale_record_whose_lock_nobody_holds_is_sent_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway, client, state, read = _setup(tmp_path, monkeypatch)
    LocalTokenStore(state).record_serving(RECORD)  # the hub died; its port may be anyone's
    with pytest.raises(HubGatewayError, match="no hub is running"):
        gateway.call(CALL)
    with pytest.raises(HubGatewayError, match="no hub is running"):
        gateway.reach(CALL)
    assert client.calls == [] and read == []


def test_a_lock_held_by_another_pid_than_the_record_names_is_sent_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hub_lock: HubLockHolder
) -> None:
    gateway, client, state, read = _setup(tmp_path, monkeypatch)
    LocalTokenStore(state).record_serving(RECORD)
    hub_lock.hold(state, RECORD.pid + 1)
    with pytest.raises(HubGatewayError, match="no hub is running"):
        gateway.call(CALL)
    hub_lock.hold(state, 0)  # held, its pid not written yet: not this record's hub either
    with pytest.raises(HubGatewayError, match="no hub is running"):
        gateway.reach(CALL)
    assert client.calls == [] and read == []


def test_the_hub_holding_its_lock_is_sent_the_agent_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hub_lock: HubLockHolder
) -> None:
    gateway, client, state, read = _setup(tmp_path, monkeypatch)
    hub_lock.serve(state, RECORD)
    gateway.call(CALL)
    [sent] = client.calls
    assert sent["base_url"] == "http://127.0.0.1:8765" and read == [True]
    assert sent["headers"]["authorization"].startswith("Bearer ")


def test_a_stale_record_starts_the_hub_and_the_started_hub_is_sent_the_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hub_lock: HubLockHolder
) -> None:
    started: list[bool] = []

    def start() -> bool:
        started.append(True)
        hub_lock.serve(tmp_path / "state", ServingRecord("127.0.0.1", 9100, os.getpid()))
        return True

    gateway, client, state, read = _setup(tmp_path, monkeypatch, starter=start)
    LocalTokenStore(state).record_serving(RECORD)
    gateway.call(CALL)
    assert started == [True]
    [sent] = client.calls
    assert sent["base_url"] == "http://127.0.0.1:9100" and read == [True]


def test_a_hub_that_dies_between_the_calls_is_never_sent_the_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hub_lock: HubLockHolder
) -> None:
    """The first send never arrives; the starter says it started a hub, but the record left is
    a stale one: the retry is not sent to it."""

    def start() -> bool:
        hub_lock.drop(tmp_path / "state")
        return True

    gateway, _, state, _ = _setup(tmp_path, monkeypatch, starter=start)
    hub_lock.serve(state, RECORD)
    sends: list[str] = []

    class _Refused(_Client):
        def request(self, method: str, route: str, **_: Any) -> httpx.Response:
            sends.append(route)
            raise httpx.ConnectError("refused")

    gateway._client = _Refused().factory
    with pytest.raises(HubGatewayError, match="no hub is running after `vibey hub start`"):
        gateway.call(CALL)
    assert sends == ["/api/v1/projects"]
