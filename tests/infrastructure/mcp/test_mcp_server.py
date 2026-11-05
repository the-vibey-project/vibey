# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the MCP hub gateway and JSON-RPC 2.0 stdio server (ADR-0100)."""

from __future__ import annotations

import io
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from vibey.cli.interfaces.mcp_interface import McpCommandInterface
from vibey.cli.mcp import MCP_COMMAND, McpCommand
from vibey.domain.config import ConfigError
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.settings import HubSettings
from vibey.infrastructure.hub.tls import CERT_FILE
from vibey.infrastructure.mcp.hub_gateway import (
    HUB_GATEWAY,
    HubGateway,
    HubGatewayError,
    HubGatewayResponse,
    _default_starter,
)
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface
from vibey.infrastructure.mcp.interfaces.stdio_server_interface import McpStdioServerInterface
from vibey.infrastructure.mcp.stdio_server import (
    INVALID_PARAMS,
    INVALID_REQUEST,
    LATEST_PROTOCOL,
    MCP_STDIO_SERVER,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    McpStdioServer,
)

SAMPLE_UUID = "12345678-1234-5678-1234-567812345678"
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


class _FakeHttpClient:
    def __init__(
        self,
        *,
        status_code: int = 200,
        text: str = '{"ok": true}',
        fail_times: int = 0,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.fail_times = fail_times
        self.calls: list[dict[str, Any]] = []

    def factory(self, **kwargs: Any) -> _FakeHttpClient:
        self._init_kwargs = kwargs
        return self

    def __enter__(self) -> _FakeHttpClient:
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def request(
        self,
        method: str,
        route: str,
        *,
        params: Any = None,
        json: Any = None,
    ) -> httpx.Response:
        self.calls.append(
            {
                **self._init_kwargs,
                "method": method,
                "route": route,
                "params": params,
                "json": json,
            }
        )
        if self.fail_times > 0:
            self.fail_times -= 1
            raise httpx.ConnectError("connection refused")
        return httpx.Response(self.status_code, text=self.text)


class _BrokenSettings:
    def load(self, path: Path) -> HubSettings:
        raise ConfigError("hub.agent_scopes", "bad config")


def test_interfaces_are_satisfied() -> None:
    assert isinstance(HUB_GATEWAY, HubGatewayInterface)
    assert isinstance(MCP_STDIO_SERVER, McpStdioServerInterface)
    assert isinstance(MCP_COMMAND, McpCommandInterface)


def test_default_starter_returns_true_on_zero_and_false_on_oserror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(args=a[0], returncode=0),
    )
    assert _default_starter() is True

    def raise_oserror(*_: Any, **__: Any) -> Any:
        raise OSError("missing binary")

    monkeypatch.setattr(subprocess, "run", raise_oserror)
    assert _default_starter() is False


def test_gateway_agent_scopes_reads_settings_and_falls_back_on_config_error(
    tmp_path: Path,
) -> None:
    toml = tmp_path / "vibey.toml"
    toml.write_text("[hub]\nagent_scopes = ['view']\n")
    gw = HubGateway(config_path=lambda: toml)
    assert gw.agent_scopes() == frozenset({HubScope.VIEW})

    broken = HubGateway(settings=_BrokenSettings(), config_path=lambda: toml)
    assert broken.agent_scopes() == AGENT_DEFAULT_SCOPES


def test_gateway_sends_agent_token_and_maps_wildcard_and_ipv6_hosts(tmp_path: Path) -> None:
    state = tmp_path / "state"
    toml = tmp_path / "vibey.toml"
    toml.write_text(f"[hub]\nstate_dir = '{state}'\n")
    store = LocalTokenStore(state)
    host_token = store.token()
    agent_token = store.agent_token()
    assert agent_token != host_token
    store.record_serving(
        ServingRecord(host="0.0.0.0", port=8765, pid=1234, tls=False)  # nosec B104
    )

    fake = _FakeHttpClient(status_code=200, text='[{"name":"demo"}]')
    gw = HubGateway(
        config_path=lambda: toml,
        client=fake.factory,
        starter=lambda: False,
    )
    res = gw.call(
        HubCall(
            tool="vibey_ledger",
            method="GET",
            route=f"/api/v1/projects/{SAMPLE_UUID}/ledger",
            query=(("limit", "10"),),
        )
    )
    assert res == HubGatewayResponse(status_code=200, text='[{"name":"demo"}]', ok=True)
    assert len(fake.calls) == 1
    sent = fake.calls[0]
    assert sent["base_url"] == "http://127.0.0.1:8765"
    assert sent["headers"] == {"authorization": f"Bearer {agent_token}"}
    assert sent["verify"] is True
    assert sent["params"] == [("limit", "10")]

    # IPv6 + TLS path
    store.record_serving(ServingRecord(host="::1", port=9000, pid=1234, tls=True))
    res_tls = gw.call(
        HubCall(
            tool="vibey_start_project",
            method="POST",
            route="/api/v1/projects",
            body={"name": "demo", "intake": "hi"},
        )
    )
    assert res_tls.ok is True
    sent_tls = fake.calls[1]
    assert sent_tls["base_url"] == "https://[::1]:9000"
    assert sent_tls["verify"] == str(state / CERT_FILE)
    assert sent_tls["json"] == {"name": "demo", "intake": "hi"}


def test_gateway_starts_hub_when_not_running_or_when_first_request_fails(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    toml = tmp_path / "vibey.toml"
    toml.write_text(f"[hub]\nstate_dir = '{state}'\n")
    store = LocalTokenStore(state)
    started = 0

    def start_hub() -> bool:
        nonlocal started
        started += 1
        store.record_serving(ServingRecord(host="127.0.0.1", port=8765, pid=99, tls=False))
        return True

    fake = _FakeHttpClient(status_code=200, text='{"ok":true}')
    gw = HubGateway(config_path=lambda: toml, client=fake.factory, starter=start_hub)
    res = gw.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))
    assert res.ok is True and started == 1

    # Now simulate stale serving.json where the first request fails with ConnectError,
    # starter restarts the hub, and retry succeeds.
    flaky = _FakeHttpClient(status_code=200, text='{"ok":true}', fail_times=1)
    gw_flaky = HubGateway(config_path=lambda: toml, client=flaky.factory, starter=start_hub)
    res2 = gw_flaky.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))
    assert res2.ok is True and started == 2 and len(flaky.calls) == 2


def test_gateway_error_paths(tmp_path: Path) -> None:
    state = tmp_path / "state"
    toml = tmp_path / "vibey.toml"

    # 1. ConfigError on load
    gw_bad_cfg = HubGateway(settings=_BrokenSettings(), config_path=lambda: toml)
    with pytest.raises(HubGatewayError, match="bad config"):
        gw_bad_cfg.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))

    # 2. agent_scopes = []
    toml.write_text(f"[hub]\nstate_dir = '{state}'\nagent_scopes = []\n")
    gw_disabled = HubGateway(config_path=lambda: toml, starter=lambda: False)
    with pytest.raises(HubGatewayError, match="agent access is disabled"):
        gw_disabled.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))

    # 3. Corrupted agent.token file (mode 0644 is rejected by LocalTokenStore)
    toml.write_text(f"[hub]\nstate_dir = '{state}'\n")
    store = LocalTokenStore(state)
    store.agent_token()
    (state / "agent.token").chmod(0o644)
    gw_bad_tok = HubGateway(config_path=lambda: toml, starter=lambda: False)
    with pytest.raises(HubGatewayError, match="agent token unusable"):
        gw_bad_tok.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))
    (state / "agent.token").unlink()

    # 4. Corrupted serving.json + starter does not produce a record
    (state / "serving.json").write_text("{not-json")
    gw_no_hub = HubGateway(config_path=lambda: toml, starter=lambda: False)
    with pytest.raises(HubGatewayError, match="no hub is running on this computer"):
        gw_no_hub.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))

    # 5. Serving record exists, request fails, starter returns False
    store.record_serving(ServingRecord(host="127.0.0.1", port=8765, pid=99, tls=False))
    always_down = _FakeHttpClient(fail_times=5)
    gw_down = HubGateway(
        config_path=lambda: toml, client=always_down.factory, starter=lambda: False
    )
    with pytest.raises(HubGatewayError, match="the hub did not answer"):
        gw_down.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))

    # 6. Starter returns True, but serving.json is cleared
    def clear_serving() -> bool:
        (state / "serving.json").unlink(missing_ok=True)
        return True

    gw_cleared = HubGateway(
        config_path=lambda: toml, client=always_down.factory, starter=clear_serving
    )
    with pytest.raises(HubGatewayError, match="no hub is running after `vibey hub start`"):
        gw_cleared.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))

    # 7. Starter returns True and serving.json exists, but second attempt also fails
    store.record_serving(ServingRecord(host="127.0.0.1", port=8765, pid=99, tls=False))
    gw_still_down = HubGateway(
        config_path=lambda: toml, client=always_down.factory, starter=lambda: True
    )
    with pytest.raises(HubGatewayError, match="the hub did not answer"):
        gw_still_down.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))


_DEFAULT_STUB_RESPONSE = HubGatewayResponse(200, '[{"id":"1"}]', True)


class _StubGateway:
    def __init__(
        self,
        *,
        scopes: frozenset[HubScope] = AGENT_DEFAULT_SCOPES,
        response: HubGatewayResponse = _DEFAULT_STUB_RESPONSE,
        error: HubGatewayError | None = None,
    ) -> None:
        self._scopes = scopes
        self._response = response
        self._error = error
        self.calls: list[HubCall] = []

    def agent_scopes(self) -> frozenset[HubScope]:
        return self._scopes

    def call(self, call: HubCall) -> HubGatewayResponse:
        self.calls.append(call)
        if self._error is not None:
            raise self._error
        return self._response


def test_stdio_server_initialize_ping_notifications_and_tools_list() -> None:
    gw = _StubGateway(scopes=frozenset({HubScope.VIEW}))
    server = McpStdioServer(gateway=gw, request_id_factory=lambda: "req-fixed")

    # Supported protocol echoed back
    init = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        }
    )
    assert init is not None
    assert init["result"]["protocolVersion"] == "2024-11-05"
    assert init["result"]["serverInfo"]["name"] == "vibey"
    assert "untrusted DATA" in init["result"]["instructions"]

    # Unknown protocol falls back to latest
    init_latest = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {"protocolVersion": "1999-01-01"},
        }
    )
    assert init_latest is not None
    assert init_latest["result"]["protocolVersion"] == LATEST_PROTOCOL

    # Notification returns None
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    # Ping returns empty object
    assert server.handle({"jsonrpc": "2.0", "id": 3, "method": "ping"}) == {
        "jsonrpc": "2.0",
        "id": 3,
        "result": {},
    }

    # tools/list filtered to VIEW scope
    listed = server.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})
    assert listed is not None
    names = {t["name"] for t in listed["result"]["tools"]}
    assert "vibey_projects" in names
    assert "vibey_answer_gate" not in names


def test_stdio_server_tools_call_success_and_error_branches() -> None:
    gw = _StubGateway(
        scopes=frozenset({HubScope.VIEW}),
        response=HubGatewayResponse(200, '{"projects": []}', True),
    )
    server = McpStdioServer(
        gateway=gw, request_id_factory=lambda: "req-fixed", max_response_chars=12
    )

    # 1. Valid call with truncation
    ok = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": "vibey_projects", "arguments": {}},
        }
    )
    assert ok is not None
    assert ok["result"]["isError"] is False
    assert "...[truncated 4 chars]" in ok["result"]["content"][0]["text"]

    # 2. Tool outside granted agent_scopes
    full_server = McpStdioServer(gateway=gw, request_id_factory=lambda: "req-fixed")
    denied = full_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "vibey_answer_gate",
                "arguments": {"gate_id": SAMPLE_UUID, "answer": {"choice": "yes"}},
            },
        }
    )
    assert denied is not None
    assert denied["result"]["isError"] is True
    assert "requires scope" in denied["result"]["content"][0]["text"]

    # 3. Invalid tool arguments -> isError=True
    bad_arg = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "vibey_status", "arguments": {"project_id": "not-a-uuid"}},
        }
    )
    assert bad_arg is not None
    assert bad_arg["result"]["isError"] is True

    # 4. Hub returns HTTP >= 400 -> isError=True
    gw_refused = _StubGateway(response=HubGatewayResponse(403, '{"detail":"forbidden"}', False))
    srv_refused = McpStdioServer(gateway=gw_refused)
    refused = srv_refused.handle(
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "vibey_projects"},
        }
    )
    assert refused is not None
    assert refused["result"]["isError"] is True
    assert "hub refused (403)" in refused["result"]["content"][0]["text"]

    # 5. Gateway raises HubGatewayError -> isError=True
    gw_err = _StubGateway(error=HubGatewayError("no hub"))
    srv_err = McpStdioServer(gateway=gw_err)
    err_reply = srv_err.handle(
        {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {"name": "vibey_projects"},
        }
    )
    assert err_reply is not None
    assert err_reply["result"]["isError"] is True
    assert "no hub" in err_reply["result"]["content"][0]["text"]


@pytest.mark.parametrize(
    ("message", "expected_code"),
    [
        ({"jsonrpc": "1.0", "id": 1, "method": "ping"}, INVALID_REQUEST),
        ({"jsonrpc": "2.0", "method": 123}, INVALID_REQUEST),
        ({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1, 2]}, INVALID_PARAMS),
        ({"jsonrpc": "2.0", "id": 1, "method": "unknown/method"}, METHOD_NOT_FOUND),
        ({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {}}, INVALID_PARAMS),
        (
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "vibey_projects", "arguments": [1]},
            },
            INVALID_PARAMS,
        ),
    ],
)
def test_stdio_server_protocol_errors(message: Mapping[str, Any], expected_code: int) -> None:
    server = McpStdioServer(gateway=_StubGateway())
    reply = server.handle(message)
    assert reply is not None
    assert reply["error"]["code"] == expected_code


def test_stdio_server_line_loop_and_cli_command() -> None:
    server = McpStdioServer(gateway=_StubGateway())
    assert server.handle_line("   \n") is None

    parse_err = json.loads(server.handle_line("{bad json") or "{}")
    assert parse_err["error"]["code"] == PARSE_ERROR

    not_obj = json.loads(server.handle_line("[1, 2, 3]") or "{}")
    assert not_obj["error"]["code"] == INVALID_REQUEST

    stdin = io.StringIO(
        '\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
        '{"jsonrpc":"2.0","id":1,"method":"ping"}\n'
    )
    stdout = io.StringIO()
    cmd = McpCommand(server=server, stdin=stdin, stdout=stdout)
    cmd.run()
    lines = stdout.getvalue().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"jsonrpc": "2.0", "id": 1, "result": {}}


def test_mcp_cli_entrypoint_invokes_command(monkeypatch: pytest.MonkeyPatch) -> None:
    called = 0

    def fake_run() -> None:
        nonlocal called
        called += 1

    monkeypatch.setattr(MCP_COMMAND, "run", fake_run)
    from vibey.cli.mcp import mcp

    mcp()
    assert called == 1
