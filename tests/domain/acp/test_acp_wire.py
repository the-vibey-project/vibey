# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The wire-exact helper fails on the two mistakes a plain `model_validate` lets through."""

import pytest
from acp.schema import PromptResponse, SessionModeState
from acp_wire import assert_wire_exact


def test_a_correct_payload_passes() -> None:
    assert_wire_exact(PromptResponse, {"stopReason": "end_turn"})
    assert_wire_exact(
        SessionModeState,
        {"currentModeId": "a", "availableModes": [{"id": "a", "name": "A"}]},
    )


def test_a_snake_case_key_is_refused() -> None:
    PromptResponse.model_validate({"stop_reason": "end_turn"})  # the SDK accepts it
    with pytest.raises(AssertionError):
        assert_wire_exact(PromptResponse, {"stop_reason": "end_turn"})


def test_a_misspelled_key_is_refused() -> None:
    payload = {"stopReason": "end_turn", "stopReasn": "end_turn"}
    PromptResponse.model_validate(payload)  # the SDK ignores the extra key
    with pytest.raises(AssertionError):
        assert_wire_exact(PromptResponse, payload)
