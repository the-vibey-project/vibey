# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a session's environment and plan say about the web (SP-LOOPS Phase 6, Task 5; R1).

With its own grant, exactly the hub's address and the path of its token file; with none, exactly
`VIBEY_WEB_STATE=none:<reason name>` (Task 6), and the plan says why in fixed text. Never a search
backend's address, a key, or the token."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from vibey.application.dto import RunWebAccess, SessionGrant
from vibey.domain.session_principal import SessionPrincipal
from vibey.domain.session_web_state import NO_HUB, NO_RUN_FOLDER, NO_TOKEN
from vibey.infrastructure.engines.interfaces.session_web_overlay_interface import (
    SessionWebOverlayInterface,
)
from vibey.infrastructure.engines.session_web_overlay import (
    SESSION_WEB_OVERLAY,
    SessionWebOverlay,
)
from vibey.infrastructure.web.session import web_access_note

RUN = UUID("00000000-0000-4000-8000-000000000007")
HUB = "http://127.0.0.1:28100"
GRANT = SessionGrant(
    token_file=Path("/runs/r/web-token"),
    principal=SessionPrincipal(name=f"session:{RUN}", run_id=RUN, expires_at=9e9),
    digest="a" * 64,
)
THROUGH_HUB = RunWebAccess("hub", hub_url=HUB, grant=GRANT)


def _no_search_backend(env: dict[str, str]) -> bool:
    return not [
        name
        for name in env
        if name.startswith("WEBSEARCH_") or "SEARXNG" in name or "BRAVE" in name
    ]


def test_it_meets_its_seam() -> None:
    assert isinstance(SESSION_WEB_OVERLAY, SessionWebOverlayInterface)
    assert isinstance(SESSION_WEB_OVERLAY, SessionWebOverlay)


def test_through_the_hub_the_session_is_given_exactly_the_address_and_the_files_path() -> None:
    env = SESSION_WEB_OVERLAY.environment(THROUGH_HUB)
    assert env == {"VIBEY_HUB_URL": HUB, "VIBEY_WEB_TOKEN_FILE": "/runs/r/web-token"}
    assert _no_search_backend(env)


@pytest.mark.parametrize(
    ("reason", "state"),
    [(NO_HUB, "none:no-hub"), (NO_RUN_FOLDER, "none:no-run-folder"), (NO_TOKEN, "none:no-token")],
)
def test_without_a_grant_the_session_is_given_only_that_it_has_none_and_why(
    reason: str, state: str
) -> None:
    """The reason travels as a fixed name in the one name the session is given (Task 6), so its
    `vibey search` says the same reason as its plan."""
    env = SESSION_WEB_OVERLAY.environment(RunWebAccess("none", reason=reason))
    assert env == {"VIBEY_WEB_STATE": state}


def test_a_reason_with_no_fixed_name_is_said_as_bare_none() -> None:
    env = SESSION_WEB_OVERLAY.environment(RunWebAccess("none", reason="made up"))
    assert env == {"VIBEY_WEB_STATE": "none"}


def test_a_run_that_says_nothing_has_no_web_either() -> None:
    """A session outside BUILD (a DESIGN or review session) was never offered a grant."""
    assert SESSION_WEB_OVERLAY.environment(None) == {"VIBEY_WEB_STATE": "none:not-given"}


def test_the_plan_tells_a_session_with_a_grant_how_to_search() -> None:
    assert SESSION_WEB_OVERLAY.plan_note(THROUGH_HUB, "/opt/v/vibey") == web_access_note(
        "/opt/v/vibey"
    )


def test_the_plan_says_search_is_unavailable_and_why_in_fixed_text() -> None:
    note = SESSION_WEB_OVERLAY.plan_note(RunWebAccess("none", reason=NO_HUB), "/opt/v/vibey")
    assert note == (
        "## Web access\n\n"
        "Web search and page fetching are unavailable in this session: no hub is running; start "
        "one with `vibey serve`. Use the repository and what you already know instead."
    )
    assert "/opt/v/vibey" not in note


def test_a_run_that_says_nothing_gets_no_web_note() -> None:
    assert SESSION_WEB_OVERLAY.plan_note(None, "vibey") is None
