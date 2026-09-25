# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibey.domain.handoff import GateResult


class VibeyError(Exception):
    """Base class for all vibey domain errors."""


class InvalidPhaseError(VibeyError):
    """A PhaseState was constructed with invalid fields."""


class IllegalTransitionError(VibeyError):
    """A phase transition was attempted that evaluate_transition denies."""


class NoEligibleEngine(VibeyError):
    """Rotation was asked to select from a candidate set with no positive weight."""


class EscalationExhausted(VibeyError):
    """The build escalation ladder has no rung left for this attempt."""

    def __init__(self, attempt: int) -> None:
        self.attempt = attempt
        super().__init__(f"escalation ladder exhausted at attempt {attempt}")


class HandoffRejected(VibeyError):
    """The no-loss gate denied a handoff after exhausting its escalation path."""

    def __init__(self, result: "GateResult") -> None:
        self.result = result
        super().__init__(f"handoff rejected: {len(result.violations)} violation(s)")


class InvalidSpecError(VibeyError):
    """A DesignSpec failed its buildability checks."""


class BudgetExceeded(VibeyError):
    """A spend would exceed the project's budget caps."""


class InvalidBudgetChange(VibeyError):
    """A requested change to a project's caps is not one vibey can make: a value that is
    not a cap (dollars must be a finite number above zero, turns a whole number above
    zero), a request that names no cap, or an actor label that cannot be recorded.
    Nothing was changed and nothing was recorded."""


class InvalidActorLabel(VibeyError):
    """A name a caller gave for the record (`--by`) cannot be recorded: empty, too long,
    or carrying control or formatting characters. Nothing was changed."""


class UnknownGate(VibeyError, LookupError):
    """No human gate exists with the given id. A `LookupError` too, as the repository
    raised before gates were answered once, so a caller catching that still does."""


class GateAlreadyAnswered(VibeyError):
    """A gate was answered once already, by another request, so this answer was not
    recorded (compare-and-set on `answered_at IS NULL`). The first answer stands; a
    gate is never answered twice. Replaying the SAME request is not this error: it is
    a no-op that reports the answer already recorded."""

    def __init__(
        self,
        gate_id: object,
        *,
        answered_by: str | None,
        answered_at: object,
        same_request: bool = False,
    ) -> None:
        self.gate_id = gate_id
        self.answered_by = answered_by
        self.answered_at = answered_at
        self.same_request = same_request
        why = (
            "this request id was already used for a different answer"
            if same_request
            else "a different request answered it first"
        )
        super().__init__(
            f"gate {gate_id} was already answered by {answered_by} at {answered_at}; "
            f"{why}, so this answer was not recorded"
        )


class UnknownProject(VibeyError):
    """No project exists with the given id."""


class WrongPhase(VibeyError):
    """The project is not in a phase the requested command applies to."""


class InvalidAnswer(VibeyError):
    """A human-gate answer was not in the expected QUESTION_ID=ANSWER form."""


class UnknownProvider(VibeyError):
    """The requested engine provider is not one vibey knows how to build."""


class SovereignResearchUnavailable(VibeyError):
    """A research provider refused a topic rather than invent a source.

    A local model has no web access. Returning its recollection with a `source` field
    would put a fabricated citation into a design spec, which is worse than having no
    research step: a wrong answer that looks sourced survives review, and a missing one
    does not. Doctrine 10 requires the floor be declared to a human at the moment it is
    known, which is what this is (ADR-0027).

    It lives in the domain, not beside the provider that raises it, so the application's
    research handler can turn the refusal into a human gate without importing
    infrastructure. `evidence_name` is the file the provider looked for, or None when the
    topic reduces to no usable file name and no evidence file could ever match it.
    """

    def __init__(self, topic: str, detail: str, *, evidence_name: str | None = None) -> None:
        self.topic = topic
        self.detail = detail
        self.evidence_name = evidence_name
        super().__init__(detail)


class ReorderRefused(VibeyError):
    """A request to reorder the queue was refused, and nothing moved (ADR-0054).

    Every subclass is a reason a bump or an un-bump did not happen. The service
    records each one on the ledger as `JobPriorityRefused` before it reaches the
    caller: every request is recorded, whatever became of it (contract item 5).
    """


class UnknownJob(ReorderRefused):
    """No job with the given id exists in the project the request named."""

    def __init__(self, job_id: object) -> None:
        self.job_id = job_id
        super().__init__(f"unknown job {job_id}")


class NotReorderable(ReorderRefused):
    """A job's place in the queue cannot be changed.

    Only a job that is still waiting, parked or running can be moved: a finished job
    will never be claimed again, and a job in a state or phase this vibey does not
    know is one it will not write (vibey#287).
    """

    def __init__(self, job_id: object, why: str) -> None:
        self.job_id = job_id
        self.why = why
        super().__init__(f"job {job_id} cannot be moved in the queue: {why}")


class DependencyCycle(ReorderRefused):
    """Jobs depend on one another in a ring, so none of them can ever be claimed.

    Refused rather than broken arbitrarily: which job of a ring should run first is
    not a question an ordering rule can answer.
    """

    def __init__(self, job_ids: tuple[object, ...]) -> None:
        self.job_ids = job_ids
        listed = ", ".join(str(job_id) for job_id in job_ids)
        super().__init__(f"these jobs depend on one another in a ring: {listed}")


class DependencyCannotFinish(ReorderRefused):
    """A job depends on one that can never succeed -- failed, cancelled, or in a state
    this vibey does not know -- so bumping it would claim a place it can never use."""

    def __init__(self, job_id: object, blockers: tuple[tuple[object, str], ...]) -> None:
        self.job_id = job_id
        self.blockers = blockers
        listed = ", ".join(f"{blocker} ({state})" for blocker, state in blockers)
        super().__init__(f"job {job_id} depends on jobs that can never finish: {listed}")


class DependentsStillBumped(ReorderRefused):
    """An un-bump of a job that bumped jobs still need. Un-bumping it would leave them
    holding a place they cannot use; un-bump them first."""

    def __init__(self, job_id: object, dependents: tuple[object, ...]) -> None:
        self.job_id = job_id
        self.dependents = dependents
        listed = ", ".join(str(dependent) for dependent in dependents)
        super().__init__(f"job {job_id} is needed by bumped jobs; un-bump them first: {listed}")


class ReorderConflict(ReorderRefused):
    """The database broke a lock cycle by aborting this request. Nothing moved; a
    retry is safe, because every reorder is idempotent under replay."""

    def __init__(self, job_id: object) -> None:
        self.job_id = job_id
        super().__init__(
            f"job {job_id} was not moved: another transaction held the same rows and the "
            "database aborted this request to break the deadlock; retry it"
        )


class PriorityRefused(ReorderRefused):
    """A request to reorder the queue came from an account or source with no grant
    (12.j). `requested_by` is who asked, as the ledger records it."""

    def __init__(self, requested_by: str, reason: str) -> None:
        self.requested_by = requested_by
        self.reason = reason
        super().__init__(f"refused: {reason}")
