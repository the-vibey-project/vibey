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


class UnknownJob(VibeyError):
    """No job exists with the given id."""

    def __init__(self, job_id: object) -> None:
        self.job_id = job_id
        super().__init__(f"unknown job {job_id}")


class NotReorderable(VibeyError):
    """A job's place in the queue cannot be changed (ADR-0054).

    Only a job that is still waiting, parked or running can be moved: a finished
    job will never be claimed again, and a job in a state this vibey does not know is
    one it will not write (vibey#287). Nothing was changed.
    """

    def __init__(self, job_id: object, why: str) -> None:
        self.job_id = job_id
        self.why = why
        super().__init__(f"job {job_id} cannot be moved in the queue: {why}")


class DependencyCycle(VibeyError):
    """Jobs depend on one another in a ring, so none of them can ever be claimed.

    The planner refuses to order a ring rather than break it arbitrarily: which job
    of a ring should run first is not a question an ordering rule can answer.
    """

    def __init__(self, job_ids: tuple[object, ...]) -> None:
        self.job_ids = job_ids
        listed = ", ".join(str(job_id) for job_id in job_ids)
        super().__init__(f"these jobs depend on one another in a ring: {listed}")


class PriorityRefused(VibeyError):
    """A request to reorder the queue came from a source with no grant (12.j).

    The refusal is recorded on the ledger before this is raised, so it is
    reportable output rather than silence (12.d).
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"refused: {reason}")
