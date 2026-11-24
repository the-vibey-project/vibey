# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stdio transport: a server leads its own process group, and closing reaps the whole group
(SP-LOOPS Phase 5, Task 3; R5, R6).

Each test starts `fake_stdio_server.py` with `sys.executable`. Nothing waits on a clock but the
0.2s timeout given to a server that never answers anything, and a 30-second safety bound on
reading a pipe whose end is the proof a process group is gone. Module-level test functions
rather than a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import Any

import pytest

from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpToolError, McpUnavailable
from vibey_runners.common.mcp.mcp_session import McpSession
from vibey_runners.common.mcp.mcp_tool import McpTool
from vibey_runners.common.mcp.stdio_transport import StdioTransport

SERVER = Path(__file__).with_name("fake_stdio_server.py")


def _transport(mode: str, *extra: str, **options: Any) -> StdioTransport:
    return StdioTransport(
        "fake",
        (sys.executable, str(SERVER), mode, *extra),
        {"PATH": os.environ.get("PATH", "")},
        SERVER.parent,
        **options,
    )


def _session(transport: StdioTransport, timeout: float = 30.0) -> McpSession:
    return McpSession(transport, client_name="test", client_version="0", timeout_seconds=timeout)


async def test_a_stdio_session_round_trips_tools_list_and_call() -> None:
    transport = _transport("ok")
    assert isinstance(transport, McpTransportInterface)
    session = _session(transport)
    await session.start()
    assert await session.list_tools() == (McpTool("echo", "Echo.", {"type": "object"}),)
    assert await session.call("echo", {"q": "hi"}) == McpCallResult('{"q": "hi"}', False)
    await session.close(5.0)
    assert not session.alive
    assert transport.describe() == "MCP server 'fake' (stdio, exited with code 0)"


async def test_a_paged_listing_and_an_older_protocol_work_over_stdio() -> None:
    session = _session(_transport("paged"))
    await session.start()
    assert [tool.name for tool in await session.list_tools()] == ["a", "b"]
    await session.close(5.0)
    old = _session(_transport("old-protocol"))
    await old.start()
    assert old.alive
    await old.close(5.0)


async def test_an_unknown_protocol_over_stdio_is_unavailable_and_the_server_is_reaped() -> None:
    transport = _transport("unknown-protocol")
    session = _session(transport)
    with pytest.raises(McpUnavailable, match="answered protocol version '1999-01-01'"):
        await session.start()
    # Killed without grace, or exited at the end of its input first: either way, reaped.
    assert transport.describe().startswith("MCP server 'fake' (stdio, ")


async def test_a_jsonrpc_error_over_stdio_is_a_tool_error_and_the_server_stays_up() -> None:
    session = _session(_transport("error"))
    await session.start()
    with pytest.raises(McpToolError, match="error -32000: exploded"):
        await session.call("echo", {})
    assert session.alive
    assert [tool.name for tool in await session.list_tools()] == ["echo"]
    await session.close(5.0)


async def test_a_server_that_exits_at_start_is_unavailable_with_its_exit_code() -> None:
    transport = _transport("exit")
    session = _session(transport)
    with pytest.raises(McpUnavailable) as caught:
        await session.start()
    assert str(caught.value) == (
        "MCP server 'fake' (stdio, exited with code 3) closed its stream during initialize"
    )
    assert not session.alive


async def test_a_stdio_server_that_never_answers_times_out_and_is_killed() -> None:
    transport = _transport("hang")
    session = _session(transport, timeout=0.2)
    with pytest.raises(McpUnavailable) as caught:
        await session.start()
    assert str(caught.value) == (
        "MCP server 'fake' (stdio, ended by signal 9) did not answer initialize within 0.2s"
    )
    assert not session.alive


async def test_close_reaps_the_whole_process_group() -> None:
    """The server ignores the end of its input and its child never reads it, so only the group
    kill ends them. Both hold the write end of a pipe the test made; the read end reaching EOF
    is the proof both have exited. The leader's pid is checked as well: the transport reaps it.
    The child's pid is not probed with `kill(pid, 0)`: until init reaps the orphan, a zombie
    still answers it, and that would make the test depend on the platform's timing."""
    read_end, write_end = os.pipe()
    spawned: list[asyncio.subprocess.Process] = []

    async def spawn(*argv: str, **options: Any) -> asyncio.subprocess.Process:
        process = await asyncio.create_subprocess_exec(*argv, pass_fds=(write_end,), **options)
        spawned.append(process)
        return process

    transport = _transport("spawns-child", str(write_end), spawn=spawn)
    session = _session(transport)
    try:
        await session.start()
    finally:
        os.close(write_end)
    child_pid = int((await session.call("pid", {})).text)
    [leader] = spawned
    assert os.getpgid(child_pid) == leader.pid
    await session.close(0.0)
    loop = asyncio.get_running_loop()
    try:
        eof = await asyncio.wait_for(loop.run_in_executor(None, os.read, read_end, 1), 30.0)
    finally:
        os.close(read_end)
    assert eof == b""
    assert leader.returncode == -signal.SIGKILL
    with pytest.raises(ProcessLookupError):
        os.kill(leader.pid, 0)


async def test_describe_holds_no_argv_tail_or_env_value() -> None:
    transport = StdioTransport(
        "files",
        (sys.executable, str(SERVER), "ok", "--token-file", "/secret/path"),
        {"PATH": os.environ.get("PATH", ""), "FILES_ROOT": "s3ntinel-value"},
        SERVER.parent,
    )
    assert transport.describe() == "MCP server 'files' (stdio)"
    session = _session(transport)
    await session.start()
    assert transport.describe() == "MCP server 'files' (stdio)"
    await session.close(5.0)
    described = transport.describe()
    for leaked in ("--token-file", "/secret/path", "s3ntinel-value", "FILES_ROOT", str(SERVER)):
        assert leaked not in described


async def test_the_server_starts_in_a_new_session_with_stderr_discarded_and_the_reader_limit(
    tmp_path: Path,
) -> None:
    seen: dict[str, Any] = {}

    async def spawn(*argv: str, **options: Any) -> asyncio.subprocess.Process:
        seen["argv"], seen["options"] = argv, options
        return await asyncio.create_subprocess_exec(*argv, **options)

    transport = StdioTransport(
        "fake",
        [sys.executable, str(SERVER), "ok"],
        {"PATH": os.environ.get("PATH", "")},
        tmp_path,
        limit_bytes=4096,
        spawn=spawn,
    )
    await transport.open()
    assert seen["argv"] == (sys.executable, str(SERVER), "ok")
    options = seen["options"]
    assert options["start_new_session"] is True
    assert options["stdin"] == asyncio.subprocess.PIPE
    assert options["stdout"] == asyncio.subprocess.PIPE
    assert options["stderr"] == asyncio.subprocess.DEVNULL
    assert options["cwd"] == tmp_path
    assert options["limit"] == 4096
    assert options["env"] == {"PATH": os.environ.get("PATH", "")}
    await transport.close(5.0)


async def test_close_treats_a_group_that_is_already_gone_as_closed() -> None:
    calls: list[tuple[int, int]] = []

    def gone(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        raise ProcessLookupError

    def forbidden(pid: int, sig: int) -> None:
        calls.append((pid, sig))
        raise PermissionError

    for killpg in (gone, forbidden):
        transport = _transport("ok", killpg=killpg)
        await transport.open()
        await transport.close(5.0)
        assert transport.describe() == "MCP server 'fake' (stdio, exited with code 0)"
    assert [sig for _, sig in calls] == [signal.SIGKILL, signal.SIGKILL]


async def test_close_before_open_and_close_twice_do_nothing() -> None:
    calls: list[int] = []
    transport = _transport("ok", killpg=lambda pid, sig: calls.append(pid))
    await transport.close(1.0)
    assert calls == []
    await transport.open()
    await transport.close(5.0)
    await transport.close(5.0)
    assert len(calls) == 1


def test_an_empty_argv_is_refused() -> None:
    with pytest.raises(ValueError, match="argv"):
        StdioTransport("fake", (), {}, SERVER.parent)
