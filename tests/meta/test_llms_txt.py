# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""docs/llms.txt is exactly what the documentation's navigation produces.

The index an AI reader fetches first is generated from `properdocs.yml` by
`scripts/llms_txt.py` (ADR-0076). A page added to the navigation without regenerating the
index would be a page the index silently does not know -- the drift sub-doctrine 7.d
forbids and 12.e says a machine must catch. So the build fails, naming the command, until
the committed file matches.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_the_committed_index_matches_the_navigation() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/llms_txt.py", "--check"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


def test_every_navigation_page_is_in_the_index() -> None:
    """The check compares bytes; this says which page is missing when it fails."""
    from vibey_gh.book import NavReader

    index = (REPO / "docs" / "llms.txt").read_text(encoding="utf-8")
    nav = (REPO / "properdocs.yml").read_text(encoding="utf-8")
    missing = [
        chapter.source
        for chapter in NavReader().read(nav)
        if f"/{chapter.site_page.removesuffix('index.html')})" not in index
    ]
    assert not missing, f"not in docs/llms.txt: {missing}"
