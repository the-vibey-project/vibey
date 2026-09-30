# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

from vibey.domain.job import FailureClass

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


class ForeignBranchRefused(VibeyError):
    """BUILD found a branch it meant to create, reuse or merge, and cannot prove this
    project created it, so it refused to touch it.

    Branches used to be named by cycle alone (`vibey/<cycle>/<item>`), so every project
    in one repository shared them: a delivery in cycle 1 checked out another project's
    months-old `vibey/1/ws` and built on that history. Names now carry the project, and
    every branch BUILD creates records the project and the commit it was cut from. A
    branch without that record, with another project's, or whose recorded base is no
    longer in its history is not adopted -- the handler parks for a person instead
    (`FOREIGN_BRANCH_GATE_KIND`), because no retry changes whose branch it is.
    """

    def __init__(self, branch: str, project_id: object, reason: str) -> None:
        self.branch = branch
        self.project_id = project_id
        self.reason = reason
        super().__init__(
            f"refusing branch {branch!r} for project {project_id}: {reason}. Vibey never "
            "builds on a branch it cannot prove this project created. Check whose branch "
            f"it is, move it aside (`git branch -m {branch} <another name>`), then answer "
            "to retry: BUILD cuts a fresh branch from the project's base."
        )


class UnknownProject(VibeyError):
    """No project exists with the given id."""


class UnknownLane(VibeyError, LookupError):
    """No listed lane has the given events file. The hub reads only files it found as
    lanes, so a path that is not one is refused rather than opened (ADR-0067)."""


class WrongPhase(VibeyError):
    """The project is not in a phase the requested command applies to."""


class CheckoutHeld(VibeyError):
    """A project was asked to start in a checkout a live project already holds.

    Two live projects never share a checkout (migration 0021's `project_repo_live_uniq`):
    every phase but `abandoned` holds one, `done` included. Nothing was created. The
    holder is named so the operator can decide: abandon it (`vibey abandon`), which lets
    the checkout go, or start the new project somewhere else.

    `holder_id` and `holder_phase` are None only when the holder left the checkout
    between the refused insert and the read that names it -- abandoned in that instant --
    in which case the checkout is free now and running the same command again succeeds.
    """

    def __init__(self, repo_path: str, *, holder_id: UUID | None, holder_phase: str | None) -> None:
        self.repo_path = repo_path
        self.holder_id = holder_id
        self.holder_phase = holder_phase
        if holder_id is None:
            held = (
                "was held by a live project when this one was refused, and that project "
                "has since let it go; run the same command again"
            )
        else:
            held = f"is held by live project {holder_id} (phase {holder_phase})"
        super().__init__(
            f"checkout {repo_path} {held}; two live projects never share a checkout, "
            "so no project was created"
        )


class InvalidAbandonment(VibeyError):
    """A request to abandon a project that vibey will not record: a reason that is empty,
    over-long or carries control or formatting characters, or a `--by` label that cannot
    be recorded. Nothing was changed."""


class AbandonmentRefused(VibeyError):
    """The project cannot be abandoned from where it stands: it is done -- finished, a
    different ending from abandoned -- or in a phase with no edge to abandoned, or in a
    phase this vibey does not know. Nothing was changed."""


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

    `evidence_supplied` says whether the operator supplied reading that could not be used
    (a file without a `source:` line, or with no body). That is a mistake to fix, not an
    absence to record: `[design.research] on_unavailable = "record_gap"` records a gap only
    when there was no evidence at all, and still parks this case for a person, so material
    the operator provided is never silently set aside.
    """

    def __init__(
        self,
        topic: str,
        detail: str,
        *,
        evidence_name: str | None = None,
        evidence_supplied: bool = False,
    ) -> None:
        self.topic = topic
        self.detail = detail
        self.evidence_name = evidence_name
        self.evidence_supplied = evidence_supplied
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


class HandbackRefused(VibeyError):
    """A handback was asked for with no successful probe recorded after the latest
    failover, or with a failover that names no known engine (ADR-0070)."""


class LeaseReapIncomplete(VibeyError):
    """Some expired leases could not be reaped (ADR-0056, #1108 review finding 8).

    Each lease is reaped in a transaction of its own, so one row that cannot be moved never
    rolls back or blocks the others. `reaped` holds the verdicts that were written and
    recorded; `failures` names each lease left as it was, and why. Raised only after every
    other lease was tried.
    """

    def __init__(self, reaped: tuple[object, ...], failures: tuple[str, ...]) -> None:
        self.reaped = reaped
        self.failures = failures
        super().__init__(
            f"{len(failures)} expired lease(s) could not be reaped, {len(reaped)} were: "
            + "; ".join(failures)
        )


class ClassifiedFailure(VibeyError):
    """A failure that already knows which `FailureClass` it is.

    The worker records any other exception a handler raises as `FailureClass.VIBEY` --
    our own bug. That is the right default and the wrong answer for a failure whose cause
    is known at the point it is raised: a model that ran out of output budget, or one
    that answered in the wrong shape, is not a bug in vibey, and an operator reading the
    exhausted-attempts gate needs to be told which it was. Subclasses name their class.
    """

    failure_class: ClassVar[FailureClass] = FailureClass.VIBEY


class OutputBudgetExhausted(ClassifiedFailure):
    """A local model spent its whole output budget without producing an answer.

    Observed on gpt-oss:20b: with `done_reason == "length"` the reply carries empty
    content and a full reasoning channel -- the reasoning consumed every token it was
    allowed. At temperature 0 an unchanged request fails the same way again, so this is
    raised only after one bounded retry with a larger budget and lighter reasoning.

    CAPACITY, not VIBEY or WORK: a configured resource limit refused the request, the way
    a vendor's quota does. It is NOT a `CapacityState`: `WindowExhausted` promises that
    waiting helps and `CreditsExhausted` that money does, and neither is true here --
    only a larger `VIBEY_OLLAMA_OUTPUT` / `VIBEY_OLLAMA_CONTEXT` (or a smaller prompt)
    changes the outcome. So it is a bounded Failure, never a Defer that would retry an
    identical request forever.
    """

    failure_class = FailureClass.CAPACITY

    def __init__(self, model: str, *, output_tokens: int, context_tokens: int) -> None:
        self.model = model
        self.output_tokens = output_tokens
        self.context_tokens = context_tokens
        super().__init__(
            f"{model} spent its whole output budget ({output_tokens} tokens in a "
            f"{context_tokens}-token context) without producing an answer, after a "
            "widened retry; raise VIBEY_OLLAMA_OUTPUT / VIBEY_OLLAMA_CONTEXT or shrink "
            "the prompt"
        )


class ModelAnswerRejected(ClassifiedFailure, ValueError):
    """A model's answer broke the shape its caller requires, after one re-ask naming why.

    ENGINE, because the engine produced it: the work asked of it is sound and vibey read
    the answer correctly. Also a `ValueError`, so every caller that already treats a
    malformed answer as one keeps doing so.
    """

    failure_class = FailureClass.ENGINE

    def __init__(self, subject: str, violations: tuple[str, ...]) -> None:
        self.subject = subject
        self.violations = violations
        super().__init__(f"{subject} was rejected after a re-ask: " + "; ".join(violations))
