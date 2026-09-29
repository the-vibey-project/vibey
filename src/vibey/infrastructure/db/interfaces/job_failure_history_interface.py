# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind a job's failures on the ledger.

Mirrors `vibey/infrastructure/db/job_failure_history.py` (ADR-0016). Interfaces declare;
they never consume. The DTO, domain and draft types are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.defect_triage import JobFailureHistory

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.application.dto import JobRecord
    from vibey.domain.defect import FailureSignature
    from vibey.domain.phase import Phase
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class JobFailedDraftBuilderInterface(Protocol):
    """Builds the `JobFailed` draft for one failed run of a job's handler."""

    def draft(
        self,
        job: JobRecord,
        signature: FailureSignature,
        *,
        detail: str,
        phase: Phase,
        at: datetime,
    ) -> LedgerEventDraft: ...


@runtime_checkable
class PostgresJobFailureHistoryInterface(JobFailureHistory, Protocol):
    """Records a job's failures on the ledger and reads the latest back, newest first."""
