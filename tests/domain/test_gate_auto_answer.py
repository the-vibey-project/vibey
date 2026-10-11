# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-answer` may answer, and, as much, what it never may."""

import pytest

from vibey.domain.gate_auto_answer import (
    AUTO_ANSWERS,
    DEFAULT_AUTO_ANSWER_LIMIT,
    GateAutoAnswerPolicy,
)


@pytest.mark.parametrize(
    ("kind", "answer"),
    [
        ("question", {"accept_defaults": True}),
        ("escalation_exhausted", {"max_attempts": 10}),
        ("verify_repair_exhausted", {"max_rounds": 6}),
        ("integrate_repair_exhausted", {"max_rounds": 6}),
        ("delivery_exhausted", {}),
    ],
)
def test_the_interview_and_the_retry_gates_get_the_answer_vibey_itself_suggests(
    kind: str, answer: dict[str, object]
) -> None:
    assert GateAutoAnswerPolicy().answer_for(kind) == answer


@pytest.mark.parametrize(
    "kind",
    [
        "budget_exhausted",
        "engine_misconfigured",
        "research_evidence",
        "approval",
        "choice",
        "deploy_acceptance",
        "deploy_demo_review",
        "no_such_kind",
        "",
    ],
)
def test_everything_else_waits_for_a_person_and_a_spending_gate_always_does(kind: str) -> None:
    assert GateAutoAnswerPolicy().answer_for(kind) is None


def test_no_gate_kind_that_spends_money_is_ever_in_the_table() -> None:
    """A guard on the table itself, so a later addition cannot quietly widen it."""
    assert not [kind for kind in AUTO_ANSWERS if "budget" in kind or "spend" in kind]


def test_the_answer_is_a_copy_a_caller_cannot_use_to_change_the_table() -> None:
    answer = GateAutoAnswerPolicy().answer_for("escalation_exhausted")
    assert answer is not None
    answer["max_attempts"] = 999
    assert GateAutoAnswerPolicy().answer_for("escalation_exhausted") == {"max_attempts": 10}


def test_the_limit_defaults_and_must_be_at_least_one() -> None:
    assert GateAutoAnswerPolicy().limit == DEFAULT_AUTO_ANSWER_LIMIT == 30
    assert GateAutoAnswerPolicy(limit=1).limit == 1
    for bad in (0, -3, True):
        with pytest.raises(ValueError, match="at least 1"):
            GateAutoAnswerPolicy(limit=bad)


REVIEW_OPTIONS = ("accept", "changes", "cancel")
DEPLOY_OPTIONS = ("local_only", "deploy")


def test_a_review_is_accepted_only_when_asked_for_and_only_with_the_accept_option() -> None:
    on = GateAutoAnswerPolicy(answer_retries=False, accept_review=True)

    assert on.answer_for("approval", REVIEW_OPTIONS) == {"verdict": "accept"}
    assert on.answer_for("approval", ("changes", "cancel")) is None
    assert on.answer_for("approval") is None
    assert GateAutoAnswerPolicy().answer_for("approval", REVIEW_OPTIONS) is None


def test_the_deployment_choice_is_only_ever_answered_local_only() -> None:
    on = GateAutoAnswerPolicy(answer_retries=False, finish_local=True)

    assert on.answer_for("choice", DEPLOY_OPTIONS) == {"choice": "local_only"}
    assert on.answer_for("choice", ("deploy",)) is None
    assert on.answer_for("choice") is None
    assert GateAutoAnswerPolicy().answer_for("choice", DEPLOY_OPTIONS) is None


def test_no_acceptance_flag_widens_to_a_deployment_a_spend_or_a_retry() -> None:
    everything = GateAutoAnswerPolicy(answer_retries=False, accept_review=True, finish_local=True)

    for kind in (
        "deploy_acceptance",
        "deploy_demo_review",
        "deploy_interview",
        "deploy_failure_triage",
        "budget_exhausted",
        "escalation_exhausted",
        "question",
        "research_evidence",
    ):
        assert everything.answer_for(kind, (*REVIEW_OPTIONS, *DEPLOY_OPTIONS)) is None, kind


def test_retries_can_be_switched_off_and_stay_on_by_default() -> None:
    assert GateAutoAnswerPolicy().answer_retries is True
    assert GateAutoAnswerPolicy(answer_retries=False).answer_for("escalation_exhausted") is None


PUBLISH_OPTIONS = ("accept_defaults", "custom", "skip")


def test_the_publish_interview_is_answered_as_proposed_only_when_asked_for() -> None:
    on = GateAutoAnswerPolicy(answer_retries=False, publish=True)

    assert on.answer_for("publish_interview", PUBLISH_OPTIONS) == {"choice": "accept_defaults"}
    assert on.answer_for("publish_interview", ("custom", "skip")) is None
    assert on.answer_for("publish_interview") is None
    assert GateAutoAnswerPolicy().answer_for("publish_interview", PUBLISH_OPTIONS) is None


def test_no_other_acceptance_flag_publishes_and_publishing_answers_nothing_else() -> None:
    everything_else = GateAutoAnswerPolicy(accept_review=True, finish_local=True)
    only_publish = GateAutoAnswerPolicy(answer_retries=False, publish=True)

    assert everything_else.answer_for("publish_interview", PUBLISH_OPTIONS) is None
    for kind in ("approval", "choice", "escalation_exhausted", "question", "deploy_acceptance"):
        assert only_publish.answer_for(kind, ("accept", "local_only")) is None, kind


def test_a_research_gap_is_recorded_only_when_asked_for() -> None:
    on = GateAutoAnswerPolicy(answer_retries=False, record_research_gaps=True)

    assert on.answer_for("research_evidence") == {}  # an empty answer, which retries the research
    assert GateAutoAnswerPolicy().answer_for("research_evidence") is None
    assert (
        GateAutoAnswerPolicy(accept_review=True, finish_local=True, publish=True).answer_for(
            "research_evidence"
        )
        is None
    )


def test_recording_research_gaps_answers_nothing_else() -> None:
    only_gaps = GateAutoAnswerPolicy(answer_retries=False, record_research_gaps=True)

    for kind in (
        "approval",
        "choice",
        "publish_interview",
        "escalation_exhausted",
        "question",
        "budget_exhausted",
        "deploy_acceptance",
    ):
        assert only_gaps.answer_for(kind, ("accept", "local_only", "accept_defaults")) is None, kind
