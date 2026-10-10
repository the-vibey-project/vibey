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
