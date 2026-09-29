# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Defect triage's seams: where a job's failures are kept, and the service that decides,
at exhaustion, between a grant and a `defect` gate.

Mirrors `vibey/application/defect_triage.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.domain.defect import DefectVerdict, FailureSignature
from vibey.domain.job import FailureClass


@runtime_checkable
class DefectGateInterface(Protocol):
    """The request a `defect` gate carries: the signature, how many attempts shared it, and
    answers that offer no more attempts."""

    def request(self, job: JobRecord, verdict: DefectVerdict) -> HumanGateRequest: ...


@runtime_checkable
class JobFailureHistory(Protocol):
    """A job's failures, one `JobFailed` event each."""

    async def record(self, job: JobRecord, signature: FailureSignature, *, detail: str) -> None:
        """Append one `JobFailed` event for this run of the job's handler."""
        ...

    async def recent(self, job: JobRecord, *, limit: int) -> tuple[FailureSignature, ...]:
        """The job's last `limit` recorded failures, newest first."""
        ...


@runtime_checkable
class DefectTriageInterface(Protocol):
    """Records each failure, and turns an exhaustion gate into a `defect` gate when the
    failures it follows were all one failure."""

    async def record(self, job: JobRecord, failure_class: FailureClass, detail: str) -> None:
        """Never raises: a failure that cannot be recorded is said at warning."""
        ...

    async def triage(self, job: JobRecord, request: HumanGateRequest) -> HumanGateRequest:
        """`request` itself unless it is a grant-offering exhaustion gate and the job's last
        failures share one signature; then the `defect` gate, which offers no grant. Never
        raises: history that cannot be read leaves `request` as it was."""
        ...
