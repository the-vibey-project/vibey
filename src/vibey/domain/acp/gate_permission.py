# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which open gates an ACP client may answer with `session/request_permission`, and how (SP-ACP).

A gate the hub reports becomes a set of permission options, one per answer the operator may
pick in the editor, each carrying the answer the hub's own parser makes of it
(`HubChat.parse_gate_answer`), so the answer sent is the one the operator saw.

A spend gate is never offered: answering one decides whether money is spent, which the agent
principal may not do and an editor click must not do either (ADR-0046, sub-doctrine 12.d). A
gate is a spend gate when its kind is in `SPEND_GATE_KINDS` *or* the hub flags it so
(`is_spend`, `requires_scope == "spend"`), so a lost or forged flag can only make a gate
stricter, never looser. A gate whose answer is a number (a new cap) is not offered either: a
permission option cannot carry a value. Both get `refusal_text` instead, which tells the
operator where to answer. Pure: no I/O. Declared by `interfaces/gate_permission_interface.py`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from vibey.domain.acp.protocol import PermissionKind
from vibey.domain.errors import LifecycleInvalid
from vibey.domain.hub_chat import ANY_ANSWER_GATE_KINDS, CHOICE_GATE_KINDS, VERDICT_GATE_KINDS
from vibey.domain.hub_scope import SPEND_GATE_KINDS
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface

LEAVE_OPEN: Final = "Leave it open"
"""The option that answers nothing; choosing it leaves the gate open for later."""


@dataclass(frozen=True, slots=True)
class PermissionChoice:
    """One option offered for a gate; `answer` is None for the option that answers nothing."""

    option_id: str
    name: str
    kind: PermissionKind
    answer: Mapping[str, Any] | None

    def option(self) -> dict[str, Any]:
        """The `PermissionOption` this choice is on the wire."""
        return {"optionId": self.option_id, "name": self.name, "kind": self.kind.value}


class GatePermissionMapper:
    """Declared by `interfaces/gate_permission_interface.py::GatePermissionMapperInterface`."""

    def __init__(self, reject_words: tuple[str, ...], chat: HubChatInterface) -> None:
        self._reject_words = frozenset(reject_words)
        self._chat = chat

    def options_for(self, gate: Mapping[str, Any]) -> tuple[PermissionChoice, ...]:
        gate_id = str(gate.get("gate_id") or "")
        kind = str(gate.get("kind") or "")
        if self._spends(gate) or not gate_id:
            return ()
        if kind in VERDICT_GATE_KINDS or kind in CHOICE_GATE_KINDS:
            return self._per_option(gate_id, kind, gate.get("options"))
        if kind == "question":
            return self._pair(gate_id, "Accept the defaults", {"accept_defaults": True})
        if kind in ANY_ANSWER_GATE_KINDS:
            return self._pair(gate_id, "Acknowledge", {})
        return ()

    def refusal_text(self, gate: Mapping[str, Any]) -> str:
        gate_id = gate.get("gate_id")
        kind = gate.get("kind")
        if self._spends(gate):
            return (
                f"Gate {gate_id} ({kind}) spends money, so I cannot answer it. Answer it on the "
                f"host (`vibey answer {gate_id}`) or in the desktop or mobile app."
            )
        return f"Gate {gate_id} ({kind}) needs a value. Answer it with `/answer {gate_id} <value>`."

    @staticmethod
    def _spends(gate: Mapping[str, Any]) -> bool:
        return (
            str(gate.get("kind") or "") in SPEND_GATE_KINDS
            or bool(gate.get("is_spend"))
            or gate.get("requires_scope") == "spend"
        )

    def _per_option(self, gate_id: str, kind: str, options: Any) -> tuple[PermissionChoice, ...]:
        if not isinstance(options, list):
            return ()
        choices: list[PermissionChoice] = []
        for index, option in enumerate(options):
            name = str(option).strip()
            try:
                answer = self._chat.parse_gate_answer(kind, name)
            except LifecycleInvalid:
                continue  # an empty option: nothing an operator could mean by picking it
            rejects = name.lower() in self._reject_words
            choices.append(
                PermissionChoice(
                    option_id=f"{gate_id}:{index}",
                    name=name,
                    kind=PermissionKind.REJECT_ONCE if rejects else PermissionKind.ALLOW_ONCE,
                    answer=answer,
                )
            )
        return tuple(choices)

    @staticmethod
    def _pair(gate_id: str, name: str, answer: Mapping[str, Any]) -> tuple[PermissionChoice, ...]:
        return (
            PermissionChoice(f"{gate_id}:0", name, PermissionKind.ALLOW_ONCE, answer),
            PermissionChoice(f"{gate_id}:1", LEAVE_OPEN, PermissionKind.REJECT_ONCE, None),
        )
