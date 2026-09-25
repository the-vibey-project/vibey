# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one actor-label policy `vibey budget --by` and `vibey answer --by` share."""

import pytest

from vibey.domain.actor_label import ACTOR_LABELS, ActorLabelPolicy
from vibey.domain.errors import InvalidActorLabel, InvalidBudgetChange
from vibey.domain.interfaces import ActorLabelPolicyInterface


def test_the_policy_satisfies_its_interface() -> None:
    assert isinstance(ACTOR_LABELS, ActorLabelPolicyInterface)


def test_no_label_is_the_account_and_a_label_is_stripped() -> None:
    assert ACTOR_LABELS.resolve(None, account="adam") == "adam"
    assert ACTOR_LABELS.resolve("  vibey-vscode ", account="adam") == "vibey-vscode"
    longest = "x" * ActorLabelPolicy.MAX_LENGTH
    assert ACTOR_LABELS.resolve(longest, account="adam") == longest


@pytest.mark.parametrize(
    ("label", "why"),
    [
        ("   ", "cannot be empty"),
        ("x" * (ActorLabelPolicy.MAX_LENGTH + 1), "is over 200 characters"),
        ("adam\nforged line", "cannot contain control or formatting"),
        ("adam‮gnissim", "cannot contain control or formatting"),
    ],
)
def test_a_label_that_cannot_be_recorded_is_refused(label: str, why: str) -> None:
    with pytest.raises(InvalidActorLabel, match=f"the name a record is made under {why}"):
        ACTOR_LABELS.resolve(label, account="adam")


def test_a_command_refuses_in_its_own_words() -> None:
    budget = ActorLabelPolicy(
        subject="the name a change is recorded under", error=InvalidBudgetChange
    )
    with pytest.raises(InvalidBudgetChange, match="the name a change is recorded under cannot"):
        budget.resolve("", account="adam")
