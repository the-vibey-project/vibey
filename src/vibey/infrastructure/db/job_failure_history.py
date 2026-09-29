# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A job's failures on the ledger: one `JobFailed` event per failed run of its handler.

The worker records each failure's signature (domain/defect.py) and, before offering an
exhausted job more attempts, reads the last few back. Each record is one run: a worker
that dies after recording and before settling leaves a record of a run that did fail, and
the job's next claim is another run with its own. So there is nothing to de-duplicate; the
records are read newest first by the ledger's own order (`seq`), never by a timestamp.

The event is filed under the job's own cycle and phase, with the job's id and no engine,
and is `trusted`: vibey's own observation that the run failed. Its `detail` quotes what the
handler raised and is redacted on append like every payload
(`ConnectionEventAppender`); `JobFailed` is withheld from publication whole.

Declared by `interfaces/job_failure_history_interface.py` (ADR-0016).
"""

import json
from datetime import datetime
from typing import Final

import asyncpg

from vibey.application.dto import JobRecord
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.defect import FailureSignature
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.db.interfaces import (
    EventAppenderInterface,
    JobFailedDraftBuilderInterface,
)
from vibey.infrastructure.db.ledger_repository import DEFAULT_EVENT_APPENDER
from vibey.infrastructure.engines.tailer import LedgerEventDraft

DETAIL_LIMIT: Final = 4_000
"""How much of a failure's own text the record keeps. The signature covers all of it."""

_RECENT: Final = """
SELECT payload FROM event
WHERE project_id = $1 AND kind = $2 AND job_id = $3
ORDER BY seq DESC
LIMIT $4
"""


class JobFailedDraftBuilder:
    """Turns one failed run into its `JobFailed` ledger draft. Stateless."""

    def __init__(self, correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION) -> None:
        self._correlation = correlation

    def draft(
        self,
        job: JobRecord,
        signature: FailureSignature,
        *,
        detail: str,
        phase: Phase,
        at: datetime,
    ) -> LedgerEventDraft:
        payload: dict[str, object] = {
            "job_id": str(job.id),
            "job_kind": job.kind,
            "work_item_id": job.work_item_id,
            "attempt": job.attempts,
            "max_attempts": job.max_attempts,
            **signature.payload(),
            "detail": detail[:DETAIL_LIMIT],
        }
        return LedgerEventDraft(
            project_id=job.project_id,
            cycle=job.cycle,
            phase=phase,
            kind=EventKind.JOB_FAILED,
            engine_id=None,
            job_id=job.id,
            causation_id=None,
            correlation_id=self._correlation.for_project(job.project_id).value,
            provenance=Provenance.TRUSTED,
            produced_at=at,
            payload=payload,
            digest=digest_event(payload),
        )


JOB_FAILED_DRAFTS: Final[JobFailedDraftBuilderInterface] = JobFailedDraftBuilder()


class PostgresJobFailureHistory:
    """Records a job's failures and reads its most recent ones back."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        drafts: JobFailedDraftBuilderInterface = JOB_FAILED_DRAFTS,
        appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER,
    ) -> None:
        self._pool = pool
        self._drafts = drafts
        self._appender = appender

    async def record(self, job: JobRecord, signature: FailureSignature, *, detail: str) -> None:
        if not isinstance(job.phase, Phase):
            # The claim never hands out a job whose phase this vibey does not know
            # (vibey#287), so nothing reaches here with one; writers stay strict anyway.
            raise ValueError(f"job {job.id} is in phase {job.phase.value!r}, unknown here")
        async with self._pool.acquire() as conn, conn.transaction():
            now = await conn.fetchval("SELECT now()")
            await self._appender.append(
                conn, self._drafts.draft(job, signature, detail=detail, phase=job.phase, at=now)
            )

    async def recent(self, job: JobRecord, *, limit: int) -> tuple[FailureSignature, ...]:

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                _RECENT, job.project_id, EventKind.JOB_FAILED.value, job.id, limit
            )
        found: list[FailureSignature] = []
        for row in rows:
            signature = FailureSignature.from_payload(json.loads(row["payload"]))
            if signature is not None:
                found.append(signature)
        return tuple(found)
