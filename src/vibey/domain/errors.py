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
