# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace
from datetime import UTC, datetime

from vibey.application.design import DesignEvent
from vibey.application.design_spec import (
    build_design_evidence,
    count_open_blocking_questions,
    render_design_artifacts,
)
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import (
    ALLOWED,
    Denied,
    Phase,
    PhaseState,
    TransitionRequest,
    evaluate_transition,
)
from vibey.domain.research_gap import ResearchGap
from vibey.domain.review import UserVerdict
from vibey.domain.spec import (
    AcceptanceCriterion,
    Constraint,
    ConstraintKind,
    DesignSpec,
    NonFunctionalRequirement,
)


def buildable_spec() -> DesignSpec:
    return DesignSpec(
        objective="Deliver a queue-based conductor",
        constraints=(Constraint("Postgres is never mocked", ConstraintKind.HARD),),
        non_goals=("Hosted control plane",),
        criteria=(
            AcceptanceCriterion(
                "AC-1",
                "a design interview",
                "the user accepts the output",
                "the spec is buildable",
                "is_buildable() returns no violations",
            ),
        ),
        nfrs=(
            NonFunctionalRequirement(
                "NFR-1",
                "question batch size",
                "questions per turn",
                "count emitted questions",
                "at most 4",
                "3 or fewer",
                "every emitted batch has len <= 4",
            ),
        ),
        walking_skeleton="One scripted interview produces all three artifacts",
    )


def test_buildable_spec_renders_all_required_context_artifacts() -> None:
    artifacts = render_design_artifacts(
        buildable_spec(), decisions=("Use Postgres",), assumptions=("Local only",)
    )
    assert set(artifacts) == {
        "spec.md",
        "acceptance.md",
        "nfr.md",
        "decisions.md",
        "open-items.md",
    }
    assert "Walking skeleton" in artifacts["spec.md"]
    assert "Given a design interview" in artifacts["acceptance.md"]
    assert "Scale: questions per turn" in artifacts["nfr.md"]
    assert buildable_spec().is_buildable() == ()


def test_a_spec_with_no_gaps_says_nothing_about_research() -> None:
    artifacts = render_design_artifacts(buildable_spec())
    assert "Research not performed" not in artifacts["spec.md"]
    assert artifacts["spec.md"].endswith(
        "## Walking skeleton\n\nOne scripted interview produces all three artifacts\n"
    )
    assert artifacts["open-items.md"] == "# Open items and assumptions\n\n- None\n"


def test_the_spec_states_plainly_each_topic_that_was_not_researched() -> None:
    gaps = (
        ResearchGap("prior-art", "a local model has no web access."),
        ResearchGap("libraries", "VIBEY_EVIDENCE_DIR is unset."),
    )
    artifacts = render_design_artifacts(
        replace(buildable_spec(), research_gaps=gaps), assumptions=("Local only",)
    )
    spec_md = artifacts["spec.md"]
    assert spec_md.endswith(
        "## Research not performed\n\n"
        "These research topics were not researched. No source was consulted for them, and "
        "nothing in this spec rests on findings about them.\n\n"
        "- prior-art: not researched. a local model has no web access.\n"
        "- libraries: not researched. VIBEY_EVIDENCE_DIR is unset.\n"
    )
    # The open items carry them too, beside the assumptions a reviewer weighs.
    assert artifacts["open-items.md"] == (
        "# Open items and assumptions\n\n"
        "- Local only\n"
        "- Research not performed -- prior-art: not researched. a local model has no web "
        "access.\n"
        "- Research not performed -- libraries: not researched. VIBEY_EVIDENCE_DIR is unset.\n"
    )


def test_renderer_rejects_an_unbuildable_spec() -> None:
    invalid = DesignSpec("", (), (), (), (), "")
    try:
        render_design_artifacts(invalid)
    except ValueError as exc:
        assert "acceptance criterion" in str(exc)
    else:
        raise AssertionError("expected invalid spec rejection")


def test_real_design_evidence_drives_the_domain_guard() -> None:
    state = PhaseState(Phase.DESIGN, 1, 10, datetime.now(UTC))
    accepted = build_design_evidence(buildable_spec(), open_blocking_questions=0, accepted=True)
    request = TransitionRequest(Phase.BUILD, "accepted", accepted)
    assert evaluate_transition(state, request) == ALLOWED

    blocked = build_design_evidence(buildable_spec(), open_blocking_questions=1, accepted=True)
    outcome = evaluate_transition(state, TransitionRequest(Phase.BUILD, "accepted", blocked))
    assert isinstance(outcome, Denied)
    assert "blocking question" in outcome.violations[0]


def test_unaccepted_design_evidence_has_no_user_verdict() -> None:
    evidence = build_design_evidence(buildable_spec(), open_blocking_questions=0, accepted=False)
    assert evidence.user_verdict is None
    assert UserVerdict.ACCEPT is not evidence.user_verdict


def test_only_unanswered_blocking_questions_are_counted() -> None:
    now = datetime.now(UTC)
    events = (
        DesignEvent(
            EventKind.QUESTION_ASKED, Provenance.AGENT, now, {"item_id": "q1", "blocking": True}
        ),
        DesignEvent(
            EventKind.QUESTION_ASKED, Provenance.AGENT, now, {"item_id": "q2", "blocking": True}
        ),
        DesignEvent(
            EventKind.QUESTION_ASKED, Provenance.AGENT, now, {"item_id": "q3", "blocking": False}
        ),
        DesignEvent(
            EventKind.ANSWER_GIVEN, Provenance.TRUSTED, now, {"item_id": "q1", "answer": "yes"}
        ),
    )
    assert count_open_blocking_questions(events) == 1
