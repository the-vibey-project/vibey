# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every outcome guide keeps the shape ADR-0077 gives it, and every link on it lands.

An outcome guide answers one question a practitioner searches for: the question is its
title, a one-sentence answer follows that a search engine or an AI reader can quote whole,
then the steps, then the evidence, then the limits, and last the way to improve the page.
The answer is also the page's `description:`, which becomes its meta description and its
line in `docs/llms.txt`, so the quotable sentence and the indexed sentence cannot drift
apart (sub-doctrine 7.d). A guide that claims more than its links prove is the failure the
record exists to prevent (10.f), so every link must land: a page, an anchor that names a
heading, or a path in this tree behind a GitHub URL. Whether the prose is true of the code
is the exact-head review's judgement; this checks what a machine can.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
OUTCOMES = DOCS / "guides" / "outcomes"
INDEX = OUTCOMES / "index.md"
GUIDES = sorted(p for p in OUTCOMES.glob("*.md") if p != INDEX)
FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
DESCRIPTION = re.compile(r"^description:\s*(.+)$", re.M)
LINK = re.compile(r"\]\(([^)\s]+)\)")
GITHUB = re.compile(r"^https://github\.com/the-vibey-project/vibey/(?:blob|tree)/develop/(.+)$")
EXPLICIT_ID = re.compile(r"\{\s*#([\w-]+)\s*\}\s*$")
FENCE = re.compile(r"```.*?```", re.S)
#: The sections every guide carries, in this order; "Improve this guide" is always last.
REQUIRED = ("The evidence", "Limits", "Improve this guide")
#: Readable in under five minutes at an ordinary silent-reading pace for non-fiction.
MAX_WORDS = 1200


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _body(path: Path) -> str:
    return FRONT_MATTER.sub("", _text(path), count=1)


def _description(path: Path) -> str:
    front = FRONT_MATTER.match(_text(path))
    assert front, f"{path.name} has no front matter"
    found = DESCRIPTION.search(front.group(1))
    assert found, f"{path.name} has no description: front matter"
    return found.group(1).strip()


def _plain(markdown: str) -> str:
    """Words as an index or a search snippet shows them: no code marks, no emphasis."""
    return " ".join(re.sub(r"[`*]", "", markdown).split())


def _slug(heading: str) -> str:
    """The anchor a heading gets: an explicit `{ #id }`, else the GitHub/ProperDocs slug."""
    explicit = EXPLICIT_ID.search(heading)
    if explicit:
        return explicit.group(1)
    words = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return re.sub(r"\s+", "-", words)


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and line.startswith("#"):
            anchors.add(_slug(line.lstrip("#")))
    return anchors


def _description_limit() -> int:
    table = tomllib.loads((REPO / "scripts" / "llms_txt.toml").read_text(encoding="utf-8"))
    limit = table["llms_txt"]["description_limit"]
    assert isinstance(limit, int)
    return limit


def test_there_are_guides_and_an_index() -> None:
    assert INDEX.is_file(), "docs/guides/outcomes/index.md is missing"
    assert GUIDES, "no outcome guides found"


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.name)
def test_the_title_is_the_question_a_practitioner_asks(guide: Path) -> None:
    title = next(line for line in _body(guide).splitlines() if line.startswith("# "))
    assert title.rstrip().endswith("?"), f"{guide.name}: the title is not a question: {title}"


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.name)
def test_the_quotable_answer_is_the_description(guide: Path) -> None:
    """The first block after the title is the answer, and it says what the meta says."""
    description = _description(guide)
    assert len(description) <= _description_limit(), (
        f"{guide.name}: the description is {len(description)} characters; "
        f"docs/llms.txt would cut it at {_description_limit()}"
    )
    blocks = [b for b in _body(guide).split("\n\n") if b.strip()]
    answer = blocks[1]
    assert answer.startswith("**Short answer:**"), f"{guide.name}: no short answer after the title"
    stated = _plain(answer.removeprefix("**Short answer:**"))
    assert stated[:1].lower() + stated[1:] == description[:1].lower() + description[1:], (
        f"{guide.name}: the short answer and the description differ:\n{stated}\n{description}"
    )


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.name)
def test_the_guide_carries_its_sections_in_order(guide: Path) -> None:
    headings = [line[3:].strip() for line in _body(guide).splitlines() if line.startswith("## ")]
    positions = [headings.index(name) for name in REQUIRED if name in headings]
    missing = [name for name in REQUIRED if name not in headings]
    assert not missing, f"{guide.name} lacks {missing}"
    assert positions == sorted(positions), f"{guide.name}: {REQUIRED} are out of order"
    assert headings[-1] == REQUIRED[-1], f"{guide.name}: '{REQUIRED[-1]}' is not last"


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.name)
def test_improving_the_guide_starts_from_the_first_hour(guide: Path) -> None:
    improve = _body(guide).split("\n## Improve this guide", 1)[1]
    assert "CONTRIBUTING.md#your-first-hour" in improve, f"{guide.name}: no first-hour path"
    assert f"docs/guides/outcomes/{guide.name}" in improve, f"{guide.name}: does not name itself"


@pytest.mark.parametrize("guide", GUIDES, ids=lambda p: p.name)
def test_the_guide_reads_in_under_five_minutes(guide: Path) -> None:
    prose = LINK.sub("]", FENCE.sub("", _body(guide)))
    words = len(prose.split())
    assert words <= MAX_WORDS, f"{guide.name} is {words} words; the ceiling is {MAX_WORDS}"


@pytest.mark.parametrize("page", [INDEX, *GUIDES], ids=lambda p: p.name)
def test_every_link_lands(page: Path) -> None:
    dead: list[str] = []
    for target in LINK.findall(FENCE.sub("", _body(page))):
        github = GITHUB.match(target)
        if github:
            location, base = github.group(1), REPO
        elif target.startswith(("http://", "https://", "mailto:")):
            continue
        else:
            location, base = target, page.parent
        path_part, _, anchor = location.partition("#")
        resolved = (base / path_part).resolve() if path_part else page
        if resolved.is_dir() and (resolved / "index.md").is_file() and not github:
            resolved = resolved / "index.md"
        missing_anchor = bool(anchor) and resolved.is_file() and anchor not in _anchors(resolved)
        if not resolved.exists() or missing_anchor:
            dead.append(target)
    assert not dead, f"{page.name}: links that do not land: {dead}"


def test_the_index_links_every_guide_and_the_nav_lists_them() -> None:
    index = _text(INDEX)
    nav = _text(REPO / "properdocs.yml")
    unlinked = [p.name for p in GUIDES if f"({p.name})" not in index]
    unlisted = [p.name for p in [INDEX, *GUIDES] if f"guides/outcomes/{p.name}" not in nav]
    assert not unlinked, f"docs/guides/outcomes/index.md does not link {unlinked}"
    assert not unlisted, f"properdocs.yml nav does not list {unlisted}"
