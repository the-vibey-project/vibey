# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every documentation page's front matter is YAML the site can parse.

A page whose front matter does not parse is not an error to the site build: the block is
printed as text at the top of the page. Two continuation pages did exactly that, because an
unquoted `description:` carried a second `": "` ("... runs: take ..."), which YAML reads as a
nested mapping and refuses. This is the check that says so before a reader sees it (12.e).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

DOCS = Path(__file__).resolve().parents[2] / "docs"
PAGES = sorted(p for p in DOCS.rglob("*.md") if p.read_text(encoding="utf-8").startswith("---\n"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: str(p.relative_to(DOCS)))
def test_front_matter_parses_as_a_mapping(page: Path) -> None:
    text = page.read_text(encoding="utf-8")
    block = text[4:].split("\n---\n", 1)
    assert len(block) == 2, f"{page}: front matter opens with --- but never closes"
    try:
        meta = yaml.safe_load(block[0])
    except yaml.YAMLError as error:
        pytest.fail(f"{page}: front matter is not valid YAML, so the site prints it: {error}")
    assert isinstance(meta, dict), f"{page}: front matter is not a mapping"
    assert all(isinstance(v, (str, int, float, bool, list, dict)) for v in meta.values())
