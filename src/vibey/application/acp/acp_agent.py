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

Each session's log is kept through the hub (`AcpSessionJournalInterface`, written behind and in
order): what a prompt turn showed, the operator's messages, mode changes, the project it
follows, and its close. `session/load` shows that log again before it answers, through
`AcpSessionReplayInterface`: every stored event is untrusted data on its way back out, rebuilt
from checked fields with its text through `UntrustedTextInterface`, never a command, a
permission request or a gate. `session/resume` restores the same mode and project without
showing anything. Both then send the commands, keep the same session context (and so the same
`offered_gates`) when the session is already live here, and follow its project. A load or resume
names a session only by its id (in the shape vibey mints), the agent principal and the folder it
was kept under: any other answers `RESOURCE_NOT_FOUND`, however it differs. `session/close`
ends the session in this process: it cancels its turn and withdraws its permission requests,
stops its live feed and records the close; a later prompt finds no session.

`session/set_mode` applies at once, in the middle of a turn too. The prompt turn reads the mode
again right before its hub call and the gate prompter before each gate and before it sends an
answer, so a switch to observe stops what has not been sent yet; a permission request still out
is withdrawn at once, and an answer picked after the switch answers nothing. A switch to drive
offers the gates held back in observe on the next turn.

Declared by `interfaces/acp_agent_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable, Coroutine, Mapping, Sequence
from pathlib import PurePath
from typing import Any, Final
from uuid import UUID

from vibey.application.acp.dto import AcpSessionContext, SessionEvent, SessionSummary
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.acp_live_feed_interface import AcpLiveFeedInterface
from vibey.application.acp.interfaces.acp_prompt_turn_interface import AcpPromptTurnInterface
from vibey.application.acp.interfaces.acp_session_journal_interface import (
    AcpSessionJournalInterface,
)
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.session_replay_interface import AcpSessionReplayInterface
from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.protocol import (
    AUTHENTICATE,
    INITIALIZE,
    PROTOCOL_VERSION,
    RESOURCE_NOT_FOUND,
    SESSION_CANCEL,
    SESSION_CLOSE,
    SESSION_LIST,
    SESSION_LOAD,
    SESSION_NEW,
    SESSION_PROMPT,
    SESSION_RESUME,
    SESSION_SET_MODE,
    StopReason,
)
from vibey.domain.acp.session_log import InvalidSessionCursor, SessionEventKind, UnknownAcpSession
from vibey.domain.acp.session_replay import SESSION_REPLAY
from vibey.domain.acp.session_state import AcpSessionState, TurnAlreadyRunning
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface
from vibey.domain.jsonrpc_errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    RpcError,
)

type TurnFactory = Callable[[], AcpPromptTurnInterface]

PROJECTS_TOOL: Final = "vibey_projects"
EMPTY_SUMMARY: Final = SessionSummary(newest_seq=0, mode=None, attach=None, title=None)
"""What a live session the hub does not keep loads as: nothing to show, nothing to fold."""
"""The hub tool that lists every project with its repository (`repo_path`)."""
_LOG: Final = logging.getLogger(__name__)


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
        journal: AcpSessionJournalInterface,
        version: str,
        new_id: Callable[[], str],
        replay: AcpSessionReplayInterface = SESSION_REPLAY,
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
        self._journal = journal
        self._replay = replay
        self._version = version
        self._new_id = new_id
        self._contexts: dict[str, AcpSessionContext] = {}
        self._turns: dict[str, asyncio.Task[StopReason]] = {}
        self._background: set[asyncio.Task[None]] = set()
        self._followed: dict[str, UUID] = {}
        """The project each session's live feed follows."""
        self._kept_project: dict[str, UUID] = {}
        """The project each session's log last recorded it attached to."""
        self._locks: dict[str, asyncio.Lock] = {}
        """One per session a load or a close has named: they run one at a time."""

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
        if method == SESSION_LOAD:
            return await self._load(params, replay=True)
        if method == SESSION_RESUME:
            return await self._load(params, replay=False)
        if method == SESSION_LIST:
            return await self._list(params)
        if method == SESSION_CLOSE:
            return await self._close(params)
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
        # What is still queued for the sessions' logs goes to the hub before the process ends;
        # what the hub's rate limit holds back is waited for, within a bound, and never lost
        # without a word.
        await self._journal.drain()

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
        self._journal.open(session_id, cwd)
        self._in_background(self._journal.flush())
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
        self._record(context.session_id, SessionEventKind.MODE, {"modeId": mode_id})
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
        self._keep_prompt(context, prompt)
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
        self._in_background(self._journal.flush())
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

    # -- the session's log ---------------------------------------------------------------

    async def _load(self, params: Mapping[str, Any], *, replay: bool) -> dict[str, Any]:
        """`session/load` (`replay`: show the newest of the log, then answer) or
        `session/resume`. One at a time per session, and never beside its close: the peer runs
        each request in a task of its own, so two loads of one id, or a close during a load,
        would otherwise each install a context of their own, or put back a closed one."""
        session_id, cwd = params.get("sessionId"), params.get("cwd")
        if not isinstance(cwd, str) or not PurePath(cwd).is_absolute():
            raise RpcError(INVALID_PARAMS, "loading or resuming a session needs an absolute cwd")
        if not isinstance(session_id, str) or not self._replay.valid_session_id(session_id):
            raise self._no_session()
        async with self._session_lock(session_id):
            return await self._load_held(session_id, cwd, replay=replay)

    async def _load_held(self, session_id: str, cwd: str, *, replay: bool) -> dict[str, Any]:
        live = self._contexts.get(session_id)
        if live is not None and live.cwd != cwd:
            raise self._no_session()
        if live is not None and live.state.turn_active:
            raise RpcError(
                INVALID_REQUEST, "a turn is running in this session: load it once the turn ends"
            )
        # What this process still holds of any log goes first -- a live session's, or the close
        # of one closed a moment ago -- so the hub has all of it.
        await self._journal.flush()
        summary = await self._read(
            self._hub.session_summary(session_id, cwd=cwd), live, EMPTY_SUMMARY
        )
        start = max(summary.newest_seq - self._settings.replay_events_max, 0)
        events: tuple[SessionEvent, ...] = ()
        if replay and summary.newest_seq:
            events = await self._read(
                self._hub.session_events(session_id, start, cwd=cwd), live, ()
            )
        context = live if live is not None else self._fold(session_id, cwd, summary)
        if replay and events and start:
            await self._say(
                context,
                f"Showing this session's newest {self._settings.replay_events_max} events; the "
                f"{start} before them are kept but not shown (`[acp] replay_events_max`).",
            )
        for event in events:
            update = self._replay.replay(event.kind, event.payload, modes=self._settings.modes)
            if update is not None:
                await self._channel.notify_update(session_id, update)
        self._journal.resume(session_id, summary.newest_seq)
        # A live session keeps its own context, so `offered_gates` stays the one object the
        # prompter writes and the live feed reads.
        self._contexts[session_id] = context
        if live is None and context.project_id is not None:
            self._kept_project[session_id] = context.project_id
        self._in_background(self._reopened(context))
        return {"modes": self._modes.session_modes(context.mode_id)}

    async def _read[T](
        self, reading: Coroutine[Any, Any, T], live: AcpSessionContext | None, empty: T
    ) -> T:
        """One read of a session's log, its refusals as the client is told them. A live session
        the hub does not keep (not prompted yet, or kept only here) reads as `empty`."""
        try:
            return await reading
        except UnknownAcpSession as exc:
            if live is None:
                raise self._no_session() from exc
            return empty
        except VibeyError as exc:
            raise RpcError(
                INTERNAL_ERROR, f"vibey could not read the session from the hub: {exc}"
            ) from exc

    def _fold(self, session_id: str, cwd: str, summary: SessionSummary) -> AcpSessionContext:
        """The session as its log leaves it: its newest mode this vibey offers, the project it
        last attached to, its title. A close in the log does not stay: a load reopens it."""
        context = AcpSessionContext(
            session_id=session_id,
            state=AcpSessionState(session_id),
            mode_id=self._replay.mode(summary.mode, modes=self._settings.modes)
            or self._settings.default_mode,
            project_id=self._replay.project(summary.attach),
            offered_gates=set(),
            cwd=cwd,
        )
        title = summary.title.get("title") if summary.title is not None else None
        if isinstance(title, str):
            context.title = self._replay.title(title, limit=self._settings.live_message_chars)
        return context

    async def _reopened(self, context: AcpSessionContext) -> None:
        """What follows a load's or a resume's answer: the commands, then the project."""
        await self._channel.notify_update(
            context.session_id, self._mapper.available_commands(self._chat.slash_commands())
        )
        if context.project_id is not None:
            self._follow(context)
            await self._journal.flush()
        else:
            await self._attach_folder(context)

    async def _list(self, params: Mapping[str, Any]) -> dict[str, Any]:
        cwd, cursor = params.get("cwd"), params.get("cursor")
        if cwd is not None and (not isinstance(cwd, str) or not PurePath(cwd).is_absolute()):
            raise RpcError(INVALID_PARAMS, "session/list takes an absolute cwd, or none")
        if cursor is not None and not isinstance(cursor, str):
            raise RpcError(INVALID_PARAMS, "session/list takes a cursor it was given, or none")
        try:
            records, next_cursor = await self._hub.list_sessions(cwd=cwd, cursor=cursor)
        except InvalidSessionCursor as exc:
            raise RpcError(INVALID_PARAMS, str(exc)) from exc
        except VibeyError as exc:
            raise RpcError(
                INTERNAL_ERROR, f"vibey could not list the sessions from the hub: {exc}"
            ) from exc
        sessions: list[dict[str, Any]] = []
        for record in records:
            # The hub's data: a record that is not a session vibey would have kept is passed over.
            if not self._replay.valid_session_id(record.session_id):
                continue
            folder = self._replay.folder(record.cwd)
            if folder is None:
                continue
            info: dict[str, Any] = {
                "sessionId": record.session_id,
                "cwd": folder,
                "updatedAt": record.updated_at.isoformat(),
            }
            title = (
                self._replay.title(record.title, limit=self._settings.live_message_chars)
                if record.title is not None
                else None
            )
            if title is not None:
                info["title"] = title
            sessions.append(info)
        result: dict[str, Any] = {"sessions": sessions}
        if next_cursor is not None:
            result["nextCursor"] = next_cursor
        return result

    async def _close(self, params: Mapping[str, Any]) -> dict[str, Any]:
        """End the session here: its turn is cancelled, its permission requests withdrawn, its
        feed stopped and its close recorded. An unknown or already closed one answers `{}`. A
        load of the same session in progress finishes first: the close then ends what it put
        in place, and nothing closed is ever put back."""
        session_id = params.get("sessionId")
        if not isinstance(session_id, str) or (
            session_id not in self._contexts and session_id not in self._locks
        ):
            return {}
        async with self._session_lock(session_id):
            return self._close_held(session_id)

    def _close_held(self, session_id: str) -> dict[str, Any]:
        context = self._contexts.pop(session_id, None)
        if context is None:
            return {}
        context.state.close()
        # Withdrawn here: `session/cancel` finds no session any more, so it could not.
        self._channel.cancel_permissions(context.session_id)
        task = self._turns.get(context.session_id)
        if task is not None:
            task.cancel()
        self._feed.detach(context.session_id)
        self._followed.pop(context.session_id, None)
        self._kept_project.pop(context.session_id, None)
        self._record(context.session_id, SessionEventKind.CLOSED, {})
        return {}

    def _keep_prompt(self, context: AcpSessionContext, prompt: Sequence[Mapping[str, Any]]) -> None:
        """Keep what the operator typed, and the session's title from its first message."""
        typed = "\n".join(
            block["text"]
            for block in prompt
            if block.get("type") == "text" and isinstance(block.get("text"), str)
        )
        if context.title is None:
            context.title = self._replay.title(typed, limit=self._settings.live_message_chars)
            if context.title is not None:
                self._journal.record(
                    context.session_id, SessionEventKind.TITLE, {"title": context.title}
                )
        self._journal.record(
            context.session_id, SessionEventKind.USER_MESSAGE, self._replay.user_message(typed)
        )

    def _record(self, session_id: str, kind: SessionEventKind, payload: Mapping[str, Any]) -> None:
        """Keep one event and send it to the hub behind the request."""
        if self._journal.record(session_id, kind, payload):
            self._in_background(self._journal.flush())

    def _session_lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    @staticmethod
    def _no_session() -> RpcError:
        # The same words for a malformed id, an unknown one, another principal's and another
        # folder's: a guessed id learns nothing.
        return RpcError(RESOURCE_NOT_FOUND, "no such session for this folder")

    # -- the session's project ------------------------------------------------------------

    async def _attach_folder(self, context: AcpSessionContext) -> None:
        """Follow the project whose repository holds the session's folder, if there is one."""
        try:
            listed = await self._hub.call_tool(
                PROJECTS_TOOL, {}, request_id=f"acp-{context.session_id}-attach"
            )
        except VibeyError as exc:
            limit = self._settings.live_message_chars
            await self._say(context, self._unlisted(self._mapper.untrusted(str(exc), limit=limit)))
            return
        except Exception as exc:
            # A defect, not an unreachable hub: logged with its traceback and said once, so the
            # folder is never silently left unfollowed.
            _LOG.exception("listing the hub's projects for session %s failed", context.session_id)
            await self._say(
                context,
                f"vibey could not follow this folder's project: {type(exc).__name__}. The "
                "agent's log on stderr has the details; `/projects` lists them.",
            )
            return
        if not listed.ok:
            await self._say(context, self._unlisted(f"the hub answered {listed.status_code}"))
            return
        found = self._project_holding(context.cwd, listed.text)
        if found is not None and context.project_id is None and not context.state.closed:
            # A turn that already named a project is the later, explicit choice: it stays.
            project, name, repo = found
            context.project_id = project
            self._follow(context)
            self._in_background(self._journal.flush())
            # The folder chose the default target of /start, /pause and /abandon: say which.
            limit = self._settings.live_message_chars
            await self._say(
                context,
                f"Following project {self._mapper.untrusted(name, limit=limit)} ({project}) "
                f"from {self._mapper.untrusted(repo, limit=limit)}. A bare `/start`, `/pause` "
                "or `/abandon` in this session now targets it.",
            )

    def _follow(self, context: AcpSessionContext) -> None:
        """Follow the session's project, unless its feed already does or it was closed."""
        project = context.project_id
        if context.state.closed or project is None:
            return
        if self._kept_project.get(context.session_id) != project:
            self._kept_project[context.session_id] = project
            self._record(context.session_id, SessionEventKind.ATTACH, {"projectId": str(project)})
        if self._followed.get(context.session_id) != project:
            self._followed[context.session_id] = project
            self._feed.attach(context)

    @staticmethod
    def _project_holding(cwd: str, listing: str) -> tuple[UUID, str, str] | None:
        """The project (id, name, repository) whose repository holds `cwd`; the deepest when
        repositories nest, the first listed (the newest) when two share one. The listing is the
        hub's data: an entry without a UUID and an absolute repository path is passed over. A
        `cwd` with a `..` part matches nothing: compared as written, it could name a folder
        outside the repository it seems to be in."""
        try:
            projects = json.loads(listing)
        except json.JSONDecodeError:
            return None
        if not isinstance(projects, list):
            return None
        folder = PurePath(cwd)
        if ".." in folder.parts:
            return None
        best: tuple[int, UUID, str, str] | None = None
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
                name = project.get("name")
                best = (len(root.parts), project_id, name if isinstance(name, str) else "", repo)
        return best[1:] if best is not None else None

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
        task.add_done_callback(self._reap)

    def _reap(self, task: asyncio.Task[None]) -> None:
        # Every background task's outcome is read: a failure (a client gone mid-update, a
        # defect) is logged with its traceback, never left "never retrieved".
        self._background.discard(task)
        with contextlib.suppress(asyncio.CancelledError):
            error = task.exception()
            if error is not None:
                _LOG.error("a background ACP update failed", exc_info=error)
