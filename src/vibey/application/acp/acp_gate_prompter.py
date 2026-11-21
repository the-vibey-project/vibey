# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Open gates put to an ACP client as permission requests (SP-ACP, ADR-0046).

After a prompt turn's hub reply, each open gate the session has not seen yet, oldest first and
at most `[acp] max_gate_prompts_per_turn` of them, is put to the client once:

- An answerable gate is a tool call titled "Answer gate: <prompt>" plus one
  `session/request_permission` whose options `GatePermissionMapper` builds. The option the
  operator picks answers the gate through the hub (`vibey_answer_gate`, as the scoped agent
  principal, request id `acp-<session>-<gate>` so a replay is the same answer). "Leave it
  open", a cancel, a timeout, a failure or an option the gate never offered answers nothing:
  silence is not consent (sub-doctrine 12.d), and nothing is ever answered on the operator's
  behalf.
- A spend gate, the deployment opt-in, a gate whose answer is a value and a kind the mapper
  does not know are each a message saying where to answer it. Money and real infrastructure
  are answered on the host, never from an editor.
- A gate whose id is not a UUID is never shown or used; one message per turn counts them.

Every frame that announces or closes a gate's tool call runs to the end even if the turn is
cancelled, so the close the client was promised is sent once and never dropped.

Nothing is offered while the session's mode, or the hub's grant to agents, does not include
`answer`: an observe session never answers a gate, and the gates are offered once it can.
A cancel closes the gate being asked truthfully: an answer already sent gets
`[acp] cancel_grace_seconds` to come back before the client is told the hub may still apply it.
Declared by `interfaces/acp_gate_prompter_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final

from vibey.application.acp.dto import AcpSessionContext, HubToolResult
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.gate_permission import PermissionChoice
from vibey.domain.acp.interfaces.gate_permission_interface import GatePermissionMapperInterface
from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.protocol import ToolCallStatus, ToolKind
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import MAX_RESPONSE_CHARS
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface

ANSWER_GATE_TOOL: Final = "vibey_answer_gate"
LEFT_OPEN: Final = "left open; nothing was answered"
"""How a gate the operator did not answer is closed: picked "Leave it open", cancelled, timed
out, failed, or answered with an option the gate never offered."""


@dataclass(slots=True)
class _GateCall:
    """How far asking one gate got, so a cancel closes it once and truthfully."""

    call_id: str
    request_id: str
    announcing: asyncio.Task[None]
    """The `pending` frame's write; it runs to the end even if the turn is cancelled."""
    answering: asyncio.Task[HubToolResult] | None = None
    closing: asyncio.Task[None] | None = None
    """The closing frame's write; like the `pending` frame it runs to the end under a cancel,
    so the close is sent once and never dropped."""


class AcpGatePrompter:
    """Declared by `interfaces/acp_gate_prompter_interface.py::AcpGatePrompterInterface`."""

    _STRAYS: ClassVar[set[asyncio.Task[HubToolResult]]] = set()
    """Answers a cancel stopped waiting for, held until they finish and their outcome read."""

    def __init__(
        self,
        channel: ClientChannelInterface,
        hub: AcpHubPortInterface,
        settings: AcpSettings,
        modes: AcpModesInterface,
        mapper: AcpUpdateMapperInterface,
        gates: GatePermissionMapperInterface,
        tools: HostToolsInterface,
        *,
        max_result_chars: int = MAX_RESPONSE_CHARS,
    ) -> None:
        self._channel = channel
        self._hub = hub
        self._settings = settings
        self._modes = modes
        self._mapper = mapper
        self._gates = gates
        self._tools = tools
        self._max_result_chars = max_result_chars

    async def offer(
        self, session: AcpSessionContext, gates: Sequence[Mapping[str, Any]], *, turn_id: str
    ) -> None:
        allowed = self._modes.scopes_for(session.mode_id, self._hub.agent_scopes())
        if HubScope.ANSWER not in allowed:
            return
        offered = 0
        invalid = 0
        for gate in gates:
            gate_id = self._gates.gate_id(gate)
            if gate_id is None:
                # Never shown, never used: an id that is not a UUID could be anything.
                key = f"invalid:{gate.get('gate_id')!r}"
                if key not in session.offered_gates:
                    session.offered_gates.add(key)
                    invalid += 1
                continue
            if gate_id in session.offered_gates:
                continue
            if offered >= self._settings.max_gate_prompts_per_turn:
                break
            offered += 1
            # Marked before it is asked: a gate is put to the client once, however it ends.
            session.offered_gates.add(gate_id)
            choices = self._gates.options_for(gate)
            if not choices:
                refusal = self._gates.refusal_text({**gate, "gate_id": gate_id})
                await self._notify(session, self._mapper.agent_text(refusal))
                continue
            call_id = f"{turn_id}-gate-{gate_id}"
            call = _GateCall(
                call_id=call_id,
                request_id=f"acp-{session.session_id}-{gate_id}",
                announcing=asyncio.ensure_future(self._announce(session, gate, gate_id, call_id)),
            )
            try:
                await self._ask(session, gate_id, choices, call)
            except asyncio.CancelledError:
                await self._settle(session, gate_id, call)
                raise
        if invalid:
            await self._notify(
                session,
                self._mapper.agent_text(
                    f"The hub listed {invalid} gate(s) whose id is not a UUID, so I did not "
                    "offer them. Check `vibey gates` on the host."
                ),
            )

    async def _ask(
        self,
        session: AcpSessionContext,
        gate_id: str,
        choices: tuple[PermissionChoice, ...],
        call: _GateCall,
    ) -> None:
        await asyncio.shield(call.announcing)
        session.state.register_permission(call.call_id)
        try:
            selected = await self._channel.request_permission(
                session.session_id,
                {"toolCallId": call.call_id},
                [choice.option() for choice in choices],
                timeout=self._settings.permission_timeout_seconds,
            )
        finally:
            session.state.resolve_permission(call.call_id)
        # Only an option this gate offered can answer it; anything else is no answer at all.
        choice = next((c for c in choices if c.option_id == selected), None)
        if choice is None or choice.answer is None:
            await self._fail(session, call, LEFT_OPEN)
            return
        await self._notify(
            session, self._mapper.tool_call_update(call.call_id, ToolCallStatus.IN_PROGRESS)
        )
        call.answering = asyncio.create_task(
            self._hub.call_tool(
                ANSWER_GATE_TOOL,
                {"gate_id": gate_id, "answer": dict(choice.answer)},
                request_id=call.request_id,
            )
        )
        try:
            result = await asyncio.shield(call.answering)
        except Exception as exc:
            await self._fail(session, call, self._describe(exc))
            return
        await self._close(session, call, self._answered(session, gate_id, call.call_id, result))

    async def _announce(
        self, session: AcpSessionContext, gate: Mapping[str, Any], gate_id: str, call_id: str
    ) -> None:
        prompt = str(gate.get("prompt") or "")
        await self._notify(
            session,
            self._mapper.tool_call(
                call_id,
                f"Answer gate: {prompt}",
                ToolKind.OTHER,
                {"gate_id": gate_id, "kind": gate.get("kind"), "prompt": prompt},
            ),
        )

    async def _settle(self, session: AcpSessionContext, gate_id: str, call: _GateCall) -> None:
        """Close a gate's tool call the cancel interrupted, once and truthfully."""
        if call.closing is not None:
            await asyncio.wait({call.closing})  # already closing: let that frame go out
            return
        await asyncio.wait({call.announcing})  # the pending frame goes out first
        if call.answering is None:
            await self._fail(session, call, LEFT_OPEN)
            return
        done, _ = await asyncio.wait({call.answering}, timeout=self._settings.cancel_grace_seconds)
        if not done:
            self._STRAYS.add(call.answering)
            call.answering.add_done_callback(self._retrieve)
            await self._fail(
                session,
                call,
                "cancelled before the hub answered; the hub may still apply it "
                f"(request id {call.request_id})",
            )
            return
        error = call.answering.exception()
        if error is not None:
            await self._fail(session, call, self._describe(error))
            return
        answered = self._answered(session, gate_id, call.call_id, call.answering.result())
        await self._close(session, call, answered)

    def _answered(
        self, session: AcpSessionContext, gate_id: str, call_id: str, result: HubToolResult
    ) -> dict[str, Any]:
        if result.ok:
            # Answered: the local view of open gates drops it, as the hub's list now does.
            session.open_gates = tuple(
                g for g in session.open_gates if self._gates.gate_id(g) != gate_id
            )
            text = self._tools.truncate(result.text, limit=self._max_result_chars)
            return self._mapper.tool_call_update(call_id, ToolCallStatus.COMPLETED, text)
        refused = self._tools.truncate(
            f"hub refused ({result.status_code}): {result.text}", limit=self._max_result_chars
        )
        return self._mapper.tool_call_update(call_id, ToolCallStatus.FAILED, refused)

    @classmethod
    def _retrieve(cls, task: asyncio.Task[HubToolResult]) -> None:
        cls._STRAYS.discard(task)
        with contextlib.suppress(asyncio.CancelledError):
            task.exception()

    @staticmethod
    def _describe(error: BaseException) -> str:
        """A `VibeyError`'s own message; any other failure named by its type as well."""
        return str(error) if isinstance(error, VibeyError) else f"{type(error).__name__}: {error}"

    async def _fail(self, session: AcpSessionContext, call: _GateCall, text: str) -> None:
        update = self._mapper.tool_call_update(call.call_id, ToolCallStatus.FAILED, text)
        await self._close(session, call, update)

    async def _close(
        self, session: AcpSessionContext, call: _GateCall, update: Mapping[str, Any]
    ) -> None:
        call.closing = asyncio.ensure_future(self._notify(session, update))
        await asyncio.shield(call.closing)

    async def _notify(self, session: AcpSessionContext, update: Mapping[str, Any]) -> None:
        await self._channel.notify_update(session.session_id, update)
