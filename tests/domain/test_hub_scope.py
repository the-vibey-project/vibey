# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's scope policy: deny by default, one scope per action, and nothing reserved."""

import itertools

import pytest

from vibey.domain.hub_scope import (
    HUB_SCOPES,
    NEVER_FROM_THE_HUB,
    REQUIRED_SCOPE,
    HubAction,
    HubForbidden,
    HubScope,
)
from vibey.domain.interfaces.hub_scope_interface import HubScopePolicyInterface


def test_the_policy_meets_its_seam_and_every_action_needs_a_scope() -> None:
    assert isinstance(HUB_SCOPES, HubScopePolicyInterface)
    assert set(REQUIRED_SCOPE) == set(HubAction)
    assert isinstance(HubForbidden("x"), Exception)


def test_the_full_matrix_permits_exactly_the_required_scope() -> None:
    for size in range(len(HubScope) + 1):
        for subset in itertools.combinations(HubScope, size):
            granted = frozenset(subset)
            for action in HubAction:
                assert HUB_SCOPES.permits(granted, action) == (REQUIRED_SCOPE[action] in granted)


def test_view_cannot_answer_and_answer_cannot_spend() -> None:
    assert not HUB_SCOPES.permits(frozenset({HubScope.VIEW}), HubAction.ANSWER_GATE)
    assert not HUB_SCOPES.permits(frozenset({HubScope.ANSWER}), HubAction.ANSWER_SPEND_GATE)


@pytest.mark.parametrize(
    ("kind", "action"),
    [
        ("budget_exhausted", HubAction.ANSWER_SPEND_GATE),
        ("deploy_acceptance", HubAction.ANSWER_SPEND_GATE),
        ("approval", HubAction.ANSWER_GATE),
        ("choice", HubAction.ANSWER_GATE),
    ],
)
def test_a_gates_kind_decides_whether_answering_spends(kind: str, action: HubAction) -> None:
    assert HUB_SCOPES.action_for_gate(kind) is action


def test_no_scope_and_no_action_can_reach_what_is_reserved() -> None:
    for name in NEVER_FROM_THE_HUB:
        assert HUB_SCOPES.reserved(name)
        assert name not in {a.value for a in HubAction} | {s.value for s in HubScope}
    assert not HUB_SCOPES.reserved("read")


def test_a_grant_naming_an_unknown_scope_is_refused() -> None:
    assert HUB_SCOPES.parse(frozenset({"view", "bump"})) == {HubScope.VIEW, HubScope.BUMP}
    with pytest.raises(ValueError):
        HUB_SCOPES.parse(frozenset({"admin"}))


@pytest.mark.parametrize(
    ("argv", "capability"),
    [
        (("migrate",), "migrations"),
        (("budget", "no-cap"), "no_cap"),
        (("budget", "cap", "p"), "change_caps"),
        (("-v", "budget", "set", "p", "--usd", "5"), "change_caps"),
        (("--log-level", "DEBUG", "budget", "clear", "p"), "change_caps"),
        (("--log-file", "migrate", "status"), None),  # the option's value is no command
        (("budget", "show"), None),
        (("status", "--json"), None),
        (("queue", "bump", "migrate"), None),
        (("ledger", "--json", "migrate"), None),
        ((), None),
    ],
)
def test_a_command_line_names_the_reserved_capability_it_reaches(
    argv: tuple[str, ...], capability: str | None
) -> None:
    assert HUB_SCOPES.reserved_command(argv) == capability
    if capability is not None:
        assert HUB_SCOPES.reserved(capability)


def test_running_on_the_workflows_needs_its_own_scope() -> None:
    assert HUB_SCOPES.permits(frozenset({HubScope.WORKFLOWS}), HubAction.RUN_ON_WORKFLOWS)
    assert not HUB_SCOPES.permits(
        frozenset({HubScope.RUN, HubScope.VIEW}), HubAction.RUN_ON_WORKFLOWS
    )
