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

HUB = {"VIBEY_HUB_URL": "http://127.0.0.1:28100", "VIBEY_WEB_TOKEN_FILE": "/runs/r/web-token"}
"""What a vibey worker gives a session that holds its own grant (SP-LOOPS Phase 6)."""


def _mock_web_tool(tmp_path: Path, script_body: str, **extra: str) -> WebSearchTool:
    script = tmp_path / "mock-vibey"
    script.write_text("#!/bin/sh\n" + script_body + "\n")
    script.chmod(0o755)
    source = {"PATH": "/usr/bin:/bin", **HUB, **extra}
    env = ShellEnvironment(source)
    return WebSearchTool(tmp_path, env, ToolLimits(), vibey=str(script), source=source)


@pytest.mark.asyncio
async def test_web_search_says_so_when_not_configured(tmp_path: Path) -> None:
    env = ShellEnvironment({"PATH": "/usr/bin"})
    tool = WebSearchTool(tmp_path, env, ToolLimits(), source={})

    for name, args in (("web_search", {"query": "x"}), ("web_fetch", {"url": "http://x"})):
        result = await tool.execute(name, args)
        assert "not set up" in str(result["error"])


@pytest.mark.asyncio
async def test_a_session_the_worker_gave_no_web_is_told_so_and_where_to_look(
    tmp_path: Path,
) -> None:
    source = {"PATH": "/usr/bin", "VIBEY_WEB_STATE": "none"}
    tool = WebSearchTool(tmp_path, ShellEnvironment(source), ToolLimits(), source=source)

    for name, args in (("web_search", {"query": "x"}), ("web_fetch", {"url": "http://x"})):
        error = str((await tool.execute(name, args))["error"])
        assert "unavailable in this session" in error and "its plan says why" in error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "given", [{"VIBEY_HUB_URL": "http://127.0.0.1:1"}, {"VIBEY_WEB_TOKEN_FILE": "/f"}]
)
async def test_half_of_the_hubs_names_is_not_set_up(tmp_path: Path, given: dict[str, str]) -> None:
    source = {"PATH": "/usr/bin", **given}
    tool = WebSearchTool(
        tmp_path, ShellEnvironment(source), ToolLimits(), vibey="/v", source=source
    )
    assert "not set up" in str((await tool.execute("web_search", {"query": "x"}))["error"])


@pytest.mark.asyncio
async def test_the_old_session_names_are_not_set_up(tmp_path: Path) -> None:
    source = {"PATH": "/usr/bin", "WEBSEARCH_PROVIDER": "searxng", "WEBSEARCH_COMMAND": "/v"}
    tool = WebSearchTool(tmp_path, ShellEnvironment(source), ToolLimits(), source=source)
    assert "not set up" in str((await tool.execute("web_search", {"query": "x"}))["error"])


@pytest.mark.asyncio
async def test_by_default_the_tool_runs_the_vibey_beside_its_own_python_and_reads_its_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from qwenloop.infrastructure import web_search as module

    script = tmp_path / "bin" / "vibey"
    script.parent.mkdir()
    script.write_text('#!/bin/sh\necho "$0 $@"\n')
    script.chmod(0o755)
    monkeypatch.setattr(module.VIBEY_COMMAND, "_executable", str(tmp_path / "bin" / "python"))
    for name, value in HUB.items():
        monkeypatch.setenv(name, value)
    tool = WebSearchTool(tmp_path, ShellEnvironment(), ToolLimits())

    result = await tool.execute("web_search", {"query": "q"})

    assert result["content"] == f"{script} search --json --limit 5 -- q\n"
    monkeypatch.setenv("VIBEY_WEB_STATE", "none")
    monkeypatch.delenv("VIBEY_HUB_URL")
    off = await WebSearchTool(tmp_path, ShellEnvironment(), ToolLimits()).execute(
        "web_search", {"query": "q"}
    )
    assert "unavailable in this session" in str(off["error"])


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
    searcher = WebSearch(
        tmp_path,
        tool_hang._shell_environment.build(),
        command=str(tmp_path / "mock-vibey"),
        timeout_seconds=0.1,
    )
    timeout_result = await searcher.search("hang")
    assert timeout_result == {"error": "the web request timed out"}

    tool_timeout = WebSearchTool(
        tmp_path,
        tool_hang._shell_environment,
        ToolLimits(),
        timeout_seconds=0.1,
        vibey=str(tmp_path / "mock-vibey"),
    )
    assert await tool_timeout.execute("web_search", {"query": "hang"}) == {
        "error": "the web request timed out"
    }


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


@pytest.mark.asyncio
async def test_web_search_class_refuses_a_blank_query_on_its_own(tmp_path: Path) -> None:
    # The tool dispatcher screens blank queries first; a direct caller of WebSearch gets
    # the same plain refusal rather than an empty `vibey search` run.
    searcher = WebSearch(tmp_path, HUB)

    assert await searcher.search("   ") == {"error": "web_search needs a query: what to look up"}


@pytest.mark.asyncio
async def test_web_fetch_class_says_so_when_not_configured(tmp_path: Path) -> None:
    searcher = WebSearch(tmp_path, {})

    result = await searcher.fetch("https://example.org")

    assert "not set up" in str(result["error"])


@pytest.mark.asyncio
async def test_web_fetch_class_refuses_a_blank_url_on_its_own(tmp_path: Path) -> None:
    searcher = WebSearch(tmp_path, HUB)

    assert await searcher.fetch("  ") == {"error": "web_fetch needs a url: the page to read"}


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["none", " none:no-hub ", "none:no-run-folder", "none:"])
async def test_the_class_says_unavailable_for_a_session_with_no_web(
    tmp_path: Path, state: str
) -> None:
    """`none`, or `none:<reason>` since the worker names why (SP-LOOPS Phase 6, Task 6)."""
    searcher = WebSearch(tmp_path, {}, state=state)

    assert "unavailable in this session" in str((await searcher.search("q"))["error"])


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["", "nonesuch", "hub"])
async def test_a_state_that_is_not_none_says_not_set_up(tmp_path: Path, state: str) -> None:
    searcher = WebSearch(tmp_path, {}, state=state)

    assert "not set up" in str((await searcher.search("q"))["error"])


# -- local-first search: the tool follows vibey's policy, through `vibey search` ---------------

_BRAVE_ANSWER = '{"untrusted": true, "backend": "brave", "provider": "brave", "results": []}'
_NOTICE = (
    "local SearXNG unavailable (could not be reached (ConnectionRefusedError)); "
    "this query went to Brave Search"
)


@pytest.mark.asyncio
async def test_the_answer_says_which_backend_answered_and_carries_vibeys_notice(
    tmp_path: Path,
) -> None:
    tool = _mock_web_tool(tmp_path, f"echo '{_BRAVE_ANSWER}'; echo '{_NOTICE}' >&2")

    result = await tool.execute("web_search", {"query": "q"})

    assert result["content"] == _BRAVE_ANSWER + "\n"
    assert result["backend"] == "brave" and result["notice"] == _NOTICE


@pytest.mark.asyncio
async def test_the_notice_is_vibeys_own_notice_only_bounded_and_one_line_each(
    tmp_path: Path,
) -> None:
    """SP-ACP Task 9c, P-9c-1: standard error may carry anything (a warning, a library's
    traceback, terminal escapes); the tool's `notice` is only vibey's own backup notice, each
    line cleaned of non-printable characters, the whole bounded."""
    noise = "Traceback (most recent call last): secret=abc\\033[2J"
    hostile = f"{_NOTICE} \\033]8;;http://x\\a" + "y" * 900
    tool = _mock_web_tool(
        tmp_path,
        f"echo '{_BRAVE_ANSWER}'; printf '%b\\n' '{noise}' '{hostile}' >&2",
    )

    result = await tool.execute("web_search", {"query": "q"})

    notice = str(result["notice"])
    assert notice.startswith(_NOTICE) and "Traceback" not in notice and "secret" not in notice
    assert all(ch.isprintable() for ch in notice)
    assert len(notice) <= 500


@pytest.mark.asyncio
async def test_standard_error_without_vibeys_notice_carries_no_notice(tmp_path: Path) -> None:
    tool = _mock_web_tool(tmp_path, f"echo '{_BRAVE_ANSWER}'; echo 'a warning' >&2")

    result = await tool.execute("web_search", {"query": "q"})

    assert "notice" not in result


@pytest.mark.asyncio
async def test_a_local_answer_says_searxng_and_carries_no_notice(tmp_path: Path) -> None:
    tool = _mock_web_tool(tmp_path, """echo '{"backend": "searxng", "results": []}'""")

    result = await tool.execute("web_search", {"query": "q"})

    assert result["backend"] == "searxng" and "notice" not in result


@pytest.mark.asyncio
@pytest.mark.parametrize("stdout", ["not json", "[1, 2]", '{"backend": 3}'])
async def test_an_answer_that_names_no_backend_is_passed_through_as_it_is(
    tmp_path: Path, stdout: str
) -> None:
    tool = _mock_web_tool(tmp_path, f"echo '{stdout}'")

    result = await tool.execute("web_search", {"query": "q"})

    assert result["content"] == stdout + "\n" and "backend" not in result


@pytest.mark.asyncio
async def test_a_failure_carries_what_vibey_said_on_either_stream(tmp_path: Path) -> None:
    tool = _mock_web_tool(tmp_path, "echo 'error: no SearXNG'; echo 'more' >&2; exit 1")

    result = await tool.execute("web_search", {"query": "q"})

    assert result == {"error": "error: no SearXNG\nmore"}


@pytest.mark.asyncio
async def test_vibey_search_is_given_the_hub_and_never_a_key_or_another_vibey_name(
    tmp_path: Path,
) -> None:
    keys = {
        "VIBEY_BRAVE_API_KEY": "fake-1",
        "WEBSEARCH_BRAVE_API_KEY": "fake-2",
        "BRAVE_SEARCH_API_KEY": "fake-3",
        "VIBEY_PG_URL": "postgresql://fake-4",
        "VIBEY_AGENT_TOKEN": "fake-5",
        "VIBEY_SEARXNG_URL": "http://fake-6",
        "WEBSEARCH_SEARXNG_URL": "http://fake-7",
    }
    tool = _mock_web_tool(tmp_path, "env", **keys)

    result = await tool.execute("web_search", {"query": "q"})

    content = str(result["content"])
    assert "VIBEY_HUB_URL=http://127.0.0.1:28100" in content
    assert "VIBEY_WEB_TOKEN_FILE=/runs/r/web-token" in content
    assert not any(name in content or value in content for name, value in keys.items())
