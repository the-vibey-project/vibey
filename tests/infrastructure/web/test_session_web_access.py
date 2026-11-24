# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether `vibey search` and `vibey fetch` run for a person, through the hub, or not at all
(SP-LOOPS Phase 6, Task 4; R1): read from the environment alone, and never a local search for a
session."""

from pathlib import Path

import pytest

from vibey.domain.session_web_state import NO_HUB, NO_RUN_FOLDER, UNSAID
from vibey.infrastructure.web.interfaces.session_web_access_interface import (
    SessionWebAccessInterface,
)
from vibey.infrastructure.web.session import (
    COMMAND_VARIABLE,
    HUB_URL_VARIABLE,
    SESSION_MARKERS,
    STATE_VARIABLE,
    TOKEN_FILE_VARIABLE,
    SessionWebAccess,
)

HUB = {HUB_URL_VARIABLE: "http://127.0.0.1:8765", TOKEN_FILE_VARIABLE: "/runs/x/web-token"}


def test_the_names_are_the_ones_the_worker_overlays() -> None:
    assert HUB_URL_VARIABLE == "VIBEY_HUB_URL"
    assert TOKEN_FILE_VARIABLE == "VIBEY_WEB_TOKEN_FILE"
    assert STATE_VARIABLE == "VIBEY_WEB_STATE"
    assert NO_HUB == "no hub is running; start one with `vibey serve`"
    assert set(SESSION_MARKERS) == {"WEBSEARCH_PROVIDER", COMMAND_VARIABLE}


def test_nothing_set_is_a_person_at_their_own_terminal() -> None:
    access = SessionWebAccess.from_environment({"PATH": "/bin", "WEBSEARCH_BRAVE_API_KEY": "k"})

    assert isinstance(access, SessionWebAccessInterface)
    assert (access.mode, access.hub_url, access.token_file, access.reason) == (
        "person",
        "",
        None,
        "",
    )


def test_both_hub_variables_route_through_the_hub_whatever_else_is_set() -> None:
    access = SessionWebAccess.from_environment(
        {**HUB, STATE_VARIABLE: "hub", "WEBSEARCH_PROVIDER": "searxng"}
    )

    assert access.mode == "hub"
    assert access.hub_url == "http://127.0.0.1:8765"
    assert access.token_file == Path("/runs/x/web-token")


def test_values_are_read_stripped() -> None:
    access = SessionWebAccess.from_environment(
        {HUB_URL_VARIABLE: " http://127.0.0.1:1 ", TOKEN_FILE_VARIABLE: " /t "}
    )

    assert (access.hub_url, access.token_file) == ("http://127.0.0.1:1", Path("/t"))


@pytest.mark.parametrize(
    ("state", "reason"),
    [("none:no-hub", NO_HUB), ("none:no-run-folder", NO_RUN_FOLDER), ("none", UNSAID)],
)
def test_no_web_says_the_workers_reason_in_fixed_text(state: str, reason: str) -> None:
    """SP-LOOPS Phase 6, Task 6: the reason travels in the state's value; bare `none` claims no
    reason, so "no hub is running" is said only when the worker said it."""
    access = SessionWebAccess.from_environment({STATE_VARIABLE: state})

    assert (access.mode, access.reason) == ("off", reason)


@pytest.mark.parametrize(
    ("given", "missing"),
    [
        ({HUB_URL_VARIABLE: "http://127.0.0.1:1"}, TOKEN_FILE_VARIABLE),
        ({TOKEN_FILE_VARIABLE: "/t"}, HUB_URL_VARIABLE),
        ({HUB_URL_VARIABLE: "  ", TOKEN_FILE_VARIABLE: "/t"}, HUB_URL_VARIABLE),
    ],
)
def test_half_a_hub_is_no_search_and_names_what_is_missing(
    given: dict[str, str], missing: str
) -> None:
    access = SessionWebAccess.from_environment(given)

    assert access.mode == "off"
    assert f"without {missing}" in access.reason


def test_a_state_other_than_none_without_the_hub_is_no_search_and_is_not_echoed() -> None:
    access = SessionWebAccess.from_environment({STATE_VARIABLE: "\x1b]0;evil\x07"})

    assert access.mode == "off"
    assert "evil" not in access.reason and f"{STATE_VARIABLE} must be `none`" in access.reason


@pytest.mark.parametrize("marker", ["WEBSEARCH_PROVIDER", "WEBSEARCH_COMMAND"])
def test_a_session_marked_the_old_way_never_searches_on_its_own(marker: str) -> None:
    access = SessionWebAccess.from_environment({marker: "searxng"})

    assert access.mode == "off"
    assert HUB_URL_VARIABLE in access.reason and TOKEN_FILE_VARIABLE in access.reason
    assert "only through the hub" in access.reason
