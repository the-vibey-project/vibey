# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP sessions of one run, one per configured server (SP-LOOPS Phase 5, R5, R6, R13).

A session is made and started on the first `tools` or `call` for its server, then reused. When
it dies (any `McpUnavailable`, a failed start included) it is closed and dropped, and the next
use starts a new one, at most `restarts` times per run. After that the server answers
`MCP server 'x' is unavailable for the rest of this run: {first reason}` and is not started
again. A JSON-RPC error answer (`McpToolError`) leaves the session alive and costs nothing.

A remote server may take at most `remote_calls` `tools/call` requests per run; each spends one
before it is sent, so a call that fails still counts. Listing tools costs nothing. `aclose`
closes every live session with `close_grace_seconds`, all at once, never raises, and is
idempotent; nothing starts after it. Declared by
`interfaces/mcp_session_pool_interface.py::McpSessionPoolInterface`.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Mapping

from vibey_runners.common.capabilities.mcp_server_spec import McpTrust
from vibey_runners.common.mcp.interfaces.mcp_session_interface import McpSessionInterface
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpUnavailable
from vibey_runners.common.mcp.mcp_tool import McpTool


class McpSessionPool:
    """Declared by `interfaces/mcp_session_pool_interface.py::McpSessionPoolInterface`."""

    def __init__(
        self,
        sessions: Mapping[str, Callable[[], McpSessionInterface]],
        *,
        trust: Mapping[str, McpTrust],
        restarts: int,
        remote_calls: int,
        close_grace_seconds: float,
    ) -> None:
        if set(trust) != set(sessions):
            raise ValueError("every MCP server needs exactly one trust level")
        self._factories = dict(sessions)
        self._trust = dict(trust)
        self._restarts = restarts
        self._remote_calls = remote_calls
        self._grace = close_grace_seconds
        self._live: dict[str, McpSessionInterface] = {}
        self._deaths: dict[str, int] = {}
        self._first_reason: dict[str, str] = {}
        self._remote_left = {
            name: remote_calls for name, level in self._trust.items() if level == "remote"
        }
        self._locks: dict[str, asyncio.Lock] = {}
        self._closed = False

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._factories)

    def trust_of(self, name: str) -> McpTrust:
        self._known(name)
        return self._trust[name]

    def remote_calls_left(self, name: str) -> int | None:
        self._known(name)
        return self._remote_left.get(name)

    async def tools(self, name: str) -> tuple[McpTool, ...]:
        session = await self._session(name)
        try:
            return await session.list_tools()
        except McpUnavailable as exc:
            await self._died(name, session, exc)
            raise

    async def call(self, name: str, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        self._known(name)
        # Check and reserve in one step with no await between them, so two concurrent calls
        # cannot both spend the last call of the budget (the budget is per run, not per task).
        left = self._remote_left.get(name)
        if left is not None:
            if left <= 0:
                raise McpUnavailable(
                    f"MCP server {name!r} has used all {self._remote_calls} tools/call requests "
                    "this run allows"
                )
            self._remote_left[name] = left - 1
        try:
            session = await self._session(name)
        except McpUnavailable:
            # The server never started, so no request was sent: give the reserved call back.
            if left is not None:
                self._remote_left[name] = self._remote_left[name] + 1
            raise
        try:
            return await session.call(tool, arguments)
        except McpUnavailable as exc:
            await self._died(name, session, exc)
            raise

    async def aclose(self) -> None:
        self._closed = True
        live, self._live = self._live, {}
        await asyncio.gather(*(self._close_quietly(n, s) for n, s in live.items()))

    # -- internals ------------------------------------------------------------------------

    def _known(self, name: str) -> None:
        if name not in self._factories:
            configured = ", ".join(self._factories) or "none"
            raise McpUnavailable(f"unknown MCP server {name!r}; configured: {configured}")

    async def _session(self, name: str) -> McpSessionInterface:
        self._known(name)
        async with self._locks.setdefault(name, asyncio.Lock()):
            if self._closed:
                raise McpUnavailable(
                    f"the MCP session pool is closed; MCP server {name!r} is not started"
                )
            session = self._live.get(name)
            if session is not None:
                return session
            if self._deaths.get(name, 0) > self._restarts:
                raise McpUnavailable(
                    f"MCP server {name!r} is unavailable for the rest of this run: "
                    f"{self._first_reason[name]}"
                )
            session = self._factories[name]()
            try:
                await session.start()
            except McpUnavailable as exc:
                await self._died(name, session, exc)
                raise
            self._live[name] = session
            return session

    async def _died(self, name: str, session: McpSessionInterface, exc: McpUnavailable) -> None:
        """Count a death, remember the first reason, and let the dead session go."""
        self._deaths[name] = self._deaths.get(name, 0) + 1
        self._first_reason.setdefault(name, str(exc))
        if self._live.get(name) is session:
            del self._live[name]
        await self._close_quietly(name, session)

    async def _close_quietly(self, name: str, session: McpSessionInterface) -> None:
        """Close one session; a failure is named on stderr, never raised, so one broken
        server cannot keep the others open or end the run."""
        try:
            await session.close(self._grace)
        except Exception as exc:
            sys.stderr.write(
                f"vibey mcp: closing MCP server {name!r} failed: {type(exc).__name__}\n"
            )
