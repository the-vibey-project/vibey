# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which open gates an ACP client may answer through `session/request_permission`, and how.

A spend gate is never offered, whatever its kind, options or flags say: money is answered on
the host (ADR-0046, sub-doctrine 12.d). Every other answerable gate becomes one option per
choice, each carrying the answer the hub's own parser makes of it.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

from typing import Any

import pytest
from acp.schema import PermissionOption
from acp_wire import assert_wire_exact

from vibey.domain.acp.gate_permission import GatePermissionMapper, PermissionChoice
from vibey.domain.acp.interfaces.gate_permission_interface import GatePermissionMapperInterface
from vibey.domain.acp.protocol import PermissionKind
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_chat import (
    ANY_ANSWER_GATE_KINDS,
    CHOICE_GATE_KINDS,
    GRANT_GATE_KEYS,
    HUB_CHAT,
    VERDICT_GATE_KINDS,
)
from vibey.domain.hub_scope import SPEND_GATE_KINDS

MAPPER = GatePermissionMapper(AcpSettings().reject_words, HUB_CHAT)
G = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b"


def _gate(kind: str, options: list[Any] | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "gate_id": G,
        "project_id": "7d6c2a8e-0c41-4c1e-9d0e-2f4b8f0a1b2c",
        "kind": kind,
        "prompt": "Ship it?",
        "options": options if options is not None else [],
        "default_answer": None,
        **HUB_CHAT.format_gate_prompt({"kind": kind}),
        **extra,
    }


def test_the_mapper_satisfies_its_interface() -> None:
    assert isinstance(MAPPER, GatePermissionMapperInterface)


@pytest.mark.parametrize("kind", sorted(SPEND_GATE_KINDS))
def test_spend_gates_are_never_offered_even_with_approve_options(kind: str) -> None:
    gate = {"gate_id": "g", "kind": kind, "options": ["approve", "accept"], "is_spend": True}

    assert MAPPER.options_for(gate) == ()
    assert "spends money" in MAPPER.refusal_text({"gate_id": "g", "kind": kind})


@pytest.mark.parametrize("kind", sorted(SPEND_GATE_KINDS))
def test_a_spend_kind_is_refused_even_when_its_flags_say_otherwise(kind: str) -> None:
    # The kind alone decides: a gate document whose flags were lost or forged still spends.
    gate = _gate(kind, ["approve", "yes"], is_spend=False, requires_scope="answer")

    assert MAPPER.options_for(gate) == ()
    assert MAPPER.refusal_text(gate) == (
        f"Gate {G} ({kind}) spends money, so I cannot answer it. Answer it on the host "
        f"(`vibey answer {G}`) or in the desktop or mobile app."
    )


def test_deploy_interview_is_a_choice_kind_and_still_refused() -> None:
    # `deploy_interview` is in both CHOICE_GATE_KINDS and SPEND_GATE_KINDS: spend wins.
    assert "deploy_interview" in CHOICE_GATE_KINDS & SPEND_GATE_KINDS
    assert MAPPER.options_for(_gate("deploy_interview", ["aws", "azure"])) == ()


def test_is_spend_flag_alone_refuses_an_unknown_kind() -> None:
    gate = {"gate_id": G, "kind": "choice", "options": ["yes", "no"], "is_spend": True}

    assert MAPPER.options_for(gate) == ()
    assert "spends money" in MAPPER.refusal_text(gate)


def test_requires_scope_spend_alone_refuses() -> None:
    gate = {"gate_id": G, "kind": "approval", "options": ["accept"], "requires_scope": "spend"}

    assert MAPPER.options_for(gate) == ()
    assert "spends money" in MAPPER.refusal_text(gate)


def test_choice_options_map_to_allow_and_reject_by_reject_words() -> None:
    kinds = [
        c.kind
        for c in MAPPER.options_for({"gate_id": "g", "kind": "choice", "options": ["yes", "no"]})
    ]
    assert kinds == [PermissionKind.ALLOW_ONCE, PermissionKind.REJECT_ONCE]


def test_each_choice_carries_the_hubs_own_parse_of_its_option() -> None:
    choices = MAPPER.options_for(_gate("choice", ["Keep going", "Decline"]))

    assert choices == (
        PermissionChoice(
            f"{G}:0", "Keep going", PermissionKind.ALLOW_ONCE, {"choice": "Keep going"}
        ),
        PermissionChoice(f"{G}:1", "Decline", PermissionKind.REJECT_ONCE, {"choice": "Decline"}),
    )


@pytest.mark.parametrize("kind", sorted(VERDICT_GATE_KINDS - SPEND_GATE_KINDS))
def test_a_verdict_gate_answers_with_a_verdict(kind: str) -> None:
    choices = MAPPER.options_for(_gate(kind, ["accept", "reject"]))

    assert [(c.answer, c.kind) for c in choices] == [
        ({"verdict": "accept"}, PermissionKind.ALLOW_ONCE),
        ({"verdict": "reject"}, PermissionKind.REJECT_ONCE),
    ]


def test_reject_words_are_configurable() -> None:
    mapper = GatePermissionMapper(("nope",), HUB_CHAT)

    kinds = [c.kind for c in mapper.options_for(_gate("choice", ["no", "NOPE"]))]

    assert kinds == [PermissionKind.ALLOW_ONCE, PermissionKind.REJECT_ONCE]


def test_an_option_the_hub_cannot_parse_is_left_out_and_indices_stay_stable() -> None:
    choices = MAPPER.options_for(_gate("choice", ["", "yes", 7]))

    assert [(c.option_id, c.name) for c in choices] == [(f"{G}:1", "yes"), (f"{G}:2", "7")]


def test_a_choice_gate_with_no_usable_option_is_not_offered() -> None:
    gate = _gate("choice", ["", "  "])

    assert MAPPER.options_for(gate) == ()
    assert MAPPER.refusal_text(gate) == (
        f"Gate {G} (choice) needs a value. Answer it with `/answer {G} <value>`."
    )


def test_options_that_are_not_a_list_are_not_offered() -> None:
    assert MAPPER.options_for(_gate("choice", None) | {"options": "yes"}) == ()


def test_question_gate_offers_defaults_or_leave_open() -> None:
    choices = MAPPER.options_for(_gate("question", ["ignored"]))

    assert choices == (
        PermissionChoice(
            f"{G}:0", "Accept the defaults", PermissionKind.ALLOW_ONCE, {"accept_defaults": True}
        ),
        PermissionChoice(f"{G}:1", "Leave it open", PermissionKind.REJECT_ONCE, None),
    )


@pytest.mark.parametrize("kind", sorted(ANY_ANSWER_GATE_KINDS))
def test_an_any_answer_gate_offers_acknowledge_or_leave_open(kind: str) -> None:
    choices = MAPPER.options_for(_gate(kind))

    assert choices == (
        PermissionChoice(f"{G}:0", "Acknowledge", PermissionKind.ALLOW_ONCE, {}),
        PermissionChoice(f"{G}:1", "Leave it open", PermissionKind.REJECT_ONCE, None),
    )


@pytest.mark.parametrize("kind", sorted(set(GRANT_GATE_KEYS) - SPEND_GATE_KINDS))
def test_grant_gates_needing_a_number_are_not_offered(kind: str) -> None:
    gate = _gate(kind, ["1", "2"])

    assert MAPPER.options_for(gate) == ()
    assert "needs a value" in MAPPER.refusal_text(gate)


def test_an_unknown_kind_is_not_offered() -> None:
    assert MAPPER.options_for(_gate("publish_interview", ["yes"])) == ()


def test_a_gate_without_an_id_is_not_offered() -> None:
    assert MAPPER.options_for({"kind": "choice", "options": ["yes"]}) == ()


def test_options_validate_against_the_sdk_permission_option() -> None:
    gates = [_gate("choice", ["yes", "no"]), _gate("question"), _gate("delivery_exhausted")]
    for gate in gates:
        for choice in MAPPER.options_for(gate):
            option = choice.option()
            assert option == {
                "optionId": choice.option_id,
                "name": choice.name,
                "kind": choice.kind.value,
            }
            assert_wire_exact(PermissionOption, option)
