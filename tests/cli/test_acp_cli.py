# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp`: stdout is protocol-only, and the command is wired the way the plan says (SP-ACP).

The stdout guard is proven in a real subprocess, against a real `print`, `typer.echo` and a
child that inherits fd 1, through the `before_serve` seam rather than a test-only switch.
Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import textwrap
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from vibey import __version__
from vibey.application.acp.acp_agent import AcpAgent
from vibey.application.acp.interfaces.acp_agent_interface import AcpAgentInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.bootstrap import build_acp_agent
from vibey.cli.acp import ACP_COMMAND, AcpCommand, acp
from vibey.cli.interfaces.acp_interface import AcpCommandInterface
from vibey.cli.main import app
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.acp.peer_client_channel import PeerClientChannel
from vibey.infrastructure.mcp.hub_gateway import HubGatewayResponse

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": 1, "clientCapabilities": {}},
}

NOISY = textwrap.dedent(
    """
    import subprocess
    import typer
    from vibey.cli.acp import AcpCommand

    def noisy():
        print("print-noise")
        typer.echo("echo-noise")
        subprocess.run(["echo", "child-noise"], check=True)

    AcpCommand(before_serve=noisy).run(no_bootstrap=True)
    """
)


def test_acp_stdout_carries_only_protocol_lines_when_code_and_children_print(
    tmp_path: Path,
) -> None:
    done = subprocess.run(
        [sys.executable, "-c", NOISY],
        cwd=tmp_path,
        input=(json.dumps(INITIALIZE) + "\n").encode(),
        capture_output=True,
        check=False,
        timeout=120,
    )

    assert done.returncode == 0, done.stderr.decode()
    lines = done.stdout.decode().splitlines()
    assert lines, done.stderr.decode()
    for line in lines:
        assert json.loads(line)["jsonrpc"] == "2.0"
    response = json.loads(lines[0])
    assert response["id"] == 1 and response["result"]["protocolVersion"] == 1
    stderr = done.stderr.decode()
    for noise in ("print-noise", "echo-noise", "child-noise"):
        assert noise in stderr
    assert "noise" not in done.stdout.decode()


def test_acp_command_is_registered_next_to_mcp() -> None:
    names = [command.name for command in app.registered_commands]
    assert names.index("acp") == names.index("mcp") + 1
    registered = next(c for c in app.registered_commands if c.name == "acp")
    assert registered.callback is acp


def test_the_command_satisfies_its_interface() -> None:
    assert isinstance(ACP_COMMAND, AcpCommandInterface)


# -- in process, through the seams ---------------------------------------------------------


class _Transport:
    """A transport whose reader is fed the given lines and whose writes are recorded."""

    def __init__(self, events: list[str], *lines: Mapping[str, Any]) -> None:
        self.events = events
        self.payload = b"".join((json.dumps(line) + "\n").encode() for line in lines)
        self.written: list[str] = []
        self.limit: int | None = None

    def guard(self) -> int:
        self.events.append("guard")
        return 99

    async def reader(self, limit: int) -> asyncio.StreamReader:
        self.limit = limit
        reader = asyncio.StreamReader(limit=limit)
        reader.feed_data(self.payload)
        reader.feed_eof()
        return reader

    async def write_line(self, line: str) -> None:
        self.written.append(line)


class _Loader:
    def __init__(self, events: list[str], settings: AcpSettings) -> None:
        self.events = events
        self.settings = settings
        self.paths: list[Path] = []

    def load(self, path: Path) -> AcpSettings:
        self.events.append("settings")
        self.paths.append(path)
        return self.settings

    def from_mapping(self, section: Mapping[str, object]) -> AcpSettings:
        return self.settings


def _command(
    events: list[str],
    transport: _Transport,
    settings: AcpSettings,
    built: list[tuple[AcpSettings, ClientChannelInterface]],
) -> tuple[AcpCommand, _Loader]:
    loader = _Loader(events, settings)

    def builder(*, settings: AcpSettings, channel: ClientChannelInterface) -> AcpAgentInterface:
        events.append("agent")
        built.append((settings, channel))
        return build_acp_agent(settings=settings, channel=channel, gateway=_Gateway())

    command = AcpCommand(
        transport=lambda: transport,
        settings=loader,
        config_path=lambda: Path("/work/vibey.toml"),
        build_agent=builder,
        before_serve=lambda: events.append("before_serve"),
    )
    return command, loader


class _Gateway:
    def agent_scopes(self) -> frozenset[HubScope]:
        return frozenset({HubScope.VIEW})

    def call(self, call: HubCall) -> HubGatewayResponse:
        return HubGatewayResponse(status_code=200, text="{}", ok=True)


def test_run_guards_first_then_serves_initialize_over_the_transport() -> None:
    events: list[str] = []
    transport = _Transport(events, INITIALIZE)
    built: list[tuple[AcpSettings, ClientChannelInterface]] = []
    command, loader = _command(events, transport, AcpSettings(max_message_bytes=70_000), built)

    command.run(no_bootstrap=False)

    assert events == ["guard", "before_serve", "settings", "agent"]
    assert loader.paths == [Path("/work/vibey.toml")]
    assert transport.limit == 70_001
    assert built[0][0].auto_bootstrap is True
    assert isinstance(built[0][1], PeerClientChannel)
    assert len(transport.written) == 1
    response = json.loads(transport.written[0])
    assert response["id"] == 1
    assert response["result"]["agentInfo"]["version"] == __version__


def test_no_bootstrap_turns_the_grant_off_for_this_process() -> None:
    events: list[str] = []
    built: list[tuple[AcpSettings, ClientChannelInterface]] = []
    command, _ = _command(events, _Transport(events), AcpSettings(), built)

    command.run(no_bootstrap=True)

    assert built[0][0].auto_bootstrap is False
    assert built[0][0] == AcpSettings(auto_bootstrap=False)


def test_the_typer_function_runs_the_module_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    class _Recorder:
        def run(self, *, no_bootstrap: bool) -> None:
            calls.append(no_bootstrap)

    monkeypatch.setattr("vibey.cli.acp.ACP_COMMAND", _Recorder())

    acp(no_bootstrap=True)
    acp()

    assert calls == [True, False]


class _RecordingChannel:
    def __init__(self) -> None:
        self.client_capabilities: Mapping[str, Any] = {}
        self.updates: list[Mapping[str, Any]] = []

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        self.updates.append(update)

    async def request_permission(
        self, session_id: str, tool_call: Any, options: Any, *, timeout: float
    ) -> str | None:
        return None


async def test_build_acp_agent_wires_a_working_agent() -> None:
    channel = _RecordingChannel()

    agent = build_acp_agent(settings=AcpSettings(), channel=channel, gateway=_Gateway())
    session = await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    session_id = str(session["sessionId"])
    help_turn = await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [{"type": "text", "text": "/help"}]}
    )

    assert isinstance(agent, AcpAgent)
    assert session["modes"]["currentModeId"] == "drive"
    assert len(session_id) == 36
    assert list(agent.sessions) == [session_id]
    assert help_turn == {"stopReason": "end_turn"}
    assert "/projects" in channel.updates[-1]["content"]["text"]
