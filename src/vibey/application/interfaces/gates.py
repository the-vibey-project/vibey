# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Human gates: the parked-job seam a person answers (ADR-0009)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import (
    GateAnswerOutcome,
    HumanGateRecord,
    HumanGateRequest,
)


@runtime_checkable
class HumanGateRepository(Protocol):
    async def raise_gate(
        self, project_id: UUID, job_id: UUID | None, request: HumanGateRequest
    ) -> HumanGateRecord: ...

    async def answer(
        self,
        gate_id: UUID,
        *,
        answer: Mapping[str, object],
        answered_by: str,
        account: str | None = None,
        request_id: str | None = None,
    ) -> HumanGateRecord:
        """`answer_once`'s record. With no `request_id` the call is a new request, so a
        gate already answered is refused (`GateAlreadyAnswered`)."""
        ...

    async def answer_once(
        self,
        gate_id: UUID,
        *,
        answer: Mapping[str, object],
        answered_by: str,
        account: str | None,
        request_id: str,
    ) -> GateAnswerOutcome:
        """Answers an open gate, once: a compare-and-set on `answered_at IS NULL`, with its
        `GateAnswered` event in the same transaction, and the gate's job made ready.

        A gate already answered by this `request_id` with this `answer` is a no-op
        (`replayed`); any other answer to an answered gate raises `GateAlreadyAnswered`,
        and a gate that does not exist `UnknownGate`. Refused, nothing is written."""
        ...

    async def latest_for_job(
        self, job_id: UUID, *, include_queue_gates: bool = False
    ) -> HumanGateRecord | None:
        """The job's most recent gate -- of the job's own asking.

        A gate the queue raised on the job's behalf (`domain.job.QUEUE_GATE_KINDS`: attempts
        or deliveries exhausted) is skipped unless `include_queue_gates`: answering one
        buys the job another delivery and answers nothing its handler asked (#1108 review,
        P7). Only the worker, which raised those gates, asks for them.
        """
        ...

    async def open_for_project(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        """Gates raised for this project and not yet answered, oldest first.

        The operator needs the whole set, not the latest: a project can be
        parked on several gates at once, and reporting only one would make
        answering it look like progress when nothing moved.
        """
        ...

    async def open_all(self) -> tuple[HumanGateRecord, ...]:
        """Every gate not yet answered, across all projects, oldest first: `raised_at`,
        then `gate_id`, so gates raised in one instant still list in one order.

        What `vibey gates` shows with no project named -- everything waiting on a
        person, in the order it started waiting.
        """
        ...
