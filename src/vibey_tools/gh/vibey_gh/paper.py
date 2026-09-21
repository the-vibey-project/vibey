# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Render docs/paper.md as a journal-class LaTeX document (#185).

The doctrine: every repository's documentation also produces a research paper that a
real journal could accept — produced always as Markdown → LaTeX → PDF, liberal with
LaTeX mathematics, and preformatted to an established venue's exact requirements. This
module is the MD → LaTeX stage, targeting IEEEtran (conference two-column by default,
`journal` on request) because IEEEtran ships with every TeX Live and its layout rules
are the requirements of a real, established publisher — the artifact is
submission-shaped by construction.

Stdlib only, like the book exporter: the converter handles the constrained markdown
this family's docs actually use, passes `$...$`, `$$...$$`, and ```latex fences through
untouched so the source can be as liberal with LaTeX as the doctrine demands, and the
LaTeX → PDF compile belongs to the workflow (TeX Live), never to this package's
dependency list.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from vibey_gh.docx import DocxWriter, write_docx as write_document
from vibey_gh.interfaces.docx_interface import DocxBlock, DocxWriterInterface
from vibey_gh.interfaces.paper_interface import PaperDocumentInterface, PaperErrorInterface

__all__ = ["PaperError", "convert", "render_docx", "render_paper", "write_docx"]


class PaperError(RuntimeError, PaperErrorInterface):
    """The paper cannot be rendered and the reason is actionable."""


_SPECIALS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
    "$": r"\$",
}
_SPECIALS_RE = re.compile("|".join(re.escape(k) for k in _SPECIALS))


def _escape(text: str) -> str:
    return _SPECIALS_RE.sub(lambda m: _SPECIALS[m.group(0)], text)


_MATH_SPLIT = re.compile(r"(\$\$.*?\$\$|\$[^$\n]+\$)", re.DOTALL)
_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"\\textbf{\1}"),
    (re.compile(r"\*(.+?)\*"), r"\\emph{\1}"),
    (re.compile(r"\[(.+?)\]\((.+?)\)"), r"\1\\footnote{\\url{\2}}"),
]
_CODE_SPAN = re.compile(r"`([^`]+)`")


def _inline(text: str) -> str:
    """Inline markdown to LaTeX, with math spans passed through untouched.

    Order is the correctness here: math is split out FIRST so `$O(n^2)$` is never
    escaped; code spans are lifted second so backticked text is never bolded; the
    remaining prose is escaped and then styled.
    """
    parts = _MATH_SPLIT.split(text)
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # a math span, verbatim
            out.append(part)
            continue
        spans: list[str] = []

        def lift(match: re.Match[str], spans: list[str] = spans) -> str:
            spans.append(match.group(1))
            return f"\x00{len(spans) - 1}\x00"

        lifted = _CODE_SPAN.sub(lift, part)
        escaped = _escape(lifted)
        for pattern, repl in _INLINE:
            escaped = pattern.sub(repl, escaped)
        for j, span in enumerate(spans):
            escaped = escaped.replace(f"\x00{j}\x00", rf"\texttt{{{_escape(span)}}}")
        out.append(escaped)
    return "".join(out)


@dataclass
class _Doc(PaperDocumentInterface):
    title: str = ""
    abstract: list[str] = None  # type: ignore[assignment]
    body: list[str] = None  # type: ignore[assignment]
    bibliography: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.abstract = []
        self.body = []
        self.bibliography = []


def convert(markdown: str) -> _Doc:
    """The constrained conversion: headings, prose, lists, tables, code, math, refs.

    `# Title` names the paper; a paragraph opening `**Abstract**` becomes the abstract;
    `## References` with a list becomes `thebibliography`; ```latex fences are emitted
    raw — the doctrine's LaTeX-liberal channel; everything else is the markdown the
    docs already write.
    """
    doc = _Doc()
    lines = markdown.splitlines()
    i = 0
    in_refs = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip()
            block: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            if lang == "latex":
                doc.body.extend(block)
            else:
                doc.body.append(r"\begin{verbatim}")
                doc.body.extend(block)
                doc.body.append(r"\end{verbatim}")
            continue
        if line.startswith("$$"):
            doc.body.append(line)
            i += 1
            # A one-line display equation opens and closes on the same line; only a
            # multi-line block consumes further lines, and only until its own closer.
            if not (len(line) > 2 and line.rstrip().endswith("$$")):
                while i < len(lines):
                    doc.body.append(lines[i])
                    i += 1
                    if lines[i - 1].rstrip().endswith("$$"):
                        break
            continue
        if line.startswith("# ") and not doc.title:
            doc.title = _inline(line[2:].strip())
        elif line.startswith("## "):
            heading = line[3:].strip()
            in_refs = heading.lower() == "references"
            if not in_refs:
                doc.body.append(rf"\section{{{_inline(heading)}}}")
        elif line.startswith("### "):
            doc.body.append(rf"\subsection{{{_inline(line[4:].strip())}}}")
        elif re.match(r"^\s*[-*]\s+", line):
            item = re.sub(r"^\s*[-*]\s+", "", line)
            if in_refs:
                doc.bibliography.append(_inline(item))
            else:
                if not doc.body or not doc.body[-1].startswith("\\item"):
                    doc.body.append(r"\begin{itemize}")
                doc.body.append(rf"\item {_inline(item)}")
                if i + 1 >= len(lines) or not re.match(r"^\s*[-*]\s+", lines[i + 1]):
                    doc.body.append(r"\end{itemize}")
        elif (
            line.startswith("|")
            and i + 1 < len(lines)
            and set(lines[i + 1].replace("|", "").strip()) <= {"-", " ", ":"}
        ):
            header = [c.strip() for c in line.strip("|").split("|")]
            rows: list[list[str]] = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            spec = "l" * len(header)
            doc.body.append(rf"\begin{{tabular}}{{{spec}}}")
            doc.body.append(r"\hline")
            doc.body.append(" & ".join(_inline(c) for c in header) + r" \\ \hline")
            for row in rows:
                doc.body.append(" & ".join(_inline(c) for c in row) + r" \\")
            doc.body.append(r"\hline")
            doc.body.append(r"\end{tabular}")
            continue
        elif re.match(r"\s*\*\*Abstract\b", line):
            text = re.sub(r"^\s*\*\*Abstract[.:]?\*\*[.:]?\s*", "", line.strip())
            para = [text] if text else []
            i += 1
            while i < len(lines) and lines[i].strip():
                para.append(lines[i].strip())
                i += 1
            doc.abstract.append(_inline(" ".join(para)))
            continue
        elif line.strip():
            doc.body.append(_inline(line))
        else:
            doc.body.append("")
        i += 1
    if not doc.title:
        raise PaperError("paper.md needs a `# Title` heading")
    if not doc.abstract:
        raise PaperError("paper.md needs a paragraph opening with **Abstract**")
    return doc


def render_paper(markdown: str, author: str, journal: bool = False, keywords: str = "") -> str:
    """The full IEEEtran document for docs/paper.md."""
    doc = convert(markdown)
    mode = "journal" if journal else "conference"
    parts = [
        rf"\documentclass[{mode}]{{IEEEtran}}",
        r"\usepackage{amsmath,amssymb,amsthm}",
        r"\usepackage{algorithmic}",
        r"\usepackage{xcolor}",
        r"\usepackage{tikz}",
        r"\usetikzlibrary{arrows.meta,backgrounds,calc,fit,positioning,shapes.geometric}",
        r"\definecolor{vibeyink}{HTML}{17324D}",
        r"\definecolor{vibeyblue}{HTML}{2F6B9A}",
        r"\definecolor{vibeyteal}{HTML}{168A8A}",
        r"\definecolor{vibeygreen}{HTML}{3A8F5B}",
        r"\definecolor{vibeygold}{HTML}{C68A19}",
        r"\definecolor{vibeyred}{HTML}{B24C4C}",
        r"\definecolor{vibeywash}{HTML}{EEF5FA}",
        r"\definecolor{vibeygray}{HTML}{64748B}",
        r"\tikzset{vibeybox/.style={draw=vibeyink,fill=vibeywash,rounded corners=2pt,align=center,inner sep=3pt,font=\scriptsize},vibeysoft/.style={draw=vibeyblue,fill=vibeyblue!10,rounded corners=2pt,align=center,inner sep=3pt,font=\scriptsize},vibeycore/.style={draw=vibeyink,fill=vibeyink, text=white,rounded corners=2pt,align=center,inner sep=4pt,font=\scriptsize\bfseries},vibeywarn/.style={draw=vibeyred,fill=vibeyred!10,rounded corners=2pt,align=center,inner sep=3pt,font=\scriptsize},vibeyarrow/.style={-{Latex[length=2mm]},thick,draw=vibeyink},vibeydashed/.style={densely dashed,draw=vibeygray,thick}}",
        r"\usepackage{url}",
        r"\newtheorem{theorem}{Theorem}",
        r"\newtheorem{invariant}{Invariant}",
        r"\newtheorem{lemma}{Lemma}",
        r"\begin{document}",
        rf"\title{{{doc.title}}}",
        rf"\author{{\IEEEauthorblockN{{{_escape(author)}}}}}",
        r"\maketitle",
        r"\begin{abstract}",
        *doc.abstract,
        r"\end{abstract}",
    ]
    if keywords:
        parts += [r"\begin{IEEEkeywords}", _escape(keywords), r"\end{IEEEkeywords}"]
    parts += doc.body
    if doc.bibliography:
        parts.append(rf"\begin{{thebibliography}}{{{len(doc.bibliography)}}}")
        for n, entry in enumerate(doc.bibliography, 1):
            parts.append(rf"\bibitem{{ref{n}}} {entry}")
        parts.append(r"\end{thebibliography}")
    parts.append(r"\end{document}")
    return "\n".join(parts) + "\n"


_DOCX_TOKEN = re.compile(
    r"(\$\$.*?\$\$|\$[^$\n]+\$|`[^`]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*|\[[^]]+\]\([^)]*\))"
)
_ABSTRACT = re.compile(r"^\s*\*\*Abstract[.:]?\*\*[.:]?\s*(.*)$", re.IGNORECASE)


def _docx_runs(
    text: str, *, bold: bool = False, italic: bool = False
) -> tuple[Mapping[str, object], ...]:
    """Markdown inline syntax to the small run vocabulary understood by ``DocxWriter``."""
    runs: list[Mapping[str, object]] = []
    position = 0
    for match in _DOCX_TOKEN.finditer(text):
        if match.start() > position:
            runs.append(
                {
                    "text": text[position : match.start()],
                    **({"bold": True} if bold else {}),
                    **({"italic": True} if italic else {}),
                }
            )
        token = match.group(0)
        if token.startswith("**"):
            runs.extend(_docx_runs(token[2:-2], bold=True, italic=italic))
        elif token.startswith("*"):
            runs.extend(_docx_runs(token[1:-1], bold=bold, italic=True))
        elif token.startswith("`"):
            runs.append(
                {
                    "text": token[1:-1],
                    "code": True,
                    **({"bold": True} if bold else {}),
                    **({"italic": True} if italic else {}),
                }
            )
        elif token.startswith("$"):
            runs.append({"kind": "math", "text": token})
        else:
            # `_DOCX_TOKEN` admits only the link shape here, so splitting its two
            # delimiters has no second failure branch to hide from the coverage gate.
            label, href = token[1:-1].split("](", 1)
            runs.append({"text": label, "href": href, "underline": True})
        position = match.end()
    if position < len(text):
        runs.append(
            {
                "text": text[position:],
                **({"bold": True} if bold else {}),
                **({"italic": True} if italic else {}),
            }
        )
    return tuple(runs)


def _docx_latex_block(lines: list[str]) -> str:
    text = " ".join(line.strip() for line in lines)
    text = re.sub(r"\\(?:begin|end)\{[^}]+\}", "", text)
    text = re.sub(r"\\(?:texttt|text|mathrm)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:mathsf|mathbb|mathbf)\{([^{}]*)\}", r"\1", text)
    return re.sub(r"\\([A-Za-z]+)", r"\1", text).replace("mathsf", "").strip()


def _paper_docx_blocks(markdown: str) -> tuple[DocxBlock, ...]:
    """Build an editable, single-column reading form of the paper."""
    blocks: list[DocxBlock] = []
    lines = markdown.splitlines()
    in_references = False
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            blocks.append({"kind": "paragraph", "runs": _docx_runs(" ".join(paragraph_lines))})
            paragraph_lines.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            flush_paragraph()
            i += 1
            continue
        if line.startswith("```"):
            flush_paragraph()
            lang = line[3:].strip()
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            if lang == "latex":
                blocks.append({"kind": "paragraph", "runs": _docx_runs(_docx_latex_block(code))})
            else:
                blocks.append({"kind": "code", "text": "\n".join(code)})
            continue
        if line.startswith("$$"):
            flush_paragraph()
            equation = [line]
            i += 1
            if not (len(line) > 2 and line.rstrip().endswith("$$")):
                while i < len(lines):
                    equation.append(lines[i])
                    i += 1
                    if lines[i - 1].rstrip().endswith("$$"):
                        break
            blocks.append(
                {
                    "kind": "paragraph",
                    "style": "Math",
                    "center": True,
                    "runs": ({"kind": "math", "text": "\n".join(equation)},),
                }
            )
            continue
        if line.startswith("## "):
            flush_paragraph()
            heading = line[3:].strip()
            in_references = heading.casefold() == "references"
            blocks.append({"kind": "heading", "level": 1, "runs": _docx_runs(heading)})
        elif line.startswith("### "):
            flush_paragraph()
            blocks.append({"kind": "heading", "level": 2, "runs": _docx_runs(line[4:].strip())})
        elif (abstract := _ABSTRACT.match(line)) is not None:
            flush_paragraph()
            blocks.append({"kind": "heading", "level": 1, "runs": ({"text": "Abstract"},)})
            paragraph = [abstract.group(1)] if abstract.group(1) else []
            i += 1
            while i < len(lines) and lines[i].strip():
                paragraph.append(lines[i].strip())
                i += 1
            blocks.append({"kind": "paragraph", "runs": _docx_runs(" ".join(paragraph))})
            continue
        elif re.match(r"^\s*[-*]\s+", line):
            flush_paragraph()
            item = re.sub(r"^\s*[-*]\s+", "", line)
            blocks.append(
                {"kind": "number" if in_references else "bullet", "runs": _docx_runs(item)}
            )
        elif (
            line.startswith("|")
            and i + 1 < len(lines)
            and set(lines[i + 1].replace("|", "").strip()) <= {"-", " ", ":"}
        ):
            flush_paragraph()
            header = [cell.strip() for cell in line.strip("|").split("|")]
            rows: list[tuple[tuple[Mapping[str, object], ...], ...]] = [
                tuple(_docx_runs(cell) for cell in header)
            ]
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(
                    tuple(_docx_runs(cell.strip()) for cell in lines[i].strip("|").split("|"))
                )
                i += 1
            blocks.append({"kind": "table", "rows": tuple(rows)})
            continue
        elif line.strip():
            paragraph_lines.append(line.strip())
        else:
            flush_paragraph()
        i += 1
    flush_paragraph()
    return tuple(blocks)


def render_docx(
    markdown: str,
    author: str,
    journal: bool = False,
    keywords: str = "",
    *,
    writer: DocxWriterInterface | None = None,
) -> bytes:
    """Return a Word version of the paper using the same Markdown source as the PDF."""
    del journal, keywords  # The editable form is deliberately single-column and prose-first.
    convert(markdown)
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if title_match is None:
        raise PaperError("paper.md needs a `# Title` heading")
    selected = writer if writer is not None else DocxWriter()
    return selected.build(
        title=title_match.group(1).strip(),
        author=author,
        blocks=_paper_docx_blocks(markdown),
    )


def write_docx(
    markdown: str,
    path: Path,
    author: str,
    journal: bool = False,
    keywords: str = "",
    *,
    writer: DocxWriterInterface | None = None,
) -> None:
    """Write the paper's DOCX form through an injectable writer."""
    del journal, keywords
    convert(markdown)
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if title_match is None:
        raise PaperError("paper.md needs a `# Title` heading")
    write_document(
        path,
        title=title_match.group(1).strip(),
        author=author,
        blocks=_paper_docx_blocks(markdown),
        writer=writer,
    )
