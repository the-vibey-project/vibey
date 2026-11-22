# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every `[web]` key is in the configuration reference's table, and every row is a key
(ADR-0102, ADR-0018).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import dataclasses
import re
from pathlib import Path

from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.web.web_settings_loader import KEYS

DOC = Path(__file__).resolve().parents[2] / "docs" / "reference" / "configuration.md"


def _documented_keys() -> set[str]:
    text = DOC.read_text(encoding="utf-8")
    start = text.index("## `[web]`")
    end = text.index("\n## ", start + 1)
    return set(re.findall(r"^\| `(\w+)` \|", text[start:end], flags=re.MULTILINE))


def test_the_web_table_documents_exactly_the_settings_and_the_loader_reads_them_all() -> None:
    fields = {field.name for field in dataclasses.fields(WebToolSettings)}
    assert fields == KEYS
    documented = _documented_keys()
    assert fields - documented == set(), "undocumented [web] keys"
    assert documented - fields == set(), "documented [web] keys that do not exist"
