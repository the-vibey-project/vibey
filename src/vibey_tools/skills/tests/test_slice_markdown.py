# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Regression tests for the context microslice migration operation."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pytest


def _module():
    path = Path(__file__).parents[1] / "tools" / "slice_markdown.py"
    spec = importlib.util.spec_from_file_location("slice_markdown", path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load slice_markdown.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_slice_markdown_preserves_source_and_links_neighbours(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "guide.md"
    original = "# Guide\n\nIntro.\n\n## First\n\nOne.\n\n## Second\n\nTwo.\n"
    source.write_text(original, encoding="utf-8")

    records = module.slice_markdown(source, tmp_path / "slices")

    assert source.read_text(encoding="utf-8") == original
    assert len(records) == 2
    assert records[0].links == (records[1].id,)
    assert records[1].requires == (records[0].id,)
    assert (tmp_path / "slices" / "index.json").exists()


def test_slice_markdown_ids_are_deterministic(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "guide.md"
    source.write_text("## One\n\nContent.\n", encoding="utf-8")

    first = module.slice_markdown(source, tmp_path / "one")[0].id
    second = module.slice_markdown(source, tmp_path / "two")[0].id

    assert first == second


def test_slice_markdown_rejects_documents_without_requested_headings(tmp_path: Path) -> None:
    module = _module()
    source = tmp_path / "guide.md"
    source.write_text("No headings.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no level-2 headings"):
        module.slice_markdown(source, tmp_path / "slices")


class SliceMarkdownFenceTest(unittest.TestCase):
    """A `## ` line inside fenced code is content, never a slice boundary.

    The converter used to split on every `## ` line, so a SKILL.md that shows another
    SKILL.md's skeleton in a fence was cut mid-fence: eight generated slices opened a code
    block they never closed (the documentation deep scan, 2026-10-02). `SKELETON` is that
    construct, as research-editing-a-reference-skill writes it.
    """

    SKELETON = (
        "## Anatomy of a generated SKILL.md\n\n"
        "```\n---\nname: <matches the directory name>\n---\n\n"
        "## 13. <Section title>\n\nBody.\n\n## 14. <Section title>\n```\n\n"
        "## The cross-reference rule\n\nText.\n"
    )

    def setUp(self) -> None:
        self.module = _module()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def titles(self, text: str) -> list[str]:
        return [title for _, title in self.module._headings(text, 2)]

    def test_a_heading_inside_a_fence_does_not_split_it(self) -> None:
        source = self.tmp / "SKILL.md"
        source.write_text(self.SKELETON, encoding="utf-8")
        records = self.module.slice_markdown(source, self.tmp / "slices")
        self.assertEqual(
            [r.purpose for r in records],
            ["anatomy of a generated skill md", "the cross reference rule"],
        )
        first = Path(records[0].output).read_text(encoding="utf-8")
        self.assertIn("## 13. <Section title>", first)
        self.assertEqual(first.count("```"), 2)

    def test_fences_open_and_close_by_the_commonmark_rule(self) -> None:
        cases = {
            "~~~\n## in tildes\n~~~\n## after\n": ["after"],
            "````md\n```\n## inside the longer fence\n```\n````\n## after\n": ["after"],
            "```\n## a shorter run does not close it\n``\n~~~\n## nor the other char\n": [],
            "```\n``` text after is no closer\n## still inside\n": [],
            "   ```\n## inside\n   ```\n## after\n": ["after"],
            "    ```\n## four columns is no fence\n": ["four columns is no fence"],
            "``` info with ` a backtick\n## not a fence\n": ["not a fence"],
            "~~~ info with ` a backtick\n## inside\n~~~\n": [],
            "\t```\n## a tab is four columns\n": ["a tab is four columns"],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.titles(text), expected)

    def test_inline_code_and_fenced_backticks_in_prose_are_not_fences(self) -> None:
        text = '## One\n\nA ` ``` ` span and r"^```bash$" in prose.\n\n## Two\n'
        self.assertEqual(self.titles(text), ["One", "Two"])

    def test_only_the_requested_level_starting_a_line_is_a_boundary(self) -> None:
        text = "# Top\n### Three\n  ## indented\n##no space\n## Two  \r\n"
        self.assertEqual(self.titles(text), ["Two"])
