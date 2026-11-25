# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Why a session has no web travels in the one name it is given, `VIBEY_WEB_STATE`, as a fixed
reason name after `none:` (SP-LOOPS Phase 6, Task 6): its `vibey search` says the true reason,
never "no hub is running" when one is."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.interfaces.no_web_reasons_interface import NoWebReasonsInterface
from vibey.domain.no_web_reasons import NO_WEB_REASONS, REASON_NAMES, NoWebReasons
from vibey.domain.session_web_state import (
    HUB_URL_VARIABLE,
    NO_HUB,
    NO_RUN_FOLDER,
    NO_TOKEN,
    NOT_GIVEN,
    STATE_VARIABLE,
    TOKEN_FILE_VARIABLE,
    UNSAID,
)


def test_it_meets_its_seam() -> None:
    assert isinstance(NO_WEB_REASONS, NoWebReasonsInterface)


def test_the_session_names_are_the_familys_own() -> None:
    from vibey_runners.common.capabilities import web_grant_names as names

    assert (HUB_URL_VARIABLE, TOKEN_FILE_VARIABLE, STATE_VARIABLE) == (
        names.HUB_URL_NAME,
        names.TOKEN_FILE_NAME,
        names.STATE_NAME,
    )


@pytest.mark.parametrize(
    ("reason", "state"),
    [
        (NO_HUB, "none:no-hub"),
        (NO_RUN_FOLDER, "none:no-run-folder"),
        (NO_TOKEN, "none:no-token"),
        (NOT_GIVEN, "none:not-given"),
    ],
)
def test_each_fixed_reason_has_its_own_name_and_reads_back(reason: str, state: str) -> None:
    assert NO_WEB_REASONS.state(reason) == state
    assert NO_WEB_REASONS.reason(state) == reason
    assert NO_WEB_REASONS.reason(f"  {state} ") == reason


def test_the_four_reasons_are_distinct_texts() -> None:
    texts = [NO_HUB, NO_RUN_FOLDER, NO_TOKEN, NOT_GIVEN, UNSAID]
    assert len(set(texts)) == len(texts)
    assert set(REASON_NAMES) == {"no-hub", "no-run-folder", "no-token", "not-given"}


def test_a_reason_that_is_not_one_of_the_fixed_ones_is_never_put_in_the_environment() -> None:
    """Free text never reaches a session's environment: only a fixed name, or bare `none`."""
    assert NO_WEB_REASONS.state("something the worker made up") == "none"


@pytest.mark.parametrize("state", ["none", "none:", "none:no-such-reason", "none:NO-HUB"])
def test_a_bare_or_unknown_none_says_no_more_than_it_knows(state: str) -> None:
    assert NO_WEB_REASONS.reason(state) == UNSAID


@pytest.mark.parametrize("state", ["", "  ", "hub", "nonesuch", "None", "no-hub"])
def test_anything_that_is_not_none_is_not_a_no_web_state(state: str) -> None:
    assert NO_WEB_REASONS.reason(state) is None


@given(st.text(max_size=40))
def test_reading_any_value_never_raises_and_never_repeats_it(value: str) -> None:
    reason = NoWebReasons().reason(value)
    assert reason is None or reason in {NO_HUB, NO_RUN_FOLDER, NO_TOKEN, NOT_GIVEN, UNSAID}
