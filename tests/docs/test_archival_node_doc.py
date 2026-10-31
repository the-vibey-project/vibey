"""Check archival node behaviour documentation."""

import pathlib
import re


def test_archival_node_section():
    root = pathlib.Path(__file__).parents[2]
    path = root / "docs/plans/qwenstorm-3.0.0/issue-audit/updates/114.md"
    text = path.read_text(encoding="utf-8")
    assert re.search(r"^## Archival node behaviour", text, re.MULTILINE), "Missing archival node section header"
