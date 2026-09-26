# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How each kind of gate is answered -- declared once, here.

`vibey gates` prints beside every open gate the exact `vibey answer` command that answers
it (`answer_with`), so nobody learns the answer shapes from the source. The shapes are the
ones `vibey answer` documents and each gate's own handler reads:

* the DESIGN interview takes `--defaults`: every question's default;
* a review takes `--verdict`, and a deployment or triage gate `--choice`, each with one of
  the gate's own options -- its declared default, else its first;
* a grant takes `--raw` naming a new bound, `{"max_dollars": N}`. `N` stays a placeholder
  because how much more money, or how many more tries, is a person's judgement, never a
  number this command picks for them;
* a gate that retries on any answer takes `--raw '{}'`, the answer vibey's own prompts give;
* a gate whose answer nothing reads, and every kind this table does not know, takes
  `--raw '<json>'`: the person writes the answer.

A placeholder is not valid JSON, so a command pasted without filling it in is refused by
`vibey answer`, never sent. Every word is shell-quoted: printed unquoted, a command such as
`--verdict accept|changes` would pipe -- and still run its `accept` half.

`tests/cli/test_gate_answers.py` fails when a gate kind is raised anywhere in `src/vibey`
without an entry here, or an entry outlives the kind it answers.
"""

import json
import shlex
from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from vibey.application.bus_dead_letter_handler import BUS_DEAD_LETTER_GATE_KIND
from vibey.application.design_research_handler import RESEARCH_EVIDENCE_GATE_KIND
from vibey.application.dto import HumanGateRecord
from vibey.application.worker import ATTEMPTS_GRANT_KEY
from vibey.cli.interfaces.gate_answers_interface import (
    AnswerRuleInterface,
    GateAnswerCommandsInterface,
)
from vibey.domain.job import ATTEMPTS_EXHAUSTED_GATE_KIND, DELIVERY_EXHAUSTED_GATE_KIND

GRANT_PLACEHOLDER: Final = "N"
"""Where a grant's new bound goes. Not a JSON value, so it cannot be sent by accident."""

FREE_FORM_PLACEHOLDER: Final = "<json>"
"""Where a free-form answer goes. Not JSON either, for the same reason."""


class FlagAnswer:
    """Answered by one flag and nothing after it: the interview's `--defaults`."""

    def __init__(self, flag: str) -> None:
        self._flag = flag

    def arguments(self, gate: HumanGateRecord) -> tuple[str, ...]:
        return (self._flag,)

    def fill_in(self, gate: HumanGateRecord) -> str | None:
        return None


class OptionAnswer:
    """Answered by `--verdict` or `--choice` with one of the gate's own options: its
    declared default, else its first. A gate offering neither is answered the way
    `fallback` is -- this never names a value the gate did not offer."""

    def __init__(self, flag: str, *, fallback: AnswerRuleInterface) -> None:
        self._flag = flag
        self._fallback = fallback

    def arguments(self, gate: HumanGateRecord) -> tuple[str, ...]:
        value = self._suggested(gate)
        if value is None:
            return self._fallback.arguments(gate)
        return (self._flag, value)

    def fill_in(self, gate: HumanGateRecord) -> str | None:
        if self._suggested(gate) is None:
            return self._fallback.fill_in(gate)
        return None

    @staticmethod
    def _suggested(gate: HumanGateRecord) -> str | None:
        if gate.default_answer:
            return gate.default_answer
        return gate.options[0] if gate.options else None


class RawAnswer:
    """Answered by `--raw` and one JSON text: a fixed answer, or a placeholder a person
    replaces -- `fill_in` says what with."""

    def __init__(self, text: str, *, fill_in: str | None = None) -> None:
        self._text = text
        self._fill_in = fill_in

    def arguments(self, gate: HumanGateRecord) -> tuple[str, ...]:
        return ("--raw", self._text)

    def fill_in(self, gate: HumanGateRecord) -> str | None:
        return self._fill_in


class GrantAnswer:
    """Answered by `--raw` naming a new bound under the key the gate's handler reads,
    `{"max_rounds": N}`; the person puts the number where the placeholder is."""

    def __init__(self, key: str, *, placeholder: str = GRANT_PLACEHOLDER) -> None:
        self._key = key
        self._placeholder = placeholder

    def arguments(self, gate: HumanGateRecord) -> tuple[str, ...]:
        return ("--raw", f"{{{json.dumps(self._key)}: {self._placeholder}}}")

    def fill_in(self, gate: HumanGateRecord) -> str | None:
        return f"{self._placeholder} with the new {self._key}"


FREE_FORM: Final[AnswerRuleInterface] = RawAnswer(
    FREE_FORM_PLACEHOLDER,
    fill_in=f"{FREE_FORM_PLACEHOLDER} with a JSON object that answers the prompt",
)
"""The answer to a gate nothing reads an answer from, and to any kind not in the table."""

DEFAULTS: Final[AnswerRuleInterface] = FlagAnswer("--defaults")
VERDICT: Final[AnswerRuleInterface] = OptionAnswer("--verdict", fallback=FREE_FORM)
CHOICE: Final[AnswerRuleInterface] = OptionAnswer("--choice", fallback=FREE_FORM)
ANY_ANSWER: Final[AnswerRuleInterface] = RawAnswer("{}")

ANSWER_RULES: Final[Mapping[str, AnswerRuleInterface]] = MappingProxyType(
    {
        # The DESIGN interview (design_handler). Question keys are model-minted per run, so
        # `--defaults` is the one answer that needs none; explicit pairs may be added.
        "question": DEFAULTS,
        # Read as {"verdict": ...}: REVIEW (review_collect_handler) and the Phase 6 demo
        # (deploy_review_handler).
        "approval": VERDICT,
        "deploy_demo_review": VERDICT,
        # Read as {"choice": ...}: the deployment opt-in after REVIEW
        # (review_deployment_choice_handler), the Phase 4 interview (deploy_design_handler),
        # the Phase 6 triage (deploy_review_handler), and a dead-lettered message
        # (bus_dead_letter_handler).
        "choice": CHOICE,
        "deploy_interview": CHOICE,
        "deploy_failure_triage": CHOICE,
        BUS_DEAD_LETTER_GATE_KIND: CHOICE,
        # Spec consent (deploy_acceptance_handler). Its declared default is `reject`, and
        # that is what is printed: accepting also takes explicit mutation consent, which no
        # flag sends and this command never suggests (docs/reference/cli.md, `vibey gates`).
        "deploy_acceptance": CHOICE,
        # Grants, under the key the raising handler reads.
        "budget_exhausted": GrantAnswer("max_dollars"),  # build_implement_handler
        "escalation_exhausted": GrantAnswer(ATTEMPTS_GRANT_KEY),  # build_implement_handler
        ATTEMPTS_EXHAUSTED_GATE_KIND: GrantAnswer(ATTEMPTS_GRANT_KEY),  # worker
        "verify_repair_exhausted": GrantAnswer("max_rounds"),  # build_verify_handler
        "integrate_repair_exhausted": GrantAnswer("max_rounds"),  # build_integrate_handler
        # Any answer retries: the fix happens outside vibey, and answering says it did.
        DELIVERY_EXHAUSTED_GATE_KIND: ANY_ANSWER,  # queue_reaper
        RESEARCH_EVIDENCE_GATE_KIND: ANY_ANSWER,  # design_research_handler
        "engine_misconfigured": ANY_ANSWER,  # build_engine_run
        "ultra_needs_cap": ANY_ANSWER,  # build_implement_handler, after a cap or no-cap
        # Nothing reads these answers (wind_down): answering re-queues a job that parks
        # again unless something outside vibey changed, so the person writes the answer.
        "handoff_gate_failed": FREE_FORM,
        "too_many_wind_downs": FREE_FORM,
    }
)
"""Every gate kind vibey raises today, and how it is answered."""


class GateAnswerCommands:
    """Renders `answer_with`: the `vibey answer` command for one gate, by the rule for its
    kind, every word quoted for the shell."""

    def __init__(
        self,
        rules: Mapping[str, AnswerRuleInterface] = ANSWER_RULES,
        *,
        fallback: AnswerRuleInterface = FREE_FORM,
        program: tuple[str, ...] = ("vibey", "answer"),
    ) -> None:
        self._rules = rules
        self._fallback = fallback
        self._program = program

    def rule(self, kind: str) -> AnswerRuleInterface:
        return self._rules.get(kind, self._fallback)

    def command(self, gate: HumanGateRecord) -> str:
        return shlex.join(
            (*self._program, str(gate.gate_id), *self.rule(gate.kind).arguments(gate))
        )


GATE_ANSWERS: Final[GateAnswerCommandsInterface] = GateAnswerCommands()
"""The renderer `vibey gates` uses. Annotated with the interface so `mypy --strict` checks
the class against its declared seam."""
