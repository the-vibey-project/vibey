# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Research gaps on the DESIGN ledger: written by `design.research`, read by synthesis.

A gap is recorded when `[design.research] on_unavailable = "record_gap"` and a topic's
provider could obtain no evidence (domain/research_gap.py). The event carries the topic,
the reason and the cycle -- no source and no content, so nothing downstream can mistake
it for research -- and synthesis reads the cycle's gaps back into the spec, which states
each one.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Final

from vibey.application.design import DesignEvent
from vibey.application.interfaces.research_gaps import ResearchGapRecordsInterface
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.research_gap import ResearchGap


class ResearchGapRecords:
    """Declared by `ResearchGapRecordsInterface`. Stateless."""

    def event(self, gap: ResearchGap, *, now: datetime, cycle: int) -> DesignEvent:
        # Trusted: every word of it is vibey's. The reason is the provider's own refusal,
        # not text read from outside, and there is no content to be untrusted about.
        return DesignEvent(
            kind=EventKind.RESEARCH_GAP_RECORDED,
            provenance=Provenance.TRUSTED,
            produced_at=now,
            payload={"topic": gap.topic, "reason": gap.reason, "cycle": cycle},
        )

    def gaps(self, events: Sequence[DesignEvent], *, cycle: int) -> tuple[ResearchGap, ...]:
        # One per topic: a research job replayed after its append but before its success
        # writes the same gap again, and the spec should state it once.
        found: dict[str, ResearchGap] = {}
        for event in events:
            if event.kind is not EventKind.RESEARCH_GAP_RECORDED:
                continue
            if event.payload.get("cycle") != cycle:
                continue
            topic = str(event.payload["topic"])
            if topic not in found:
                found[topic] = ResearchGap(topic=topic, reason=str(event.payload["reason"]))
        return tuple(found.values())


RESEARCH_GAP_RECORDS: Final[ResearchGapRecordsInterface] = ResearchGapRecords()
"""What the research and synthesis handlers record and read gaps through."""
