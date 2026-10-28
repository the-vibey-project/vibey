# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The README's table of contents lists every section, and every link lands (#853).

A contents list written by hand goes stale the first time a section is added or renamed, and
nothing says so: the link just stops working, on GitHub and on PyPI's page, where there is no
other way to jump. So the list is checked against the headings it summarises (sub-doctrine
12.e): one entry per `##` heading, in order, each pointing at that heading's own anchor.

The list sits after the first screen, so it does not change what tests/meta/test_first_screen.py
holds the first screen to.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
CONTENTS = "Contents"
ENTRY = re.compile(r"^- \[(?P<title>.+)\]\(#(?P<anchor>[^)]+)\)$")


def anchor(title: str) -> str:
    """The anchor GitHub gives a heading: lower case, punctuation gone, spaces to hyphens."""
    slug = re.sub(r"[^\w\- ]", "", title).strip().lower()
    return re.sub(r"\s+", "-", slug)


def headings(text: str) -> list[str]:
    """The `##` headings outside code fences, in order."""
    found: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            found.append(line[3:].strip())
    return found


def listed(text: str) -> list[tuple[str, str]]:
    """The (title, anchor) pairs under the Contents heading, up to the next heading."""
    block = text.split(f"\n## {CONTENTS}\n", 1)[1].split("\n## ", 1)[0]
    pairs = []
    for line in block.splitlines():
        match = ENTRY.match(line)
        if match:
            pairs.append((match["title"], match["anchor"]))
    return pairs


def test_there_is_one_contents_section_and_it_comes_before_the_first_section() -> None:
    text = README.read_text(encoding="utf-8")
    found = headings(text)
    assert found.count(CONTENTS) == 1
    assert found.index(CONTENTS) == 0, (
        "the contents list is the first section, after the first screen"
    )


def test_the_contents_list_has_one_entry_per_section_in_order() -> None:
    text = README.read_text(encoding="utf-8")
    sections = [title for title in headings(text) if title != CONTENTS]
    assert [title for title, _ in listed(text)] == sections


def test_every_entry_points_at_its_own_headings_anchor() -> None:
    text = README.read_text(encoding="utf-8")
    for title, target in listed(text):
        assert target == anchor(title), (
            f"{title!r} links to #{target}, its anchor is #{anchor(title)}"
        )


def test_the_anchor_rule_matches_the_headings_that_have_punctuation() -> None:
    assert (
        anchor("Why it isn't just another agent framework")
        == "why-it-isnt-just-another-agent-framework"
    )
    assert anchor("The shape of it") == "the-shape-of-it"


def test_the_checker_sees_a_stale_list() -> None:
    stale = "## Contents\n\n- [One](#one)\n\n## One\n\n## Two\n"
    sections = [title for title in headings(stale) if title != CONTENTS]
    assert [title for title, _ in listed("\n" + stale)] != sections


def test_a_heading_inside_a_code_fence_is_not_a_section() -> None:
    assert headings("## A\n\n```\n## not a heading\n```\n\n## B\n") == ["A", "B"]
