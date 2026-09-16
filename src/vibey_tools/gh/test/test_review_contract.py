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


def test_fields_is_the_two_halves_in_order_and_not_the_yaml_key_order():
    """`fields` orders the diff-groundable half first, then the documentation contract.

    That is deliberately NOT the primary schema's own key order -- `pr-automation.yml`
    puts `summary` and `findings` LAST -- so a caller who zips `fields` against a schema's
    values positionally binds them to the wrong names. The docstring says so; this checks
    it, and checks it against the local fallback's own ordering rather than against
    `fields` itself, which would only restate the claim.
    """
    schema = _primary_review_schema()

    assert REVIEW_CONTRACT.fields == (
        tuple(local_review.REVIEW_SCHEMA["required"]) + local_review.UNEVALUATED_FIELDS
    )
    assert REVIEW_CONTRACT.fields[:3] == ("pass", "summary", "findings")
    # The concrete fact the "not schema order" claim rests on. Reorder the YAML to match
    # and this fails, which is the moment to change the docstring rather than ignore it.
    assert list(schema["properties"])[1] == "complete"
    assert list(schema["properties"])[-2:] == ["summary", "findings"]


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


@pytest.mark.parametrize(
    "half, other",
    [
        ("diff_groundable", "requires_wider_context"),
        ("requires_wider_context", "diff_groundable"),
    ],
)
def test_a_half_cannot_name_the_same_field_twice(half: str, other: str):
    """A duplicate inside ONE half, which the cross-half check above cannot see.

    `ReviewContract` is constructible by embedding repositories, so the halves are a
    caller's input rather than this module's own constant. A repeated name produces a
    duplicated entry in `fields` and in a JSON Schema's `required` list while
    `placeholders()` silently collapses it back to one -- so the count a reader takes
    from the schema and the count a verdict carries would disagree.

    Both halves are exercised because the guard is a loop over the two, and a loop only
    ever entered once would leave the other half unguarded.
    """
    label = DIFF_GROUNDABLE if half == "diff_groundable" else REQUIRES_WIDER_CONTEXT
    kwargs = {half: ("pass", "summary", "summary"), other: ()}
    with pytest.raises(ValueError, match=f"{label} review fields must be unique"):
        ReviewContract(**kwargs)  # type: ignore[arg-type]


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

    # Including the placeholder value itself: it decides what `placeholders()` writes into
    # every verdict, so a caller holding only the seam has to be able to read it, and a
    # substitute implementation must not be able to satisfy the Protocol without it.
    port: ReviewContractPort = REVIEW_CONTRACT
    assert port.unevaluated_placeholder is True
    assert set(port.placeholders().values()) == {port.unevaluated_placeholder}
