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

An ACP session's log goes through the hub's `/api/v1/acp/sessions` routes. A 403 or 404 there
is `UnknownAcpSession` (the hub answers a session that is not the agent's, or not under that
folder, as it answers one that does not exist), a 409 `SessionEventConflict`, a 429 `SessionWritesThrottled`, a 507 `AcpSessionLimitReached` (`[acp] sessions_max` or
`session_events_max` reached), and a 422 on a list
`InvalidSessionCursor`; anything else refused is a `HubGatewayError` as elsewhere.

Declared by `application/acp/interfaces/acp_hub_port_interface.py::AcpHubPortInterface`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final
from uuid import UUID

from vibey.application.acp.dto import (
    HubToolResult,
    HubTurn,
    LedgerPage,
    SessionEvent,
    SessionRecord,
    SessionSummary,
)
from vibey.domain.acp.session_log import (
    SESSION_ID_SHAPE,
    SESSION_PAGE,
    AcpSessionLimitReached,
    InvalidSessionCursor,
    SessionEventConflict,
    SessionWritesThrottled,
    UnknownAcpSession,
)
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import HOST_TOOL_CATALOG, HubCall
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.infrastructure.mcp.hub_gateway import HUB_GATEWAY, HubGatewayError, HubGatewayResponse
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface

CHAT_ROUTE: Final = "/api/v1/chat/messages"
SESSIONS_ROUTE: Final = "/api/v1/acp/sessions"
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

    async def create_session(self, session_id: str, cwd: str) -> None:
        response = await self._send(
            HubCall(
                tool="vibey_acp_session",
                method="POST",
                route=SESSIONS_ROUTE,
                body={"session_id": session_id, "cwd": cwd},
            )
        )
        self._kept(response)

    async def append_event(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any]
    ) -> None:
        response = await self._send(
            HubCall(
                tool="vibey_acp_session_event",
                method="POST",
                route=self._events_route(session_id),
                body={"seq": seq, "kind": kind, "payload": dict(payload)},
            )
        )
        self._kept(response)

    async def session_events(
        self, session_id: str, after: int, *, cwd: str
    ) -> tuple[SessionEvent, ...]:
        events: list[SessionEvent] = []
        cursor = after
        while True:
            response = await self._send(
                HubCall(
                    tool="vibey_acp_session_events",
                    method="GET",
                    route=self._events_route(session_id),
                    query=(("after", str(cursor)), ("limit", str(SESSION_PAGE)), ("cwd", cwd)),
                )
            )
            document = self._document(self._kept(response), "a page of session events")
            raw = document.get("events")
            items = self._mappings(raw)
            events += [
                SessionEvent(seq=item["seq"], kind=item["kind"], payload=item["payload"])
                for item in items
                if self._is_int(item.get("seq"))
                and item["seq"] > cursor
                and isinstance(item.get("kind"), str)
                and isinstance(item.get("payload"), Mapping)
            ]
            # The end is a short page as the hub sent it, counted before anything malformed is
            # passed over, or a page that does not move past the cursor.
            ahead = [item["seq"] for item in items if self._is_int(item.get("seq"))]
            ahead = [seq for seq in ahead if seq > cursor]
            if not isinstance(raw, list) or len(raw) < SESSION_PAGE or not ahead:
                return tuple(events)
            cursor = max(ahead)

    async def session_summary(self, session_id: str, *, cwd: str) -> SessionSummary:
        response = await self._send(
            HubCall(
                tool="vibey_acp_session_summary",
                method="GET",
                route=self._session_route(session_id),
                query=(("cwd", cwd),),
            )
        )
        document = self._document(self._kept(response), "a session summary")
        newest = document.get("newest_seq")
        mode, attach, title = (
            value if isinstance(value := document.get(key), Mapping) else None
            for key in ("mode", "attach", "title")
        )
        return SessionSummary(
            newest_seq=newest if type(newest) is int and newest > 0 else 0,
            mode=mode,
            attach=attach,
            title=title,
        )

    async def list_sessions(
        self, *, cwd: str | None, cursor: str | None
    ) -> tuple[tuple[SessionRecord, ...], str | None]:
        query: list[tuple[str, str]] = [("limit", str(SESSION_PAGE))]
        if cwd is not None:
            query.append(("cwd", cwd))
        if cursor is not None:
            query.append(("cursor", cursor))
        response = await self._send(
            HubCall(
                tool="vibey_acp_sessions", method="GET", route=SESSIONS_ROUTE, query=tuple(query)
            )
        )
        if response.status_code == 422 and cursor is not None:
            raise InvalidSessionCursor("that cursor is not one the hub gave out")
        document = self._document(self._kept(response), "a page of sessions")
        records = tuple(
            record
            for item in self._mappings(document.get("sessions"))
            if (record := self._record(item)) is not None
        )
        next_cursor = document.get("next_cursor")
        return records, next_cursor if isinstance(next_cursor, str) else None

    def agent_scopes(self) -> frozenset[HubScope]:
        return self._gateway.agent_scopes()

    async def _send(self, call: HubCall) -> HubGatewayResponse:
        try:
            return await asyncio.to_thread(self._gateway.call, call)
        except OSError as exc:
            # The port promises a `VibeyError` for an unreachable hub; the gateway can let an
            # OSError through (a state directory it cannot write).
            raise HubGatewayError(f"the hub could not be reached: {exc}") from exc

    @classmethod
    def _kept(cls, response: HubGatewayResponse) -> str:
        """A session route's answer, with its refusals as the port names them."""
        if response.status_code in (403, 404):
            raise UnknownAcpSession("the hub keeps no such session for vibey's agent principal")
        if response.status_code == 409:
            raise SessionEventConflict(f"the hub refused it as a conflict: {response.text}")
        if response.status_code == 507:
            raise AcpSessionLimitReached(f"the hub keeps no more: {response.text}")
        if response.status_code == 429:
            raise SessionWritesThrottled("the hub's rate limit refused it for now")
        return cls._accepted(response)

    @classmethod
    def _record(cls, item: Mapping[str, Any]) -> SessionRecord | None:
        """One listed session, or None when the hub's entry is not one."""
        session_id, cwd, title = item.get("session_id"), item.get("cwd"), item.get("title")
        stamp = item.get("updated_at")
        if not isinstance(session_id, str) or not isinstance(cwd, str):
            return None
        if title is not None and not isinstance(title, str):
            return None
        try:
            updated_at = datetime.fromisoformat(stamp) if isinstance(stamp, str) else None
        except ValueError:
            return None
        if updated_at is None:
            return None
        return SessionRecord(
            session_id=session_id,
            cwd=cwd,
            title=title,
            updated_at=updated_at,
            closed=item.get("closed") is True,
        )

    @classmethod
    def _events_route(cls, session_id: str) -> str:
        return f"{cls._session_route(session_id)}/events"

    @staticmethod
    def _session_route(session_id: str) -> str:
        # Only an id in the shape vibey mints is ever put in a route.
        if SESSION_ID_SHAPE.fullmatch(session_id) is None:
            raise UnknownAcpSession("that is not a session id vibey made")
        return f"{SESSIONS_ROUTE}/{session_id}"

    @staticmethod
    def _is_int(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

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
