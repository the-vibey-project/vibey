# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Test cases for the residency policy implementation.

These tests follow the specification in ADR‑0046 and the TDD plan in the
issue.
"""

import re

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from vibey.domain.interfaces.residency_interface import (
    ModelChoiceInterface,
    ModelDeclarationInterface,
    ResidencyPolicyInterface,
    SeatSlugInterface,
)
from vibey.domain.residency import (
    CHOSEN_DEFAULT,
    CHOSEN_FIRST_DECLARED,
    CHOSEN_RESIDENT,
    UNROUTABLE_NO_MODEL,
    ModelChoice,
    ModelDeclaration,
    ResidencyPolicy,
    SeatSlug,
)

# convenience instances
GPT = ModelDeclaration("gpt-oss:20b", 131072)
QWEN = ModelDeclaration("qwen2.5-coder:14b", 32768)

# ---------- SeatSlug tests ----------


def test_the_default_model_slugs_as_the_adr_says():
    s = SeatSlug()
    assert s.of("gpt-oss:20b") == "gpt-oss-20b"
    assert s.of("Qwen2.5-Coder:14B") == "qwen2-5-coder-14b"
    assert s.of("a/b c") == "a-b-c"


def test_every_slug_uses_only_the_seat_alphabet():
    s = SeatSlug()

    @given(st.text(min_size=1))
    def helper(name: str):
        # skip reserved
        assume(name.lower() not in {"probe", "dead"})
        slug = s.of(name)
        assert re.fullmatch(r"[a-z0-9-]+", slug) is not None
        assert len(slug) == len(name.lower())

    helper()


def test_an_empty_name_is_refused():
    with pytest.raises(ValueError, match="seat name '' is empty"):
        SeatSlug().of("")


def test_reserved_slugs_are_refused():
    with pytest.raises(ValueError, match="seat name 'probe' slugs to 'probe', which is reserved"):
        SeatSlug().of("probe")
    with pytest.raises(ValueError, match="seat name 'PROBE' slugs to 'probe', which is reserved"):
        SeatSlug().of("PROBE")
    with pytest.raises(ValueError, match="seat name 'dead' slugs to 'dead', which is reserved"):
        SeatSlug().of("dead")


def test_a_paid_seat_is_the_engine_id_or_engine_dot_model():
    s = SeatSlug()
    assert s.of_paid("claudeloop") == "claudeloop"
    assert s.of_paid("vscode-paid", "gpt-5:mini") == "vscode-paid.gpt-5-mini"


def test_unique_maps_slugs_to_names_in_declared_order():
    s = SeatSlug()
    result = s.unique(["gpt-oss:20b", "qwen2.5-coder:14b"])
    expected = {
        "gpt-oss-20b": "gpt-oss:20b",
        "qwen2-5-coder-14b": "qwen2.5-coder:14b",
    }
    assert list(result.items()) == list(expected.items())
    with pytest.raises(TypeError):
        result["foo"] = "bar"


def test_unique_refuses_two_names_that_share_a_slug():
    s = SeatSlug()
    with pytest.raises(
        ValueError, match="seats gpt-oss-20b and gpt-oss-20b share the slug gpt-oss-20b"
    ):
        s.unique(["gpt-oss:20b", "gpt-oss-20b"])


# ---------- ModelDeclaration tests ----------


def test_a_model_declaration_needs_a_positive_context_window():
    with pytest.raises(
        ValueError, match="ModelDeclaration.context_window must be at least 1, got 0"
    ):
        ModelDeclaration("m", 0)


# ---------- ResidencyPolicy tests ----------


@pytest.fixture
def policy():
    return ResidencyPolicy()


def test_the_resident_model_is_kept_when_it_can_carry(policy):
    choice = policy.choose(
        resident="qwen2.5-coder:14b",
        default="gpt-oss:20b",
        declared=(GPT, QWEN),
        model_pin=None,
        min_context=None,
    )
    assert choice == ModelChoice(model="qwen2.5-coder:14b", switched=False, reason=CHOSEN_RESIDENT)


def test_the_default_is_chosen_when_the_resident_cannot_carry(policy):
    choice = policy.choose(
        resident="qwen2.5-coder:14b",
        default="gpt-oss:20b",
        declared=(GPT, QWEN),
        model_pin=None,
        min_context=65536,
    )
    assert choice == ModelChoice(model="gpt-oss:20b", switched=True, reason=CHOSEN_DEFAULT)


def test_the_first_declared_model_is_the_last_resort(policy):
    choice = policy.choose(
        resident=None,
        default="missing:1b",
        declared=(QWEN, GPT),
        model_pin=None,
        min_context=65536,
    )
    assert choice == ModelChoice(model="gpt-oss:20b", switched=False, reason=CHOSEN_FIRST_DECLARED)


def test_a_pin_names_the_only_model_that_can_carry(policy):
    choice = policy.choose(
        resident="gpt-oss:20b",
        default="gpt-oss:20b",
        declared=(GPT, QWEN),
        model_pin="qwen2.5-coder:14b",
        min_context=None,
    )
    assert choice == ModelChoice(
        model="qwen2.5-coder:14b", switched=True, reason=CHOSEN_FIRST_DECLARED
    )


def test_an_undeclared_resident_is_never_chosen(policy):
    choice = policy.choose(
        resident="phantom:7b",
        default=None,
        declared=(GPT,),
        model_pin=None,
        min_context=None,
    )
    assert choice == ModelChoice(model="gpt-oss:20b", switched=True, reason=CHOSEN_FIRST_DECLARED)


def test_nothing_can_carry_is_unroutable(policy):
    choice = policy.choose(
        resident="gpt-oss:20b",
        default=None,
        declared=(GPT,),
        model_pin=None,
        min_context=10**6,
    )
    assert choice is None
    assert UNROUTABLE_NO_MODEL == "no local model can carry this job"


def test_no_resident_is_never_a_switch(policy):
    choice = policy.choose(
        resident=None,
        default="gpt-oss:20b",
        declared=(GPT,),
        model_pin=None,
        min_context=None,
    )
    assert choice.switched is False
    assert choice.reason == CHOSEN_DEFAULT


# ---------- Interface conformance tests ----------


def test_classes_satisfy_their_interfaces():
    assert isinstance(SeatSlug(), SeatSlugInterface)
    assert isinstance(ResidencyPolicy(), ResidencyPolicyInterface)
    assert isinstance(GPT, ModelDeclarationInterface)
    # ModelChoice instance
    mc = ModelChoice("foo", switched=True, reason="bar")
    assert isinstance(mc, ModelChoiceInterface)
