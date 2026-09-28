"""Regression tests for the context microslice migration operation."""

from __future__ import annotations

import importlib.util
import sys
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
