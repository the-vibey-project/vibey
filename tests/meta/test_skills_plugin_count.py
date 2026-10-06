# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The root pages' "the N skills plugins" matches vibey-skills' catalogue.

vibey-skills polices its own counts (`src/vibey_tools/skills/tests/test_catalogue_counts.py`),
but the repository's README and docs index say it too, and nothing read them: when #1430
merged develop, a resolution that kept one side of README.md wholesale put "the 138 skills
plugins" back over #1433's 141, and nothing noticed. This is the check that says so.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CATALOGUE = REPO / "src" / "vibey_tools" / "skills" / ".claude-plugin" / "marketplace.json"
ADVERTISED = ("README.md", "docs/index.md")
COUNT = re.compile(r"the (\d+)\s+skills plugins")


def _actual() -> int:
    return len(json.loads(CATALOGUE.read_text(encoding="utf-8"))["plugins"])


@pytest.mark.parametrize("page", ADVERTISED)
def test_each_page_states_the_skills_plugin_count_the_catalogue_holds(page: str) -> None:
    found = COUNT.findall((REPO / page).read_text(encoding="utf-8"))
    assert found, f"{page} no longer says how many skills plugins the marketplace carries"
    assert {int(n) for n in found} == {_actual()}, (page, found, _actual())
