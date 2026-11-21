# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One ACP prompt turn over the hub chat (SP-ACP).

The prompt's text goes to `POST /api/v1/chat/messages` exactly as an operator would type it in
krypton, so the hub's own parser, scope check and tool catalogue decide what runs. The turn
parses the text locally only to learn which tool that is, so the session's mode can refuse it
before anything reaches the hub: the hub enforces the agent principal's scopes, but only this
process knows the mode. The hub call is one tool call on the client's screen: `pending`, then
`in_progress`, then `completed` or `failed`, then the hub's reply as a message.

Only the text the user typed is parsed for a command and its options. An embedded resource is
data: its text is sent only as the description a new project takes (`/new`, `/ask`), after a
blank line, and is otherwise dropped with one message saying so. A prompt of resources alone
therefore runs nothing.

After the hub's reply, the open gates it listed become the session's (so the local parse reads
`/answer 1` and a bare number as the hub does), and the ones the session has not seen yet are
put to the client by `AcpGatePrompterInterface`: answerable ones as permission requests, spend
ones as a message saying to answer them on the host. A bare number is announced as a gate
answer, the stricter of its two readings, and renamed for what the hub actually ran.

A cancel is the task running `run` being cancelled. A hub call already in flight cannot be
taken back, so the turn waits up to `[acp] cancel_grace_seconds` for its real outcome before
saying the hub may still apply it, names the request id, and lets the cancel propagate.
Declared by `interfaces/acp_prompt_turn_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final

from vibey.application.acp.dto import AcpSessionContext, HubTurn
from vibey.application.acp.interfaces.acp_gate_prompter_interface import (
    AcpGatePrompterInterface,
)
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.protocol import StopReason, ToolCallStatus
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import LifecycleInvalid, VibeyError
from vibey.domain.host_tools import MAX_RESPONSE_CHARS, HostTool
from vibey.domain.hub_chat import ChatSlashSpec
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface

ANSWER_GATE_TOOL: Final = "vibey_answer_gate"
"""The tool the hub runs when it reads a bare number as an answer to the oldest open gate."""
FREE_TEXT_INTENTS: Final = frozenset({"start_project"})
"""The intents whose free text an embedded resource may extend: `/new` and `/ask` take the
rest of the message as the project's description, and neither reads a flag from it."""


@dataclass(slots=True)
class _HubCall:
    """How far one turn's hub call got, so a cancel reports it once and truthfully."""

    call_id: str
    request_id: str
    tool: HostTool
    """The tool the call was announced as."""
    announcing: asyncio.Task[None] | None = None
    """The `pending` frame's write. Once started it runs to the end even if the turn is
    cancelled, so a frame that reached the client is always closed by the settle."""
    task: asyncio.Task[HubTurn] | None = None
    reported: bool = False


class AcpPromptTurn:
    """Declared by `interfaces/acp_prompt_turn_interface.py::AcpPromptTurnInterface`."""

    _STRAYS: ClassVar[set[asyncio.Task[HubTurn]]] = set()
    """Hub calls a cancel stopped waiting for. The loop holds tasks only weakly, so these are
    held here until they finish; each one's outcome is then read and dropped."""

    def __init__(
        self,
        channel: ClientChannelInterface,
        hub: AcpHubPortInterface,
        settings: AcpSettings,
        modes: AcpModesInterface,
        mapper: AcpUpdateMapperInterface,
        chat: HubChatInterface,
        tools: HostToolsInterface,
        gates: AcpGatePrompterInterface,
        *,
        max_result_chars: int = MAX_RESPONSE_CHARS,
    ) -> None:
        self._gates = gates
        self._channel = channel
        self._hub = hub
        self._settings = settings
        self._modes = modes
        self._mapper = mapper
        self._chat = chat
        self._tools = tools
        self._max_result_chars = max_result_chars

    async def run(
        self, session: AcpSessionContext, prompt: Sequence[Mapping[str, Any]], *, turn_id: str
    ) -> StopReason:
        typed, attached = self._blocks(prompt)
        try:
            # The command is read from what the user typed and nothing else: an embedded
            # resource is data, so its text can never choose a command or a flag.
            known = session.open_gates
            intent = self._chat.parse(typed, project_id=session.project_id, open_gates=known)
            carried = intent.kind in FREE_TEXT_INTENTS
            message = "\n\n".join([typed, *attached]) if carried else typed
            # The length bound, over the whole message.
            self._chat.parse(message, project_id=session.project_id, open_gates=known)
        except LifecycleInvalid as exc:
            await self._say(session, str(exc))
            return StopReason.END_TURN
        if attached and not carried:
            await self._say(session, self._dropped(len(attached)))
        if intent.tool_name is None:
            # Only `/help` names no tool; it needs no hub and no scope.
            await self._say(session, self._chat.help_text())
            return StopReason.END_TURN
        tool = self._admit(session, intent.tool_name, typed)
        if isinstance(tool, str):
            await self._say(session, tool)
            return StopReason.END_TURN
        call = _HubCall(
            call_id=f"{turn_id}-1", request_id=f"acp-{session.session_id}-{turn_id}", tool=tool
        )
        try:
            return await self._call_hub(session, message, call, turn_id=turn_id)
        except asyncio.CancelledError:
            await self._settle(session, call)
            raise

    # -- the hub call ---------------------------------------------------------------------

    async def _call_hub(
        self, session: AcpSessionContext, message: str, call: _HubCall, *, turn_id: str
    ) -> StopReason:
        title = self._title(call.tool)
        kind = self._mapper.tool_kind_for(call.tool.scope)
        call.announcing = asyncio.ensure_future(
            self._notify(
                session, self._mapper.tool_call(call.call_id, title, kind, {"message": message})
            )
        )
        await asyncio.shield(call.announcing)
        await self._notify(
            session, self._mapper.tool_call_update(call.call_id, ToolCallStatus.IN_PROGRESS)
        )
        call.task = asyncio.create_task(
            self._hub.chat(message, project_id=session.project_id, request_id=call.request_id)
        )
        try:
            turn = await asyncio.shield(call.task)
        except Exception as exc:
            # Any failure, not only a `VibeyError`: an unexpected one must still close the
            # tool call on the client's screen and end the turn, never leave it spinning.
            call.reported = True
            failure = self._describe(exc)
            await self._notify(
                session,
                self._mapper.tool_call_update(call.call_id, ToolCallStatus.FAILED, failure),
            )
            await self._say(session, failure)
            return StopReason.END_TURN
        if turn.project_id is not None:
            session.project_id = turn.project_id
        session.open_gates = turn.gates
        call.reported = True
        await self._notify(session, self._completed(call, turn))
        await self._say(session, turn.reply)
        await self._gates.offer(session, turn.gates, turn_id=turn_id)
        return StopReason.END_TURN

    async def _settle(self, session: AcpSessionContext, call: _HubCall) -> None:
        """Close an announced tool call the cancel interrupted, once and truthfully."""
        if call.reported or call.announcing is None:
            return
        await asyncio.wait({call.announcing})  # the pending frame goes out first
        if call.task is None:
            await self._notify(
                session,
                self._mapper.tool_call_update(
                    call.call_id, ToolCallStatus.FAILED, "cancelled before it was sent to the hub"
                ),
            )
            return
        done, _ = await asyncio.wait({call.task}, timeout=self._settings.cancel_grace_seconds)
        if not done:
            # The call keeps running in its thread; its outcome is read, not reported.
            self._STRAYS.add(call.task)
            call.task.add_done_callback(self._retrieve)
            await self._notify(
                session,
                self._mapper.tool_call_update(
                    call.call_id,
                    ToolCallStatus.FAILED,
                    "cancelled before the hub answered; the hub may still apply it "
                    f"(request id {call.request_id})",
                ),
            )
            return
        error = call.task.exception()
        update = (
            self._mapper.tool_call_update(
                call.call_id, ToolCallStatus.FAILED, self._describe(error)
            )
            if error is not None
            else self._completed(call, call.task.result())
        )
        await self._notify(session, update)

    @classmethod
    def _retrieve(cls, task: asyncio.Task[HubTurn]) -> None:
        # Reading the outcome keeps asyncio from logging "exception was never retrieved" for a
        # call whose failure the turn already told the client it could not wait for.
        cls._STRAYS.discard(task)
        with contextlib.suppress(asyncio.CancelledError):
            task.exception()

    @staticmethod
    def _describe(error: BaseException) -> str:
        """A `VibeyError`'s own message; any other failure named by its type as well."""
        return str(error) if isinstance(error, VibeyError) else f"{type(error).__name__}: {error}"

    def _completed(self, call: _HubCall, turn: HubTurn) -> dict[str, Any]:
        if not turn.tool_calls:
            return self._mapper.tool_call_update(call.call_id, ToolCallStatus.COMPLETED)
        first = turn.tool_calls[0]
        rendered = json.dumps(first.get("result"), indent=2, default=str)
        text = self._tools.truncate(rendered, limit=self._max_result_chars)
        ran = self._tools.by_name(str(first.get("name")))
        if ran is None or ran.name == call.tool.name:
            return self._mapper.tool_call_update(call.call_id, ToolCallStatus.COMPLETED, text)
        # Announced as one reading of the message (a bare number as a gate answer), run as
        # another: the client is told what actually ran.
        return self._mapper.tool_call_update(
            call.call_id,
            ToolCallStatus.COMPLETED,
            text,
            title=self._title(ran),
            kind=self._mapper.tool_kind_for(ran.scope),
        )

    # -- the session mode -----------------------------------------------------------------

    def _admit(self, session: AcpSessionContext, tool_name: str, message: str) -> HostTool | str:
        """The tool this message is announced as, or why the session's mode may not run it."""
        names = [tool_name]
        if message.strip().isdigit():
            # The hub reads a bare number against its own, fresher list of open gates: as an
            # answer to the oldest one, or a projects query when none matches. Hold it to both
            # readings, and announce it as the stricter one (the last name).
            names.append(ANSWER_GATE_TOOL)
        granted = self._hub.agent_scopes()
        allowed = self._modes.scopes_for(session.mode_id, granted)
        admitted: list[HostTool] = []
        for name in names:
            tool = self._tools.by_name(name)
            if tool is None:
                return f"vibey has no tool named `{name}`, so it cannot run that."
            if tool.scope not in allowed:
                return self._needs(tool, granted)
            admitted.append(tool)
        return admitted[-1]

    def _needs(self, tool: HostTool, granted: frozenset[HubScope]) -> str:
        spec = self._spec(tool)
        command = f"/{spec.slash}" if spec is not None else tool.name
        for mode in self._modes.available():
            if tool.scope in self._modes.scopes_for(mode.id, granted):
                return f"`{command}` needs {mode.id} mode; switch with the mode picker."
        return (
            f"`{command}` needs the `{tool.scope.value}` scope, which this hub does not grant "
            "to agents ([hub] agent_scopes in vibey.toml)."
        )

    def _title(self, tool: HostTool) -> str:
        spec = self._spec(tool)
        return spec.title if spec is not None else tool.title

    def _spec(self, tool: HostTool) -> ChatSlashSpec | None:
        """The `/` command that runs `tool`, if the chat offers one."""
        for spec in self._chat.slash_commands():
            if spec.tool_name == tool.name:
                return spec
        return None

    # -- prompt and output ----------------------------------------------------------------

    @staticmethod
    def _blocks(prompt: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
        """What the user typed (text blocks joined by a newline) and each embedded resource's
        text, kept apart: only the first is ever parsed for a command."""
        typed: list[str] = []
        attached: list[str] = []
        for block in prompt:
            kind = block.get("type")
            if kind == "text" and isinstance(block.get("text"), str):
                typed.append(block["text"])
            elif kind == "resource":
                resource = block.get("resource")
                if isinstance(resource, Mapping) and isinstance(resource.get("text"), str):
                    attached.append(resource["text"])
        return "\n".join(typed), attached

    @staticmethod
    def _dropped(count: int) -> str:
        return (
            f"vibey did not send the {count} attached resource(s) to the hub: attached text is "
            "used only as the description of a new project (`/new`, `/ask`), never as a "
            "command or an option."
        )

    async def _say(self, session: AcpSessionContext, text: str) -> None:
        await self._notify(session, self._mapper.agent_text(text))

    async def _notify(self, session: AcpSessionContext, update: Mapping[str, Any]) -> None:
        await self._channel.notify_update(session.session_id, update)
