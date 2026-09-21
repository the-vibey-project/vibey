# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""docs/paper.md is the one paper, and it survives the renderer that turns it into paper.pdf.

`vibey-gh paper` converts the body one line at a time, so an inline `$...$` span that wraps
onto a second line is never recognised as math: its backslashes are escaped and it prints as
literal TeX. Until #155 the published paper carried three such spans (the claim order, the
lease expiry and the selector weight), and the weight's stray `$` then paired with the next
span and swallowed "for base weight" into math mode. Nothing failed; the PDF was just wrong.
Emphasis has the same failure: `*` markers on two lines print as two literal stars.

Section titles carry no colon (ADR-0032), and the paper no longer points at a companion:
#155 consolidated the family's papers into this one.
"""

from __future__ import annotations

import re
from pathlib import Path

from vibey_gh.paper import convert

REPO = Path(__file__).resolve().parents[2]
PAPER = REPO / "docs" / "paper.md"
_MATH_SPAN = re.compile(r"\$[^$]*\$")
_CODE_SPAN = re.compile(r"`[^`]*`")


def _prose_lines() -> list[tuple[int, str]]:
    """Body lines the renderer runs through its inline converter, with 1-based numbers."""
    lines = PAPER.read_text(encoding="utf-8").splitlines()
    prose: list[tuple[int, str]] = []
    fenced = False
    in_display = False
    for number, line in enumerate(lines, 1):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.startswith("$$"):
            in_display = not (len(line) > 2 and line.rstrip().endswith("$$"))
            continue
        if in_display:
            in_display = not line.rstrip().endswith("$$")
            continue
        prose.append((number, line))
    return prose


def test_every_inline_math_span_closes_on_the_line_it_opens() -> None:
    body = _prose_lines()
    abstract_end = next(n for n, line in body if line.startswith("*Artifacts.*"))
    odd = [n for n, line in body if n > abstract_end and line.count("$") % 2]
    assert not odd, f"docs/paper.md lines with an unclosed inline math span: {odd}"


def test_every_emphasis_closes_on_the_line_it_opens() -> None:
    """The same line-at-a-time rule prints a wrapped `*emphasis*` as two literal stars."""
    body = _prose_lines()
    abstract_end = next(n for n, line in body if line.startswith("*Artifacts.*"))
    odd = [
        n
        for n, line in body
        if n > abstract_end and _CODE_SPAN.sub("", _MATH_SPAN.sub("", line)).count("*") % 2
    ]
    assert not odd, f"docs/paper.md lines with an unclosed emphasis: {odd}"


def test_the_rendered_body_contains_no_escaped_tex() -> None:
    doc = convert(PAPER.read_text(encoding="utf-8"))
    escaped = [line for line in doc.body if r"\textbackslash{}" in line or r"\$" in line]
    assert not escaped, f"math or TeX reached the escaper: {escaped[:3]}"


def test_section_titles_carry_no_colon() -> None:
    titles = [line for _, line in _prose_lines() if line.startswith(("## ", "### "))]
    colons = [title for title in titles if ":" in title]
    assert not colons, f"ADR-0032: a section title carries no colon: {colons}"


def test_the_paper_is_not_one_of_several() -> None:
    text = PAPER.read_text(encoding="utf-8").lower()
    assert "companion paper" not in text, "#155: docs/paper.md is the one paper"


def test_the_paper_carries_the_reproducible_visual_atlas() -> None:
    text = PAPER.read_text(encoding="utf-8")
    expected_labels = (
        "fig:cdd-orbits",
        "fig:cdd-loop",
        "fig:digital-atom",
        "fig:software-molecule",
        "fig:digital-hierarchy",
        "fig:web-ecology",
        "fig:six-phase-machine",
        "fig:ledger-handoff",
        "fig:engine-pool",
        "fig:exact-head",
        "fig:qwen-cdd",
        "fig:stress-rate",
        "fig:qwen-disposition",
        "fig:completion-band",
        "fig:six-materials",
        "fig:record-effect",
    )
    assert text.count(r"\begin{figure") >= len(expected_labels)
    assert all(rf"\label{{{label}}}" in text for label in expected_labels)
