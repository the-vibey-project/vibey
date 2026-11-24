# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `capabilities` row of `vibey loops` in the CLI reference names every capability.

`vibey loops --json` reports one key per `EngineAffordances` field; the reference's row was
written when there were six and went stale when `skills` and `web_search` joined. A field the
row does not name is a key a reader of the document has no description of.
"""

from dataclasses import fields
from pathlib import Path

from vibey.domain.engine import EngineAffordances

CLI_DOC = Path(__file__).resolve().parents[2] / "docs" / "reference" / "cli.md"


def _capabilities_row() -> str:
    rows = [
        line
        for line in CLI_DOC.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `capabilities` |")
    ]
    assert len(rows) == 1, rows
    return rows[0]


def test_the_capabilities_row_names_every_affordance() -> None:
    row = _capabilities_row()
    missing = [
        f.name
        for f in fields(EngineAffordances)
        if f.name != "evidence" and f"`{f.name}`" not in row
    ]
    assert not missing, f"docs/reference/cli.md's capabilities row does not name {missing}"


def test_the_capabilities_row_names_its_evidence() -> None:
    assert "`evidence`" in _capabilities_row()


def test_the_cli_doc_names_builtin_web_and_the_capabilities_flag() -> None:
    """The per-loop row for claudeloop says what Phase 4 changed: web search is off unless
    `[loops] builtin_web` turns it on, and plugins, skills and MCP come from the snapshot
    `run --capabilities` names, not from a `--web-search` vibey passes."""
    rows = [
        line
        for line in CLI_DOC.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `claudeloop`, `claudeloop-local` |")
    ]
    assert len(rows) == 1, rows
    row = rows[0]
    assert "`[loops] builtin_web`" in row
    assert "`run --capabilities`" in row
    assert "--web-search" not in row
