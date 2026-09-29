# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A grant, or a defect: what an exhausted job's gate offers.

A job that burns its last attempt parks on a gate (ADR-0024), and until now that gate
always offered more attempts -- `attempts_exhausted` from the worker, `escalation_exhausted`
from build.implement's effort ladder -- however the attempts had failed. On one project the
operator granted attempts six times on two jobs that failed identically every time.

So the worker records every failure (`JobFailed`, with its signature: domain/defect.py),
and before it raises a grant-offering gate it reads the job's last `[queue.defect]
identical_failures` back. When they are one failure, it raises a `defect` gate instead: the
signature and how many attempts shared it, and two answers that offer nothing more --
`requeue` to run the job once more after a fix has landed, `abandon` to cancel it. Varied
failures keep the grant: they may yet succeed.

Every step fails open to the old behaviour. A failure that cannot be recorded, or history
that cannot be read, is said at warning and leaves the gate a grant: a person is still
asked, and nothing is concluded from a record nobody could read (10.f).
"""

from typing import Final

from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces.defect_triage import DefectGateInterface, JobFailureHistory
from vibey.application.interfaces.observability import Logger
from vibey.domain.defect import (
    DEFAULT_IDENTICAL_FAILURES,
    DEFECT_ABANDON,
    DEFECT_OPTIONS,
    DEFECT_REQUEUE,
    FAILURE_NORMALIZER,
    MIN_IDENTICAL_FAILURES,
    REPEATED_FAILURE_POLICY,
    DefectVerdict,
)
from vibey.domain.interfaces.defect_interface import (
    FailureNormalizerInterface,
    RepeatedFailurePolicyInterface,
)
from vibey.domain.job import DEFECT_GATE_KIND, GRANT_EXHAUSTION_KINDS, FailureClass


class DefectGate:
    """The request a `defect` gate carries. Stateless."""

    def request(self, job: JobRecord, verdict: DefectVerdict) -> HumanGateRequest:
        signature = verdict.signature
        item = f" (work item {job.work_item_id!r})" if job.work_item_id is not None else ""
        return HumanGateRequest(
            kind=DEFECT_GATE_KIND,
            prompt=(
                f"job {job.kind!r}{item} failed the same way on each of its last "
                f"{verdict.identical} attempts -- {signature.failure_class}: "
                f"{signature.excerpt} (signature {signature.digest}). More attempts will "
                "not change that, so none are offered. Fix the cause, then answer "
                f"--choice {DEFECT_REQUEUE} to run it again -- it parks here at once if "
                f"it fails the same way -- or --choice {DEFECT_ABANDON} to cancel it "
                "(work that depends on it will not run)."
            ),
            options=DEFECT_OPTIONS,
        )


DEFECT_GATE: Final[DefectGateInterface] = DefectGate()


class DefectTriage:
    """Records each failure of a job, and decides at exhaustion between a grant and a
    `defect` gate."""

    def __init__(
        self,
        *,
        history: JobFailureHistory,
        logger: Logger,
        threshold: int = DEFAULT_IDENTICAL_FAILURES,
        normalizer: FailureNormalizerInterface = FAILURE_NORMALIZER,
        policy: RepeatedFailurePolicyInterface = REPEATED_FAILURE_POLICY,
        gate: DefectGateInterface = DEFECT_GATE,
    ) -> None:
        self._history = history
        self._log = logger
        self._threshold = threshold
        self._normalizer = normalizer
        self._policy = policy
        self._gate = gate

    async def record(self, job: JobRecord, failure_class: FailureClass, detail: str) -> None:
        signature = self._normalizer.signature(failure_class.value, detail)
        try:
            await self._history.record(job, signature, detail=detail)
        except Exception as exc:  # noqa: BLE001 - an unrecorded failure must not lose the job
            self._log.warning(
                "job.failure_unrecorded",
                job_id=str(job.id),
                project_id=str(job.project_id),
                kind=job.kind,
                signature=signature.digest,
                error=repr(exc),
            )

    async def triage(self, job: JobRecord, request: HumanGateRequest) -> HumanGateRequest:
        if request.kind not in GRANT_EXHAUSTION_KINDS or self._threshold < MIN_IDENTICAL_FAILURES:
            return request
        try:
            recent = await self._history.recent(job, limit=self._threshold)
        except Exception as exc:  # noqa: BLE001 - unread history leaves the grant in place
            self._log.warning(
                "job.failure_history_unreadable",
                job_id=str(job.id),
                project_id=str(job.project_id),
                kind=job.kind,
                error=repr(exc),
            )
            return request
        verdict = self._policy.judge(recent, threshold=self._threshold)
        if verdict is None:
            return request
        self._log.warning(
            "job.defect",
            job_id=str(job.id),
            project_id=str(job.project_id),
            kind=job.kind,
            signature=verdict.signature.digest,
            failure_class=verdict.signature.failure_class,
            identical=verdict.identical,
            instead_of=request.kind,
        )
        return self._gate.request(job, verdict)
