# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/the-vibey-project/vibey/)).
"""A small dependency-free DOCX writer for the paper and book surfaces.

``vibey-gh`` deliberately has no runtime dependencies.  Pulling ``python-docx`` into
every consuming repository just to publish an editable documentation copy would violate
that contract, so this module writes the small OOXML vocabulary these exports need
directly.  The result is an ordinary Word document: Word, LibreOffice and Pages can
open it, while the richer PDF/EPUB renderers remain unchanged.
"""

from __future__ import annotations

import html.parser
import io
import re
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast
from xml.sax.saxutils import escape

from vibey_gh.interfaces.docx_interface import (
    DocxBlock,
    DocxErrorInterface,
    DocxWriterInterface,
    HtmlToDocxInterface,
)

__all__ = [
    "DocxError",
    "DocxWriter",
    "HtmlToDocx",
    "write_docx",
]


class DocxError(RuntimeError, DocxErrorInterface):
    """A DOCX export cannot be written and the reason is actionable."""


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

_BLOCK_KINDS = frozenset(
    {"paragraph", "title", "subtitle", "heading", "bullet", "number", "code", "table", "page_break"}
)
_HEADING_STYLES = {1: "Heading1", 2: "Heading2", 3: "Heading3"}
_MATH_REPLACEMENTS = (
    (r"\\mathrm\{([^{}]*)\}", r"\1"),
    (r"\\text\{([^{}]*)\}", r"\1"),
    (r"\\operatorname\{([^{}]*)\}", r"\1"),
    (r"\\mathsf\{([^{}]*)\}", r"\1"),
    (r"\\mathbb\{([^{}]*)\}", r"\1"),
    (r"\\mathbf\{([^{}]*)\}", r"\1"),
    (r"\\leq", "≤"),
    (r"\\geq", "≥"),
    (r"\\subseteq", "⊆"),
    (r"\\supseteq", "⊇"),
    (r"\\to", "→"),
    (r"\\Rightarrow", "⇒"),
    (r"\\left", ""),
    (r"\\right", ""),
    (r"\\infty", "∞"),
    (r"\\sum", "Σ"),
    (r"\\prod", "Π"),
    (r"\\forall", "∀"),
    (r"\\exists", "∃"),
    (r"\\land", "∧"),
    (r"\\lor", "∨"),
    (r"\\top", "⊤"),
    (r"\\bot", "⊥"),
    (r"\\models", "⊨"),
    (r"\\equiv", "≡"),
    (r"\\cup", "∪"),
    (r"\\cap", "∩"),
    (r"\\subset", "⊂"),
    (r"\\in", "∈"),
    (r"\\notin", "∉"),
    (r"\\neq", "≠"),
    (r"\\iff", "⇔"),
    (r"\\succeq", "⪰"),
    (r"\\preceq", "⪯"),
    (r"\\Delta", "Δ"),
    (r"\\Sigma", "Σ"),
    (r"\\phi", "φ"),
    (r"\\Phi", "Φ"),
    (r"\\rho", "ρ"),
    (r"\\sigma", "σ"),
    (r"\\times", "×"),
    (r"\\cdot", "·"),
    (r"\\cdots", "⋯"),
    (r"\\ldots", "…"),
    (r"\\,|\\;|\\!", ""),
)


def _xml_text(value: str) -> str:
    return escape(value, {'"': "&quot;", "'": "&apos;"})


def _math_text(value: str) -> str:
    """Make common inline TeX readable in a Word math run.

    DOCX is an editable delivery format, but ``vibey-gh`` cannot add a TeX or MathJax
    dependency.  The exporter therefore uses Word's math run with a conservative,
    Unicode-normalised rendering of the commands found in the paper.  Unknown commands
    remain visible rather than being silently discarded.
    """
    text = value.strip()
    if text.startswith("$$") and text.endswith("$$"):
        text = text[2:-2].strip()
    elif text.startswith("$") and text.endswith("$"):
        text = text[1:-1].strip()
    text = text.replace(r"\\", "\n")
    for pattern, replacement in _MATH_REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"\\begin\{(?:cases|aligned|array)(?:\{[^}]*\})?\}", "", text)
    text = re.sub(r"\\end\{(?:cases|aligned|array)\}", "", text)
    text = re.sub(r"\\(?:qquad|quad|enspace|space)\b", "  ", text)
    text = text.replace(r"\{", "{").replace(r"\}", "}")
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    return text.replace("\\", "")


def _as_runs(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, str):
        return ({"text": value},)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return ()
    runs: list[Mapping[str, object]] = []
    for item in value:
        if isinstance(item, str):
            runs.append({"text": item})
        elif isinstance(item, Mapping):
            runs.append(item)
    return tuple(runs)


def _plain_runs(runs: Sequence[Mapping[str, object]]) -> str:
    return "".join(str(run.get("text", "")) for run in runs)


class DocxWriter(DocxWriterInterface):
    """Serialize semantic blocks to an OOXML Word document."""

    def build(
        self,
        *,
        title: str,
        author: str,
        blocks: Sequence[DocxBlock],
        page_width_twips: int = 12240,
        page_height_twips: int = 15840,
    ) -> bytes:
        if not title.strip():
            raise DocxError("DOCX metadata needs a title")
        if not author.strip():
            raise DocxError("DOCX metadata needs an author")
        if page_width_twips < 1 or page_height_twips < 1:
            raise DocxError("DOCX page dimensions must be positive twips")
        relationships: list[tuple[str, str]] = []
        document = self._document(
            title,
            author,
            blocks,
            page_width_twips,
            page_height_twips,
            relationships,
        )
        files = {
            "[Content_Types].xml": self._content_types(),
            "_rels/.rels": self._package_relationships(),
            "word/document.xml": document,
            "word/styles.xml": self._styles(),
            "word/numbering.xml": self._numbering(),
            "word/settings.xml": self._settings(),
            "word/_rels/document.xml.rels": self._document_relationships(relationships),
            "docProps/core.xml": self._core_properties(title, author),
            "docProps/app.xml": self._app_properties(),
        }
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return output.getvalue()

    def write(
        self,
        path: Path,
        *,
        title: str,
        author: str,
        blocks: Sequence[DocxBlock],
        page_width_twips: int = 12240,
        page_height_twips: int = 15840,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            self.build(
                title=title,
                author=author,
                blocks=blocks,
                page_width_twips=page_width_twips,
                page_height_twips=page_height_twips,
            )
        )

    def _document(
        self,
        title: str,
        author: str,
        blocks: Sequence[DocxBlock],
        page_width_twips: int,
        page_height_twips: int,
        relationships: list[tuple[str, str]],
    ) -> str:
        body = [
            self._paragraph({"kind": "title", "runs": ({"text": title},)}, relationships),
            self._paragraph({"kind": "subtitle", "runs": ({"text": author},)}, relationships),
        ]
        body.extend(self._block(block, relationships) for block in blocks)
        body.append(
            "<w:sectPr>"
            f'<w:pgSz w:w="{page_width_twips}" w:h="{page_height_twips}"/> '
            '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" '
            'w:header="720" w:footer="720" w:gutter="0"/>'
            "</w:sectPr>"
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<w:document xmlns:w="{_W_NS}" xmlns:r="{_R_NS}" xmlns:m="{_M_NS}">'
            f"<w:body>{''.join(body)}</w:body></w:document>"
        )

    def _block(self, block: DocxBlock, relationships: list[tuple[str, str]]) -> str:
        kind = str(block.get("kind", "paragraph"))
        if kind not in _BLOCK_KINDS:
            raise DocxError(f"unknown DOCX block kind {kind!r}")
        if kind == "page_break":
            return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        if kind == "table":
            return self._table(block, relationships)
        if kind == "code":
            return self._paragraph(block, relationships, text=str(block.get("text", "")))
        return self._paragraph(block, relationships)

    def _paragraph(
        self,
        block: Mapping[str, object],
        relationships: list[tuple[str, str]],
        *,
        text: str | None = None,
    ) -> str:
        kind = str(block.get("kind", "paragraph"))
        props: list[str] = []
        if kind == "title":
            style = "Title"
        elif kind == "subtitle":
            style = "Subtitle"
        elif kind == "heading":
            level = int(cast(Any, block.get("level", 1)))
            style = _HEADING_STYLES.get(level, "Heading3")
        elif kind == "code":
            style = "Code"
        else:
            style = str(block.get("style", "Normal"))
        props.append(f'<w:pStyle w:val="{style}"/>')
        if kind in {"title", "subtitle"} or block.get("center"):
            props.append('<w:jc w:val="center"/>')
        if kind in {"bullet", "number"}:
            num_id = 1 if kind == "bullet" else 2
            level = max(0, min(8, int(cast(Any, block.get("level", 0)))))
            props.append(f'<w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="{num_id}"/></w:numPr>')
        raw_runs: object = ({"text": text},) if text is not None else block.get("runs", ())
        runs = _as_runs(raw_runs)
        if not runs and text is None:
            runs = ({"text": ""},)
        return f"<w:p><w:pPr>{''.join(props)}</w:pPr>{''.join(self._run(run, relationships) for run in runs)}</w:p>"

    def _run(self, run: Mapping[str, object], relationships: list[tuple[str, str]]) -> str:
        text = str(run.get("text", ""))
        if run.get("kind") == "math":
            return (
                '<w:r><w:rPr><w:rStyle w:val="MathChar"/></w:rPr>'
                f"{self._text_nodes(_math_text(text))}</w:r>"
            )
        props: list[str] = []
        if run.get("bold"):
            props.append("<w:b/>")
        if run.get("italic"):
            props.append("<w:i/>")
        if run.get("code"):
            props.append('<w:rStyle w:val="Code"/>')
        if run.get("underline"):
            props.append('<w:u w:val="single"/>')
        run_xml = f"<w:r><w:rPr>{''.join(props)}</w:rPr>{self._text_nodes(text)}</w:r>"
        href = str(run.get("href", ""))
        if not href:
            return run_xml
        if not href.startswith(("https://", "http://", "mailto:")):
            return run_xml
        relationship_id = f"rId{len(relationships) + 1}"
        relationships.append((relationship_id, href))
        return f'<w:hyperlink r:id="{relationship_id}">{run_xml}</w:hyperlink>'

    @staticmethod
    def _text_nodes(text: str) -> str:
        pieces = text.split("\n")
        nodes: list[str] = []
        for index, piece in enumerate(pieces):
            if index:
                nodes.append("<w:br/>")
            nodes.append(f'<w:t xml:space="preserve">{_xml_text(piece)}</w:t>')
        return "".join(nodes)

    def _table(self, block: DocxBlock, relationships: list[tuple[str, str]]) -> str:
        raw_rows = block.get("rows", ())
        rows = raw_rows if isinstance(raw_rows, Sequence) else ()
        row_xml: list[str] = []
        for row_index, raw_row in enumerate(rows):
            cells = raw_row if isinstance(raw_row, Sequence) else ()
            cell_xml: list[str] = []
            for raw_cell in cells:
                runs = _as_runs(raw_cell)
                if row_index == 0:
                    runs = tuple({**run, "bold": True} for run in runs)
                shading = '<w:shd w:fill="D9EAF7"/>' if row_index == 0 else ""
                cell_xml.append(
                    "<w:tc><w:tcPr>"
                    f'<w:tcW w:w="2400" w:type="dxa"/>{shading}<w:vAlign w:val="center"/>'
                    f'</w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr>'
                    f"{''.join(self._run(run, relationships) for run in runs)}</w:p></w:tc>"
                )
            row_xml.append(f"<w:tr>{''.join(cell_xml)}</w:tr>")
        return (
            '<w:tbl><w:tblPr><w:tblLayout w:type="autofit"/>'
            '<w:tblBorders><w:top w:val="single" w:sz="4" w:color="D9D9D9"/>'
            '<w:left w:val="single" w:sz="4" w:color="D9D9D9"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="D9D9D9"/>'
            '<w:right w:val="single" w:sz="4" w:color="D9D9D9"/>'
            '<w:insideH w:val="single" w:sz="4" w:color="D9D9D9"/>'
            '<w:insideV w:val="single" w:sz="4" w:color="D9D9D9"/></w:tblBorders>'
            f"</w:tblPr>{''.join(row_xml)}</w:tbl>"
        )

    @staticmethod
    def _content_types() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
            '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
            "</Types>"
        )

    @staticmethod
    def _package_relationships() -> str:
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Relationships xmlns="{_REL_NS}">'
            f'<Relationship Id="rId1" Type="{_R_NS}/officeDocument" Target="word/document.xml"/>'
            f'<Relationship Id="rId2" Type="{_REL_NS}/metadata/core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>"
        )

    @staticmethod
    def _document_relationships(relationships: Sequence[tuple[str, str]]) -> str:
        base = [
            (
                "rIdStyles",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
                "styles.xml",
            ),
            (
                "rIdNumbering",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering",
                "numbering.xml",
            ),
            (
                "rIdSettings",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings",
                "settings.xml",
            ),
        ]
        links = [
            (
                rid,
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                href,
            )
            for rid, href in relationships
        ]
        parts = [
            f'<Relationship Id="{rid}" Type="{typ}" Target="{_xml_text(target)}"'
            + (' TargetMode="External"' if typ.endswith("/hyperlink") else "")
            + "/>"
            for rid, typ, target in (*base, *links)
        ]
        return f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{_REL_NS}">{"".join(parts)}</Relationships>'

    @staticmethod
    def _styles() -> str:
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:styles xmlns:w="{_W_NS}">'
            '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/> '
            '<w:sz w:val="22"/></w:rPr></w:rPrDefault></w:docDefaults>'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="240"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:spacing w:after="480"/></w:pPr><w:rPr><w:color w:val="000000"/><w:sz w:val="24"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:keepNext/><w:spacing w:before="360" w:after="160"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="28"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="24"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>'
            '<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="000000"/><w:sz w:val="22"/></w:rPr></w:style>'
            '<w:style w:type="character" w:styleId="Code"><w:name w:val="Code"/><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="19"/></w:rPr></w:style>'
            '<w:style w:type="character" w:styleId="MathChar"><w:name w:val="MathChar"/><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:sz w:val="22"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Math"><w:name w:val="Math"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/></w:pPr><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr></w:style>'
            "</w:styles>"
        )

    @staticmethod
    def _numbering() -> str:
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:numbering xmlns:w="{_W_NS}">'
            '<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="multilevel"/>'
            '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>'
            '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="◦"/><w:pPr><w:ind w:left="1440" w:hanging="360"/></w:pPr></w:lvl>'
            '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
            '<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="multilevel"/>'
            '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>'
            '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%2."/><w:pPr><w:ind w:left="1440" w:hanging="360"/></w:pPr></w:lvl>'
            '</w:abstractNum><w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num>'
            "</w:numbering>"
        )

    @staticmethod
    def _settings() -> str:
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{_W_NS}"><w:zoom w:percent="100"/></w:settings>'

    @staticmethod
    def _core_properties(title: str, author: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:title>{_xml_text(title)}</dc:title><dc:creator>{_xml_text(author)}</dc:creator>"
            "</cp:coreProperties>"
        )

    @staticmethod
    def _app_properties() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>vibey-gh</Application></Properties>'
        )


class HtmlToDocx(html.parser.HTMLParser, HtmlToDocxInterface):
    """Convert the sanitized chapter HTML into blocks the writer can serialize."""

    def __init__(self) -> None:
        self._blocks: list[DocxBlock] = []
        self._current: list[Mapping[str, object]] = []
        self._current_kind: str | None = None
        self._current_level = 0
        self._pre = False
        self._pre_text: list[str] = []
        self._list_stack: list[str] = []
        self._bold = 0
        self._italic = 0
        self._code = 0
        self._links: list[str] = []
        self._table_rows: list[tuple[tuple[Mapping[str, object], ...], ...]] = []
        self._table_row: list[tuple[Mapping[str, object], ...]] = []
        self._cell: list[Mapping[str, object]] | None = None
        super().__init__(convert_charrefs=True)

    def convert(self, body: str, *, leading_title: str = "") -> Sequence[DocxBlock]:
        self.reset()
        self.feed(body)
        self.close()
        self._flush()
        blocks = list(self._blocks)
        if leading_title and blocks and blocks[0].get("kind") == "heading":
            first = _plain_runs(_as_runs(blocks[0].get("runs", ())))
            if first.strip() == leading_title.strip():
                blocks.pop(0)
        return tuple(blocks)

    def reset(self) -> None:
        super().reset()
        self._blocks.clear()
        self._current.clear()
        self._current_kind = None
        self._current_level = 0
        self._pre = False
        self._pre_text.clear()
        self._list_stack.clear()
        self._bold = self._italic = self._code = 0
        self._links.clear()
        self._table_rows.clear()
        self._table_row.clear()
        self._cell = None

    def _run(self, text: str) -> Mapping[str, object]:
        run: dict[str, object] = {"text": text}
        if self._bold:
            run["bold"] = True
        if self._italic:
            run["italic"] = True
        if self._code or self._pre:
            run["code"] = True
        if self._links:
            run["href"] = self._links[-1]
            run["underline"] = True
        return run

    def _append(self, text: str) -> None:
        if not text:
            return
        target = self._cell if self._cell is not None else self._current
        target.append(self._run(text))

    def _flush(self) -> None:
        if not self._current_kind:
            return
        if self._current_kind == "code":
            text = "".join(self._pre_text)
            if text:
                self._blocks.append({"kind": "code", "text": text.rstrip("\n")})
        elif any(str(run.get("text", "")) for run in self._current):
            block: dict[str, object] = {"kind": self._current_kind, "runs": tuple(self._current)}
            if self._current_kind in {"heading", "bullet", "number"}:
                block["level"] = self._current_level
            self._blocks.append(block)
        self._current.clear()
        self._pre_text.clear()
        self._current_kind = None
        self._current_level = 0

    def _flush_cell(self) -> None:
        if self._cell is None:
            return
        self._table_row.append(tuple(self._cell))
        self._cell = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            if self._cell is None:
                self._flush()
            self._current_kind = "heading"
            self._current_level = min(3, int(tag[1]))
        elif tag in {"p", "div", "blockquote"} and self._cell is None and not self._pre:
            self._flush()
            self._current_kind = "paragraph"
        elif tag == "pre":
            if self._cell is None:
                self._flush()
            self._pre = True
            self._current_kind = "code"
        elif tag in {"ul", "ol"}:
            if self._cell is None:
                self._flush()
            self._list_stack.append(tag)
        elif tag == "li":
            if self._cell is None:
                self._flush()
            self._current_kind = (
                "number" if self._list_stack and self._list_stack[-1] == "ol" else "bullet"
            )
            self._current_level = max(0, len(self._list_stack) - 1)
        elif tag == "table" and self._cell is None:
            self._flush()
            self._table_rows.clear()
        elif tag == "tr":
            self._flush_cell()
            self._table_row = []
        elif tag in {"td", "th"}:
            self._flush_cell()
            self._cell = []
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            self._links.append(href)
        elif tag in {"strong", "b"}:
            self._bold += 1
        elif tag in {"em", "i"}:
            self._italic += 1
        elif tag == "code":
            self._code += 1
        elif tag == "br":
            self._append("\n")
        elif tag == "img":
            alt = dict(attrs).get("alt") or "image"
            self._append(f"[Image: {alt}]")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "pre":
            self._pre = False
            self._flush()
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "blockquote", "li"}:
            if self._cell is None:
                self._flush()
        elif tag in {"ul", "ol"}:
            if self._list_stack:
                self._list_stack.pop()
        elif tag == "td" or tag == "th":
            self._flush_cell()
        elif tag == "tr":
            self._flush_cell()
            if self._table_row:
                self._table_rows.append(tuple(self._table_row))
                self._table_row = []
        elif tag == "table":
            self._flush_cell()
            if self._table_row:
                self._table_rows.append(tuple(self._table_row))
                self._table_row = []
            if self._table_rows:
                self._blocks.append({"kind": "table", "rows": tuple(self._table_rows)})
            self._table_rows.clear()
        elif tag == "a":
            if self._links:
                self._links.pop()
        elif tag in {"strong", "b"}:
            self._bold = max(0, self._bold - 1)
        elif tag in {"em", "i"}:
            self._italic = max(0, self._italic - 1)
        elif tag == "code":
            self._code = max(0, self._code - 1)

    def handle_data(self, data: str) -> None:
        if self._pre:
            self._pre_text.append(data)
        else:
            self._append(data)


def write_docx(
    path: Path,
    *,
    title: str,
    author: str,
    blocks: Sequence[DocxBlock],
    page_width_twips: int = 12240,
    page_height_twips: int = 15840,
    writer: DocxWriterInterface | None = None,
) -> None:
    """Write one DOCX through an injectable writer.

    This façade is intentionally module-level: it is the stable publishing entry point,
    while ``DocxWriter`` owns the stateful OOXML serialization and has its interface
    beside it.
    """
    selected = writer if writer is not None else DocxWriter()
    selected.write(
        path,
        title=title,
        author=author,
        blocks=blocks,
        page_width_twips=page_width_twips,
        page_height_twips=page_height_twips,
    )
