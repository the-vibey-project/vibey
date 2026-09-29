# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""``design.research`` handler with forced untrusted provenance.

A provider that can obtain no evidence refuses rather than invent a source. What the job
does then is `[design.research] on_unavailable`: park a `research_evidence` gate for a
person (`gate`, the default), or record the topic as not researched and succeed
(`record_gap`) -- a `ResearchGapRecorded` event, never a fabricated `ResearchResult`.
"""

from vibey.application.design import research_event
from vibey.application.design_handler import DesignLedger
from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces import (
    ResearchProvider,
)
from vibey.application.interfaces.research_gaps import ResearchGapRecordsInterface
from vibey.application.ports import Clock
from vibey.application.research_gaps import RESEARCH_GAP_RECORDS
from vibey.application.worker import Failure, Outcome, Park, Success
from vibey.domain.engine import EngineId
from vibey.domain.errors import SovereignResearchUnavailable
from vibey.domain.job import FailureClass
from vibey.domain.research_gap import (
    DEFAULT_RESEARCH_ON_UNAVAILABLE,
    ResearchGap,
    ResearchOnUnavailable,
)

#: The human gate a research refusal parks on. Its own kind rather than the generic
#: `attempts_exhausted`, because what the human is being asked for is different: not
#: "grant more tries" but "supply the reading" -- and a prompt about the wrong thing is
#: how a gate gets answered without the problem being fixed.
RESEARCH_EVIDENCE_GATE_KIND = "research_evidence"

#: Where the operator leaves reading for a provider that cannot fetch its own. Declared
#: once, here, so the gate prompt and the provider that reads the variable (ADR-0027)
#: can never name two different knobs.
EVIDENCE_DIR_ENV = "VIBEY_EVIDENCE_DIR"


class DesignResearchHandler:
    def __init__(
        self,
        *,
        ledger: DesignLedger,
        researcher: ResearchProvider,
        clock: Clock,
        engine_id: EngineId | None,
        on_unavailable: ResearchOnUnavailable = DEFAULT_RESEARCH_ON_UNAVAILABLE,
        gaps: ResearchGapRecordsInterface = RESEARCH_GAP_RECORDS,
    ) -> None:
        self._ledger = ledger
        self._researcher = researcher
        self._clock = clock
        self._engine_id = engine_id
        self._on_unavailable = on_unavailable
        self._gaps = gaps

    async def handle(self, job: JobRecord) -> Outcome:
        if job.kind != "design.research":
            return Failure(FailureClass.VIBEY, "expected design.research job")
        topic = str(job.payload.get("topic", "")).strip()
        if not topic:
            return Failure(FailureClass.WORK, "design.research requires a topic")
        try:
            result = await self._researcher.research(topic)
        except SovereignResearchUnavailable as refusal:
            if self._records_gap(refusal):
                return await self._record_gap(job, topic, refusal)
            # Parked on the first attempt, never retried. Before this the refusal
            # surfaced as a generic VIBEY failure: six silent retries with backoff, then
            # an `attempts_exhausted` gate asking for more attempts -- none of which could
            # ever succeed, because nothing about the next try would be different until a
            # human supplied the reading. Doctrine 10 wants the floor declared at the
            # moment it is known; this is that moment.
            return Park(
                HumanGateRequest(
                    kind=RESEARCH_EVIDENCE_GATE_KIND,
                    prompt=self._evidence_prompt(topic, refusal),
                )
            )
        event = research_event(result, now=self._clock.now())
        await self._ledger.append(job.project_id, job.cycle, job.id, self._engine_id, event)
        return Success({"topic": topic, "source": result.source})

    def _records_gap(self, refusal: SovereignResearchUnavailable) -> bool:
        """Whether this refusal becomes a recorded gap instead of a gate.

        Only when the operator declared `record_gap`, and only for an absence of evidence.
        Reading that was supplied and cannot be attributed is an operator's mistake to fix:
        recording it as "not researched" would silently set their material aside.
        """
        return (
            self._on_unavailable is ResearchOnUnavailable.RECORD_GAP
            and not refusal.evidence_supplied
        )

    async def _record_gap(
        self, job: JobRecord, topic: str, refusal: SovereignResearchUnavailable
    ) -> Outcome:
        gap = ResearchGap(topic=topic, reason=refusal.detail)
        event = self._gaps.event(gap, now=self._clock.now(), cycle=job.cycle)
        await self._ledger.append(job.project_id, job.cycle, job.id, self._engine_id, event)
        # No `source` key: there is none, and a result shaped like research would invite a
        # reader to treat it as research.
        return Success({"topic": topic, "researched": False, "gap": gap.reason})

    def _evidence_prompt(self, topic: str, refusal: SovereignResearchUnavailable) -> str:
        if refusal.evidence_name is None:
            remedy = (
                "No evidence file can match this topic, so the remedy is a provider that "
                "can retrieve the reading itself (for example `--provider claudeloop`); "
                "answer this gate once the worker runs one to retry the research."
            )
        else:
            remedy = (
                f"Put the reading at `{refusal.evidence_name}` in the directory "
                f"{EVIDENCE_DIR_ENV} names for this worker -- first line "
                "`source: <where it came from>`, then the text -- and answer this gate "
                "to run the research again."
            )
        if not refusal.evidence_supplied:
            # Said only for an absence: a supplied file that cannot be attributed is fixed,
            # never skipped, whatever the policy.
            remedy += (
                " Or, to let DESIGN proceed without this reading, declare "
                f'`[design.research] on_unavailable = "{ResearchOnUnavailable.RECORD_GAP}"` '
                "for the worker and answer this gate: the topic is then recorded as not "
                "researched, and the spec says so."
            )
        return (
            f"design.research stopped on {topic!r} rather than invent a source. "
            f"{refusal.detail}\n\n{remedy} Any answer retries, for example "
            "`vibey answer GATE_ID --raw '{}'`."
        )


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "EVIDENCE_DIR_ENV",
    "RESEARCH_EVIDENCE_GATE_KIND",
    "DesignResearchHandler",
    "ResearchProvider",
]
