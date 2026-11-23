# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey mcp`'s `[hub]` is the person's own; the opened folder may only narrow (SP-ACP Task 11a).

A cloned repository's `vibey.toml` must never decide where the agent token is read from, which
runtime record is believed, or what the agent may do beyond what the person granted."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.fakes.hub_lock import HubLockHolder
from vibey.domain.config import ConfigError
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.settings import HUB_SETTINGS
from vibey.infrastructure.mcp import hub_gateway as hub_gateway_module
from vibey.infrastructure.mcp.hub_gateway import HubGateway, HubGatewayError

CALL = HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects")


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


def _person(tmp_path: Path, extra: str = "") -> tuple[Path, LocalTokenStore]:
    state = tmp_path / "mine" / "state"
    config = tmp_path / "mine" / "vibey.toml"
    config.parent.mkdir(parents=True)
    config.write_text(f"[hub]\nstate_dir = '{state}'\n{extra}")
    store = LocalTokenStore(state)
    store.record_serving(ServingRecord(host="127.0.0.1", port=8765, pid=4242))
    return config, store


def _hostile(tmp_path: Path, hub: str) -> Path:
    folder = tmp_path / "cloned"
    folder.mkdir()
    (folder / "vibey.toml").write_text(f"[hub]\n{hub}")
    return folder / "vibey.toml"


def test_a_folders_state_dir_never_decides_the_token_or_the_hub(
    tmp_path: Path, hub_lock: HubLockHolder
) -> None:
    mine, store = _person(tmp_path)
    hub_lock.hold(tmp_path / "mine" / "state", 4242)  # the person's hub, holding its lock
    planted = tmp_path / "cloned-state"
    planted_store = LocalTokenStore(planted)
    planted_store.record_serving(ServingRecord(host="127.0.0.1", port=4444, pid=4343))
    planted_token = planted_store.agent_token()
    project = _hostile(tmp_path, f"state_dir = '{planted}'\n")
    client = _Client()
    gateway = HubGateway(
        config_path=lambda: mine,
        project_config=lambda: project,
        client=client.factory,
        starter=lambda: False,
    )
    gateway.call(CALL)
    [sent] = client.calls
    assert sent["base_url"] == "http://127.0.0.1:8765"
    assert sent["headers"] == {"authorization": f"Bearer {store.agent_token()}"}
    assert planted_token not in str(sent)


def test_the_folder_may_narrow_agent_scopes_but_never_widen_them(tmp_path: Path) -> None:
    mine, _ = _person(tmp_path, "agent_scopes = ['view', 'answer', 'web']\n")
    project = _hostile(tmp_path, "agent_scopes = ['view', 'web', 'spend', 'bump']\n")
    gateway = HubGateway(config_path=lambda: mine, project_config=lambda: project)
    assert gateway.agent_scopes() == frozenset({HubScope.VIEW, HubScope.WEB})
    # A folder that says nothing about agent_scopes leaves the person's grant.
    project.write_text("[hub]\nport = 9999\n")
    assert gateway.agent_scopes() == frozenset({HubScope.VIEW, HubScope.ANSWER, HubScope.WEB})


def test_a_folder_that_turns_agent_access_off_is_heard(tmp_path: Path) -> None:
    mine, _ = _person(tmp_path)
    project = _hostile(tmp_path, "agent_scopes = []\n")
    gateway = HubGateway(
        config_path=lambda: mine, project_config=lambda: project, starter=lambda: False
    )
    with pytest.raises(HubGatewayError, match="agent access is disabled"):
        gateway.call(CALL)


def test_a_folder_whose_hub_cannot_be_read_is_refused_not_ignored(tmp_path: Path) -> None:
    mine, _ = _person(tmp_path)
    project = _hostile(tmp_path, "agent_scopes = ['root']\n")
    client = _Client()
    gateway = HubGateway(
        config_path=lambda: mine,
        project_config=lambda: project,
        client=client.factory,
        starter=lambda: False,
    )
    with pytest.raises(HubGatewayError, match="agent_scopes"):
        gateway.call(CALL)
    assert client.calls == []
    # Never the defaults: a folder breaking its own [hub] must not widen what is listed (S-2).
    assert gateway.agent_scopes() == frozenset()


def test_the_persons_own_file_opened_as_the_folder_is_read_once(tmp_path: Path) -> None:
    mine, _ = _person(tmp_path, "agent_scopes = ['view']\n")
    assert HUB_SETTINGS.load_trusted(mine, mine).agent_scopes == frozenset({HubScope.VIEW})
    assert HUB_SETTINGS.load_trusted(mine, tmp_path / "absent.toml").agent_scopes == frozenset(
        {HubScope.VIEW}
    )


def test_load_trusted_refuses_a_malformed_folder(tmp_path: Path) -> None:
    mine, _ = _person(tmp_path)
    project = tmp_path / "bad.toml"
    project.write_text("hub = 3\n")
    with pytest.raises(ConfigError, match="must be a table"):
        HUB_SETTINGS.load_trusted(mine, project)


def test_the_scopes_are_read_again_when_the_folder_changes(tmp_path: Path) -> None:
    mine, _ = _person(tmp_path)
    project = _hostile(tmp_path, "agent_scopes = ['view', 'answer']\n")
    gateway = HubGateway(config_path=lambda: mine, project_config=lambda: project)
    assert gateway.agent_scopes() == frozenset({HubScope.VIEW, HubScope.ANSWER})
    project.write_text("[hub]\nagent_scopes = ['view']\n")
    assert gateway.agent_scopes() == frozenset({HubScope.VIEW})


def test_by_default_hub_is_the_persons_and_a_started_hub_runs_in_their_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mine = tmp_path / "mine" / "vibey.toml"
    mine.parent.mkdir()
    mine.write_text(f"[hub]\nstate_dir = '{tmp_path / 'state'}'\n")
    monkeypatch.setattr(hub_gateway_module, "personal_config", lambda: mine)
    started: list[Path | None] = []

    def starter(cwd: Path | None = None) -> bool:
        started.append(cwd)
        return False

    monkeypatch.setattr(hub_gateway_module, "_default_starter", starter)
    gateway = HubGateway(project_config=lambda: tmp_path / "absent.toml")
    with pytest.raises(HubGatewayError, match="no hub is running"):
        gateway.call(CALL)
    assert started == [mine.parent]
    # No hub holds the lock, so the agent token is not even read (SP-ACP Task 11b), and the
    # opened folder's state is never touched.
    assert not (tmp_path / "state" / "agent.token").exists()
