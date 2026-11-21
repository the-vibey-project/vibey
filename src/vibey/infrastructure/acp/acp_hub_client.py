# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's hub port over the MCP `HubGateway` (SP-ACP, ADR-0100, ADR-0017).

Every request goes through the gateway `vibey mcp` already uses, as the scoped agent
principal (`<state_dir>/agent.token`), so the hub stays the one place scopes are enforced and
`spend` is never in reach. The gateway is synchronous (`httpx`, and `vibey hub start` once when
no hub answers), so each call runs in a worker thread and never blocks the event loop that is
reading `session/cancel`.

Only a failure to reach the hub becomes "the hub could not be reached": the gateway's own
`HubGatewayError`, or an `OSError` (a state directory it cannot write, a socket error). Anything
else is a defect and reaches the caller as itself, so it is logged with its traceback instead of
reading as a connection problem; `healthy`, which never raises, logs it and answers False.

Declared by `application/acp/interfaces/acp_hub_port_interface.py::AcpHubPortInterface`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any, Final
from uuid import UUID

from vibey.application.acp.dto import HubToolResult, HubTurn, LedgerPage
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import HOST_TOOL_CATALOG, HubCall
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.infrastructure.mcp.hub_gateway import HUB_GATEWAY, HubGatewayError, HubGatewayResponse
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface

CHAT_ROUTE: Final = "/api/v1/chat/messages"
LIVENESS_ROUTE: Final = "/health/live"
_LOG: Final = logging.getLogger(__name__)


class AcpHubClient:
    """Declared by `application/acp/interfaces/acp_hub_port_interface.py`."""

    def __init__(
        self,
        *,
        gateway: HubGatewayInterface = HUB_GATEWAY,
        tools: HostToolsInterface = HOST_TOOL_CATALOG,
    ) -> None:
        self._gateway = gateway
        self._tools = tools

    async def chat(self, message: str, *, project_id: UUID | None, request_id: str) -> HubTurn:
        response = await self._send(
            HubCall(
                tool="vibey_chat",
                method="POST",
                route=CHAT_ROUTE,
                body={
                    "message": message,
                    "project_id": str(project_id) if project_id is not None else None,
                    "request_id": request_id,
                },
            )
        )
        document = self._document(self._accepted(response), "a chat turn")
        try:
            raw_project = document.get("project_id")
            project = UUID(str(raw_project)) if raw_project else None
        except ValueError as exc:
            raise HubGatewayError(f"the hub's answer is not a chat turn: {exc}") from exc
        return HubTurn(
            reply=str(document.get("reply", "")),
            tool_calls=self._mappings(document.get("tool_calls")),
            gates=self._mappings(document.get("gates")),
            project_id=project,
        )

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any], *, request_id: str
    ) -> HubToolResult:
        call = self._tools.build_call(name, arguments, request_id=request_id)
        response = await self._send(call)
        return HubToolResult(ok=response.ok, status_code=response.status_code, text=response.text)

    async def ledger_after(self, project_id: UUID, after: int, limit: int) -> LedgerPage:
        response = await self._send(
            HubCall(
                tool="vibey_ledger_after",
                method="GET",
                route=f"/api/v1/projects/{project_id}/ledger/after",
                query=(("seq", str(after)), ("limit", str(limit))),
            )
        )
        document = self._document(self._accepted(response), "a ledger page")
        last_seq = document.get("last_seq")
        return LedgerPage(
            events=self._mappings(document.get("events")),
            last_seq=(
                last_seq if isinstance(last_seq, int) and not isinstance(last_seq, bool) else None
            ),
        )

    async def healthy(self) -> bool:
        try:
            response = await self._send(
                HubCall(tool="vibey_health", method="GET", route=LIVENESS_ROUTE)
            )
        except VibeyError:
            return False
        except Exception:
            # Not an unreachable hub but a defect: the check still answers, and the traceback
            # is kept so the defect is found rather than read as the hub being down.
            _LOG.exception("the hub's liveness check failed unexpectedly")
            return False
        return response.ok

    def agent_scopes(self) -> frozenset[HubScope]:
        return self._gateway.agent_scopes()

    async def _send(self, call: HubCall) -> HubGatewayResponse:
        try:
            return await asyncio.to_thread(self._gateway.call, call)
        except OSError as exc:
            # The port promises a `VibeyError` for an unreachable hub; the gateway can let an
            # OSError through (a state directory it cannot write).
            raise HubGatewayError(f"the hub could not be reached: {exc}") from exc

    @staticmethod
    def _accepted(response: HubGatewayResponse) -> str:
        if not response.ok:
            raise HubGatewayError(f"hub refused ({response.status_code}): {response.text}")
        return response.text

    @staticmethod
    def _document(text: str, what: str) -> Mapping[str, Any]:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HubGatewayError(f"the hub's answer is not {what}: {exc.msg}") from exc
        if not isinstance(parsed, Mapping):
            raise HubGatewayError(f"the hub's answer is not {what}: expected a JSON object")
        return parsed

    @staticmethod
    def _mappings(value: Any) -> tuple[Mapping[str, Any], ...]:
        if not isinstance(value, list):
            return ()
        return tuple(item for item in value if isinstance(item, Mapping))
