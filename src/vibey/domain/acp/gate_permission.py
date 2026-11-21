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
- An option sends exactly what it shows, and no two options read alike. A choice or verdict
  gate is refused whole as ambiguous -- offering the others alone could hide the very option
  the operator meant -- when any label:
  - holds a character outside an allowlist: letters, numbers, punctuation and symbols, with
    one plain space (U+0020) between words. Marks, controls, format, private-use, unassigned
    and surrogate code points, every other space and separator, and the glyphs known to render
    blank (`_BLANK_GLYPHS`) are all outside it;
  - holds a right-to-left character or a bidirectional control (`_BIDI_REFUSED`): such text
    can display in another order than it is sent, and vibey's own gate labels are English, so
    refusing it fails safe;
  - mixes scripts inside one word (Latin "o" beside a Cyrillic "о"), read from the Unicode
    character names, with Han, Hiragana and Katakana counted as one script; or
  - reads the same as another label once normalised (NFKC, then case-folded): "no" and a
    full-width "ＮＯ", "Stop" and "stop".
  Only an exact repeat of a label is folded into one. Whole words that are lookalikes in
  another single script (a Cyrillic "сор" for "cop") are not caught: a parked follow-up.
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
_ALLOWED_CATEGORIES: Final = frozenset(
    {"Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Nl", "No"}
    | {"Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So"}
)
"""Letters, numbers, punctuation and symbols: the only categories a gate label may use."""
_BLANK_GLYPHS: Final = frozenset("\u115f\u1160\u2800\u3164\uffa0")
"""Allowed by category, but drawn as nothing: the Hangul fillers and the Braille blank."""
_BIDI_REFUSED: Final = frozenset(
    {"R", "AL", "AN", "RLE", "RLO", "RLI", "FSI", "LRE", "LRO", "LRI", "PDF", "PDI"}
)
"""Bidirectional classes that let a label display in another order than it is sent."""
_ONE_SCRIPT: Final[Mapping[str, str]] = {
    "CJK": "HAN",
    "HIRAGANA": "HAN",
    "KATAKANA": "HAN",
    "KATAKANA-HIRAGANA": "HAN",
    "IDEOGRAPHIC": "HAN",
}
"""Scripts written together within one word, read as one: Japanese mixes all of these."""
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
                f"Gate {gate_id} ({kind}) has options I cannot show unambiguously (unusual or "
                "hidden characters, irregular spacing, mixed scripts, or labels that read "
                f"alike), so I cannot offer it. {host}"
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
            rejects = self._normal(label) in self._reject_words
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
        """Whether a choice or verdict gate has a label the operator could misread."""
        options = gate.get("options")
        kind = str(gate.get("kind") or "")
        if kind not in VERDICT_GATE_KINDS and kind not in CHOICE_GATE_KINDS:
            return False
        if not isinstance(options, list):
            return False
        read: dict[str, str] = {}
        for option in options:
            label = str(option).strip()
            if not label:
                continue
            if not cls._plain(label):
                return True
            normal = cls._normal(label)
            if read.setdefault(normal, label) != label:
                return True  # two different labels that read alike
        return False

    @staticmethod
    def _normal(label: str) -> str:
        return unicodedata.normalize("NFKC", label).casefold()

    @classmethod
    def _plain(cls, label: str) -> bool:
        """Allowlisted characters only, one U+0020 between words, one script within a word."""
        words = label.split(" ")
        return all(word and cls._plain_word(word) for word in words)

    @staticmethod
    def _plain_word(word: str) -> bool:
        if any(
            unicodedata.category(ch) not in _ALLOWED_CATEGORIES
            or ch in _BLANK_GLYPHS
            or unicodedata.bidirectional(ch) in _BIDI_REFUSED
            for ch in word
        ):
            return False
        scripts = {
            _ONE_SCRIPT.get(head, head)
            for ch in unicodedata.normalize("NFKC", word)
            if unicodedata.category(ch).startswith("L")
            for head in (unicodedata.name(ch, "?").split()[0],)
        }
        return len(scripts) <= 1

    @staticmethod
    def _with_leave_open(
        gate_id: str, choices: list[PermissionChoice]
    ) -> tuple[PermissionChoice, ...]:
        leave = PermissionChoice(f"{gate_id}:open", LEAVE_OPEN, PermissionKind.REJECT_ONCE, None)
        return (*choices, leave)
