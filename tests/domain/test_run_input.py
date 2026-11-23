# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The run input value, its digest rule and the names a run input may have (SP-LOOPS Phase 3,
Task 1). Module-level test functions: pytest collects them, and the class-and-interface rule is
about production code (ADR-0016)."""

from __future__ import annotations

import dataclasses

import pytest

from vibey.domain.interfaces.run_input_interface import RunInputRuleInterface
from vibey.domain.run_input import (
    INPUT_KINDS,
    NAME_MAX_BYTES,
    RUN_INPUT_RULE,
    InputListing,
    RunInput,
    digest_of,
    valid_name,
)


def test_digest_is_sha256_hex() -> None:
    assert digest_of(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_digest_of_bytes_that_are_not_text_is_still_a_digest() -> None:
    assert RUN_INPUT_RULE.is_digest(digest_of(b"\x00\xff"))


@pytest.mark.parametrize("name", ["../x", "a/b", "a\\b", "bad\x00name", "x" * 256, "", ".", ".."])
def test_refused_names_return_a_reason(name: str) -> None:
    reason = valid_name(name)
    assert reason is not None
    assert reason  # a reason a person can read, never an empty string


def test_a_name_over_the_byte_limit_counts_utf8_bytes_not_characters() -> None:
    # 128 two-byte characters are 256 bytes: one over the limit though only 128 characters.
    assert valid_name("é" * 128) is not None
    assert valid_name("é" * 127) is None


def test_a_name_with_a_lone_surrogate_is_refused_rather_than_raising() -> None:
    assert valid_name("bad\udcffname") is not None


def test_the_byte_limit_is_a_parameter() -> None:
    assert valid_name("abcd", max_bytes=3) is not None
    assert valid_name("abc", max_bytes=3) is None
    assert NAME_MAX_BYTES == 255


@pytest.mark.parametrize("name", ["spec.md", "..hidden", "with space.txt", "esc\x1bname"])
def test_plain_names_are_accepted(name: str) -> None:
    assert valid_name(name) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", True),
        ("BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD", False),
        ("ba7816bf", False),
        ("../" + "a" * 61, False),
        ("g" * 64, False),
    ],
)
def test_is_digest_accepts_only_64_lowercase_hex(text: str, expected: bool) -> None:
    assert RUN_INPUT_RULE.is_digest(text) is expected


def test_the_value_is_frozen_and_the_kinds_are_the_two() -> None:
    item = RunInput(digest=digest_of(b"x"), kind="paste", name="paste", size=1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.size = 2  # type: ignore[misc]
    assert INPUT_KINDS == ("paste", "file")
    assert InputListing(items=(item,), skipped=0).items == (item,)


def test_the_rule_meets_its_interface() -> None:
    assert isinstance(RUN_INPUT_RULE, RunInputRuleInterface)
