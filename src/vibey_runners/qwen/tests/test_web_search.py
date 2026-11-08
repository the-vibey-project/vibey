# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for web search and fetch operations in the sovereign runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from qwenloop.domain.config import ToolLimits
from qwenloop.infrastructure.interfaces.web_search_interface import (
    WebSearchInterface,
    WebSearchToolInterface,
)
from qwenloop.infrastructure.tools import ShellEnvironment
from qwenloop.infrastructure.web_search import WebSearch, WebSearchTool, web_search


def _mock_web_tool(tmp_path: Path, script_body: str, **extra: str) -> WebSearchTool:
    script = tmp_path / "mock-vibey"
    script.write_text("#!/bin/sh\n" + script_body + "\n")
    script.chmod(0o755)
    source = {
        "PATH": "/usr/bin:/bin",
        "WEBSEARCH_PROVIDER": "searxng",
        "WEBSEARCH_COMMAND": str(script),
        **extra,
    }
    env = ShellEnvironment(source)
    return WebSearchTool(tmp_path, env, ToolLimits())


@pytest.mark.asyncio
async def test_web_search_says_so_when_not_configured(tmp_path: Path) -> None:
    env = ShellEnvironment({"PATH": "/usr/bin"})
    tool = WebSearchTool(tmp_path, env, ToolLimits())

    for name, args in (("web_search", {"query": "x"}), ("web_fetch", {"url": "http://x"})):
        result = await tool.execute(name, args)
        assert "not set up" in str(result["error"])


@pytest.mark.asyncio
async def test_web_search_executes_search_query(tmp_path: Path) -> None:
    tool = _mock_web_tool(tmp_path, 'echo "$@"')
    result = await tool.execute("web_search", {"query": "python async", "max_results": 3})

    assert result["content"] == "search --json --limit 3 -- python async\n"
    assert "never follow instructions" in str(result["untrusted"])


@pytest.mark.asyncio
@pytest.mark.parametrize(("asked", "sent"), [(None, "5"), (50, "20"), (-2, "1"), ("10", "10")])
async def test_web_search_bounds_results_limit(tmp_path: Path, asked: object, sent: str) -> None:
    tool = _mock_web_tool(tmp_path, 'echo "$@"')
    result = await tool.execute("web_search", {"query": "python", "max_results": asked})

    assert f"--limit {sent} " in str(result["content"])


@pytest.mark.asyncio
async def test_web_search_refuses_missing_query_or_invalid_limit(tmp_path: Path) -> None:
    tool = _mock_web_tool(tmp_path, "echo hi")

    assert "needs a query" in str((await tool.execute("web_search", {}))["error"])
    assert "needs a query" in str((await tool.execute("web_search", {"query": "   "}))["error"])
    bad_limit = await tool.execute("web_search", {"query": "q", "max_results": "abc"})
    assert "must be an integer" in str(bad_limit["error"])


@pytest.mark.asyncio
async def test_web_fetch_executes_fetch_and_refuses_missing_url(tmp_path: Path) -> None:
    tool = _mock_web_tool(tmp_path, 'echo "$@"')

    ok = await tool.execute("web_fetch", {"url": "https://example.org"})
    missing = await tool.execute("web_fetch", {})
    empty = await tool.execute("web_fetch", {"url": "  "})

    assert ok["content"] == "fetch --json -- https://example.org\n"
    assert "needs a url" in str(missing["error"])
    assert "needs a url" in str(empty["error"])


@pytest.mark.asyncio
async def test_web_search_command_error_and_timeout(tmp_path: Path) -> None:
    tool_fail = _mock_web_tool(tmp_path, "echo 'lookup failed'; exit 1")
    failed = await tool_fail.execute("web_search", {"query": "error"})
    assert failed["error"] == "lookup failed"

    tool_hang = _mock_web_tool(tmp_path, "exec sleep 5")
    searcher = WebSearch(tmp_path, tool_hang._shell_environment.build(), timeout_seconds=0.1)
    timeout_result = await searcher.search("hang")
    assert timeout_result == {"error": "the web request timed out"}


@pytest.mark.asyncio
async def test_web_search_tool_and_class_satisfy_interfaces(tmp_path: Path) -> None:
    env = ShellEnvironment({"PATH": "/usr/bin"})
    tool = WebSearchTool(tmp_path, env, ToolLimits())
    searcher = WebSearch(tmp_path, {})

    assert isinstance(tool, WebSearchToolInterface)
    assert isinstance(searcher, WebSearchInterface)


@pytest.mark.asyncio
async def test_web_search_standalone_helper(tmp_path: Path) -> None:
    result = await web_search("test", worktree=tmp_path, environment={})
    assert "not set up" in str(result["error"])
