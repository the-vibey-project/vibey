# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey mcp --scope web`: the stdio MCP server a claudeloop run's `vibey-web` connector starts
(SP-LOOPS Phase 6, Task 6; R3).

It serves exactly `vibey_search` and `vibey_fetch`, and never another hub tool: they are the only
two it lists, the only two it will build a call for, and it holds only the `web` scope. Each call
goes to the hub with the session's own token, read from its file on every call, through the same
client `vibey search` uses. A session with no web, or a person, is told why and nothing is sent.
The hub is an `httpx.MockTransport`; the token file is real and POSIX-moded. No network, no real
process, no sleeps.
"""

from __future__ import annotations

import io
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tests.infrastructure.web.session_hub_fakes import (
    FETCH_ANSWER,
    HUB_URL,
    SEARCH_ANSWER,
    TOKEN,
    StubHub,
    token_file,
)
from vibey.cli import mcp as mcp_module
from vibey.cli.main import app
from vibey.cli.mcp import McpCommand, McpScope
from vibey.domain.host_tools import (
    HOST_TOOLS,
    SESSION_WEB_INSTRUCTIONS,
    WEB_TOOL_CATALOG,
    HubCall,
)
from vibey.domain.hub_scope import HubScope
from vibey.domain.session_principal import SESSION_SCOPES
from vibey.domain.session_web_state import NO_RUN_FOLDER, STATE_VARIABLE, TOKEN_FILE_VARIABLE
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface
from vibey.infrastructure.mcp.interfaces.session_web_gateway_interface import (
    SessionWebGatewayInterface,
)
from vibey.infrastructure.mcp.session_web_gateway import SessionWebGateway
from vibey.infrastructure.mcp.stdio_server import McpStdioServer
from vibey.infrastructure.web.interfaces.session_web_access_interface import (
    SessionWebAccessInterface,
)
from vibey.infrastructure.web.session import HUB_URL_VARIABLE, SessionWebAccess
from vibey.infrastructure.web.session_hub_client import SessionHubClient

pytestmark = pytest.mark.skipif(os.name != "posix", reason="token file modes are POSIX")

WEB_TOOLS = {"vibey_search", "vibey_fetch"}


def _through(hub: StubHub) -> Any:
    def make(access: SessionWebAccessInterface) -> SessionHubClient:
        assert access.token_file is not None
        return SessionHubClient(
            access.hub_url, access.token_file, client=hub, web_settings=lambda: WebToolSettings()
        )

    return make


def _never(access: SessionWebAccessInterface) -> SessionHubClient:
    raise AssertionError("no hub may be asked for a session without web, or a person")


def _server(environ: Mapping[str, str], hub: Any = _never) -> McpStdioServer:
    gateway = SessionWebGateway(SessionWebAccess.from_environment(environ), hub=hub)
    return McpStdioServer(
        gateway=gateway, tools=WEB_TOOL_CATALOG, instructions=SESSION_WEB_INSTRUCTIONS
    )


def _call(server: McpStdioServer, name: str, arguments: Mapping[str, object]) -> dict[str, Any]:
    reply = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(arguments)},
        }
    )
    assert reply is not None
    result: dict[str, Any] = reply["result"]
    return result


def _session(path: Path) -> dict[str, str]:
    return {HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: str(path)}


def test_the_gateway_meets_its_seams_and_holds_only_web() -> None:
    gateway = SessionWebGateway(SessionWebAccess.from_environment({}))
    assert isinstance(gateway, SessionWebGatewayInterface)
    assert isinstance(gateway, HubGatewayInterface)
    assert gateway.agent_scopes() == SESSION_SCOPES == frozenset({HubScope.WEB})


def test_the_web_catalog_is_exactly_the_hubs_two_web_tools() -> None:
    assert {tool.name for tool in WEB_TOOL_CATALOG.all()} == WEB_TOOLS
    assert {tool.name for tool in HOST_TOOLS if tool.scope is HubScope.WEB} == WEB_TOOLS
    assert len(HOST_TOOLS) > len(WEB_TOOLS)


def test_it_lists_exactly_vibey_search_and_vibey_fetch(tmp_path: Path) -> None:
    server = _server(_session(token_file(tmp_path)))
    listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    assert {tool["name"] for tool in listed["result"]["tools"]} == WEB_TOOLS


def test_initialize_names_the_web_only_instructions(tmp_path: Path) -> None:
    server = _server(_session(token_file(tmp_path)))
    init = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init is not None
    instructions = init["result"]["instructions"]
    assert instructions == SESSION_WEB_INSTRUCTIONS
    assert "vibey_search" in instructions and "vibey_fetch" in instructions
    assert "untrusted" in instructions.lower()


@pytest.mark.parametrize(
    "name",
    sorted({tool.name for tool in HOST_TOOLS} - WEB_TOOLS) + ["vibey_anything"],
)
def test_every_other_hub_tool_is_unknown_here_and_nothing_is_sent(
    tmp_path: Path, name: str
) -> None:
    hub = StubHub()
    result = _call(_server(_session(token_file(tmp_path)), _through(hub)), name, {})
    assert result["isError"] is True
    assert "unknown tool" in result["content"][0]["text"]
    assert hub.requests == []


def test_a_search_goes_to_the_hub_with_the_sessions_own_token(tmp_path: Path) -> None:
    hub = StubHub()
    result = _call(
        _server(_session(token_file(tmp_path)), _through(hub)), "vibey_search", {"query": "q"}
    )

    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == SEARCH_ANSWER
    assert hub.bearer() == f"Bearer {TOKEN}"
    assert hub.requests[-1].url.path == "/api/v1/web/search"
    assert hub.body() == {"query": "q"}


def test_a_fetch_goes_to_the_hub_and_the_token_is_never_in_the_answer(tmp_path: Path) -> None:
    hub = StubHub()
    result = _call(
        _server(_session(token_file(tmp_path)), _through(hub)),
        "vibey_fetch",
        {"url": "https://a.example/"},
    )

    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == FETCH_ANSWER
    assert hub.requests[-1].url.path == "/api/v1/web/fetch"
    assert TOKEN not in result["content"][0]["text"]


def test_a_hub_refusal_is_said_as_a_tool_error_without_the_token(tmp_path: Path) -> None:
    hub = StubHub(429, {"detail": "[web] session_searches is spent for this session"})
    result = _call(
        _server(_session(token_file(tmp_path)), _through(hub)), "vibey_search", {"query": "q"}
    )

    assert result["isError"] is True
    assert "session_searches" in result["content"][0]["text"]
    assert TOKEN not in result["content"][0]["text"]


def test_an_argument_the_hub_would_refuse_is_refused_before_anything_is_sent(
    tmp_path: Path,
) -> None:
    hub = StubHub()
    result = _call(_server(_session(token_file(tmp_path)), _through(hub)), "vibey_search", {})
    assert result["isError"] is True
    assert hub.requests == []


@pytest.mark.parametrize(
    ("environ", "said"),
    [
        ({STATE_VARIABLE: "none:no-run-folder"}, NO_RUN_FOLDER),
        ({HUB_URL_VARIABLE: HUB_URL}, TOKEN_FILE_VARIABLE),
        ({}, "only an engine session"),
    ],
)
def test_without_a_grant_every_call_says_why_and_nothing_is_sent(
    environ: dict[str, str], said: str
) -> None:
    result = _call(_server(environ), "vibey_search", {"query": "q"})
    assert result["isError"] is True
    assert said in result["content"][0]["text"]


def test_reach_is_the_same_call_and_never_starts_a_hub(tmp_path: Path) -> None:
    hub = StubHub()
    access = SessionWebAccess.from_environment(_session(token_file(tmp_path)))
    gateway = SessionWebGateway(access, hub=_through(hub))
    call = WEB_TOOL_CATALOG.build_call("vibey_search", {"query": "q"}, request_id="r")
    response = gateway.reach(call)
    assert (response.status_code, response.ok) == (200, True)
    assert json.loads(response.text) == SEARCH_ANSWER


def test_a_call_for_a_tool_the_session_client_does_not_know_is_refused() -> None:
    """A defence in depth: the gateway sends only the two web routes, whatever it is handed."""
    access = SessionWebAccess.from_environment(
        {HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: "/t"}
    )
    gateway = SessionWebGateway(access, hub=_never)
    with pytest.raises(Exception, match="only vibey_search and vibey_fetch"):
        gateway.call(HubCall(tool="vibey_projects", method="GET", route="/api/v1/projects"))


# -- the command ----------------------------------------------------------------------------------


def test_the_scope_is_web_alone() -> None:
    assert [scope.value for scope in McpScope] == ["web"]


def test_the_command_serves_the_web_only_server_over_stdio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = StubHub()
    monkeypatch.setattr(mcp_module, "SESSION_HUB", _through(hub))
    path = token_file(tmp_path)
    lines = (
        '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'
        '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"vibey_search",'
        '"arguments":{"query":"q"}}}\n'
        '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"vibey_status",'
        '"arguments":{}}}\n'
    )

    result = CliRunner().invoke(
        app,
        ["mcp", "--scope", "web", "--token-file", str(path)],
        input=lines,
        env={HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: "", STATE_VARIABLE: ""},
    )

    assert result.exit_code == 0, result.output
    listed, searched, refused = (json.loads(line) for line in result.output.splitlines())
    assert {tool["name"] for tool in listed["result"]["tools"]} == WEB_TOOLS
    assert searched["result"]["isError"] is False
    assert refused["result"]["isError"] is True
    assert len(hub.requests) == 1 and hub.bearer() == f"Bearer {TOKEN}"
    assert TOKEN not in result.output


def test_the_token_file_argument_stands_for_the_environments_name(tmp_path: Path) -> None:
    path = token_file(tmp_path)
    command = McpCommand.web(
        {HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: "/somewhere/else"},
        path,
        stdin=io.StringIO(""),
        stdout=io.StringIO(),
    )
    assert command.access.token_file == path


def test_without_the_argument_the_environments_token_file_is_used(tmp_path: Path) -> None:
    path = token_file(tmp_path)
    command = McpCommand.web({HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: str(path)}, None)
    assert command.access.token_file == path


@pytest.mark.parametrize(
    "argv",
    [
        ["mcp", "--scope", "view"],
        ["mcp", "--scope", "agent"],
        ["mcp", "--token-file", "/runs/x/web-token"],
    ],
)
def test_any_other_scope_or_a_token_file_without_the_web_scope_is_a_usage_error(
    argv: list[str],
) -> None:
    result = CliRunner().invoke(app, argv, input="")
    assert result.exit_code == 2
