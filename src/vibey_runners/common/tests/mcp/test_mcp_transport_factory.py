# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The transport factory: a `local` server over stdio through the scrubbed launcher, a `remote`
one over HTTP (SP-LOOPS Phase 5, Task 4; R13, R14).

Nothing is started: the stdio transport is opened through an injected recording spawn. Module-
level test functions rather than a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.scrubbed_launch import ScrubbedLaunch
from vibey_runners.common.mcp.http_transport import HttpTransport
from vibey_runners.common.mcp.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from vibey_runners.common.mcp.mcp_transport_factory import McpTransportFactory
from vibey_runners.common.mcp.stdio_transport import StdioTransport

LAUNCHER = ("/usr/bin/python3", "-I", "-m", "vibey_runners.common.capabilities.scrubbed_exec")
ENV_SECRET = "env-sentinel-91c2"


def _factory(tmp_path: Path) -> McpTransportFactory:
    return McpTransportFactory(
        ScrubbedLaunch(LAUNCHER),
        cwd=tmp_path,
        environ={"PATH": "/bin", "API_TOKEN": ENV_SECRET},
        timeout_seconds=7.0,
    )


async def test_the_factory_gives_local_stdio_through_the_launcher_and_remote_http(
    tmp_path: Path,
) -> None:
    factory = _factory(tmp_path)
    assert isinstance(factory, McpTransportFactoryInterface)
    local_spec = McpServerSpec("fs", "local", ("fs-server", "--root", "."), None, ("PATH",))
    local = factory.for_spec(local_spec)
    assert isinstance(local, StdioTransport)
    assert local.describe() == "MCP server 'fs' (stdio)"

    spawned: list[tuple[tuple[str, ...], dict[str, Any]]] = []

    class Spawned(Exception):
        pass

    async def spawn(*argv: str, **options: Any) -> asyncio.subprocess.Process:
        spawned.append((argv, options))
        raise Spawned

    # The factory's transport, opened through a recording spawn: the argv is the launcher's,
    # and the environment reaches only the launcher, which scrubs it.
    local._spawn = spawn
    with pytest.raises(Spawned):
        await local.open()
    ((argv, options),) = spawned
    assert argv == (*LAUNCHER, "--allow", "PATH", "--", "fs-server", "--root", ".")
    assert ENV_SECRET not in " ".join(argv)
    assert options["env"] == {"PATH": "/bin", "API_TOKEN": ENV_SECRET}
    assert options["cwd"] == tmp_path

    remote_spec = McpServerSpec("api", "remote", None, "https://api.example.test/mcp?k=v", ())
    remote = factory.for_spec(remote_spec)
    assert isinstance(remote, HttpTransport)
    assert remote.describe() == "MCP server 'api' (https api.example.test)"
    assert remote._timeout == 7.0


def test_a_remote_server_without_a_url_or_a_local_one_without_a_command_is_refused(
    tmp_path: Path,
) -> None:
    factory = _factory(tmp_path)
    with pytest.raises(ValueError, match="MCP server 'api' is remote but has no URL"):
        factory.for_spec(McpServerSpec("api", "remote", None, None, ()))
    with pytest.raises(ValueError, match="not a local server with a command"):
        factory.for_spec(McpServerSpec("fs", "local", None, None, ()))
