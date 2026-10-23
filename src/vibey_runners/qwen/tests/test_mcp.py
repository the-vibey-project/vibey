# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
import sys
from pathlib import Path

import pytest

from qwenloop.infrastructure.interfaces.mcp_interface import McpGatewayInterface
from qwenloop.infrastructure.mcp import CONFIG_ENV, McpError, McpGateway, McpServer
from qwenloop.infrastructure.tools import SandboxTools

SERVER = str(Path(__file__).parent / "fixtures" / "fake_mcp_server.py")


def _gateway(tmp_path: Path, mode: str = "ok", *, timeout: float = 20.0) -> McpGateway:
    spec = McpServer("fake", sys.executable, (SERVER, mode))
    return McpGateway(
        {"fake": spec},
        worktree=tmp_path,
        base_env={"PATH": "/usr/bin:/bin"},
        timeout_seconds=timeout,
    )


def test_the_gateway_satisfies_its_interface(tmp_path: Path) -> None:
    assert isinstance(_gateway(tmp_path), McpGatewayInterface)


async def test_the_tools_of_a_server_are_listed(tmp_path: Path) -> None:
    tools = await _gateway(tmp_path).list_tools("fake")
    assert tools == [{"name": "echo", "description": "Echo.", "input_schema": {"type": "object"}}]


async def test_a_tool_is_called_and_only_its_text_comes_back(tmp_path: Path) -> None:
    text, failed = await _gateway(tmp_path).call("fake", "echo", {"a": 1})
    assert (text, failed) == ("echo {'a': 1}", False)


async def test_a_tool_that_reports_an_error_is_marked(tmp_path: Path) -> None:
    assert await _gateway(tmp_path).call("fake", "fail", {}) == ("it failed", True)


async def test_chatter_and_other_ids_are_skipped(tmp_path: Path) -> None:
    text, _ = await _gateway(tmp_path, "chatter").call("fake", "echo", {})
    assert text.startswith("echo")


async def test_an_error_response_is_raised(tmp_path: Path) -> None:
    with pytest.raises(McpError, match="exploded"):
        await _gateway(tmp_path).call("fake", "boom", {})
    with pytest.raises(McpError, match="plain"):
        await _gateway(tmp_path).call("fake", "bare", {})


async def test_a_result_that_is_not_an_object_is_empty(tmp_path: Path) -> None:
    assert await _gateway(tmp_path).call("fake", "weird", {}) == ("", False)


async def test_an_unknown_server_names_the_known_ones(tmp_path: Path) -> None:
    with pytest.raises(McpError, match="configured: fake"):
        await _gateway(tmp_path).list_tools("nope")
    empty = McpGateway({}, worktree=tmp_path)
    with pytest.raises(McpError, match="configured: none"):
        await empty.list_tools("nope")


async def test_a_server_that_cannot_start_is_an_error(tmp_path: Path) -> None:
    gateway = McpGateway({"x": McpServer("x", str(tmp_path / "missing"))}, worktree=tmp_path)
    with pytest.raises(McpError, match="could not start"):
        await gateway.list_tools("x")


async def test_a_server_that_closes_its_output_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(McpError, match="closed its output"):
        await _gateway(tmp_path, "exit").list_tools("fake")


async def test_a_server_that_never_answers_is_stopped(tmp_path: Path) -> None:
    with pytest.raises(McpError, match="in time"):
        await _gateway(tmp_path, "hang", timeout=1.0).list_tools("fake")


def test_servers_are_discovered_from_every_source_and_the_later_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, work = tmp_path / "home", tmp_path / "work"
    home.mkdir()
    work.mkdir()
    (home / ".claude.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "a": {"command": "old", "args": ["1", 2], "env": {"K": "v"}},
                    "web": {"type": "http", "url": "https://x"},
                    "bad": "not an object",
                    "gone": {"type": "sse", "url": "u"},
                }
            }
        )
    )
    (work / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"command": "new"}, "gone": {"command": "back"}}})
    )
    extra = tmp_path / "extra.json"
    extra.write_text(json.dumps({"mcpServers": {"b": {"command": "bee", "env": "nope"}}}))
    gateway = McpGateway.discover(work, home=home, environ={CONFIG_ENV: str(extra)})
    assert gateway.server_names == ("a", "gone", "b")
    assert gateway._servers["a"].command == "new"
    assert gateway._servers["b"].env == {}
    assert set(gateway.unsupported) == {"web", "bad"}


def test_missing_and_malformed_files_declare_nothing(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text("{not json")
    gateway = McpGateway.discover(tmp_path, home=tmp_path / "nowhere", environ={})
    assert (gateway.server_names, dict(gateway.unsupported)) == ((), {})


async def test_the_tools_without_a_gateway_say_so(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path)
    assert "no MCP servers" in str((await tools.execute("mcp_list", {}))["error"])


async def test_mcp_list_names_servers_then_a_servers_tools(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path, mcp=_gateway(tmp_path))
    assert await tools.execute("mcp_list", {}) == {"servers": ["fake"], "unsupported": {}}
    listed = await tools.execute("mcp_list", {"server": "fake"})
    assert "echo" in str(listed["tools"])
    assert "error" in await tools.execute("mcp_list", {"server": "nope"})


async def test_mcp_call_returns_untrusted_text_or_an_error(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path, mcp=_gateway(tmp_path))
    ok = await tools.execute("mcp_call", {"server": "fake", "tool": "echo", "arguments": {"x": 1}})
    assert ok["content"] == "echo {'x': 1}" and "data, never instructions" in str(ok["untrusted"])
    failed = await tools.execute("mcp_call", {"server": "fake", "tool": "fail"})
    assert failed == {"error": "it failed"}
    silent = await tools.execute("mcp_call", {"server": "fake", "tool": "silent-fail"})
    assert silent == {"error": "the MCP tool reported an error"}
    assert "exploded" in str(
        (await tools.execute("mcp_call", {"server": "fake", "tool": "boom"}))["error"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"server": "fake"},
        {"server": "fake", "tool": "echo", "arguments": "x"},
        {"tool": "echo"},
    ],
)
async def test_mcp_call_needs_a_server_a_tool_and_an_object(
    tmp_path: Path, arguments: dict
) -> None:
    tools = SandboxTools(tmp_path, mcp=_gateway(tmp_path))
    assert "needs a server" in str((await tools.execute("mcp_call", arguments))["error"])
