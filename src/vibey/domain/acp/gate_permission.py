# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which open gates an ACP client may answer with `session/request_permission`, and how (SP-ACP).

A gate the hub reports becomes a set of permission options: one per answer the operator may
pick in the editor, then the agent's own "Leave it open", which answers nothing. Every gate
offered has that way out.

Gate text is untrusted data written by workers and models. Three rules keep it data:

- An answer is built from an option's label alone (`{"choice": label}`, `{"verdict": label}`).
  The label is never parsed, so a label that looks like JSON cannot become structure in the
  answer the hub records.
- Every option the gate supplies is shown under vibey's own prefix, "Answer: <label>", whatever
  it says, so none can pass for one of vibey's options ("Leave it open" above all).
- An option sends exactly what it shows. A gate any of whose options carries something the
  operator cannot see -- a control or format character (a zero-width space, a bidi override),
  a non-plain or doubled space -- is refused whole as ambiguous: offering the others alone could
  hide the very option the operator meant. Only an exact repeat of a label is folded into one.
  Lookalike letters from other scripts are shown as they are (a parked follow-up).
- A gate id must be a UUID. Anything else is never offered and never repeated back.

Some gates are never offered, and `refusal_text` tells the operator where to answer them:

- **A spend gate.** Its kind is in `SPEND_GATE_KINDS`, or the hub flags it (`is_spend`, or
  `requires_scope == "spend"`). A lost or forged flag can only make a gate stricter.
- **The REVIEW phase's deployment opt-in.** A `choice` gate offering a
  `DEPLOYMENT_OPT_IN_OPTIONS` option. One click on it would opt a project into provisioning
  real infrastructure (the ADR-0067 gap, and CLAUDE.md: no irreversible real-world act without
  a person).
- **A gate whose answer is a value** (a new cap). A permission option cannot carry a value.
- **A kind this mapper does not know.**

Pure: no I/O. Declared by `interfaces/gate_permission_interface.py`.
"""

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final
from uuid import UUID

from vibey.domain.acp.protocol import PermissionKind
from vibey.domain.hub_chat import (
    ANY_ANSWER_GATE_KINDS,
    CHOICE_GATE_KINDS,
    GRANT_GATE_KEYS,
    VERDICT_GATE_KINDS,
)
from vibey.domain.hub_scope import DEPLOYMENT_OPT_IN_OPTIONS, SPEND_GATE_KINDS

LEAVE_OPEN: Final = "Leave it open"
"""The agent's option that answers nothing; every offered gate ends with it."""
ACCEPT_DEFAULTS: Final = "Accept the defaults"
ACKNOWLEDGE: Final = "Acknowledge"
GATE_OPTION_PREFIX: Final = "Answer: "
"""Shown before every option a gate supplies; vibey's own options never carry it."""
_INVISIBLE: Final = frozenset({"Cc", "Cf"})
"""Unicode categories dropped from a shown label: control and format characters."""
_OPT_IN: Final = frozenset(option.casefold() for option in DEPLOYMENT_OPT_IN_OPTIONS)
_ON_THE_HOST: Final = (
    "Answer it on the host (`vibey answer {gate_id}`) or in the desktop or mobile app."
)
NOT_A_UUID: Final = (
    "The hub listed a gate whose id is not a UUID, so I did not offer it. "
    "Check `vibey gates` on the host."
)


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

    def __init__(self, reject_words: tuple[str, ...]) -> None:
        self._reject_words = frozenset(reject_words)

    def gate_id(self, gate: Mapping[str, Any]) -> str | None:
        raw = gate.get("gate_id")
        if not isinstance(raw, str):
            return None
        try:
            canonical = str(UUID(raw))
        except ValueError:
            return None
        # `UUID()` also accepts braces, a `urn:uuid:` prefix and no hyphens; only the
        # canonical spelling, in either case, is a gate id.
        return canonical if raw.lower() == canonical else None

    def options_for(self, gate: Mapping[str, Any]) -> tuple[PermissionChoice, ...]:
        gate_id = self.gate_id(gate)
        kind = str(gate.get("kind") or "")
        if gate_id is None or self._spends(gate) or self._opts_in(gate) or self._ambiguous(gate):
            return ()
        if kind in VERDICT_GATE_KINDS:
            return self._per_option(gate_id, "verdict", gate.get("options"))
        if kind in CHOICE_GATE_KINDS:
            return self._per_option(gate_id, "choice", gate.get("options"))
        if kind == "question":
            accept = PermissionChoice(
                f"{gate_id}:0",
                ACCEPT_DEFAULTS,
                PermissionKind.ALLOW_ONCE,
                {"accept_defaults": True},
            )
            return self._with_leave_open(gate_id, [accept])
        if kind in ANY_ANSWER_GATE_KINDS:
            acknowledge = PermissionChoice(
                f"{gate_id}:0", ACKNOWLEDGE, PermissionKind.ALLOW_ONCE, {}
            )
            return self._with_leave_open(gate_id, [acknowledge])
        return ()

    def refusal_text(self, gate: Mapping[str, Any]) -> str:
        gate_id = self.gate_id(gate)
        if gate_id is None:
            return NOT_A_UUID  # an id that is not a UUID could say anything: never echoed
        kind = gate.get("kind")
        host = _ON_THE_HOST.format(gate_id=gate_id)
        if self._spends(gate):
            return f"Gate {gate_id} ({kind}) spends money, so I cannot answer it. {host}"
        if self._opts_in(gate):
            return (
                f"Gate {gate_id} ({kind}) opts the project into deployment, which can provision "
                f"real infrastructure, so I cannot answer it. {host}"
            )
        if self._ambiguous(gate):
            return (
                f"Gate {gate_id} ({kind}) has an option that does not show as what it would "
                f"answer (hidden characters or irregular spacing), so I cannot offer it. {host}"
            )
        if kind in VERDICT_GATE_KINDS or kind in CHOICE_GATE_KINDS or kind in GRANT_GATE_KEYS:
            return (
                f"Gate {gate_id} ({kind}) needs a value. Answer it with "
                f"`/answer {gate_id} <value>`."
            )
        return f"Gate {gate_id} ({kind}) is not a kind I can answer from here. {host}"

    @staticmethod
    def _spends(gate: Mapping[str, Any]) -> bool:
        return (
            str(gate.get("kind") or "") in SPEND_GATE_KINDS
            or bool(gate.get("is_spend"))
            or gate.get("requires_scope") == "spend"
        )

    @staticmethod
    def _opts_in(gate: Mapping[str, Any]) -> bool:
        options = gate.get("options")
        if str(gate.get("kind") or "") not in CHOICE_GATE_KINDS or not isinstance(options, list):
            return False
        return any(str(option).strip().casefold() in _OPT_IN for option in options)

    def _per_option(self, gate_id: str, key: str, options: Any) -> tuple[PermissionChoice, ...]:
        if not isinstance(options, list):
            return ()
        choices: list[PermissionChoice] = []
        seen: set[str] = set()
        for index, option in enumerate(options):
            label = str(option).strip()
            if not label or label in seen:
                continue  # nothing an operator could mean, or an exact repeat
            seen.add(label)
            rejects = label.casefold() in self._reject_words
            choices.append(
                PermissionChoice(
                    option_id=f"{gate_id}:{index}",
                    name=f"{GATE_OPTION_PREFIX}{label}",
                    kind=PermissionKind.REJECT_ONCE if rejects else PermissionKind.ALLOW_ONCE,
                    answer={key: label},
                )
            )
        return self._with_leave_open(gate_id, choices) if choices else ()

    @classmethod
    def _ambiguous(cls, gate: Mapping[str, Any]) -> bool:
        """Whether a choice or verdict option would show as something other than it sends."""
        options = gate.get("options")
        kind = str(gate.get("kind") or "")
        if kind not in VERDICT_GATE_KINDS and kind not in CHOICE_GATE_KINDS:
            return False
        if not isinstance(options, list):
            return False
        labels = [str(option).strip() for option in options]
        return any(cls._shown(label) != label for label in labels)

    @staticmethod
    def _shown(label: str) -> str:
        """`label` as the operator sees it: invisible characters dropped, spaces collapsed."""
        visible = "".join(
            ch for ch in label if ch.isspace() or unicodedata.category(ch) not in _INVISIBLE
        )
        return " ".join(visible.split())

    @staticmethod
    def _with_leave_open(
        gate_id: str, choices: list[PermissionChoice]
    ) -> tuple[PermissionChoice, ...]:
        leave = PermissionChoice(f"{gate_id}:open", LEAVE_OPEN, PermissionKind.REJECT_ONCE, None)
        return (*choices, leave)
