# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP servers a run can reach, behind two gateway tools (vibey ADR-0092, #1666; SP-LOOPS
Phase 5, R4 to R7, R13).

A local model has a small context window and has been seen misusing a long tool list, so the
servers' own tools are not added to the one it is told. `mcp_list` names the servers, a server's
tools, or one tool's schema; `mcp_call` calls one. This gateway is an adapter over the family's
`McpSessionPool`: one persistent session per server per run, started on first use, restarted at
most `[mcp] restarts` times, closed by `aclose` when the run ends, and every failure an
`McpUnavailable` or `McpToolError` the tool dispatcher turns into an answer.

Where the servers come from:

- `from_document`: a run given a capability snapshot reaches exactly the snapshot's servers (R4),
  through `McpTransportFactory`: a `local` one is started by the scrubbed launcher, so it keeps
  only its `env_allow` names, and a `remote` one is sent no environment at all. Neither
  `~/.claude.json` nor `QWENLOOP_MCP_CONFIG` is read.
- `discover`: a run without one reaches the servers the operator already declared for their
  other tools, `~/.claude.json` and the file `QWENLOOP_MCP_CONFIG` names, the later winning.
  Only stdio servers are supported; a declared server that is not one is reported, not dropped.

The worktree's own `.mcp.json` is never read, in either mode: a server is a command, the model
can write that file, and so can any repository a run checks out, so reading it would let either
run any program outside the shell tool's policy. Declared by
`interfaces/mcp_interface.py::McpGatewayInterface`.
"""

import json
import sys
from collections.abc import Callable, Mapping
from functools import partial
from pathlib import Path

from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpTrust
from vibey_runners.common.capabilities.scrubbed_exec import LAUNCHER_ARGS
from vibey_runners.common.capabilities.scrubbed_launch import ScrubbedLaunch
from vibey_runners.common.mcp.interfaces.mcp_session_interface import McpSessionInterface
from vibey_runners.common.mcp.interfaces.mcp_session_pool_interface import (
    McpSessionPoolInterface,
)
from vibey_runners.common.mcp.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpToolError
from vibey_runners.common.mcp.mcp_session import McpSession
from vibey_runners.common.mcp.mcp_session_pool import McpSessionPool
from vibey_runners.common.mcp.mcp_tool import McpTool
from vibey_runners.common.mcp.mcp_transport_factory import McpTransportFactory
from vibey_runners.common.mcp.stdio_transport import StdioTransport

from qwenloop.domain.config import McpLimits

CONFIG_ENV = "QWENLOOP_MCP_CONFIG"

_Transport = Callable[[], McpTransportInterface]


class McpGateway:
    """Declared by `interfaces/mcp_interface.py::McpGatewayInterface`."""

    def __init__(
        self,
        pool: McpSessionPoolInterface,
        *,
        unsupported: Mapping[str, str] | None = None,
        max_tools: int = McpLimits().max_tools,
    ) -> None:
        self._pool = pool
        self._unsupported = dict(unsupported or {})
        self._max_tools = max_tools

    @classmethod
    def from_document(
        cls,
        document: SnapshotDocumentInterface,
        *,
        cwd: Path,
        environ: Mapping[str, str],
        limits: McpLimits,
        client: tuple[str, str],
        transports: McpTransportFactoryInterface | None = None,
    ) -> "McpGateway":
        """Exactly the snapshot's servers (R4). `transports` is the seam a test replaces; a run
        uses the family's factory, whose local servers start through the scrubbed launcher run
        by this interpreter. A server the factory refuses (a remote one with no URL, a local one
        with no command, both of which the document reader already refuses) is reported in
        `unsupported` and never started."""
        factory = transports or McpTransportFactory(
            ScrubbedLaunch((sys.executable, *LAUNCHER_ARGS)),
            cwd=cwd,
            environ=environ,
            timeout_seconds=limits.request_timeout_seconds,
        )
        makers: dict[str, _Transport] = {}
        trust: dict[str, McpTrust] = {}
        unsupported: dict[str, str] = {}
        for spec in document.mcp_servers:
            try:
                factory.for_spec(spec)  # builds an unopened transport: no process, no request
            except ValueError as exc:
                unsupported[spec.name] = str(exc)
                continue
            makers[spec.name] = partial(factory.for_spec, spec)
            trust[spec.name] = spec.trust
        return cls(
            cls._pool_of(makers, trust, limits, client),
            unsupported=unsupported,
            max_tools=limits.max_tools,
        )

    @classmethod
    def discover(
        cls,
        cwd: Path,
        *,
        home: Path,
        environ: Mapping[str, str],
        base_env: Mapping[str, str],
        limits: McpLimits,
        client: tuple[str, str],
    ) -> "McpGateway":
        """The stdio servers declared in `home/.claude.json` and the file `QWENLOOP_MCP_CONFIG`
        names, and nowhere in the worktree. A file that is missing or is not JSON declares none.
        Each runs as its own command and arguments, with `base_env` and its own `env`."""
        sources = [home / ".claude.json"]
        if environ.get(CONFIG_ENV):
            sources.append(Path(environ[CONFIG_ENV]))
        found: dict[str, tuple[tuple[str, ...], dict[str, str]]] = {}
        unsupported: dict[str, str] = {}
        for source in sources:
            servers, refused = cls._parse(cls._load(source), str(source))
            found.update(servers)
            unsupported.update(refused)
        unsupported = {name: why for name, why in unsupported.items() if name not in found}
        makers: dict[str, _Transport] = {
            name: partial(StdioTransport, name, argv, {**base_env, **env}, cwd)
            for name, (argv, env) in found.items()
        }
        local: McpTrust = "local"
        trust = dict.fromkeys(makers, local)
        return cls(
            cls._pool_of(makers, trust, limits, client),
            unsupported=unsupported,
            max_tools=limits.max_tools,
        )

    @property
    def server_names(self) -> tuple[str, ...]:
        return self._pool.names

    @property
    def unsupported(self) -> Mapping[str, str]:
        return self._unsupported

    @property
    def max_tools(self) -> int:
        return self._max_tools

    def trust_of(self, server: str) -> McpTrust:
        return self._pool.trust_of(server)

    def remote_calls_left(self, server: str) -> int | None:
        return self._pool.remote_calls_left(server)

    async def list_tools(self, server: str) -> tuple[McpTool, ...]:
        return await self._pool.tools(server)

    async def schema(self, server: str, tool: str) -> Mapping[str, object]:
        for listed in await self._pool.tools(server):
            if listed.name == tool:
                return listed.input_schema
        raise McpToolError(
            f"MCP server {server!r} lists no tool {tool!r}; call mcp_list with the server alone "
            "to see its tools"
        )

    async def call(self, server: str, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        return await self._pool.call(server, tool, arguments)

    async def aclose(self) -> None:
        await self._pool.aclose()

    # -- internals ------------------------------------------------------------------------

    @classmethod
    def _pool_of(
        cls,
        makers: Mapping[str, _Transport],
        trust: Mapping[str, McpTrust],
        limits: McpLimits,
        client: tuple[str, str],
    ) -> McpSessionPool:
        """One pool over `makers`: each start is a fresh session on a fresh transport."""
        return McpSessionPool(
            {name: partial(cls._session, make, limits, client) for name, make in makers.items()},
            trust=trust,
            restarts=limits.restarts,
            remote_calls=limits.remote_calls_per_session,
            close_grace_seconds=limits.close_grace_seconds,
        )

    @staticmethod
    def _session(
        make: _Transport, limits: McpLimits, client: tuple[str, str]
    ) -> McpSessionInterface:
        return McpSession(
            make(),
            client_name=client[0],
            client_version=client[1],
            timeout_seconds=limits.request_timeout_seconds,
            max_tools=limits.max_tools,
        )

    @staticmethod
    def _load(path: Path) -> object:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _parse(
        document: object, source: str
    ) -> tuple[dict[str, tuple[tuple[str, ...], dict[str, str]]], dict[str, str]]:
        """The stdio servers one file declares, each as its argv and its own environment, and
        the declared servers that are not stdio servers with a command, each with why."""
        table = document.get("mcpServers") if isinstance(document, dict) else None
        servers: dict[str, tuple[tuple[str, ...], dict[str, str]]] = {}
        unsupported: dict[str, str] = {}
        for name, entry in table.items() if isinstance(table, dict) else ():
            entry = entry if isinstance(entry, dict) else {}
            command = entry.get("command")
            if entry.get("type", "stdio") != "stdio" or not isinstance(command, str):
                unsupported[str(name)] = f"{source}: only stdio servers with a command"
                continue
            env = entry.get("env")
            servers[str(name)] = (
                (command, *(str(a) for a in entry.get("args") or ())),
                {str(k): str(v) for k, v in env.items()} if isinstance(env, dict) else {},
            )
        return servers, unsupported
