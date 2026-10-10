# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which waiting gates a worker may answer for the operator who asked it to, and with what.

A local run parks on gates that are not decisions: a question whose own default is the
answer, an attempt budget the operator would grant again, a delivery that died with its
worker. Waiting on a person for each is what stops an unattended run. Answering them on a
timer would make silence consent, which sub-doctrine 12.d forbids; so this is not a timer.
It is `vibey worker --auto-answer`: the operator says so, on the command line, for that one
worker, and the answers stop after a limit they can also set.

The table below is the whole of what may be answered. Everything else waits for a person,
and the omissions are the point:

- **Spending gates** (`budget_exhausted`): raising a money cap is never an automation's
  call, whatever it costs per token.
- `engine_misconfigured`: something needs fixing first; answering retries into the same wall.
- `research_evidence`: a person supplies the reading.
- Every approval, acceptance and review gate: a person's judgement is the point.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

DEFAULT_AUTO_ANSWER_LIMIT: Final[int] = 30
"""How many answers one worker gives before it stops and leaves every gate to a person."""

AUTO_ANSWERS: Final[Mapping[str, Mapping[str, object]]] = MappingProxyType(
    {
        # The DESIGN interview: every question's own declared default (`vibey answer --defaults`).
        "question": MappingProxyType({"accept_defaults": True}),
        # The grants `vibey gates` itself suggests for each kind.
        "escalation_exhausted": MappingProxyType({"max_attempts": 10}),
        "verify_repair_exhausted": MappingProxyType({"max_rounds": 6}),
        "integrate_repair_exhausted": MappingProxyType({"max_rounds": 6}),
        # "Answer anything to deliver it once more": the answer carries nothing.
        "delivery_exhausted": MappingProxyType({}),
    }
)
"""Every gate kind that may be answered automatically, and the answer it gets."""


@dataclass(frozen=True, slots=True)
class GateAutoAnswerPolicy:
    """What one `--auto-answer` worker may do: the table above, up to `limit` answers."""

    limit: int = DEFAULT_AUTO_ANSWER_LIMIT

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or self.limit < 1:
            raise ValueError(f"the auto-answer limit must be at least 1, got {self.limit!r}")

    def answer_for(self, kind: str) -> dict[str, object] | None:
        """The answer a gate of this kind gets, or None when it waits for a person."""
        answer = AUTO_ANSWERS.get(kind)
        return None if answer is None else dict(answer)
