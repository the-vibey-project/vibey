# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `answer_with`, the command `vibey gates` prints beside a gate.

Mirrors `vibey/cli/gate_answers.py` (ADR-0016). Interfaces declare; they never consume. The
record the seams are declared over is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import HumanGateRecord


@runtime_checkable
class AnswerRuleInterface(Protocol):
    """How one kind of gate is answered: the `vibey answer` arguments after the gate id."""

    def arguments(self, gate: HumanGateRecord) -> tuple[str, ...]:
        """The flag and its value for this gate, unquoted: the caller quotes them."""
        ...

    def fill_in(self, gate: HumanGateRecord) -> str | None:
        """What a person must replace before the command will run -- for example
        "N with the new max_dollars" -- or None when it runs as printed."""
        ...


@runtime_checkable
class GateAnswerCommandsInterface(Protocol):
    """Renders the exact `vibey answer` command for a gate, by the gate's kind."""

    def rule(self, kind: str) -> AnswerRuleInterface:
        """The rule for `kind`; the free-form fallback for a kind with none."""
        ...

    def command(self, gate: HumanGateRecord) -> str:
        """One line a shell runs as printed: every word quoted as the shell needs it."""
        ...
