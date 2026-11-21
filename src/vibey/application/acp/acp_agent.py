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

Right after `session/new` answers, the client is sent the `/` commands it can offer, and the
session follows a project's ledger (`AcpLiveFeedInterface`) when one is known. Which project a
session follows -- and which one a prompt's commands default to -- comes from two places:

- **Its folder, at the start.** The hub's projects are listed (`vibey_projects`, as the agent
  principal) and the one whose repository holds the session's `cwd` is attached; when
  repositories nest, the deepest one wins.
- **The hub, after every turn.** The project the hub's last reply named (a `/status <id>`, a
  `/new`) replaces it, and the feed moves with it, as krypton's chat does.

The hub's reply is the later and more explicit choice, so it wins: a folder lookup that ends
after a turn already named a project changes nothing.

`session/set_mode` applies at once, in the middle of a turn too. The prompt turn reads the mode
again right before its hub call and the gate prompter before each gate and before it sends an
answer, so a switch to observe stops what has not been sent yet; a permission request still out
is withdrawn at once, and an answer picked after the switch answers nothing. A switch to drive
offers the gates held back in observe on the next turn.

Declared by `interfaces/acp_agent_interface.py`.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine, Mapping, Sequence
from pathlib import PurePath
from typing import Any, Final
from uuid import UUID

from vibey.application.acp.dto import AcpSessionContext
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.acp_live_feed_interface import AcpLiveFeedInterface
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
    SESSION_SET_MODE,
    StopReason,
)
from vibey.domain.acp.session_state import AcpSessionState, TurnAlreadyRunning
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface
from vibey.domain.jsonrpc_errors import INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, RpcError

type TurnFactory = Callable[[], AcpPromptTurnInterface]

PROJECTS_TOOL: Final = "vibey_projects"
"""The hub tool that lists every project with its repository (`repo_path`)."""


class AcpAgent:
    """Declared by `interfaces/acp_agent_interface.py::AcpAgentInterface`.

    `tools` is held for the methods later SP-ACP tasks add; a prompt turn reaches the hub,
    the chat and the tools through `turn_factory`.
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
        feed: AcpLiveFeedInterface,
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
        self._feed = feed
        self._version = version
        self._new_id = new_id
        self._contexts: dict[str, AcpSessionContext] = {}
        self._turns: dict[str, asyncio.Task[StopReason]] = {}
        self._background: set[asyncio.Task[None]] = set()
        self._followed: dict[str, UUID] = {}
        """The project each session's live feed follows."""

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
        if method == SESSION_SET_MODE:
            return self._set_mode(params)
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    async def handle_notification(self, method: str, params: Mapping[str, Any]) -> None:
        # Any other notification is ignored, as JSON-RPC lets a receiver do.
        if method == SESSION_CANCEL:
            self._cancel(params)

    async def close(self) -> None:
        background = list(self._background)
        for task in background:
            task.cancel()
        await asyncio.gather(*background, return_exceptions=True)
        await self._feed.close()

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
        context = AcpSessionContext(
            session_id=session_id,
            state=AcpSessionState(session_id),
            mode_id=self._settings.default_mode,
            project_id=None,
            offered_gates=set(),
            cwd=cwd,
        )
        self._contexts[session_id] = context
        # Sent from a task of its own: the peer writes this response before the task runs, and
        # an update naming a session the client has not been told of yet is refused.
        self._in_background(self._opened(context, ignored))
        return {
            "sessionId": session_id,
            "modes": self._modes.session_modes(self._settings.default_mode),
        }

    async def _opened(self, context: AcpSessionContext, ignored_servers: int) -> None:
        """What follows a new session's response: its commands, then its project."""
        await self._channel.notify_update(
            context.session_id, self._mapper.available_commands(self._chat.slash_commands())
        )
        if ignored_servers:
            await self._say(
                context,
                f"vibey ignored the {ignored_servers} MCP server(s) this client offered: it "
                "reaches its own tools through the vibey hub, as the scoped agent "
                "principal, and runs no client MCP servers.",
            )
        await self._attach_folder(context)

    def _set_mode(self, params: Mapping[str, Any]) -> dict[str, Any]:
        context = self._context(params)
        mode_id = params.get("modeId")
        if not isinstance(mode_id, str) or mode_id not in self._settings.modes:
            offered = ", ".join(self._settings.modes)
            raise RpcError(
                INVALID_PARAMS, f"mode {mode_id!r} is not offered; the modes are: {offered}"
            )
        context.mode_id = mode_id
        if HubScope.ANSWER not in self._modes.scopes_for(mode_id, self._hub.agent_scopes()):
            # A permission request still out may not be answered any more: withdrawn at once,
            # it resolves as unanswered, as under `session/cancel`.
            self._channel.cancel_permissions(context.session_id)
        self._in_background(
            self._channel.notify_update(context.session_id, self._mapper.current_mode(mode_id))
        )
        return {}

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
            self._run_turn(context, prompt, turn_id),
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
        self._follow(context)  # the hub may have named another project: follow it instead
        return {"stopReason": context.state.finish_turn(proposed).value}

    async def _run_turn(
        self, context: AcpSessionContext, prompt: Sequence[Mapping[str, Any]], turn_id: str
    ) -> StopReason:
        # What the live feed held back between turns goes out before the turn's own updates.
        await self._feed.flush(context.session_id)
        return await self._turn_factory().run(context, prompt, turn_id=turn_id)

    def _cancel(self, params: Mapping[str, Any]) -> None:
        session_id = params.get("sessionId")
        context = self._contexts.get(session_id) if isinstance(session_id, str) else None
        if context is None or context.state.cancel_requested:
            # A repeated cancel (Esc pressed twice, a client that resends) must not cancel the
            # turn again: that would interrupt the settle that reports the hub call's outcome.
            return
        if context.state.request_cancel():
            # Permission requests were out: they resolve as unanswered now, so a client that
            # never answers them cannot hold the turn, and none is ever read as an approval.
            self._channel.cancel_permissions(context.session_id)
        task = self._turns.get(context.session_id)
        if task is not None:
            task.cancel()

    # -- the session's project ------------------------------------------------------------

    async def _attach_folder(self, context: AcpSessionContext) -> None:
        """Follow the project whose repository holds the session's folder, if there is one."""
        try:
            listed = await self._hub.call_tool(
                PROJECTS_TOOL, {}, request_id=f"acp-{context.session_id}-attach"
            )
        except VibeyError as exc:
            await self._say(context, self._unlisted(str(exc)))
            return
        if not listed.ok:
            await self._say(context, self._unlisted(f"the hub answered {listed.status_code}"))
            return
        project = self._project_holding(context.cwd, listed.text)
        if project is not None and context.project_id is None:
            # A turn that already named a project is the later, explicit choice: it stays.
            context.project_id = project
            self._follow(context)

    def _follow(self, context: AcpSessionContext) -> None:
        """Follow the session's project, unless its feed already does."""
        project = context.project_id
        if project is not None and self._followed.get(context.session_id) != project:
            self._followed[context.session_id] = project
            self._feed.attach(context)

    @staticmethod
    def _project_holding(cwd: str, listing: str) -> UUID | None:
        """The project whose repository holds `cwd`; the deepest when repositories nest, the
        first listed (the newest) when two share one. The listing is the hub's data: an entry
        without a UUID and an absolute repository path is passed over."""
        try:
            projects = json.loads(listing)
        except json.JSONDecodeError:
            return None
        if not isinstance(projects, list):
            return None
        folder = PurePath(cwd)
        best: tuple[int, UUID] | None = None
        for project in projects:
            if not isinstance(project, Mapping):
                continue
            repo, raw_id = project.get("repo_path"), project.get("project_id")
            if not isinstance(repo, str) or not isinstance(raw_id, str):
                continue
            root = PurePath(repo)
            if not root.is_absolute() or (root != folder and root not in folder.parents):
                continue
            try:
                project_id = UUID(raw_id)
            except ValueError:
                continue
            if best is None or len(root.parts) > best[0]:
                best = (len(root.parts), project_id)
        return best[1] if best is not None else None

    @staticmethod
    def _unlisted(why: str) -> str:
        return (
            f"vibey could not list the hub's projects to follow the one in this folder ({why}). "
            "`/projects` lists them; a command that names a project follows it."
        )

    # -- helpers --------------------------------------------------------------------------

    async def _say(self, context: AcpSessionContext, text: str) -> None:
        await self._channel.notify_update(context.session_id, self._mapper.agent_text(text))

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
