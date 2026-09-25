# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's smaller adapters: `[hub]`, the host token, lanes, exposure, the server.

Each reads or writes real files in a temporary directory; nothing here needs a network
or a database.
"""

import json
import os
import socket
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI

from vibey.application.dto import HubPrincipal
from vibey.domain.config import ConfigError
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.hub.authenticator import (
    HOST_PRINCIPAL,
    HubRequest,
    LocalTokenAuthenticator,
)
from vibey.infrastructure.hub.exposure import ExposureFinding, HubExposureCheck
from vibey.infrastructure.hub.interfaces.authenticator_interface import (
    HubAuthenticatorInterface,
)
from vibey.infrastructure.hub.interfaces.exposure_interface import HubExposureCheckInterface
from vibey.infrastructure.hub.interfaces.lanes_interface import LaneScannerInterface
from vibey.infrastructure.hub.interfaces.local_token_interface import LocalTokenStoreInterface
from vibey.infrastructure.hub.interfaces.server_interface import (
    HubServerInterface,
    LocalNamesInterface,
)
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.lanes import LaneEngine, LaneScanner
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.server import LocalNames, UvicornServer
from vibey.infrastructure.hub.settings import DEFAULT_PORT, HubSettings, HubSettingsLoader

NOW = 1_800_000_000.0


def _request(**headers: str) -> HubRequest:
    return HubRequest(method="GET", path="/", query="", headers=headers, body=b"")


def test_every_adapter_meets_its_declared_seam(tmp_path: Path) -> None:
    assert isinstance(HubSettingsLoader(), HubSettingsLoaderInterface)
    assert isinstance(LocalTokenStore(tmp_path), LocalTokenStoreInterface)
    assert isinstance(LocalTokenAuthenticator("x"), HubAuthenticatorInterface)
    assert isinstance(HubExposureCheck(), HubExposureCheckInterface)
    assert isinstance(LaneScanner(engines=[], roots=[], now=lambda: NOW), LaneScannerInterface)
    assert isinstance(UvicornServer(), HubServerInterface)
    assert isinstance(LocalNames(), LocalNamesInterface)


# --- [hub] ------------------------------------------------------------------------------


def test_no_file_and_no_table_declare_nothing(tmp_path: Path) -> None:
    loader = HubSettingsLoader()
    assert loader.load(tmp_path / "missing.toml") == HubSettings()
    (tmp_path / "vibey.toml").write_text('[project]\nname = "x"\n')
    settings = loader.load(tmp_path / "vibey.toml")
    assert settings.lan is False and settings.port == DEFAULT_PORT and settings.names == frozenset()
    assert settings.state_dir.name == "hub" and settings.lane_roots == ()


def test_a_declared_table_is_read(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text(
        "[hub]\nlan = true\nport = 9000\nnames = [' Studio.local ']\n"
        f"state_dir = '{tmp_path}/state'\nlane_roots = ['{tmp_path}/lanes']\n"
    )
    settings = HubSettingsLoader().load(tmp_path / "vibey.toml")
    assert settings == HubSettings(
        lan=True,
        port=9000,
        names=frozenset({"studio.local"}),
        state_dir=tmp_path / "state",
        lane_roots=(tmp_path / "lanes",),
    )


@pytest.mark.parametrize(
    ("table", "where"),
    [
        ("lna = true", "hub"),
        ('lan = "yes"', "hub.lan"),
        ("port = 0", "hub.port"),
        ("port = true", "hub.port"),
        ('port = "80"', "hub.port"),
        ("names = ['']", "hub.names"),
        ("names = 'a'", "hub.names"),
        ("state_dir = 3", "hub.state_dir"),
        ("lane_roots = [3]", "hub.lane_roots"),
    ],
)
def test_a_malformed_table_is_refused_never_read_as_undeclared(
    tmp_path: Path, table: str, where: str
) -> None:
    (tmp_path / "vibey.toml").write_text(f"[hub]\n{table}\n")
    with pytest.raises(ConfigError) as caught:
        HubSettingsLoader().load(tmp_path / "vibey.toml")
    assert caught.value.path == where


def test_an_unreadable_or_invalid_file_is_refused(tmp_path: Path) -> None:
    (tmp_path / "bad.toml").write_text("[hub\n")
    with pytest.raises(ConfigError, match="not valid TOML"):
        HubSettingsLoader().load(tmp_path / "bad.toml")
    (tmp_path / "dir.toml").mkdir()
    with pytest.raises(ConfigError, match="cannot be read"):
        HubSettingsLoader().load(tmp_path / "dir.toml")
    (tmp_path / "scalar.toml").write_text("hub = 3\n")
    with pytest.raises(ConfigError, match="must be a table"):
        HubSettingsLoader().load(tmp_path / "scalar.toml")


# --- the host token and the runtime record ----------------------------------------------


def test_the_token_is_made_once_owner_only_and_then_reused(tmp_path: Path) -> None:
    store = LocalTokenStore(tmp_path / "hub")
    token = store.token()
    assert len(token) >= 40
    assert store.token() == token
    assert (tmp_path / "hub" / "token").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "hub").stat().st_mode & 0o777 == 0o700


def test_a_token_others_can_read_is_refused(tmp_path: Path) -> None:
    store = LocalTokenStore(tmp_path)
    store.token()
    (tmp_path / "token").chmod(0o644)
    with pytest.raises(PermissionError, match="open to other accounts"):
        store.token()


def test_the_runtime_record_round_trips_and_clears(tmp_path: Path) -> None:
    store = LocalTokenStore(tmp_path)
    assert store.serving() is None
    store.record_serving(ServingRecord(host="127.0.0.1", port=8765, pid=42))
    assert store.serving() == ServingRecord(host="127.0.0.1", port=8765, pid=42)
    assert (tmp_path / "serving.json").stat().st_mode & 0o777 == 0o600
    store.clear_serving()
    store.clear_serving()
    assert store.serving() is None


@pytest.mark.parametrize("content", ["[]", '{"host": "h", "port": "p", "pid": 1}'])
def test_a_malformed_runtime_record_is_not_read_as_none(tmp_path: Path, content: str) -> None:
    (tmp_path / "serving.json").write_text(content)
    with pytest.raises(ValueError):
        LocalTokenStore(tmp_path).serving()


async def test_the_local_token_names_the_host_and_nothing_else_does() -> None:
    authenticator = LocalTokenAuthenticator("secret")
    assert await authenticator.authenticate(_request(authorization="Bearer secret")) is (
        HOST_PRINCIPAL
    )
    assert await authenticator.authenticate(_request(authorization="bearer  secret ")) is (
        HOST_PRINCIPAL
    )
    assert await authenticator.authenticate(_request(authorization="Bearer other")) is None
    assert await authenticator.authenticate(_request(authorization="Token secret")) is None
    assert await authenticator.authenticate(_request()) is None
    assert HubPrincipal(name="host", scopes=frozenset(HubScope)) == HOST_PRINCIPAL
    with pytest.raises(ValueError):
        LocalTokenAuthenticator("")


# --- exposure ---------------------------------------------------------------------------


def _exposure(
    tmp_path: Path, host: str | None, *, lan: bool, pid: int | None = None
) -> ExposureFinding:
    store = LocalTokenStore(tmp_path)
    if host is not None:
        store.record_serving(ServingRecord(host=host, port=8765, pid=pid or os.getpid()))
    return HubExposureCheck().run(HubSettings(lan=lan, state_dir=tmp_path), store)


def test_exposure_passes_loopback_and_a_declared_lan(tmp_path: Path) -> None:
    loopback = _exposure(tmp_path, "127.0.0.1", lan=False)
    declared = _exposure(tmp_path, "192.168.1.20", lan=True)
    assert (loopback.mark, loopback.ok) == ("PASS", True) and "loopback" in loopback.detail
    assert (declared.mark, declared.ok) == ("PASS", True) and "declared" in declared.detail


def test_exposure_fails_an_undeclared_lan(tmp_path: Path) -> None:
    finding = _exposure(tmp_path, "0.0.0.0", lan=False)  # nosec B104 - a record, not a bind
    assert (finding.mark, finding.ok) == ("FAIL", False)
    assert "does not declare [hub] lan = true" in finding.detail


def test_exposure_is_unknown_without_evidence(tmp_path: Path) -> None:
    assert _exposure(tmp_path, None, lan=False).mark == "UNKNOWN"
    stale = _exposure(tmp_path, "0.0.0.0", lan=False, pid=2**22 + 12345)  # nosec B104
    assert (stale.mark, stale.ok) == ("UNKNOWN", True) and "gone" in stale.detail
    (tmp_path / "serving.json").write_text("[]")
    assert HubExposureCheck().run(
        HubSettings(state_dir=tmp_path), LocalTokenStore(tmp_path)
    ).mark == ("UNKNOWN")


def test_a_process_of_another_account_is_alive(monkeypatch: pytest.MonkeyPatch) -> None:
    def denied(pid: int, signal: int) -> None:
        raise PermissionError

    monkeypatch.setattr(os, "kill", denied)
    assert HubExposureCheck._alive(1) is True


# --- lanes ------------------------------------------------------------------------------


def _lane(
    cwd: Path, run: str, *, mtime: float, status: str | None = None, raw: str | None = None
) -> Path:
    events = cwd / ".qwenloop" / "runs" / run / "events.jsonl"
    events.parent.mkdir(parents=True)
    events.write_text('{"type": "turn"}\n')
    os.utime(events, (mtime, mtime))
    if status is not None or raw is not None:
        snapshots = events.parent / "snapshots"
        snapshots.mkdir()
        (snapshots / "latest.json").write_text(
            raw if raw is not None else json.dumps({"status": status})
        )
    return events


def test_lanes_are_found_in_each_root_and_its_children(tmp_path: Path) -> None:
    worktree = tmp_path / "storm" / "lane-a"
    _lane(tmp_path / "storm", "r0", mtime=NOW - 10)
    running = _lane(worktree, "r1", mtime=NOW - 5)
    _lane(worktree, "r2", mtime=NOW - 600)
    _lane(worktree, "r3", mtime=NOW - 30, status="completed")
    _lane(worktree, "r4", mtime=NOW - 40, status="winding_down")
    _lane(worktree, "r5", mtime=NOW - 50, status="thinking")
    _lane(worktree, "r6", mtime=NOW - 55, raw="not json")
    _lane(worktree, "r7", mtime=NOW - 58, raw='{"status": 3}')
    _lane(worktree, "old", mtime=NOW - 3 * 24 * 3600)
    (worktree / ".qwenloop" / "runs" / "empty").mkdir()
    scanner = LaneScanner(
        engines=[LaneEngine("qwenloop", ".qwenloop"), LaneEngine("claudeloop", ".claudeloop")],
        roots=[tmp_path / "storm", tmp_path / "storm", tmp_path / "missing"],
        now=lambda: NOW,
    )
    lanes = scanner.lanes()
    assert [lane["id"] for lane in lanes] == ["r1", "r0", "r3", "r4", "r5", "r6", "r7", "r2"]
    first = lanes[0]
    assert first == {
        "id": "r1",
        "engine": "qwenloop",
        "cwd": str(worktree),
        "events_path": str(running),
        "label": "lane-a · qwenloop",
        "state": "running",
        "outcome": None,
        "offset": len('{"type": "turn"}\n'),
        "last_event_at": NOW - 5,
    }
    by_id = {lane["id"]: lane for lane in lanes}
    assert by_id["r2"]["state"] == "quiet"
    assert (by_id["r3"]["state"], by_id["r3"]["outcome"]) == ("finished", "completed")
    assert by_id["r4"]["outcome"] == "stopped"
    assert by_id["r5"]["state"] == "running" and by_id["r5"]["outcome"] is None
    assert by_id["r6"]["outcome"] is None and by_id["r7"]["outcome"] is None


def test_a_lane_with_no_float_time_sorts_last() -> None:
    assert LaneScanner._last_event({"last_event_at": "x"}) == 0.0


# --- the server and this computer's names ------------------------------------------------


async def test_the_server_runs_uvicorn_without_trusting_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}

    async def serve(self: uvicorn.Server) -> None:
        seen["config"] = self.config

    monkeypatch.setattr(uvicorn.Server, "serve", serve)
    app = FastAPI()
    await UvicornServer().serve(app, host="127.0.0.1", port=9999)
    config = seen["config"]
    assert (config.host, config.port, config.proxy_headers) == ("127.0.0.1", 9999, False)
    assert config.server_header is False and config.app is app


def test_this_computers_names_include_its_mdns_name_and_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(socket, "gethostname", lambda: "Studio")
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_: [(0, 0, 0, "", ("192.168.1.20", 0)), (0, 0, 0, "", ("fe80::1", 0, 0, 0))],
    )
    names = LocalNames().names("0.0.0.0")  # nosec B104 - a name, not a bind
    assert names == frozenset({"studio", "studio.local", "192.168.1.20", "fe80::1"})
    monkeypatch.setattr(socket, "gethostname", lambda: "box.local")

    def unresolvable(*_: Any) -> Any:
        raise OSError

    monkeypatch.setattr(socket, "getaddrinfo", unresolvable)
    assert LocalNames().names("192.168.1.30") == frozenset({"box.local", "192.168.1.30"})


def test_a_runtime_record_is_cleared_only_by_the_process_it_names(tmp_path: Path) -> None:
    store = LocalTokenStore(tmp_path)
    store.clear_serving(pid=1)
    store.record_serving(ServingRecord(host="127.0.0.1", port=8765, pid=42))
    store.clear_serving(pid=7)
    assert store.serving() is not None
    store.clear_serving(pid=42)
    assert store.serving() is None
    (tmp_path / "serving.json").write_text("[]")
    store.clear_serving(pid=42)
    assert (tmp_path / "serving.json").exists()


def test_a_state_directory_of_another_account_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(os, "getuid", lambda: 12345)
    with pytest.raises(PermissionError, match="another account"):
        LocalTokenStore(tmp_path / "hub").token()


def test_a_symlinked_token_is_never_followed(tmp_path: Path) -> None:
    store = LocalTokenStore(tmp_path / "hub")
    store.token()
    (tmp_path / "hub" / "token").unlink()
    (tmp_path / "planted").write_text("known")
    (tmp_path / "hub" / "token").symlink_to(tmp_path / "planted")
    with pytest.raises(OSError):
        store.token()
