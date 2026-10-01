# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A gate resolves to its default on timeout only where the project declared it (12.d)."""

from datetime import timedelta

import pytest

from vibey.domain.config import ConfigError
from vibey.domain.gate_timeout import (
    DEFAULT_ANSWER_KEYS,
    GateTimeoutPolicy,
)
from vibey.domain.interfaces import GateTimeoutPolicyInterface


def _policy(**waits: object) -> GateTimeoutPolicy:
    return GateTimeoutPolicy.from_config({"human_gates": {"timeout_defaults": waits}})


def test_the_policy_honours_its_interface() -> None:
    assert isinstance(GateTimeoutPolicy(), GateTimeoutPolicyInterface)


def test_nothing_times_out_unless_declared() -> None:
    """Silence is not consent: with no declaration every gate waits for a person."""
    for config in ({}, {"human_gates": {}}, {"human_gates": {"timeout_defaults": {}}}):
        policy = GateTimeoutPolicy.from_config(config)
        for kind in DEFAULT_ANSWER_KEYS:
            assert policy.resolution(kind=kind, default_answer="x", waited_seconds=10**9) is None


def test_a_declared_kind_resolves_to_its_default_once_it_has_waited() -> None:
    policy = _policy(choice=60)

    assert (
        policy.resolution(kind="choice", default_answer="local_only", waited_seconds=3599) is None
    )
    assert policy.resolution(kind="choice", default_answer="local_only", waited_seconds=3600) == {
        "choice": "local_only"
    }


def test_each_kind_answers_under_the_key_its_handler_reads() -> None:
    policy = _policy(**{kind: 1 for kind in DEFAULT_ANSWER_KEYS})
    assert policy.resolution(
        kind="deploy_demo_review", default_answer="approve", waited_seconds=60
    ) == {"verdict": "approve"}
    assert policy.resolution(
        kind="deploy_acceptance", default_answer="reject", waited_seconds=60
    ) == {"choice": "reject"}
    assert policy.resolution(
        kind="deploy_interview", default_answer="accept_defaults", waited_seconds=60
    ) == {"choice": "accept_defaults"}
    assert policy.resolution(
        kind="deploy_failure_triage", default_answer="LOOP_DEPLOY_DESIGN", waited_seconds=60
    ) == {"choice": "LOOP_DEPLOY_DESIGN"}


def test_a_gate_without_a_default_never_times_out() -> None:
    policy = _policy(choice=1)
    for default in (None, "", "   "):
        assert policy.resolution(kind="choice", default_answer=default, waited_seconds=60) is None


def test_the_declared_wait_is_reported() -> None:
    assert _policy(choice=90).wait_for("choice") == timedelta(minutes=90)
    assert _policy(choice=90).wait_for("deploy_interview") is None


@pytest.mark.parametrize(
    ("waits", "message"),
    [
        ({"approval": 60}, "approval"),  # no default to time out to
        ({"made_up_kind": 60}, "made_up_kind"),
        ({"choice": 0}, "positive"),
        ({"choice": -5}, "positive"),
        ({"choice": True}, "positive"),
        ({"choice": "60"}, "positive"),
    ],
)
def test_a_declaration_that_cannot_be_honoured_is_refused(
    waits: dict[str, object], message: str
) -> None:
    with pytest.raises(ConfigError, match=message):
        _policy(**waits)


@pytest.mark.parametrize(
    "config",
    [
        {"human_gates": "nope"},
        {"human_gates": {"timeout_defaults": ["choice"]}},
    ],
)
def test_a_malformed_table_is_refused(config: dict[str, object]) -> None:
    with pytest.raises(ConfigError, match="human_gates"):
        GateTimeoutPolicy.from_config(config)
