# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The numbered phase diagram and its legend stay intact, and stay identical in both copies.

Issue #98 put circled numbers on the phases in "The shape of it" diagram so a reader could
tell which phase a sentence elsewhere is talking about; PR #99 shipped it into README.md and
docs/index.md. Nothing guarded it. The diagram, the legend that maps ① to "Design", and the
sentence naming which phases talk to you are three hand-maintained things in two
hand-maintained files -- six copies of one fact -- and the numbering could have been dropped
from any of them, or drifted out of agreement with the bold interactive markers, with no test
saying a word.

So: every circled number appears in the diagram beside its phase name, the legend maps all six,
the "Phases N, N ... talk to you" sentence names exactly the phases the diagram bolds, and the
two files' sections are byte-for-byte the same. The expected names live in PHASES, once.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
COPIES = ("README.md", "docs/index.md")
HEADING = "## The shape of it"

#: The single source of the expected numbering: circled numeral, ordinal, phase name.
PHASES = (
    ("①", 1, "Design"),
    ("②", 2, "Build"),
    ("③", 3, "Review"),
    ("④", 4, "Deploy Design"),
    ("⑤", 5, "Deploy Execute"),
    ("⑥", 6, "Deploy Review"),
)
CIRCLED = {circled: number for circled, number, _ in PHASES}
FENCE = re.compile(r"```\n(.*?)```", re.DOTALL)
BOLD = re.compile(r"\*\*([^*]+)\*\*")
TALK = re.compile(r"Phases ([0-9,\s]*?and\s*[0-9]+) talk to you")


def _section(name: str) -> str:
    """The "The shape of it" section of one copy, heading to the next heading."""
    text = (REPO / name).read_text(encoding="utf-8")
    start = text.find(HEADING)
    assert start != -1, f"{name} no longer has a {HEADING!r} section"
    rest = text[start + len(HEADING) :]
    end = rest.find("\n## ")
    return rest[:end] if end != -1 else rest


def _diagram(section: str, name: str) -> str:
    fences = FENCE.findall(section)
    assert fences, f"{name}: the {HEADING!r} section no longer contains a diagram block"
    return str(fences[0])


def _paragraphs(section: str) -> list[str]:
    """The prose paragraphs of the section, unwrapped, with the diagram block removed."""
    prose = FENCE.sub("", section)
    return [" ".join(block.split()) for block in prose.split("\n\n") if block.strip()]


def _only(paragraphs: list[str], needle: str, name: str) -> str:
    found = [p for p in paragraphs if needle in p]
    assert len(found) == 1, (
        f"{name}: expected exactly one paragraph containing {needle!r}, got {found}"
    )
    return found[0]


@pytest.mark.parametrize("name", COPIES)
def test_the_diagram_numbers_every_phase(name: str) -> None:
    """A circled number with no phase beside it in the diagram is a number nobody can resolve."""
    diagram = _diagram(_section(name), name)
    missing = [
        f"{circled} {phase.upper()}"
        for circled, _, phase in PHASES
        if not re.search(rf"{circled}\s*{re.escape(phase.upper())}", diagram)
    ]
    assert not missing, f"{name}: the diagram no longer numbers {missing}"


@pytest.mark.parametrize("name", COPIES)
def test_the_legend_maps_every_number_to_its_phase(name: str) -> None:
    """The diagram is only readable if the legend says what the circled numbers mean."""
    legend = _only(_paragraphs(_section(name)), "**The six phases**", name)
    missing = [
        f"{circled} {phase}"
        for circled, _, phase in PHASES
        if not re.search(rf"{circled}\s*{re.escape(phase)}", legend)
    ]
    assert not missing, f"{name}: the legend no longer maps {missing}"


@pytest.mark.parametrize("name", COPIES)
def test_the_interactive_sentence_matches_what_the_diagram_marks(name: str) -> None:
    """The talk-to-you sentence and the bold markers are one claim written twice."""
    paragraphs = _paragraphs(_section(name))
    flow = _only(paragraphs, "→", name)
    bolded = {CIRCLED[segment[0]] for segment in BOLD.findall(flow) if segment[:1] in CIRCLED}
    assert bolded, f"{name}: the phase flow no longer bolds any interactive phase"

    sentence = _only(paragraphs, "talk to you", name)
    match = TALK.search(sentence)
    assert match, f"{name}: no 'Phases ... talk to you' sentence found in {sentence!r}"
    claimed = {int(n) for n in re.findall(r"[0-9]+", match.group(1))}
    assert claimed == bolded, (
        f"{name}: the sentence says phases {sorted(claimed)} talk to you; "
        f"the diagram bolds {sorted(bolded)}"
    )


@pytest.mark.parametrize("name", COPIES)
def test_the_flow_names_every_phase_in_order(name: str) -> None:
    """The flow line is the legend's numbering applied; a renamed phase must be renamed here too."""
    flow = _only(_paragraphs(_section(name)), "→", name)
    expected = [f"{circled} {phase}" for circled, _, phase in PHASES]
    found = [re.sub(r"\*", "", step).strip() for step in flow.split("→")]
    assert found == expected, f"{name}: the phase flow reads {found}, expected {expected}"


def test_both_copies_of_the_section_agree() -> None:
    """Two hand-maintained copies of one diagram is exactly how a diagram goes stale."""
    sections = {name: _section(name) for name in COPIES}
    first, *rest = COPIES
    for name in rest:
        assert sections[name] == sections[first], (
            f"{name} and {first} disagree about the {HEADING!r} section; "
            "they are maintained by hand in both places and must stay identical"
        )
