# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/the-vibey-project/vibey/)).
"""Contract tests for the dependency-free editable-document surface."""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from vibey_gh.docx import DocxError, DocxWriter, HtmlToDocx, write_docx
from vibey_gh.interfaces.docx_interface import (
    DocxErrorInterface,
    DocxWriterInterface,
    HtmlToDocxInterface,
)


def test_the_writer_is_a_valid_ooxml_package_with_semantic_content():
    payload = DocxWriter().build(
        title="A & <Title>",
        author="An Author",
        blocks=(
            {
                "kind": "paragraph",
                "runs": (
                    {"text": 'plain & quoted "text"'},
                    {"text": "bold", "bold": True, "italic": True, "code": True, "underline": True},
                    {"text": "safe", "href": "javascript:ignored"},
                    {"text": "link", "href": "https://example.test/a?x=1&y=2"},
                    {"kind": "math", "text": "$$\\sum_{i=0}^{n} x_i \\leq \\infty$$"},
                ),
            },
            {"kind": "heading", "level": 4, "runs": "A heading"},
            {"kind": "bullet", "level": 1, "runs": ({"text": "bullet"},)},
            {"kind": "number", "runs": ({"text": "number"},)},
            {"kind": "code", "text": "one\ntwo"},
            {"kind": "table", "rows": (("Column", "Value"), (("row",), ("cell",)))},
            {"kind": "page_break"},
            {"kind": "paragraph", "runs": None},
        ),
    )
    expected = {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/document.xml",
        "word/styles.xml",
        "word/numbering.xml",
        "word/settings.xml",
        "word/_rels/document.xml.rels",
        "docProps/core.xml",
        "docProps/app.xml",
    }
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == expected
        document = archive.read("word/document.xml").decode()
        relationships = archive.read("word/_rels/document.xml.rels").decode()
        for name in expected:
            if name.endswith(".xml"):
                ET.fromstring(archive.read(name))
    assert "A &amp; &lt;Title&gt;" in document
    assert "plain &amp; quoted" in document
    assert "bold" in document and "bullet" in document and "number" in document
    assert "one" in document and "two" in document
    assert "Column" in document and "cell" in document
    assert 'w:type="page"' in document
    assert "MathChar" in document
    assert "https://example.test/a?x=1&amp;y=2" in relationships
    assert "javascript:ignored" not in relationships


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"title": "", "author": "A"}, "title"),
        ({"title": "T", "author": ""}, "author"),
        ({"title": "T", "author": "A", "page_width_twips": 0}, "dimensions"),
    ],
)
def test_the_writer_rejects_invalid_metadata_or_dimensions(kwargs, message):
    with pytest.raises(DocxError, match=message):
        DocxWriter().build(blocks=(), page_height_twips=1, **kwargs)


def test_the_writer_rejects_unknown_blocks_and_the_facade_writes(tmp_path):
    with pytest.raises(DocxError, match="unknown DOCX block"):
        DocxWriter().build(title="T", author="A", blocks=({"kind": "unknown"},))

    output = tmp_path / "document.docx"
    write_docx(output, title="T", author="A", blocks=())
    assert output.is_file()

    class SpyWriter:
        def __init__(self) -> None:
            self.called = False

        def write(self, path: Path, **kwargs: object) -> None:
            self.called = True
            assert kwargs["title"] == "T"
            path.write_bytes(b"spy")

    spy = SpyWriter()
    write_docx(output, title="T", author="A", blocks=(), writer=spy)
    assert spy.called and output.read_bytes() == b"spy"


def test_html_is_converted_to_blocks_without_dropping_editable_content():
    html = """
    <h1>Chapter title</h1>
    <h4>Deep heading</h4>
    <p>Hello <strong>bold</strong> <em>italic</em> <code>code</code>
      <a href="https://example.test">link</a><br/>line <img alt="diagram"/></p>
    <ul><li>one<ul><li>nested</li></ul></li></ul>
    <ol><li>two</li></ol>
    <pre><code>alpha
beta</code></pre>
    <table><tr><th>Head</th><th>Value</th></tr><tr><td>Cell</td><td><b>bold cell</b></td></tr></table>
    <div>tail</div>
    """
    converter = HtmlToDocx()
    blocks = converter.convert(html, leading_title="Chapter title")
    kinds = [str(block["kind"]) for block in blocks]
    assert kinds[0] == "heading" and blocks[0]["level"] == 3
    assert not any("Chapter title" == str(run.get("text")) for run in blocks[0].get("runs", ()))
    assert "paragraph" in kinds and "bullet" in kinds and "number" in kinds
    assert "code" in kinds and "table" in kinds
    paragraph_text = " ".join(
        str(run.get("text", ""))
        for block in blocks
        if block["kind"] == "paragraph"
        for run in block.get("runs", ())
    )
    assert (
        "bold" in paragraph_text
        and "italic" in paragraph_text
        and "[Image: diagram]" in paragraph_text
    )
    assert any(block.get("level") == 1 for block in blocks if block["kind"] == "bullet")
    assert any(block["kind"] == "code" and "alpha\nbeta" in str(block["text"]) for block in blocks)
    table = next(block for block in blocks if block["kind"] == "table")
    assert len(table["rows"]) == 2

    assert isinstance(converter, HtmlToDocxInterface)
    assert converter.convert("<h1>Keep me</h1>", leading_title="Other")[0]["kind"] == "heading"


def test_html_converter_reset_and_empty_elements_are_safe():
    converter = HtmlToDocx()
    assert converter.convert("") == ()
    assert converter.convert("<p></p><pre></pre>") == ()
    blocks = converter.convert("<p>one</p><p>two</p>")
    assert [block["kind"] for block in blocks] == ["paragraph", "paragraph"]
    assert isinstance(converter, HtmlToDocxInterface)


def test_html_converter_handles_empty_closers_and_tags_inside_cells():
    converter = HtmlToDocx()
    blocks = converter.convert(
        "</ul></a><table><tr></tr></table>"
        "<table><tr><td><h6>cell heading</h6><pre>cell code</pre>"
        "<ul><li>cell item</li></ul><p>cell prose</p></td></tr></table>"
        "<table><tr><td>unclosed</table>"
    )
    assert isinstance(blocks, tuple)
    assert converter.convert("$$open") == ()
    converter._append("")


def test_run_normalization_skips_nonsemantic_items_after_a_mapping():
    from vibey_gh.docx import _as_runs

    assert _as_runs(({"text": "kept"}, object())) == ({"text": "kept"},)


def test_writer_and_converter_interfaces_are_runtime_checkable():
    assert isinstance(DocxWriter(), DocxWriterInterface)
    assert isinstance(DocxError("x"), DocxErrorInterface)
