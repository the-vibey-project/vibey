# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one token estimate a loop's capability budgets are measured in: characters over four,
rounded up (SP-LOOPS Phase 5, R8)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from vibey_runners.common.capabilities.interfaces.token_estimate_interface import (
    TokenEstimateInterface,
)
from vibey_runners.common.capabilities.token_estimate import TOKEN_ESTIMATE, TokenEstimate


def test_an_estimate_rounds_up_and_empty_text_costs_nothing() -> None:
    assert isinstance(TOKEN_ESTIMATE, TokenEstimateInterface)
    assert isinstance(TokenEstimate(), TokenEstimateInterface)
    assert TokenEstimate.CHARS_PER_TOKEN == 4
    assert TOKEN_ESTIMATE.tokens("") == 0
    assert TOKEN_ESTIMATE.tokens("a") == 1
    assert TOKEN_ESTIMATE.tokens("abcd") == 1
    assert TOKEN_ESTIMATE.tokens("abcde") == 2
    assert TOKEN_ESTIMATE.chars(0) == 0
    assert TOKEN_ESTIMATE.chars(3072) == 12288


@given(text=st.text(max_size=200))
def test_text_within_a_budget_of_chars_never_costs_more_than_its_tokens(text: str) -> None:
    """`chars` and `tokens` agree: text no longer than `chars(n)` costs at most `n`."""
    cost = TOKEN_ESTIMATE.tokens(text)
    assert len(text) <= TOKEN_ESTIMATE.chars(cost) < len(text) + TokenEstimate.CHARS_PER_TOKEN
