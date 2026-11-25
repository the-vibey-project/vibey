# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run's web access is exactly one of two shapes (SP-LOOPS Phase 6, Task 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from vibey.application.dto import RunSpec, RunWebAccess, SessionGrant
from vibey.domain.effort import Effort
from vibey.domain.engine import IsolationLevel
from vibey.domain.session_principal import SessionPrincipal
from vibey.domain.session_web_state import NO_HUB, WEB_STATES

RUN = UUID("00000000-0000-4000-8000-000000000006")
GRANT = SessionGrant(
    token_file=Path("/run/web-token"),
    principal=SessionPrincipal(name=f"session:{RUN}", run_id=RUN, expires_at=2.0),
    digest="e" * 64,
)


def test_the_two_states() -> None:
    assert WEB_STATES == ("hub", "none")


def test_through_the_hub_it_carries_the_url_and_the_grant_path() -> None:
    access = RunWebAccess("hub", hub_url="http://127.0.0.1:1", grant=GRANT)
    assert access.token_file == Path("/run/web-token")


def test_none_carries_only_its_reason() -> None:
    assert RunWebAccess("none", reason=NO_HUB).token_file is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"state": "hub", "grant": GRANT},
        {"state": "hub", "hub_url": "http://127.0.0.1:1"},
        {"state": "hub", "hub_url": "http://127.0.0.1:1", "grant": GRANT, "reason": NO_HUB},
        {"state": "none"},
        {"state": "none", "reason": NO_HUB, "hub_url": "http://127.0.0.1:1"},
        {"state": "none", "reason": NO_HUB, "grant": GRANT},
        {"state": "maybe", "reason": NO_HUB},
    ],
)
def test_any_other_shape_is_refused(kwargs: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        RunWebAccess(**kwargs)


def test_a_run_spec_says_nothing_about_the_web_unless_told() -> None:
    spec = RunSpec(
        run_id=RUN,
        worktree_path=Path("/w"),
        prompt="p",
        effort=Effort.LOW,
        isolation=IsolationLevel.WORKTREE,
    )
    assert spec.web is None
