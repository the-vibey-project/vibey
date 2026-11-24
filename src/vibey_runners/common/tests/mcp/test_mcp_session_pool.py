# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The per-run MCP session pool: lazy start, bounded restarts, the remote call budget and a
close that never raises (SP-LOOPS Phase 5, Task 3; R5, R6, R13).

Sessions are `mcp_fakes.FakeSession` doubles, so no server runs. Module-level test functions
rather than a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest
from mcp_fakes import FakeSession

from vibey_runners.common.capabilities.mcp_server_spec import McpTrust
from vibey_runners.common.mcp.interfaces.mcp_session_pool_interface import (
    McpSessionPoolInterface,
)
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpToolError, McpUnavailable
from vibey_runners.common.mcp.mcp_session_pool import McpSessionPool
from vibey_runners.common.mcp.mcp_tool import McpTool


class _Factory:
    """Hands out the scripted sessions in order and records how many were made."""

    def __init__(self, *sessions: FakeSession) -> None:
        self.sessions = list(sessions)
        self.made: list[FakeSession] = []

    def __call__(self) -> FakeSession:
        session = self.sessions.pop(0) if self.sessions else FakeSession()
        self.made.append(session)
        return session


def _pool(
    factories: dict[str, Callable[[], Any]],
    trust: dict[str, McpTrust] | None = None,
    **options: Any,
) -> McpSessionPool:
    settings: dict[str, Any] = {
        "restarts": 1,
        "remote_calls": 64,
        "close_grace_seconds": 2.0,
        **options,
    }
    return McpSessionPool(
        factories,
        trust=trust if trust is not None else dict.fromkeys(factories, "local"),
        **settings,
    )


async def test_a_session_starts_on_first_use_and_is_reused() -> None:
    files = _Factory()
    pool = _pool({"files": files, "docs": _Factory()})
    assert isinstance(pool, McpSessionPoolInterface)
    assert pool.names == ("files", "docs")
    assert files.made == []
    assert await pool.tools("files") == (McpTool("echo", "Echo.", {"type": "object"}),)
    assert await pool.call("files", "echo", {"a": 1}) == McpCallResult("echo done", False)
    assert await pool.call("files", "echo", {"a": 2}) == McpCallResult("echo done", False)
    [session] = files.made
    assert session.started == 1
    assert session.calls == [("echo", {"a": 1}), ("echo", {"a": 2})]
    await pool.aclose()
    assert session.closed == [2.0]


async def test_a_dead_session_restarts_once_then_the_server_is_unavailable_for_the_run() -> None:
    first = FakeSession(call_errors=[McpUnavailable("first death")])
    second = FakeSession(call_errors=[McpUnavailable("second death")])
    files = _Factory(first, second)
    pool = _pool({"files": files}, restarts=1)
    with pytest.raises(McpUnavailable, match="^first death$"):
        await pool.call("files", "echo", {})
    assert first.closed == [2.0]
    with pytest.raises(McpUnavailable, match="^second death$"):
        await pool.tools("files")
    assert len(files.made) == 2
    for _ in range(2):
        with pytest.raises(McpUnavailable) as caught:
            await pool.call("files", "echo", {})
        assert str(caught.value) == (
            "MCP server 'files' is unavailable for the rest of this run: first death"
        )
    assert len(files.made) == 2


async def test_a_server_that_will_not_start_counts_as_a_death() -> None:
    files = _Factory(FakeSession(start_error="no binary"), FakeSession(start_error="still none"))
    pool = _pool({"files": files}, restarts=1)
    with pytest.raises(McpUnavailable, match="^no binary$"):
        await pool.tools("files")
    with pytest.raises(McpUnavailable, match="^still none$"):
        await pool.tools("files")
    with pytest.raises(McpUnavailable, match="for the rest of this run: no binary$"):
        await pool.tools("files")
    assert len(files.made) == 2
    assert [s.closed for s in files.made] == [[2.0], [2.0]]


async def test_with_no_restarts_the_first_death_is_final() -> None:
    files = _Factory(FakeSession(call_errors=[McpUnavailable("gone")]))
    pool = _pool({"files": files}, restarts=0)
    with pytest.raises(McpUnavailable, match="^gone$"):
        await pool.call("files", "echo", {})
    with pytest.raises(McpUnavailable, match="rest of this run: gone$"):
        await pool.call("files", "echo", {})
    assert len(files.made) == 1


async def test_a_tool_error_leaves_the_session_alive_and_uncounted() -> None:
    session = FakeSession(call_errors=[McpToolError("bad arguments"), McpToolError("again")])
    files = _Factory(session)
    pool = _pool({"files": files}, restarts=0)
    with pytest.raises(McpToolError, match="bad arguments"):
        await pool.call("files", "echo", {})
    with pytest.raises(McpToolError, match="again"):
        await pool.tools("files")
    assert await pool.call("files", "echo", {}) == McpCallResult("echo done", False)
    assert files.made == [session]
    assert session.closed == []


async def test_the_remote_call_budget_is_per_server_and_local_servers_have_none() -> None:
    docs, wiki, files = _Factory(), _Factory(), _Factory()
    pool = _pool(
        {"docs": docs, "wiki": wiki, "files": files},
        {"docs": "remote", "wiki": "remote", "files": "local"},
        remote_calls=2,
    )
    assert pool.trust_of("docs") == "remote"
    assert pool.trust_of("files") == "local"
    assert pool.remote_calls_left("docs") == 2
    assert pool.remote_calls_left("files") is None
    await pool.tools("docs")
    assert pool.remote_calls_left("docs") == 2
    await pool.call("docs", "echo", {})
    await pool.call("docs", "echo", {})
    assert pool.remote_calls_left("docs") == 0
    assert pool.remote_calls_left("wiki") == 2
    with pytest.raises(McpUnavailable) as caught:
        await pool.call("docs", "echo", {})
    assert str(caught.value) == (
        "MCP server 'docs' has used all 2 tools/call requests this run allows"
    )
    assert len(docs.made[0].calls) == 2
    for _ in range(3):
        await pool.call("files", "echo", {})
    assert pool.remote_calls_left("files") is None
    await pool.call("wiki", "echo", {})
    assert pool.remote_calls_left("wiki") == 1


async def test_a_failed_remote_call_still_spends_its_budget() -> None:
    docs = _Factory(FakeSession(call_errors=[McpToolError("refused")]))
    pool = _pool({"docs": docs}, {"docs": "remote"}, remote_calls=1)
    with pytest.raises(McpToolError):
        await pool.call("docs", "echo", {})
    assert pool.remote_calls_left("docs") == 0


class _YieldingStart(FakeSession):
    """A session whose start yields to the loop, so a concurrent call can run in between."""

    async def start(self) -> None:
        await asyncio.sleep(0)
        await super().start()


async def test_concurrent_calls_cannot_both_spend_the_last_remote_call() -> None:
    docs = _Factory(_YieldingStart())
    pool = _pool({"docs": docs}, {"docs": "remote"}, remote_calls=1)
    results = await asyncio.gather(
        pool.call("docs", "echo", {}),
        pool.call("docs", "echo", {}),
        return_exceptions=True,
    )
    refused = [r for r in results if isinstance(r, McpUnavailable)]
    served = [r for r in results if isinstance(r, McpCallResult)]
    assert len(served) == 1
    assert len(refused) == 1
    assert pool.remote_calls_left("docs") == 0
    assert len(docs.made[0].calls) == 1


async def test_a_server_that_never_starts_gives_its_reserved_call_back() -> None:
    docs = _Factory(FakeSession(start_error="no binary"))
    pool = _pool({"docs": docs}, {"docs": "remote"}, remote_calls=1, restarts=0)
    with pytest.raises(McpUnavailable, match="^no binary$"):
        await pool.call("docs", "echo", {})
    assert pool.remote_calls_left("docs") == 1


async def test_aclose_closes_every_live_session_and_never_raises() -> None:
    broken = FakeSession(close_error=RuntimeError("close failed"))
    files, docs, idle = _Factory(broken), _Factory(), _Factory()
    pool = _pool({"files": files, "docs": docs, "idle": idle}, close_grace_seconds=0.5)
    await pool.tools("files")
    await pool.tools("docs")
    await pool.aclose()
    assert broken.closed == [0.5]
    assert docs.made[0].closed == [0.5]
    assert idle.made == []
    await pool.aclose()
    assert broken.closed == [0.5]
    with pytest.raises(McpUnavailable) as caught:
        await pool.tools("idle")
    assert str(caught.value) == "the MCP session pool is closed; MCP server 'idle' is not started"
    assert idle.made == []


async def test_an_unknown_server_names_the_configured_ones() -> None:
    pool = _pool({"a": _Factory(), "b": _Factory()})
    expected = "unknown MCP server 'x'; configured: a, b"
    with pytest.raises(McpUnavailable, match=f"^{expected}$"):
        await pool.call("x", "echo", {})
    with pytest.raises(McpUnavailable, match=f"^{expected}$"):
        await pool.tools("x")
    with pytest.raises(McpUnavailable, match=f"^{expected}$"):
        pool.trust_of("x")
    with pytest.raises(McpUnavailable, match=f"^{expected}$"):
        pool.remote_calls_left("x")
    with pytest.raises(McpUnavailable, match="^unknown MCP server 'x'; configured: none$"):
        await _pool({}).tools("x")


def test_every_server_needs_a_trust_level_and_no_more() -> None:
    with pytest.raises(ValueError, match="trust"):
        McpSessionPool(
            {"a": _Factory()}, trust={}, restarts=1, remote_calls=1, close_grace_seconds=1.0
        )
    with pytest.raises(ValueError, match="trust"):
        McpSessionPool(
            {}, trust={"a": "local"}, restarts=1, remote_calls=1, close_grace_seconds=1.0
        )
