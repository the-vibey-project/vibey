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

from collections.abc import Mapping, Sequence
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
    """What one worker may answer, up to `limit` answers.

    `answer_retries` is `--auto-answer`: the table above. The other two are separate flags
    an operator gives on purpose, each one acceptance and nothing wider:

    - `accept_review` (`--auto-accept-review`): the REVIEW `approval` gate, answered `accept`
      (never `changes` or `cancel`), and only when the gate offers it.
    - `finish_local` (`--auto-finish-local`): the deployment choice after REVIEW, answered
      `local_only` -- the gate's own default -- and never `deploy`, and only when it offers it.
    - `publish` (`--auto-publish`): the `publish_interview` gate, answered `accept_defaults`:
      publish exactly what its prompt showed (never `custom`), and only when it offers it. It
      is its own flag because it is the one acceptance that sends work off the machine; the
      other flags, `--auto-accept-all` included, never answer it.

    A deployment gate (`deploy_acceptance` is consent to change real infrastructure) and a
    spending gate have no flag and are never answered, whatever is set here.
    """

    limit: int = DEFAULT_AUTO_ANSWER_LIMIT
    answer_retries: bool = True
    accept_review: bool = False
    finish_local: bool = False
    publish: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or self.limit < 1:
            raise ValueError(f"the auto-answer limit must be at least 1, got {self.limit!r}")

    def answer_for(self, kind: str, options: Sequence[str] = ()) -> dict[str, object] | None:
        """The answer a gate of this kind gets, or None when it waits for a person."""
        if kind == "approval":
            return {"verdict": "accept"} if self.accept_review and "accept" in options else None
        if kind == "choice":
            return (
                {"choice": "local_only"} if self.finish_local and "local_only" in options else None
            )
        if kind == "publish_interview":
            return (
                {"choice": "accept_defaults"}
                if self.publish and "accept_defaults" in options
                else None
            )
        if not self.answer_retries:
            return None
        answer = AUTO_ANSWERS.get(kind)
        return None if answer is None else dict(answer)
