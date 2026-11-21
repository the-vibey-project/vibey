# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent: method dispatch and the session registry (SP-ACP, ADR-0100).

`handle_request` and `handle_notification` are the JSON-RPC peer's two handlers. The peer runs
each inbound message in its own task, in arrival order, so a `session/cancel` read in the same
chunk as its `session/prompt` is handled right after the prompt's handler first yields. The
prompt handler therefore begins the turn on the session state before it awaits anything: the
cancel always finds the turn it belongs to, and a cancel with no turn active changes nothing.
The turn itself runs in a task of its own so a cancel can stop it; the handler waits for it
and answers with the one stop reason the session state allows. A cancelled turn answers
`{"stopReason": "cancelled"}`, never a JSON-RPC error.

Declared by `interfaces/acp_agent_interface.py`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine, Mapping
from pathlib import PurePath
from typing import Any

from vibey.application.acp.dto import AcpSessionContext
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.acp_prompt_turn_interface import AcpPromptTurnInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.protocol import (
    AUTHENTICATE,
    INITIALIZE,
    PROTOCOL_VERSION,
    RESOURCE_NOT_FOUND,
    SESSION_CANCEL,
    SESSION_NEW,
    SESSION_PROMPT,
    StopReason,
)
from vibey.domain.acp.session_state import AcpSessionState, TurnAlreadyRunning
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface
from vibey.domain.jsonrpc_errors import INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, RpcError

type TurnFactory = Callable[[], AcpPromptTurnInterface]


class AcpAgent:
    """Declared by `interfaces/acp_agent_interface.py::AcpAgentInterface`.

    `hub`, `chat` and `tools` are held for the methods later SP-ACP tasks add (session
    attach, slash commands, gates); a prompt turn reaches them through `turn_factory`.
    """

    def __init__(
        self,
        channel: ClientChannelInterface,
        hub: AcpHubPortInterface,
        settings: AcpSettings,
        modes: AcpModesInterface,
        mapper: AcpUpdateMapperInterface,
        chat: HubChatInterface,
        tools: HostToolsInterface,
        turn_factory: TurnFactory,
        *,
        version: str,
        new_id: Callable[[], str],
    ) -> None:
        self._channel = channel
        self._hub = hub
        self._settings = settings
        self._modes = modes
        self._mapper = mapper
        self._chat = chat
        self._tools = tools
        self._turn_factory = turn_factory
        self._version = version
        self._new_id = new_id
        self._contexts: dict[str, AcpSessionContext] = {}
        self._turns: dict[str, asyncio.Task[StopReason]] = {}
        self._background: set[asyncio.Task[None]] = set()

    @property
    def sessions(self) -> Mapping[str, AcpSessionStateInterface]:
        return {session_id: context.state for session_id, context in self._contexts.items()}

    async def handle_request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        if method == INITIALIZE:
            return self._initialize(params)
        if method == AUTHENTICATE:
            return {}
        if method == SESSION_NEW:
            return self._new_session(params)
        if method == SESSION_PROMPT:
            return await self._prompt(params)
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    async def handle_notification(self, method: str, params: Mapping[str, Any]) -> None:
        # Any other notification is ignored, as JSON-RPC lets a receiver do.
        if method == SESSION_CANCEL:
            self._cancel(params)

    # -- methods --------------------------------------------------------------------------

    def _initialize(self, params: Mapping[str, Any]) -> dict[str, Any]:
        # vibey speaks one protocol version and says which; a client that cannot speak it
        # closes the connection, as the protocol's version negotiation lays down.
        capabilities = params.get("clientCapabilities")
        self._channel.client_capabilities = (
            dict(capabilities) if isinstance(capabilities, Mapping) else {}
        )
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "agentCapabilities": {
                "loadSession": True,
                "promptCapabilities": {"image": False, "audio": False, "embeddedContext": True},
                "mcpCapabilities": {"http": False, "sse": False},
                "sessionCapabilities": {"list": {}, "close": {}, "resume": {}},
            },
            "agentInfo": {"name": "vibey", "title": "vibey", "version": self._version},
            "authMethods": [],
        }

    def _new_session(self, params: Mapping[str, Any]) -> dict[str, Any]:
        cwd = params.get("cwd")
        if not isinstance(cwd, str) or not PurePath(cwd).is_absolute():
            raise RpcError(INVALID_PARAMS, "session/new needs an absolute cwd")
        servers = params.get("mcpServers")
        ignored = len(servers) if isinstance(servers, list) else 0
        session_id = self._new_id()
        self._contexts[session_id] = AcpSessionContext(
            session_id=session_id,
            state=AcpSessionState(session_id),
            mode_id=self._settings.default_mode,
            project_id=None,
            offered_gates=set(),
            cwd=cwd,
        )
        if ignored:
            # Sent from a task of its own: the peer writes this response before the task runs,
            # and an update naming a session the client has not been told of yet is refused.
            self._in_background(
                self._channel.notify_update(
                    session_id,
                    self._mapper.agent_text(
                        f"vibey ignored the {ignored} MCP server(s) this client offered: it "
                        "reaches its own tools through the vibey hub, as the scoped agent "
                        "principal, and runs no client MCP servers."
                    ),
                )
            )
        return {
            "sessionId": session_id,
            "modes": self._modes.session_modes(self._settings.default_mode),
        }

    async def _prompt(self, params: Mapping[str, Any]) -> dict[str, Any]:
        context = self._context(params)
        prompt = params.get("prompt")
        if not isinstance(prompt, list) or not all(isinstance(b, Mapping) for b in prompt):
            raise RpcError(
                INVALID_PARAMS, "session/prompt needs a prompt: a list of content blocks"
            )
        turn_id = self._new_id()
        # Nothing above awaits, so a cancel read with this prompt finds the turn begun.
        try:
            context.state.begin_turn(turn_id)
        except TurnAlreadyRunning as exc:
            raise RpcError(INVALID_REQUEST, "a turn is already running in this session") from exc
        task = asyncio.create_task(
            self._turn_factory().run(context, prompt, turn_id=turn_id),
            name=f"acp-turn-{context.session_id}-{turn_id}",
        )
        self._turns[context.session_id] = task
        try:
            proposed = await task
        except asyncio.CancelledError:
            if not context.state.cancel_requested:
                # This handler itself was cancelled (the peer is shutting down), not the turn.
                context.state.finish_turn(StopReason.CANCELLED)
                raise
            proposed = StopReason.CANCELLED
        except Exception:
            context.state.finish_turn(StopReason.END_TURN)
            raise
        finally:
            self._turns.pop(context.session_id, None)
        return {"stopReason": context.state.finish_turn(proposed).value}

    def _cancel(self, params: Mapping[str, Any]) -> None:
        session_id = params.get("sessionId")
        context = self._contexts.get(session_id) if isinstance(session_id, str) else None
        if context is None or context.state.cancel_requested:
            # A repeated cancel (Esc pressed twice, a client that resends) must not cancel the
            # turn again: that would interrupt the settle that reports the hub call's outcome.
            return
        context.state.request_cancel()
        task = self._turns.get(context.session_id)
        if task is not None:
            task.cancel()

    # -- helpers --------------------------------------------------------------------------

    def _context(self, params: Mapping[str, Any]) -> AcpSessionContext:
        session_id = params.get("sessionId")
        context = self._contexts.get(session_id) if isinstance(session_id, str) else None
        if context is None:
            raise RpcError(RESOURCE_NOT_FOUND, f"no session {session_id!r} in this process")
        return context

    def _in_background(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(work)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
