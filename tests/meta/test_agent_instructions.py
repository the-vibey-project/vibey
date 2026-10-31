# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""CLAUDE.md, AGENTS.md and GEMINI.md are what `docs/agents/instructions.toml` makes of them (#1688).

The three front doors had diverged: AGENTS.md carried a non-negotiable the others lacked and cited
a different Article for the same rule. They are now generated from one source by
`scripts/agent_instructions.py`, and the build fails, naming the command, when one is edited by
hand or not regenerated (sub-doctrine 12.e). The invariants below pin what the operator ruled and
what must survive a regeneration.

Module-level test functions rather than a class: pytest collects `test_*` functions, and the
class-and-interface rule is about production code (ADR-0016).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOORS = ("CLAUDE.md", "AGENTS.md", "GEMINI.md")


def _text(door: str) -> str:
    return (REPO / door).read_text(encoding="utf-8")


def test_the_doors_match_the_source() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/agent_instructions.py", "check"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"


@pytest.mark.parametrize("door", DOORS)
def test_every_door_says_it_is_generated_and_keeps_the_provisioners_block(door: str) -> None:
    text = _text(door)
    assert "Generated from docs/agents/instructions.toml" in text.splitlines()[2]
    assert text.count("<!-- vibey:begin -->") == 1 and text.count("<!-- vibey:end -->") == 1
    assert text.index("<!-- vibey:begin -->") < text.index("<!-- vibey:end -->")


@pytest.mark.parametrize("door", ("CLAUDE.md", "AGENTS.md"))
def test_the_governing_rule_cites_the_article_the_operator_ruled_correct(door: str) -> None:
    # Operator ruling on #1688: Article II.3, not IV.4.
    text = " ".join(_text(door).split())
    assert "ratified by the operator's merge per Article II.3" in text
    assert "Article IV.4" not in text


@pytest.mark.parametrize("door", DOORS)
def test_the_sovereign_default_rule_is_in_every_door(door: str) -> None:
    assert "Sovereign self-hosted free is the only default" in " ".join(_text(door).split())


def test_the_standing_subdoctrine_is_carried_by_claude_md_alone_as_declared() -> None:
    assert "Subdoctrine SD-01" in _text("CLAUDE.md")
    assert "Subdoctrine SD-01" not in _text("AGENTS.md")
    assert "Subdoctrine SD-01" not in _text("GEMINI.md")
