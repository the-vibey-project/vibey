# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/llms_txt.py`: descriptions, sections, the offline forms, and the drift check.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import llms_txt as lt

SITE = """\
site_name: demo
site_description: >-
  A demo site that exists
  for the tests.
site_url: https://example.org/demo/
repo_url: https://example.org/src/demo

nav:
  - Home: index.md
  - Guides:
      - First: guides/first.md
  - Architecture:
      - Decision records:
          - "0001 — Keep it simple": adr/0001-simple.md
"""


def _describer() -> lt.MarkdownPageDescriber:
    return lt.MarkdownPageDescriber(limit=80)


def _page(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_declared_description_wins(tmp_path: Path) -> None:
    page = _page(tmp_path, "a.md", "---\ndescription: Said on purpose.\n---\n# A\n\nProse.\n")
    assert _describer().describe(page) == "Said on purpose."


def test_the_first_prose_sentence_is_plain_text(tmp_path: Path) -> None:
    page = _page(
        tmp_path,
        "b.md",
        "<!-- a comment\n spanning lines -->\n# B\n\n[![badge](x)](y)\n\n"
        "**Bottom line:** the [`queue`](q.md) *never* loses work. It re-reads.\n",
    )
    assert _describer().describe(page) == "the queue never loses work."


def test_a_decision_record_carries_its_title_alone(tmp_path: Path) -> None:
    page = _page(tmp_path, "c.md", "# 0001 — X\n\n**Status:** accepted\n\n## Decision\n\nDo X.\n")
    assert _describer().describe(page) == ""


def test_a_long_sentence_is_cut_at_a_word(tmp_path: Path) -> None:
    page = _page(tmp_path, "d.md", "# D\n\n" + "word " * 40 + "end.\n")
    described = _describer().describe(page)
    assert described.endswith("…") and len(described) <= 81 and "  " not in described


def test_a_page_with_no_prose_has_no_description(tmp_path: Path) -> None:
    page = _page(tmp_path, "e.md", "# E\n\n```\ncode only\n```\n\n| a | b |\n")
    assert _describer().describe(page) == ""


def test_site_facts_read_a_folded_description() -> None:
    facts = lt.SiteFacts.read(SITE)
    assert facts == lt.SiteFacts(
        "demo", "A demo site that exists for the tests.", "https://example.org/demo/"
    )
    with pytest.raises(ValueError, match="site_name"):
        lt.SiteFacts.read("nav:\n")


def _docs(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    _page(docs, "index.md", "# Home\n\nThe home page.\n")
    _page(docs, "guides/first.md", "# First\n\nThe first guide.\n")
    _page(docs, "adr/0001-simple.md", "# 0001\n\n## Decision\n\nSimple.\n")
    return docs


def test_the_index_follows_the_navigation_and_its_sections(tmp_path: Path) -> None:
    docs = _docs(tmp_path)
    governance = _page(
        tmp_path / "law", "constitution.md", "# The Constitution\n\nThe law.\n"
    ).parent
    _page(governance, "sd-01-x.md", "# SD-01: Trust\n\nStanding.\n")
    builder = lt.LlmsTxtBuilder(
        output=docs / "llms.txt",
        sources=(
            lt.NavLinkSource(
                SITE, docs, "https://example.org/demo/main/", "Start here", _describer()
            ),
            lt.GovernanceLinkSource(
                governance,
                ("constitution.md",),
                "sd-*.md",
                "https://example.org/demo/main/",
                "Governance",
                _describer(),
            ),
            lt.DownloadLinkSource(True, True, "https://example.org/demo/main/", "Offline forms"),
        ),
        renderer=lt.LlmsTxtRenderer(lt.SiteFacts.read(SITE), "https://example.org/src/demo"),
    )
    text = builder.text()
    assert text.startswith("# demo\n\n> A demo site that exists for the tests.\n")
    assert "## Start here\n\n- [Home](https://example.org/demo/main/): The home page.\n" in text
    assert (
        "## Guides\n\n- [First](https://example.org/demo/main/guides/first/): The first guide.\n"
        in text
    )
    assert "## Architecture — Decision records\n\n- [0001 — Keep it simple](" in text
    assert "adr/0001-simple/)\n" in text
    assert (
        "- [SD-01 — Trust](https://example.org/demo/main/governance/sd-01-x/): Standing.\n" in text
    )
    assert "paper.pdf" in text and "book.epub" in text

    ok, message = builder.check()
    assert not ok and "missing" in message
    builder.write()
    assert builder.check() == (True, "llms.txt matches the navigation")
    (docs / "llms.txt").write_text("stale\n", encoding="utf-8")
    ok, message = builder.check()
    assert not ok and "stale" in message


def test_offline_forms_follow_what_the_site_publishes() -> None:
    assert lt.DownloadLinkSource(False, False, "u/", "h").entries() == []
    only_paper = lt.DownloadLinkSource(True, False, "u/", "h").entries()
    assert [e.url for e in only_paper] == ["u/paper.pdf"]


def test_a_missing_page_or_governance_document_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="index.md"):
        lt.NavLinkSource(SITE, tmp_path, "u/", "s", _describer()).entries()
    with pytest.raises(FileNotFoundError, match="constitution.md"):
        lt.GovernanceLinkSource(
            tmp_path, ("constitution.md",), "sd-*.md", "u/", "g", _describer()
        ).entries()
    assert lt.GovernanceLinkSource(None, (), "", "u/", "g", _describer()).entries() == []
