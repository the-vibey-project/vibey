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
from vibey.application.acp.dto import DoctorResult
from vibey.application.acp.interfaces.acp_agent_interface import AcpAgentInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.bootstrap import acp_machine, build_acp_agent
from vibey.cli.acp import ACP_COMMAND, AcpCommand, acp
from vibey.cli.doctor_probes import LOCAL_DOCTOR_PROBES
from vibey.cli.interfaces.acp_interface import AcpCommandInterface
from vibey.cli.main import app
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.acp.acp_postgres_installer import AcpPostgresInstaller
from vibey.infrastructure.acp.host_connector import HostConnector
from vibey.infrastructure.acp.peer_client_channel import PeerClientChannel
from vibey.infrastructure.hub.serve_lock import ServeLock
from vibey.infrastructure.hub.settings import HubSettings
from vibey.infrastructure.mcp.hub_gateway import HubGateway, HubGatewayResponse
from vibey.infrastructure.mcp.hub_start_policy import BoundedHubStarter

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


def test_acp_with_stdin_from_dev_null_exits_at_eof(tmp_path: Path) -> None:
    # `vibey acp --no-bootstrap </dev/null` must end, not hang (review A-2).
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            "from vibey.cli.acp import AcpCommand; AcpCommand().run(no_bootstrap=True)",
        ],
        cwd=tmp_path,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert done.returncode == 0, done.stderr.decode()
    assert done.stdout == b""


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
    parts: list[dict[str, Any]] | None = None,
) -> tuple[AcpCommand, _Loader]:
    loader = _Loader(events, settings)

    def builder(
        *, settings: AcpSettings, channel: ClientChannelInterface, **given: Any
    ) -> AcpAgentInterface:
        events.append("agent")
        built.append((settings, channel))
        if parts is not None:
            parts.append(given)
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
        return frozenset({HubScope.VIEW, HubScope.ACP_SESSIONS})

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


def test_the_agent_gets_doctors_sections_and_this_computers_bootstrap_parts() -> None:
    events: list[str] = []
    parts: list[dict[str, Any]] = []
    command, _ = _command(events, _Transport(events), AcpSettings(), [], parts)

    command.run(no_bootstrap=True)

    given = parts[0]
    assert tuple(given["doctor_probes"]) == LOCAL_DOCTOR_PROBES
    assert isinstance(given["connector"], HostConnector)
    assert isinstance(given["postgres"], AcpPostgresInstaller)
    assert isinstance(given["lock"], ServeLock)


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

    def cancel_permissions(self, session_id: str) -> tuple[str, ...]:
        return ()


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


async def test_build_acp_agent_puts_an_open_gate_to_the_client_and_answers_through_the_hub() -> (
    None
):
    gate_id = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b"
    gate = {
        "gate_id": gate_id,
        "project_id": "7d6c2a8e-0c41-4c1e-9d0e-2f4b8f0a1b2c",
        "kind": "choice",
        "prompt": "Ship it?",
        "options": ["ship", "nope"],
        "default_answer": None,
        "is_spend": False,
        "requires_scope": "answer",
        "grant_key": None,
    }
    turn = {"reply": "1 open gate(s)", "tool_calls": [], "gates": [gate], "project_id": None}
    calls: list[HubCall] = []

    class _Hub(_Gateway):
        def agent_scopes(self) -> frozenset[HubScope]:
            return frozenset({HubScope.VIEW, HubScope.ANSWER})

        def call(self, call: HubCall) -> HubGatewayResponse:
            calls.append(call)
            text = json.dumps(turn) if call.tool == "vibey_chat" else '{"answered": true}'
            return HubGatewayResponse(status_code=200, text=text, ok=True)

    class _Picks(_RecordingChannel):
        def __init__(self) -> None:
            super().__init__()
            self.offered: list[Any] = []

        async def request_permission(
            self, session_id: str, tool_call: Any, options: Any, *, timeout: float
        ) -> str | None:
            self.offered.append(list(options))
            return str(options[1]["optionId"])

    channel = _Picks()
    agent = build_acp_agent(
        settings=AcpSettings(reject_words=("nope",)), channel=channel, gateway=_Hub()
    )
    session = await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.handle_request(
        "session/prompt",
        {"sessionId": session["sessionId"], "prompt": [{"type": "text", "text": "/gates"}]},
    )

    assert [o["kind"] for o in channel.offered[0]] == ["allow_once", "reject_once", "reject_once"]
    # The session's log goes to the hub behind the turn: the answer is the one gate call.
    (answer,) = [call for call in calls if call.tool == "vibey_answer_gate"]
    assert (answer.tool, answer.route) == ("vibey_answer_gate", f"/api/v1/gates/{gate_id}/answer")
    assert answer.body is not None and answer.body["answer"] == {"choice": "nope"}


def test_the_agent_is_closed_once_the_connection_ends() -> None:
    # The live feeds poll in tasks of their own; none may outlive the connection (EOF).
    events: list[str] = []
    transport = _Transport(events, INITIALIZE)
    closed: list[bool] = []

    class _Closing:
        def __init__(self, inner: AcpAgentInterface) -> None:
            self._inner = inner
            self.sessions = inner.sessions

        async def handle_request(self, method: str, params: Mapping[str, Any]) -> Any:
            return await self._inner.handle_request(method, params)

        async def handle_notification(self, method: str, params: Mapping[str, Any]) -> None:
            await self._inner.handle_notification(method, params)

        async def close(self) -> None:
            closed.append(True)
            await self._inner.close()

    def builder(
        *, settings: AcpSettings, channel: ClientChannelInterface, **parts: Any
    ) -> AcpAgentInterface:
        return _Closing(build_acp_agent(settings=settings, channel=channel, gateway=_Gateway()))

    AcpCommand(
        transport=lambda: transport,
        settings=_Loader(events, AcpSettings()),
        config_path=lambda: Path("/work/vibey.toml"),
        build_agent=builder,
    ).run(no_bootstrap=True)

    assert closed == [True]
    assert len(transport.written) == 1


async def test_build_acp_agent_follows_the_project_in_the_sessions_folder() -> None:
    project_id = "7d6c2a8e-0c41-4c1e-9d0e-2f4b8f0a1b2c"
    listing = [{"project_id": project_id, "name": "demo", "repo_path": "/work"}]
    ledger = {
        "project_id": project_id,
        "events": [{"seq": 1, "phase": "build", "kind": "TurnCompleted", "payload": {}}],
        "last_seq": 1,
    }
    calls: list[HubCall] = []

    class _Hub(_Gateway):
        def call(self, call: HubCall) -> HubGatewayResponse:
            calls.append(call)
            if call.tool == "vibey_projects":
                return HubGatewayResponse(status_code=200, text=json.dumps(listing), ok=True)
            return HubGatewayResponse(status_code=200, text=json.dumps(ledger), ok=True)

    channel = _RecordingChannel()
    agent = build_acp_agent(settings=AcpSettings(), channel=channel, gateway=_Hub())
    await agent.handle_request("session/new", {"cwd": "/work/src", "mcpServers": []})
    for _ in range(500):
        if any(update["sessionUpdate"] == "plan" for update in channel.updates):
            break
        await asyncio.sleep(0.01)
    await agent.close()

    kinds = [update["sessionUpdate"] for update in channel.updates]
    assert kinds[0] == "available_commands_update" and "plan" in kinds
    assert any("Following project demo" in str(u.get("content")) for u in channel.updates)
    reads = [call for call in calls if call.tool == "vibey_ledger_after"]
    assert reads[0].route == f"/api/v1/projects/{project_id}/ledger/after"
    assert reads[0].query == (("seq", "0"), ("limit", "200"))


class _NoProbe:
    name = "nothing"

    async def run(self) -> tuple[DoctorResult, ...]:
        return (DoctorResult("PASS", "nothing", "fine"),)


async def test_build_acp_agent_runs_the_bootstrap_after_session_new() -> None:
    channel = _RecordingChannel()

    agent = build_acp_agent(
        settings=AcpSettings(), channel=channel, gateway=_Gateway(), doctor_probes=(_NoProbe(),)
    )
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    for _ in range(200):
        if any(u.get("toolCallId") == "bootstrap-doctor" for u in channel.updates):
            break
        await asyncio.sleep(0)
    await agent.close()

    doctor = [u for u in channel.updates if u.get("toolCallId") == "bootstrap-doctor"]
    assert doctor[0]["title"] == "vibey doctor"


def test_build_acp_agent_bounds_its_own_hub_start() -> None:
    agent = build_acp_agent(settings=AcpSettings(hub_start_seconds=5), channel=_RecordingChannel())

    gateway = agent._hub._gateway  # type: ignore[attr-defined]
    assert isinstance(gateway, HubGateway)
    assert isinstance(gateway._starter, BoundedHubStarter)
    assert gateway._starter._window == 5


def test_build_acp_agent_without_bootstrap_parts_has_no_bootstrap() -> None:
    agent = build_acp_agent(settings=AcpSettings(), channel=_RecordingChannel(), gateway=_Gateway())

    assert agent._bootstrap is None  # type: ignore[attr-defined]


def test_the_machine_lives_under_the_hubs_state_dir(tmp_path: Path) -> None:
    config = tmp_path / "vibey.toml"
    config.write_text(f"[hub]\nstate_dir = '{tmp_path / 'hub'}'\n")

    machine = acp_machine(AcpSettings(bootstrap_timeout_seconds=7), config_path=config)

    assert machine.connector._marker.parent == tmp_path / "hub"  # type: ignore[attr-defined]
    assert machine.lock._path == tmp_path / "hub" / "acp-bootstrap.lock"  # type: ignore[attr-defined]
    runner = machine.postgres._runner  # type: ignore[attr-defined]
    assert runner._timeout == 7


def test_an_unreadable_hub_table_still_gives_the_machine_a_home(tmp_path: Path) -> None:
    config = tmp_path / "vibey.toml"
    config.write_text("[hub]\nstate_dir = 3\n")

    machine = acp_machine(AcpSettings(), config_path=config)

    assert machine.lock._path.parent == HubSettings().state_dir  # type: ignore[attr-defined]
