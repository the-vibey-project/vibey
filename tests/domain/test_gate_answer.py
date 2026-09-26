# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What identifies one request that answers a gate (`domain/gate_answer.py`)."""

from uuid import UUID

import pytest

from vibey.domain.errors import InvalidAnswer
from vibey.domain.gate_answer import GATE_ANSWER_REQUEST_IDS, GateAnswerRequestIds
from vibey.domain.interfaces import GateAnswerRequestIdsInterface

GATE = UUID("00000000-0000-4000-8000-000000000001")
OTHER = UUID("00000000-0000-4000-8000-000000000002")


def test_the_policy_satisfies_its_interface() -> None:
    assert isinstance(GATE_ANSWER_REQUEST_IDS, GateAnswerRequestIdsInterface)


def test_a_storable_request_id_is_kept_as_given() -> None:
    assert GATE_ANSWER_REQUEST_IDS.checked("vscode:7f3a") == "vscode:7f3a"
    longest = "r" * GateAnswerRequestIds.MAX_LENGTH
    assert GATE_ANSWER_REQUEST_IDS.checked(longest) == longest


@pytest.mark.parametrize(
    ("request_id", "why"),
    [
        ("", "cannot be empty"),
        ("r" * (GateAnswerRequestIds.MAX_LENGTH + 1), "is over 200 characters"),
        ("two words", "cannot contain spaces"),
        (" leading", "cannot contain spaces"),
        ("line\nbreak", "cannot contain spaces"),
        ("bidi‮", "cannot contain spaces"),
    ],
)
def test_a_request_id_that_cannot_be_stored_is_refused(request_id: str, why: str) -> None:
    with pytest.raises(InvalidAnswer, match=why):
        GATE_ANSWER_REQUEST_IDS.checked(request_id)


def test_a_derived_id_is_the_same_for_the_same_answer_every_time() -> None:
    first = GATE_ANSWER_REQUEST_IDS.derived("operator", GATE, {"choice": "a", "n": 1})
    again = GATE_ANSWER_REQUEST_IDS.derived("operator", GATE, {"n": 1, "choice": "a"})
    assert first == again
    assert first.startswith("operator:")
    assert len(first) == len("operator:") + 64


def test_a_derived_id_differs_with_the_answer_the_gate_or_the_source() -> None:
    base = GATE_ANSWER_REQUEST_IDS.derived("operator", GATE, {"choice": "a"})
    assert base != GATE_ANSWER_REQUEST_IDS.derived("operator", GATE, {"choice": "b"})
    assert base != GATE_ANSWER_REQUEST_IDS.derived("operator", OTHER, {"choice": "a"})
    assert base != GATE_ANSWER_REQUEST_IDS.derived("hub", GATE, {"choice": "a"})
