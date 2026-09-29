# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Synthesis and final publication handlers for DESIGN."""

from dataclasses import replace

from vibey.application.design_handler import DesignLedger
from vibey.application.dto import JobRecord
from vibey.application.interfaces import (
    DesignSpecRepository,
    SpecSynthesizer,
)
from vibey.application.interfaces.research_gaps import ResearchGapRecordsInterface
from vibey.application.research_gaps import RESEARCH_GAP_RECORDS
from vibey.application.worker import Failure, Outcome, Success
from vibey.domain.job import FailureClass


class DesignSynthesizeHandler:
    def __init__(
        self,
        *,
        ledger: DesignLedger,
        synthesizer: SpecSynthesizer,
        specs: DesignSpecRepository,
        gaps: ResearchGapRecordsInterface = RESEARCH_GAP_RECORDS,
    ) -> None:
        self._ledger = ledger
        self._synthesizer = synthesizer
        self._specs = specs
        self._gaps = gaps

    async def handle(self, job: JobRecord) -> Outcome:
        if job.kind != "design.synthesize":
            return Failure(FailureClass.VIBEY, "expected design.synthesize job")
        events = await self._ledger.all_for_project(job.project_id)
        spec = await self._synthesizer.synthesize(events)
        violations = spec.is_buildable()
        if violations:
            return Failure(FailureClass.WORK, "; ".join(violations))
        # The gaps come from the ledger, not the model: whatever the synthesizer wrote, the
        # spec states every topic this cycle did not research, so REVIEW and a person see
        # the gap rather than a silence.
        gaps = self._gaps.gaps(events, cycle=job.cycle)
        spec = replace(spec, research_gaps=gaps)
        await self._specs.save(job.project_id, job.cycle, spec)
        return Success(
            {
                "acceptance_criteria": len(spec.criteria),
                "research_gaps": [gap.topic for gap in gaps],
            }
        )


class DesignSpecHandler:
    def __init__(self, *, specs: DesignSpecRepository) -> None:
        self._specs = specs

    async def handle(self, job: JobRecord) -> Outcome:
        if job.kind != "design.spec":
            return Failure(FailureClass.VIBEY, "expected design.spec job")
        spec = await self._specs.load(job.project_id, job.cycle)
        if spec is None:
            return Failure(FailureClass.WORK, "no synthesized design spec exists")
        await self._specs.publish(job.project_id, job.cycle, spec)
        return Success({"acceptance_criteria": len(spec.criteria)})


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "DesignSpecRepository",
    "SpecSynthesizer",
]
