# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The first screen of the README and of the documentation site keeps its contract.

ADR-0076 makes the first screen a deliverable: the problem before any project vocabulary
(doctrine 1), then one definitional sentence a search engine or an AI reader can quote
whole (sub-doctrine 7.d), proof points that link to their evidence, and a path to a first
contribution and to the project's law (7.b) -- in both copies, which say the same thing.
The pull-request review judges the prose; this checks the parts a machine can check, so
that none of them is lost in an edit nobody noticed (sub-doctrine 12.e).

Every link on the first screen must land: a repository path must exist, an anchor must
name a heading in the page it points at, and a link to this repository on GitHub must name
a path that exists in this tree. A proof point whose evidence link is dead is a claim
without evidence (sub-doctrine 10.f).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
#: Each copy of the first screen, and the directory its relative links resolve from.
COPIES = {"README.md": REPO, "docs/index.md": REPO / "docs"}
GITHUB = re.compile(r"^https://github\.com/the-vibey-project/vibey/(?:blob|tree)/develop/(.+)$")
LINK = re.compile(r"\]\(([^)\s]+)\)")
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def _first_screen(name: str) -> str:
    text = FRONT_MATTER.sub("", (REPO / name).read_text(encoding="utf-8"), count=1)
    return text.split("\n## ", 1)[0]


def _paragraphs(name: str) -> list[str]:
    blocks = [" ".join(b.split()) for b in _first_screen(name).split("\n\n") if b.strip()]
    return [b for b in blocks if not b.startswith("# ")]


def _slug(heading: str) -> str:
    """The anchor GitHub and ProperDocs both give a heading made of words and code marks."""
    words = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s+", "-", words)


def _anchors(path: Path) -> set[str]:
    return {
        _slug(line.lstrip("#"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    }


@pytest.mark.parametrize("name", sorted(COPIES))
def test_the_problem_comes_before_the_project(name: str) -> None:
    """Doctrine 1: a page that opens with what something is before what it fixes fails."""
    first, second = _paragraphs(name)[:2]
    assert "vibey" not in first.lower(), f"{name} names the project before the problem"
    assert second.startswith("**vibey is "), f"{name}'s second block is not the definition"


def test_both_copies_define_vibey_in_the_same_words() -> None:
    definitions = {name: _paragraphs(name)[1] for name in COPIES}
    assert len(set(definitions.values())) == 1, definitions


@pytest.mark.parametrize("name", sorted(COPIES))
def test_the_first_screen_leads_to_a_contribution_and_to_the_law(name: str) -> None:
    screen = _first_screen(name)
    assert "CONTRIBUTING.md#your-first-hour" in screen, f"{name} has no first-hour path"
    assert "constitution" in screen.lower(), f"{name} has no path to the Constitution (7.b)"
    assert re.search(r"\(\d+ ADRs\)", screen), f"{name} no longer counts its decision records"


@pytest.mark.parametrize("name", sorted(COPIES))
def test_every_first_screen_link_lands(name: str) -> None:
    base = COPIES[name]
    page = REPO / name
    dead: list[str] = []
    for target in LINK.findall(_first_screen(name)):
        github = GITHUB.match(target)
        if github:
            location, base_dir = github.group(1), REPO
        elif target.startswith(("http://", "https://", "mailto:")):
            continue
        else:
            location, base_dir = target, base
        path_part, _, anchor = location.partition("#")
        resolved = (base_dir / path_part) if path_part else page
        missing_anchor = bool(anchor) and resolved.is_file() and anchor not in _anchors(resolved)
        if not resolved.exists() or missing_anchor:
            dead.append(target)
    assert not dead, f"{name}: first-screen links that do not land: {dead}"
