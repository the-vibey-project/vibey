# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A research gap: the typed statement that a topic was not researched, and why.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

import dataclasses

import pytest

from vibey.domain.errors import SovereignResearchUnavailable
from vibey.domain.interfaces import ResearchGapInterface
from vibey.domain.research_gap import (
    DEFAULT_RESEARCH_ON_UNAVAILABLE,
    ResearchGap,
    ResearchOnUnavailable,
)
from vibey.domain.spec import AcceptanceCriterion, DesignSpec


def test_absence_of_evidence_waits_for_a_person_by_default() -> None:
    assert DEFAULT_RESEARCH_ON_UNAVAILABLE is ResearchOnUnavailable.GATE
    assert [policy.value for policy in ResearchOnUnavailable] == ["gate", "record_gap"]


def test_a_gap_names_its_topic_and_reason_and_carries_no_source() -> None:
    gap = ResearchGap(topic="prior-art", reason="no web access and no evidence file.")
    assert isinstance(gap, ResearchGapInterface)
    assert gap.statement() == "prior-art: not researched. no web access and no evidence file."
    # There is nothing to cite, so there is no field a citation could be put in.
    assert {field.name for field in dataclasses.fields(gap)} == {"topic", "reason"}


@pytest.mark.parametrize(
    ("topic", "reason", "message"),
    [("  ", "why", "names the topic"), ("prior-art", "", "says why")],
)
def test_a_gap_without_a_topic_or_a_reason_is_refused(
    topic: str, reason: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ResearchGap(topic=topic, reason=reason)


def test_a_spec_states_no_gaps_unless_given_them() -> None:
    criterion = AcceptanceCriterion("AC-1", "a", "b", "c", "d")
    spec = DesignSpec("Ship", (), (), (criterion,), (), "one path")
    assert spec.research_gaps == ()
    gap = ResearchGap("libraries", "none supplied")
    assert dataclasses.replace(spec, research_gaps=(gap,)).research_gaps == (gap,)


def test_a_refusal_says_whether_the_operator_supplied_reading() -> None:
    """An absence may become a recorded gap; supplied reading that cannot be used may not."""
    absent = SovereignResearchUnavailable("topic", "none", evidence_name="topic.md")
    assert absent.evidence_supplied is False
    unusable = SovereignResearchUnavailable(
        "topic", "no source line", evidence_name="topic.md", evidence_supplied=True
    )
    assert unusable.evidence_supplied is True
    assert (unusable.topic, unusable.detail, unusable.evidence_name) == (
        "topic",
        "no source line",
        "topic.md",
    )
