# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every `[acp]` key is in the configuration reference's table, and every row is a key."""

import dataclasses
import re
from pathlib import Path

from vibey.domain.acp.settings import AcpSettings

DOC = Path(__file__).resolve().parents[2] / "docs" / "reference" / "configuration.md"


def _documented_keys() -> set[str]:
    text = DOC.read_text(encoding="utf-8")
    start = text.index("## `[acp]`")
    end = text.index("\n## ", start + 1)
    return set(re.findall(r"^\| `(\w+)` \|", text[start:end], flags=re.MULTILINE))


def test_the_acp_table_documents_exactly_the_settings_fields() -> None:
    fields = {field.name for field in dataclasses.fields(AcpSettings)}
    documented = _documented_keys()
    assert fields - documented == set(), "undocumented [acp] keys"
    assert documented - fields == set(), "documented [acp] keys that do not exist"
