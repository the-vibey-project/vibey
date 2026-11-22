# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp`: the Agent Client Protocol agent an editor launches over stdio (SP-ACP).

An editor such as Zed starts `vibey acp` and speaks ACP v1 (JSON-RPC 2.0, one message per
line) on its stdin and stdout. The first thing `run` does is guard stdout, so every byte that
reaches it afterwards is a protocol frame; anything else in this process or its children that
prints lands on stderr. The root callback has already pointed logging at stderr, and the guard
also catches any handler still holding fd 1. Then `[acp]` is read -- the user's own
`vibey.toml` (`bootstrap.acp_user_config`) grants, and `./vibey.toml`, the project the editor
opened, may only narrow it (ADR-0101) -- the agent is composed (`bootstrap.build_acp_agent`) and
the peer serves until stdin closes.

The agent's bootstrap runs `vibey doctor`'s local sections (`LOCAL_DOCTOR_PROBES`, which never
print) and, under `[acp]`'s grant, connects the user-scope clients and offers a PostgreSQL
install (`bootstrap.acp_machine`).
"""

from __future__ import annotations

import asyncio
import dataclasses
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Final

import typer

from vibey.application.acp.interfaces.doctor_probe_interface import DoctorProbeInterface
from vibey.bootstrap import AcpMachine, acp_machine, acp_user_config, build_acp_agent
from vibey.cli.acp_unload import ACP_UNLOAD
from vibey.cli.doctor_probes import LOCAL_DOCTOR_PROBES
from vibey.cli.errors import EXIT_USAGE
from vibey.cli.interfaces.acp_interface import AcpAgentBuilder, AcpCommandInterface
from vibey.domain.acp.settings import AcpSettings
from vibey.infrastructure.acp.acp_settings_loader import AcpSettingsLoader
from vibey.infrastructure.acp.interfaces.acp_settings_loader_interface import (
    AcpSettingsLoaderInterface,
)
from vibey.infrastructure.acp.interfaces.stdio_transport_interface import StdioTransportInterface
from vibey.infrastructure.acp.peer_client_channel import PeerClientChannel
from vibey.infrastructure.acp.stdio_transport import StdioTransport
from vibey.infrastructure.jsonrpc.codec import CODEC
from vibey.infrastructure.jsonrpc.peer import JsonRpcPeer


class AcpCommand:
    """Runs the ACP agent over standard input and a guarded standard output.

    Declared by `interfaces/acp_interface.py::AcpCommandInterface`. `before_serve` runs after
    the guard and before the peer starts: an ordinary seam, which is how the guard is proven
    against a real `print`, `typer.echo` and an inheriting child.
    """

    def __init__(
        self,
        *,
        transport: Callable[[], StdioTransportInterface] = StdioTransport,
        settings: AcpSettingsLoaderInterface | None = None,
        config_path: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        user_config: Callable[[], Path] = acp_user_config,
        build_agent: AcpAgentBuilder = build_acp_agent,
        before_serve: Callable[[], None] = lambda: None,
        doctor_probes: Sequence[DoctorProbeInterface] = LOCAL_DOCTOR_PROBES,
        machine: Callable[..., AcpMachine] = acp_machine,
    ) -> None:
        self._transport = transport
        self._settings = settings if settings is not None else AcpSettingsLoader()
        self._config_path = config_path
        self._user_config = user_config
        self._build_agent = build_agent
        self._before_serve = before_serve
        self._doctor_probes = doctor_probes
        self._machine = machine

    def run(self, *, no_bootstrap: bool) -> None:
        transport = self._transport()
        transport.guard()
        self._before_serve()
        # The user's own file grants; the project's (the folder the editor opened) only narrows.
        settings = self._settings.load_trusted(self._user_config(), self._config_path())
        if no_bootstrap:
            settings = dataclasses.replace(settings, auto_bootstrap=False)
        asyncio.run(self._serve(transport, settings))

    async def _serve(self, transport: StdioTransportInterface, settings: AcpSettings) -> None:
        # One byte over the bound, so a message exactly `max_message_bytes` long plus its
        # newline fits the reader; the peer refuses anything longer by name.
        reader = await transport.reader(limit=settings.max_message_bytes + 1)
        channel = PeerClientChannel()
        machine = self._machine(settings, user_config=self._user_config())
        agent = self._build_agent(
            settings=settings,
            channel=channel,
            doctor_probes=self._doctor_probes,
            connector=machine.connector,
            postgres=machine.postgres,
            lock=machine.lock,
            units=machine.units,
            loader=machine.loader,
        )
        peer = JsonRpcPeer(
            reader,
            transport.write_line,
            on_request=agent.handle_request,
            on_notification=agent.handle_notification,
            codec=CODEC,
            id_prefix="vibey",
            max_message_bytes=settings.max_message_bytes,
        )
        channel.attach(peer)
        try:
            await peer.run()
        finally:
            # The live feeds poll in tasks of their own: none may outlive the connection.
            await agent.close()


ACP_COMMAND: Final[AcpCommandInterface] = AcpCommand()


def acp(
    action: Annotated[
        str | None,
        typer.Argument(
            help="`unload`: stop the services vibey acp loaded, for good, and delete the unit "
            "files vibey wrote. Without it, serve ACP over stdio.",
            show_default=False,
        ),
    ] = None,
    no_bootstrap: Annotated[
        bool,
        typer.Option(
            "--no-bootstrap",
            help="Do not run doctor or connect, load services or install anything for this "
            "process, whatever [acp] auto_bootstrap says.",
        ),
    ] = False,
) -> None:
    """Serve the Agent Client Protocol (ACP) over stdio for an editor such as Zed; or, with
    `unload`, stop the services it loaded (ADR-0101)."""
    # Module-level function because Typer builds the command from a plain function signature.
    if action is None:
        ACP_COMMAND.run(no_bootstrap=no_bootstrap)
        return
    if action != "unload":
        typer.echo(f"vibey acp: unknown action {action!r}; the only one is `unload`", err=True)
        raise typer.Exit(EXIT_USAGE)
    raise typer.Exit(ACP_UNLOAD.run())
