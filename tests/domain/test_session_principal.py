# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The per-session web principal (SP-LOOPS Phase 6, Task 1): it holds only `web`, it is
permitted only the two web actions, and only before it expires -- expiry is exclusive."""

import dataclasses
import math
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.hub_scope import HUB_SCOPES, HubAction, HubScope
from vibey.domain.interfaces.session_principal_interface import (
    SessionPrincipalInterface,
    SessionPrincipalPolicyInterface,
)
from vibey.domain.session_principal import (
    SESSION_PRINCIPAL_PREFIX,
    SESSION_PRINCIPALS,
    SESSION_SCOPES,
    SessionPrincipal,
    SessionPrincipalPolicy,
)

RUN = UUID("00000000-0000-4000-8000-000000000001")
WEB_ACTIONS = frozenset({HubAction.WEB_SEARCH, HubAction.WEB_FETCH})

_times = st.floats(min_value=-1e12, max_value=1e12, allow_nan=False, allow_infinity=False)


def test_a_session_principal_holds_only_web() -> None:
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    assert p.scopes == frozenset({HubScope.WEB})
    assert p.scopes is SESSION_SCOPES
    assert (p.name, p.run_id, p.expires_at) == ("session:abc", RUN, 100.0)


def test_it_permits_only_the_two_web_actions_before_expiry() -> None:
    policy = SessionPrincipalPolicy()
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    assert policy.permits(p, HubAction.WEB_SEARCH, now=99.9)
    assert policy.permits(p, HubAction.WEB_FETCH, now=99.9)
    assert not policy.permits(p, HubAction.READ, now=0.0)
    assert not policy.permits(p, HubAction.WEB_SEARCH, now=100.0)  # expiry is exclusive
    assert not policy.permits(p, HubAction.WEB_FETCH, now=100.0)


def test_expired_is_inclusive_of_the_expiry_instant() -> None:
    """`expired` is the exact complement of the time half of `permits`: a caller telling a
    401 (expired) from a 403 (wrong action) reads the same boundary."""
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    assert not SESSION_PRINCIPALS.expired(p, now=99.9)
    assert SESSION_PRINCIPALS.expired(p, now=100.0)
    assert SESSION_PRINCIPALS.expired(p, now=100.1)


def test_the_classes_meet_their_seams() -> None:
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    assert isinstance(p, SessionPrincipalInterface)
    assert isinstance(SESSION_PRINCIPALS, SessionPrincipalPolicyInterface)
    assert isinstance(SessionPrincipalPolicy(), SessionPrincipalPolicyInterface)


def test_a_session_principal_is_frozen_and_its_scopes_cannot_be_widened() -> None:
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.expires_at = 1e18  # type: ignore[misc]
    with pytest.raises((AttributeError, TypeError)):
        p.scopes = frozenset(HubScope)  # type: ignore[misc]
    assert "scopes" not in {f.name for f in dataclasses.fields(SessionPrincipal)}


@pytest.mark.parametrize("name", ["", "session:", "abc", "agent", "Session:abc", " session:abc"])
def test_a_name_that_is_not_a_session_name_is_refused(name: str) -> None:
    """A session principal is named `session:<id>`, so no paired device's or the agent's name
    can be read as one, and a bare prefix names nothing."""
    with pytest.raises(ValueError, match=SESSION_PRINCIPAL_PREFIX):
        SessionPrincipal(name=name, run_id=RUN, expires_at=100.0)


@pytest.mark.parametrize("expires_at", [math.inf, -math.inf, math.nan])
def test_an_expiry_that_is_not_a_finite_instant_is_refused(expires_at: float) -> None:
    """An infinite expiry would never expire; a NaN one would compare false every way."""
    with pytest.raises(ValueError, match="finite"):
        SessionPrincipal(name="session:abc", run_id=RUN, expires_at=expires_at)


def test_the_policy_delegates_the_scope_rule_to_the_hub_policy() -> None:
    """Before expiry the answer is exactly the hub's own answer for `{web}`, so the scope
    rule has one owner."""
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    for action in HubAction:
        assert SESSION_PRINCIPALS.permits(p, action, now=0.0) == HUB_SCOPES.permits(
            SESSION_SCOPES, action
        )
    assert {a for a in HubAction if SESSION_PRINCIPALS.permits(p, a, now=0.0)} == WEB_ACTIONS


@given(
    action=st.sampled_from(sorted(set(HubAction) - WEB_ACTIONS)),
    expires_at=_times,
    now=_times,
)
def test_no_action_but_the_two_web_ones_is_ever_permitted(
    action: HubAction, expires_at: float, now: float
) -> None:
    p = SessionPrincipal(name="session:x", run_id=RUN, expires_at=expires_at)
    assert not SESSION_PRINCIPALS.permits(p, action, now=now)


@given(action=st.sampled_from(sorted(WEB_ACTIONS)), expires_at=_times, now=_times)
def test_a_web_action_is_permitted_exactly_before_expiry(
    action: HubAction, expires_at: float, now: float
) -> None:
    p = SessionPrincipal(name="session:x", run_id=RUN, expires_at=expires_at)
    assert SESSION_PRINCIPALS.permits(p, action, now=now) == (now < expires_at)
    assert SESSION_PRINCIPALS.expired(p, now=now) == (now >= expires_at)
