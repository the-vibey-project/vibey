# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Abandoning a project (`vibey abandon`): the operator's clean exit.

Abandoned is a terminal phase the machine allows from every phase short of done, intake
included (`phase.py`), and nothing in vibey reaches it on its own -- a person decides a
project is not going to finish. This decides whether it may, through the one guard every
phase move takes (`evaluate_transition`), and names what the decision records:

- **The move.** A `PhaseTransitioned` into abandoned whose `guard` is `GUARD` and whose
  payload carries the operator's `reason`, `by` and `account`, and the ids of every job
  it cancelled and every gate it withdrew -- one event, so the ledger says what stopped.
- **The gates.** Each open gate is closed, never deleted: its row records the withdrawal
  as its answer, and a `GateWithdrawn` event records why. Nobody answered the question;
  the project it asked for no longer wants one.

A done project is refused: it finished, which is a different ending, and nothing leads
out of abandoned, so abandoning twice is a no-op -- the verdict says so, and nothing is
written. A reason and a `--by` label are printed and stored as given, so each must be
visible text: not empty, not over its length, free of control and formatting characters.

Pure: states in, verdicts and payloads out.
"""

import unicodedata
from collections.abc import Sequence
from enum import StrEnum
from typing import ClassVar, Final
from uuid import UUID

from vibey.domain.actor_label import ActorLabelPolicy
from vibey.domain.errors import AbandonmentRefused, InvalidAbandonment
from vibey.domain.interfaces.abandonment_interface import AbandonmentPolicyInterface
from vibey.domain.interfaces.actor_label_interface import ActorLabelPolicyInterface
from vibey.domain.job import JobState
from vibey.domain.phase import (
    Denied,
    Phase,
    PhaseState,
    TransitionEvidence,
    TransitionRequest,
    evaluate_transition,
)

GUARD: Final = "operator abandoned"
"""The rule an abandonment's `PhaseTransitioned` names: a person decided, no evidence did."""

WITHDRAWN_REASON: Final = "project abandoned"
"""Why every gate an abandonment closes was closed."""

UNSETTLED_JOB_STATES: Final = frozenset(
    {
        JobState.READY,
        JobState.LEASED,
        JobState.AWAITING_HUMAN,
        JobState.AWAITING_CAPACITY,
    }
)
"""Every state a job can still leave. Succeeded, failed and cancelled jobs are settled and
stay as they are: an abandonment stops work, it does not rewrite what already happened."""


ABANDONMENT_ACTORS: Final[ActorLabelPolicyInterface] = ActorLabelPolicy(
    subject="the name an abandonment is recorded under", error=InvalidAbandonment
)
"""`--by`, checked as every person-made record checks it, refused in this command's words."""


class AbandonmentVerdict(StrEnum):
    ABANDON = "abandon"
    ALREADY_ABANDONED = "already_abandoned"


class AbandonmentPolicy:
    """Declared by `interfaces/abandonment_interface.py::AbandonmentPolicyInterface`."""

    MAX_REASON_LENGTH: ClassVar[int] = 2000
    """Room for a sentence or two of why; short enough to print."""

    def __init__(
        self,
        *,
        actors: ActorLabelPolicyInterface = ABANDONMENT_ACTORS,
    ) -> None:
        self._actors = actors

    @property
    def guard(self) -> str:
        return GUARD

    @property
    def unsettled_states(self) -> frozenset[str]:
        return frozenset(state.value for state in UNSETTLED_JOB_STATES)

    def reason(self, text: str) -> str:
        reason = text.strip()
        if not reason:
            raise InvalidAbandonment("the reason for abandoning a project cannot be empty")
        if len(reason) > self.MAX_REASON_LENGTH:
            raise InvalidAbandonment(
                f"the reason for abandoning a project is over {self.MAX_REASON_LENGTH} characters"
            )
        if any(unicodedata.category(char).startswith("C") for char in reason):
            raise InvalidAbandonment(
                "the reason for abandoning a project cannot contain control or formatting "
                "characters"
            )
        return reason

    def actor(self, label: str | None, *, account: str) -> str:
        return self._actors.resolve(label, account=account)

    def decide(self, state: PhaseState) -> AbandonmentVerdict:
        if state.phase is Phase.ABANDONED:
            return AbandonmentVerdict.ALREADY_ABANDONED
        if state.phase is Phase.DONE:
            raise AbandonmentRefused(
                "the project is done: it finished, which is a different ending from "
                "abandoned, so it is left as it is"
            )
        outcome = evaluate_transition(
            state, TransitionRequest(Phase.ABANDONED, GUARD, TransitionEvidence())
        )
        if isinstance(outcome, Denied):
            raise AbandonmentRefused(
                f"the project cannot be abandoned from phase {state.phase.value!r}: "
                + "; ".join(outcome.violations)
            )
        return AbandonmentVerdict.ABANDON

    def transition_attribution(
        self,
        *,
        reason: str,
        by: str,
        account: str,
        cancelled_jobs: Sequence[UUID],
        withdrawn_gates: Sequence[UUID],
    ) -> dict[str, object]:
        return {
            "reason": reason,
            "by": by,
            "account": account,
            "cancelled_jobs": [str(job_id) for job_id in cancelled_jobs],
            "withdrawn_gates": [str(gate_id) for gate_id in withdrawn_gates],
        }

    def withdrawn_answer(self) -> dict[str, object]:
        return {"withdrawn": True, "reason": WITHDRAWN_REASON}

    def request_id(self, project_id: UUID) -> str:
        return f"abandon:{project_id}"

    def withdrawal_payload(
        self,
        *,
        gate_id: UUID,
        gate_kind: str,
        job_id: UUID | None,
        request_id: str,
        by: str,
        account: str,
    ) -> dict[str, object]:
        return {
            "gate_id": str(gate_id),
            "gate_kind": gate_kind,
            "job_id": str(job_id) if job_id is not None else None,
            "request_id": request_id,
            "reason": WITHDRAWN_REASON,
            "by": by,
            "account": account,
        }


ABANDONMENT_POLICY: Final[AbandonmentPolicyInterface] = AbandonmentPolicy()
"""The policy every abandonment shares. Stateless, so one instance serves."""
