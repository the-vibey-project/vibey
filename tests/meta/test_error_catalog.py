# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`docs/reference/errors.md` is generated from the error catalog, and says so out loud when not (#1691).

Runs `scripts/error_catalog.py check` as `tests/meta/test_minimum_specs.py` runs its script, and pins
the page into the reference nav and the CLI reference.

Module-level test functions rather than a class: pytest collects `test_*` functions, and the
class-and-interface rule is about production code (ADR-0016).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_the_page_matches_the_catalog() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/error_catalog.py", "check"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


def test_the_page_is_in_the_reference_nav_and_linked_from_the_cli_reference() -> None:
    nav = (REPO / "properdocs.yml").read_text(encoding="utf-8")
    reference = nav.split("  - Reference:", 1)[1].split("\n  - ", 1)[0]
    assert "Error codes: reference/errors.md" in reference
    assert (REPO / "docs" / "reference" / "errors.md").is_file()
    cli = (REPO / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    assert "](errors.md)" in cli and "vibey explain" in cli
