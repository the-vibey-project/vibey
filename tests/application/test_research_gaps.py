# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Research gaps on the DESIGN ledger: the event written, and a cycle's gaps read back.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from datetime import UTC, datetime

from vibey.application.design import DesignEvent, ResearchResult, research_event
from vibey.application.interfaces import ResearchGapRecordsInterface
from vibey.application.research_gaps import RESEARCH_GAP_RECORDS, ResearchGapRecords
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.research_gap import ResearchGap

NOW = datetime(2026, 9, 29, tzinfo=UTC)


def test_the_records_meet_their_declared_seam() -> None:
    assert isinstance(RESEARCH_GAP_RECORDS, ResearchGapRecordsInterface)
    assert isinstance(ResearchGapRecords(), ResearchGapRecordsInterface)


def test_a_gap_is_a_trusted_event_with_no_source_and_no_content() -> None:
    event = RESEARCH_GAP_RECORDS.event(ResearchGap("prior-art", "no web"), now=NOW, cycle=2)
    assert event == DesignEvent(
        kind=EventKind.RESEARCH_GAP_RECORDED,
        provenance=Provenance.TRUSTED,
        produced_at=NOW,
        payload={"topic": "prior-art", "reason": "no web", "cycle": 2},
    )


def test_a_cycles_gaps_are_read_back_once_each_in_order() -> None:
    records = RESEARCH_GAP_RECORDS
    events = [
        records.event(ResearchGap("prior-art", "first"), now=NOW, cycle=1),
        research_event(ResearchResult("docs", "https://example.test", "text"), now=NOW),
        records.event(ResearchGap("libraries", "second"), now=NOW, cycle=1),
        # A replayed research job writes its gap again; the spec states it once.
        records.event(ResearchGap("prior-art", "replayed"), now=NOW, cycle=1),
        # Another cycle's gap is that cycle's: a later design may have done the research.
        records.event(ResearchGap("api-docs", "old"), now=NOW, cycle=2),
    ]
    assert records.gaps(events, cycle=1) == (
        ResearchGap("prior-art", "first"),
        ResearchGap("libraries", "second"),
    )
    assert records.gaps(events, cycle=2) == (ResearchGap("api-docs", "old"),)
    assert records.gaps(events, cycle=3) == ()
