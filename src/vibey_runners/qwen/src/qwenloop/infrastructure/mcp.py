# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP servers a run can reach, behind two gateway tools (vibey ADR-0092, #1666).

A local model has a small context window and has been seen misusing a long tool list, so
the servers' own tools are not added to the one it is told. `mcp_list` names the servers
and, for one, its tools; `mcp_call` calls one. The servers are the ones the operator already
declared for their other tools: `~/.claude.json` and the file `QWENLOOP_MCP_CONFIG` names,
the later winning. The worktree's own `.mcp.json` is never read: a server is a command, the
model can write that file, and so can any repository a run checks out, so reading it would let
either run any program outside the shell tool's policy. Only stdio servers are supported, and
a declared server that is not one is reported rather than dropped.

Each call starts the server, speaks newline-delimited JSON-RPC to it, and stops it: no
process outlives the call, so a run that dies leaves none behind.
"""

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

PROTOCOL_VERSION = "2024-11-05"
CONFIG_ENV = "QWENLOOP_MCP_CONFIG"
DEFAULT_TIMEOUT_SECONDS = 60.0


class McpError(RuntimeError):
    """The server could not be reached, or answered with an error."""


@dataclass(frozen=True, slots=True)
class McpServer:
    name: str
    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)


class McpGateway:
    def __init__(
        self,
        servers: Mapping[str, McpServer],
        *,
        worktree: Path,
        unsupported: Mapping[str, str] | None = None,
        base_env: Mapping[str, str] | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._servers = dict(servers)
        self._unsupported = dict(unsupported or {})
        self._worktree = worktree
        self._base_env = dict(base_env or {})
        self._timeout = timeout_seconds

    @classmethod
    def discover(
        cls,
        worktree: Path,
        *,
        home: Path,
        environ: Mapping[str, str],
        base_env: Mapping[str, str] | None = None,
    ) -> "McpGateway":
        """The servers declared in `home/.claude.json` and the file `QWENLOOP_MCP_CONFIG`
        names, and nowhere in the worktree. A file that is missing or is not JSON declares
        none."""
        sources = [home / ".claude.json"]
        if environ.get(CONFIG_ENV):
            sources.append(Path(environ[CONFIG_ENV]))
        servers: dict[str, McpServer] = {}
        unsupported: dict[str, str] = {}
        for source in sources:
            found, refused = cls._parse(cls._load(source), str(source))
            servers.update(found)
            unsupported.update(refused)
        unsupported = {name: why for name, why in unsupported.items() if name not in servers}
        return cls(servers, worktree=worktree, unsupported=unsupported, base_env=base_env)

    @staticmethod
    def _load(path: Path) -> object:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _parse(document: object, source: str) -> tuple[dict[str, McpServer], dict[str, str]]:
        table = document.get("mcpServers") if isinstance(document, dict) else None
        servers: dict[str, McpServer] = {}
        unsupported: dict[str, str] = {}
        for name, entry in table.items() if isinstance(table, dict) else ():
            entry = entry if isinstance(entry, dict) else {}
            command = entry.get("command")
            if entry.get("type", "stdio") != "stdio" or not isinstance(command, str):
                unsupported[str(name)] = f"{source}: only stdio servers with a command"
                continue
            env = entry.get("env")
            servers[str(name)] = McpServer(
                str(name),
                command,
                tuple(str(a) for a in entry.get("args") or ()),
                {str(k): str(v) for k, v in env.items()} if isinstance(env, dict) else {},
            )
        return servers, unsupported

    @property
    def server_names(self) -> tuple[str, ...]:
        return tuple(self._servers)

    @property
    def unsupported(self) -> Mapping[str, str]:
        return self._unsupported

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        result = await self._request(self._server(server), "tools/list", {})
        return [
            {
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "input_schema": tool.get("inputSchema", {}),
            }
            for tool in result.get("tools", [])
            if isinstance(tool, dict)
        ]

    async def call(self, server: str, tool: str, arguments: Mapping[str, Any]) -> tuple[str, bool]:
        """The tool's text, and whether the server reported it as an error."""
        result = await self._request(
            self._server(server), "tools/call", {"name": tool, "arguments": dict(arguments)}
        )
        text = "\n".join(
            str(part.get("text", ""))
            for part in result.get("content", [])
            if isinstance(part, dict) and part.get("type") == "text"
        )
        return text, result.get("isError") is True

    def _server(self, name: str) -> McpServer:
        if name not in self._servers:
            known = ", ".join(self._servers) or "none"
            raise McpError(f"unknown MCP server {name!r}; configured: {known}")
        return self._servers[name]

    async def _request(self, server: McpServer, method: str, params: dict[str, Any]) -> Any:
        try:
            process = await asyncio.create_subprocess_exec(
                server.command,
                *server.args,
                cwd=self._worktree,
                env={**self._base_env, **server.env},
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            raise McpError(f"could not start MCP server {server.name!r}: {exc}") from exc
        try:
            return await asyncio.wait_for(self._exchange(process, method, params), self._timeout)
        except TimeoutError as exc:
            raise McpError(f"MCP server {server.name!r} did not answer in time") from exc
        finally:
            if process.returncode is None:
                process.kill()
            await process.wait()

    async def _exchange(
        self, process: asyncio.subprocess.Process, method: str, params: dict[str, Any]
    ) -> Any:
        await self._call(
            process,
            1,
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "qwenloop", "version": "0"},
            },
        )
        await self._send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        return await self._call(process, 2, method, params)

    async def _call(
        self, process: asyncio.subprocess.Process, request_id: int, method: str, params: Any
    ) -> dict[str, Any]:
        await self._send(
            process, {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        # Both pipes were asked for when the process was started, so neither is None.
        stdout = cast(asyncio.StreamReader, process.stdout)
        while True:
            line = await stdout.readline()
            if not line:
                raise McpError("the MCP server closed its output before answering")
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if "error" in message:
                detail = message["error"]
                raise McpError(
                    str(detail.get("message", detail)) if isinstance(detail, dict) else str(detail)
                )
            result = message.get("result")
            return result if isinstance(result, dict) else {}

    @staticmethod
    async def _send(process: asyncio.subprocess.Process, message: dict[str, Any]) -> None:
        stdin = cast(asyncio.StreamWriter, process.stdin)
        stdin.write(json.dumps(message).encode() + b"\n")
        await stdin.drain()
