# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one argv that starts a local MCP server through the scrubbed launcher (SP-LOOPS Phase 5,
Task 3; R14).

One test starts a real server behind the real launcher, `fake_stdio_server.py echo-env`, which
answers the names in its environment and never a value. Module-level test functions rather than
a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from vibey_runners.common.capabilities.interfaces.scrubbed_launch_interface import (
    ScrubbedLaunchInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.scrubbed_exec import LAUNCHER_ARGS, LAUNCHER_MODULE
from vibey_runners.common.capabilities.scrubbed_launch import ScrubbedLaunch
from vibey_runners.common.mcp.mcp_session import McpSession
from vibey_runners.common.mcp.stdio_transport import StdioTransport

SERVER = Path(__file__).parents[1] / "mcp" / "fake_stdio_server.py"
SENTINEL = "s3ntinel-0b5e55ed"


def _local(
    *env_allow: str, command: tuple[str, ...] | None = ("srv", "--root", ".")
) -> McpServerSpec:
    return McpServerSpec(
        name="files", trust="local", command=command, url=None, env_allow=env_allow
    )


def test_the_argv_is_the_launcher_then_one_allow_per_name_then_the_command() -> None:
    launch = ScrubbedLaunch(["/usr/bin/python3", "-I", "-m", LAUNCHER_MODULE])
    assert isinstance(launch, ScrubbedLaunchInterface)
    assert launch.argv(_local("A", "B")) == (
        "/usr/bin/python3",
        "-I",
        "-m",
        LAUNCHER_MODULE,
        "--allow",
        "A",
        "--allow",
        "B",
        "--",
        "srv",
        "--root",
        ".",
    )
    assert ScrubbedLaunch(("/opt/scrubbed",)).argv(_local()) == (
        "/opt/scrubbed",
        "--",
        "srv",
        "--root",
        ".",
    )


async def test_a_local_server_starts_only_through_the_scrubbed_launcher(tmp_path: Path) -> None:
    server = _local("SENTINEL_ROOT", command=(sys.executable, str(SERVER), "echo-env"))
    argv = ScrubbedLaunch((sys.executable, *LAUNCHER_ARGS)).argv(server)
    environ = {
        **os.environ,
        "SENTINEL_ROOT": SENTINEL,
        "ANTHROPIC_API_KEY": "fake-key-never-real",
        "VIBEY_PLAIN_NEIGHBOUR": "not-allowed",
    }
    transport = StdioTransport(server.name, argv, environ, tmp_path)
    session = McpSession(transport, client_name="test", client_version="0", timeout_seconds=30.0)
    await session.start()
    try:
        result = await session.call("env", {})
    finally:
        await session.close(5.0)
    names = result.text.splitlines()
    assert "SENTINEL_ROOT" in names
    assert "ANTHROPIC_API_KEY" not in names
    assert "VIBEY_PLAIN_NEIGHBOUR" not in names
    assert "PATH" not in names
    assert SENTINEL not in result.text
    assert all(SENTINEL not in element for element in argv)
    assert SENTINEL not in transport.describe()


@pytest.mark.parametrize(
    "server",
    [
        McpServerSpec(
            name="files", trust="remote", command=None, url="https://x.invalid/mcp", env_allow=()
        ),
        McpServerSpec(
            name="files", trust="remote", command=("srv",), url="https://x.invalid", env_allow=()
        ),
        McpServerSpec(name="files", trust="local", command=None, url=None, env_allow=()),
        McpServerSpec(name="files", trust="local", command=(), url=None, env_allow=()),
    ],
)
def test_scrubbed_launch_refuses_a_remote_server(server: McpServerSpec) -> None:
    with pytest.raises(ValueError, match="'files' is not a local server with a command"):
        ScrubbedLaunch(("/opt/scrubbed",)).argv(server)


def test_an_empty_launcher_is_refused() -> None:
    with pytest.raises(ValueError, match="launcher"):
        ScrubbedLaunch(())
