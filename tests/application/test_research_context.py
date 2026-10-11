# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the project is about, in a sentence, for a research query."""

from datetime import UTC, datetime

from vibey.application.design import DesignEvent
from vibey.application.research_context import research_context
from vibey.domain.ledger import EventKind, Provenance


def _event(kind: EventKind, text: str = "") -> DesignEvent:
    return DesignEvent(
        kind=kind,
        provenance=Provenance.UNTRUSTED,
        produced_at=datetime(2026, 10, 10, tzinfo=UTC),
        payload={"text": text},
    )


def _intake(text: str) -> list[DesignEvent]:
    return [_event(EventKind.PHASE_TRANSITIONED), _event(EventKind.TRANSCRIPT_RECORDED, text)]


def test_the_objective_sections_first_sentence_is_the_context() -> None:
    text = "# Intake: x\n\n## Objective\n\nFold the ministry into this site. Reuse the essays code.\n\n## Source\n\nmore"
    assert research_context(_intake(text)) == "Fold the ministry into this site."


def test_a_wrapped_objective_paragraph_is_joined_and_stops_at_the_next_heading() -> None:
    text = "## objective\nBuild the thing\nacross two lines. Second sentence.\n## Next\nignored"
    assert research_context(_intake(text)) == "Build the thing across two lines."


def test_without_an_objective_section_the_first_line_of_prose_is_used() -> None:
    assert (
        research_context(_intake("# Title only\n\nBuild a widget. It is small.\n"))
        == "Build a widget."
    )


def test_an_objective_heading_with_nothing_under_it_gives_nothing() -> None:
    assert research_context(_intake("## Objective\n\n## Next\ntext")) == ""
    assert research_context(_intake("## Objective\n")) == ""


def test_an_intake_with_no_prose_or_no_intake_at_all_gives_nothing() -> None:
    assert research_context(_intake("# Only a heading\n")) == ""
    assert research_context([_event(EventKind.PHASE_TRANSITIONED)]) == ""
    assert research_context([]) == ""
