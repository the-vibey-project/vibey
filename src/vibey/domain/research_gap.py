# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What DESIGN research does when no evidence can be had, and the record it leaves.

A research provider that cannot obtain a source refuses rather than invent one
(`SovereignResearchUnavailable`, ADR-0027). What happens next is the operator's declared
policy, `[design.research] on_unavailable`:

- `gate` (the default) parks a `research_evidence` human gate and waits for the reading.
  Absence of evidence waits for a person, as it always has.
- `record_gap` lets the phase proceed without a person -- never by fabricating. The topic
  becomes a `ResearchGap`: no source, no findings, only the topic and why it could not be
  researched. It is written to the ledger (`ResearchGapRecorded`) and carried into the
  synthesized spec, which says plainly that the topic was not researched, so REVIEW and
  a human can see the gap rather than a silence (sub-doctrine 10.f).
"""

from dataclasses import dataclass
from enum import StrEnum


class ResearchOnUnavailable(StrEnum):
    """What a research job does when its provider can obtain no evidence."""

    GATE = "gate"
    RECORD_GAP = "record_gap"


DEFAULT_RESEARCH_ON_UNAVAILABLE = ResearchOnUnavailable.GATE
"""Absence of evidence waits for a person unless the operator declares otherwise."""


@dataclass(frozen=True, slots=True)
class ResearchGap:
    """A research topic that was not researched, and why.

    Deliberately carries no `source` and no content: it is the typed statement that there
    is nothing to cite, so no reader can mistake it for research.
    """

    topic: str
    reason: str

    def __post_init__(self) -> None:
        if not self.topic.strip():
            raise ValueError("a research gap names the topic that was not researched")
        if not self.reason.strip():
            raise ValueError("a research gap says why the topic was not researched")

    def statement(self) -> str:
        """The gap as one plain sentence, for the spec a person and REVIEW read."""
        return f"{self.topic}: not researched. {self.reason}"
