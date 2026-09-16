# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The review contract.

What is worth pinning here is not that the module holds two tuples. It is that the two
tuples are the SAME meaning the review schema and the local fallback already carry, so a
change to any one of the three has to move the other two.
"""

from __future__ import annotations

import json
import shlex

import pytest

from vibey_gh import local_review
from vibey_gh.install import WORKFLOWS
from vibey_gh.interfaces import ReviewContractPort
from vibey_gh.review_contract import (
    DIFF_GROUNDABLE,
    REQUIRES_WIDER_CONTEXT,
    REVIEW_CONTRACT,
    ReviewContract,
)


def _primary_review_schema() -> dict:
    """The `--json-schema` the paid exact-head reviewer is held to."""
    for line in (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8").splitlines():
        if "--json-schema " not in line:
            continue
        tokens = shlex.split(line.strip())
        schema = json.loads(tokens[tokens.index("--json-schema") + 1])
        if "links_valid" in schema["properties"]:
            return schema
    raise AssertionError("pr-automation.yml no longer declares the review schema")


def test_the_contract_covers_the_primary_review_schema_exactly():
    """The split is a split OF something. If the paid reviewer's schema grows a judgment
    and the contract does not classify it, nobody has decided whether a diff can carry it
    — and the local fallback would silently neither ask for it nor placeholder it."""
    schema = _primary_review_schema()

    assert set(REVIEW_CONTRACT.fields) == set(schema["required"])
    assert set(REVIEW_CONTRACT.fields) == set(schema["properties"])


def test_the_local_fallback_asks_for_exactly_the_diff_groundable_half():
    assert REVIEW_CONTRACT.diff_groundable == ("pass", "summary", "findings")
    assert set(local_review.REVIEW_SCHEMA["properties"]) == set(REVIEW_CONTRACT.diff_groundable)
    assert local_review.REVIEW_SCHEMA["required"] == list(REVIEW_CONTRACT.diff_groundable)
    assert local_review.UNEVALUATED_FIELDS == REVIEW_CONTRACT.requires_wider_context


def test_the_documentation_contract_is_the_half_a_diff_cannot_carry():
    """Named individually rather than by count: each one is a statement about documents
    the diff does not contain, and a reader should be able to check that claim field by
    field."""
    assert REVIEW_CONTRACT.requires_wider_context == (
        "complete",
        "accurate",
        "human_readable",
        "opening_accessible",
        "opening_bluf",
        "audience_order",
        "architecture_diagram_complete",
        "all_capabilities_documented",
        "all_commands_documented",
        "all_configuration_documented",
        "examples_sufficient",
        "onboarding_sufficient",
        "operations_sufficient",
        "security_sufficient",
        "release_process_sufficient",
        "links_valid",
    )
    assert REVIEW_CONTRACT.fields == (
        REVIEW_CONTRACT.diff_groundable + REVIEW_CONTRACT.requires_wider_context
    )


@pytest.mark.parametrize(
    ("field", "half"),
    [
        ("pass", DIFF_GROUNDABLE),
        ("findings", DIFF_GROUNDABLE),
        ("audience_order", REQUIRES_WIDER_CONTEXT),
        ("links_valid", REQUIRES_WIDER_CONTEXT),
    ],
)
def test_classify_names_the_half(field, half):
    assert REVIEW_CONTRACT.classify(field) == half
    assert REVIEW_CONTRACT.is_diff_groundable(field) is (half == DIFF_GROUNDABLE)


def test_an_unknown_field_raises_rather_than_defaulting_to_either_answer():
    """Defaulting to "diff-groundable" would licence a local model to certify something
    nobody decided it could; defaulting the other way would silently drop a judgment."""
    with pytest.raises(KeyError, match="not a review field"):
        REVIEW_CONTRACT.classify("verdict")
    with pytest.raises(KeyError):
        REVIEW_CONTRACT.is_diff_groundable("verdict")


def test_a_field_cannot_sit_in_both_halves():
    """The exact lie this module exists to prevent: something a caller would read as
    evaluated and unevaluated at once."""
    with pytest.raises(ValueError, match="both halves: accurate, summary"):
        ReviewContract(
            diff_groundable=("pass", "summary", "accurate"),
            requires_wider_context=("accurate", "summary"),
        )


def test_the_placeholders_are_shape_compatibility_and_say_so():
    """`audience_order` is unevaluated AND emitted as `true`. Both are true at once, and
    the reconciliation has to be readable from the code rather than inferred from a
    boolean that looks like an answer."""
    placeholders = REVIEW_CONTRACT.placeholders()

    assert set(placeholders) == set(REVIEW_CONTRACT.requires_wider_context)
    assert placeholders["audience_order"] is True
    assert all(value is True for value in placeholders.values())
    # The value alone is a lie; the notice is what makes the pair honest, so it travels
    # in the same verdict.
    assert "NOT evaluated" in REVIEW_CONTRACT.unevaluated_notice


def test_a_repository_can_declare_its_own_split():
    """Everything is a constructor argument, not a literal in a method: a repository whose
    review schema is shaped differently configures this rather than forking it."""
    contract = ReviewContract(
        diff_groundable=("pass",),
        requires_wider_context=("house_style",),
        unevaluated_placeholder=False,
        unevaluated_notice="not checked here",
    )

    assert contract.fields == ("pass", "house_style")
    assert contract.placeholders() == {"house_style": False}
    assert contract.unevaluated_notice == "not checked here"


def test_the_contract_satisfies_the_declared_seam():
    assert isinstance(REVIEW_CONTRACT, ReviewContractPort)
    assert REVIEW_CONTRACT == ReviewContract.default()
