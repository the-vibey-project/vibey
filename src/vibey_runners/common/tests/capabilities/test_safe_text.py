# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plugin text bound for a model context or a terminal: one line, no control or bidi characters,
capped with a visible mark (SP-LOOPS Task 6; design Decision 10)."""

from __future__ import annotations

import pytest

from vibey_runners.common.capabilities.interfaces.safe_text_interface import SafeTextInterface
from vibey_runners.common.capabilities.safe_text import ELLIPSIS, SafeText


def test_plain_text_is_unchanged() -> None:
    assert SafeText().clean("Audits a reference for staleness.", 100) == (
        "Audits a reference for staleness."
    )
    assert isinstance(SafeText(), SafeTextInterface)


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("a\x1b[2Jb", "a[2Jb"),  # ESC, the start of a terminal escape
        ("a\x00b\x7fc\x9bd", "abcd"),  # NUL, DEL and a C1 control
        ("left‮right⁦x⁩", "leftrightx"),  # bidi overrides and isolates
        ("zero​width‍﻿", "zerowidth"),  # zero-width characters and a BOM
        ("one\ntwo\r\nthree\tfour", "one two three four"),  # line breaks become spaces
        ("para line end", "para line end"),  # Unicode line/paragraph separators
        ("  spaced   out   ", "spaced out"),  # runs of space collapse, ends trimmed
        ("lone \udcff surrogate", "lone surrogate"),  # an undecodable byte from a file name
    ],
)
def test_control_format_and_separator_characters_are_removed(raw: str, clean: str) -> None:
    assert SafeText().clean(raw, 100) == clean


def test_text_over_the_limit_is_cut_with_a_visible_mark() -> None:
    cleaned = SafeText().clean("word " * 100, 20)
    assert len(cleaned) <= 20
    assert cleaned.endswith(ELLIPSIS)
    assert cleaned == "word word word word" + ELLIPSIS


def test_text_exactly_at_the_limit_is_not_cut() -> None:
    assert SafeText().clean("x" * 20, 20) == "x" * 20


def test_the_limit_is_counted_after_cleaning() -> None:
    assert SafeText().clean("ab\x1b\x1b\x1bcd", 4) == "abcd"


def test_a_limit_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        SafeText().clean("x", 0)
