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

Three things a submitted article carries that a Markdown file does not are added here,
never typed by hand. The *provenance* — who wrote it, from which revision, committed and
rendered when — is computed by the caller from git and the clock and placed in the
byline, the first-page note and wherever the source writes the `<!-- vibey:provenance -->`
marker. The *visual atlas* is the set of ```latex figure fences; `figures()` reads them
out, `figure_document()` wraps one as a standalone document a TeX engine can compile on
its own, and `inline_figures()` puts a rendered SVG back into the Markdown for the site
and the book, which cannot run TeX. And the *design system* the figures share — the
palette, the node and edge styles, the plot house style — is one preamble, `PREAMBLE`,
so the PDF, the standalone figures and any figure lab draw from the same definitions.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from vibey_gh.docx import DocxWriter, write_docx as write_document
from vibey_gh.interfaces.docx_interface import DocxBlock, DocxWriterInterface
from vibey_gh.interfaces.paper_interface import (
    PaperDocumentInterface,
    PaperErrorInterface,
    PaperFigureInterface,
    PaperProvenanceInterface,
    RevisionReaderInterface,
)

__all__ = [
    "PREAMBLE",
    "PROVENANCE_MARKER",
    "Figure",
    "PaperError",
    "Provenance",
    "RevisionReader",
    "convert",
    "figure_document",
    "figures",
    "inline_figures",
    "provenance_markdown",
    "render_docx",
    "render_paper",
    "write_docx",
]

PROVENANCE_MARKER = "<!-- vibey:provenance -->"
#: The project's provenance line, as every source file in the family carries it.
HEART = "❤️"


class PaperError(RuntimeError, PaperErrorInterface):
    """The paper cannot be rendered and the reason is actionable."""


#: The visual design system every figure inherits: palette, node and edge styles, and the
#: pgfplots house style. One definition for the PDF and for every standalone figure.
PREAMBLE: tuple[str, ...] = (
    # IEEEtran asks for Times, Helvetica and Courier by their Type 1 family names (ptm, phv,
    # pcr); under XeTeX those families have no TU font definitions, so without fontspec the
    # whole paper silently falls back to Latin Modern. The TeX Gyre clones are named by file
    # so Tectonic finds them in its bundle without a system font lookup.
    r"\usepackage{fontspec}",
    r"\setmainfont{texgyretermes}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]",
    r"\setsansfont{texgyreheros}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]",
    r"\setmonofont{texgyrecursor}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]",
    r"\usepackage{amsmath,amssymb,amsthm}",
    r"\usepackage{algorithmic}",
    r"\usepackage{xcolor}",
    r"\usepackage{tikz}",
    (
        r"\usetikzlibrary{arrows.meta,backgrounds,calc,fit,positioning,shapes.geometric,shapes.misc,"
        r"shapes.symbols,decorations.pathreplacing,decorations.markings,"
        r"decorations.pathmorphing,patterns,matrix,chains,intersections,angles,quotes}"
    ),
    r"\usepackage{pgfplots}",
    r"\pgfplotsset{compat=1.18}",
    r"\usepgfplotslibrary{fillbetween,statistics,polar,groupplots}",
    r"\usepackage{pifont}",
    r"\usepackage{url}",
    r"\definecolor{vibeyink}{HTML}{17324D}",
    r"\definecolor{vibeyblue}{HTML}{2F6B9A}",
    r"\definecolor{vibeysky}{HTML}{4FA3D1}",
    r"\definecolor{vibeyteal}{HTML}{168A8A}",
    r"\definecolor{vibeymint}{HTML}{2EA97F}",
    r"\definecolor{vibeygreen}{HTML}{3A8F5B}",
    r"\definecolor{vibeygold}{HTML}{C68A19}",
    r"\definecolor{vibeyamber}{HTML}{E0A83A}",
    r"\definecolor{vibeyred}{HTML}{B24C4C}",
    r"\definecolor{vibeyrose}{HTML}{D98A8A}",
    r"\definecolor{vibeyviolet}{HTML}{6B5BD2}",
    r"\definecolor{vibeylilac}{HTML}{A89BE8}",
    r"\definecolor{vibeygray}{HTML}{64748B}",
    r"\definecolor{vibeysilver}{HTML}{A7B2C2}",
    r"\definecolor{vibeyline}{HTML}{D6E0EA}",
    r"\definecolor{vibeywash}{HTML}{EEF5FA}",
    r"\definecolor{vibeymist}{HTML}{F6F9FC}",
    (
        r"\tikzset{"
        r"every node/.append style={font=\sffamily},"
        r"vbase/.style={rounded corners=4pt,align=center,inner xsep=7pt,inner ysep=5pt,"
        r"font=\sffamily\scriptsize,line width=.65pt,minimum height=.75cm},"
        r"vibeybox/.style={vbase,draw=vibeyblue!65,fill=white},"
        r"vibeysoft/.style={vbase,draw=vibeyblue!80,fill=vibeyblue!11},"
        r"vibeycore/.style={vbase,draw=vibeyink,fill=vibeyink,"
        r"text=white,font=\sffamily\scriptsize\bfseries},"
        r"vibeywarn/.style={vbase,draw=vibeyred!85,fill=vibeyred!9},"
        r"vibeygood/.style={vbase,draw=vibeygreen!85,fill=vibeygreen!10},"
        r"vibeygate/.style={vbase,draw=vibeygold!90,fill=vibeygold!11,line width=.85pt,double,double distance=1.2pt},"
        r"vibeytealbox/.style={vbase,draw=vibeyteal!85,fill=vibeyteal!9},"
        r"vibeyvioletbox/.style={vbase,draw=vibeyviolet!85,fill=vibeyviolet!9},"
        r"vibeyghost/.style={vbase,draw=vibeysilver,dashed,fill=white,text=vibeygray},"
        r"vibeypill/.style={rounded rectangle,fill=vibeyink!8,draw=none,font=\sffamily\tiny,"
        r"inner xsep=5pt,inner ysep=2.2pt,text=vibeyink,align=center},"
        r"vibeytag/.style={rounded corners=2.5pt,fill=vibeyink,text=white,draw=none,font=\sffamily\tiny\bfseries,"
        r"inner xsep=4pt,inner ysep=2pt,align=center},"
        r"vibeybadgeteal/.style={rounded corners=2.5pt,fill=vibeyteal,text=white,draw=none,font=\sffamily\tiny\bfseries,"
        r"inner xsep=4pt,inner ysep=2pt,align=center},"
        r"vibeybadgered/.style={rounded corners=2.5pt,fill=vibeyred,text=white,draw=none,font=\sffamily\tiny\bfseries,"
        r"inner xsep=4pt,inner ysep=2pt,align=center},"
        r"vibeybadgegreen/.style={rounded corners=2.5pt,fill=vibeygreen,text=white,draw=none,font=\sffamily\tiny\bfseries,"
        r"inner xsep=4pt,inner ysep=2pt,align=center},"
        r"vibeybadgegold/.style={rounded corners=2.5pt,fill=vibeygold!90!black,text=white,draw=none,font=\sffamily\tiny\bfseries,"
        r"inner xsep=4pt,inner ysep=2pt,align=center},"
        r"vibeypanel/.style={draw=vibeyline,fill=vibeymist,rounded corners=8pt,inner sep=8pt,line width=.6pt},"
        r"vibeynote/.style={font=\sffamily\tiny,text=vibeygray,align=center},"
        r"vibeycallout/.style={font=\sffamily\tiny,text=vibeyred,align=center},"
        r"vibeyhead/.style={font=\sffamily\scriptsize\bfseries,text=vibeyink},"
        r"vibeylane/.style={draw=vibeyline,fill=vibeymist,rounded corners=6pt,inner sep=7pt,line width=.5pt},"
        r"vibeylanelabel/.style={font=\sffamily\tiny\bfseries,text=vibeygray,anchor=north west,inner sep=3pt},"
        r"vibeyorbit/.style={line width=.9pt},"
        r"vibeynucleus/.style={circle,draw=vibeyink,fill=vibeyink,"
        r"text=white,font=\sffamily\tiny\bfseries,align=center},"
        r"vibeyarrow/.style={-{Stealth[length=2.4mm,width=1.8mm,round]},line width=.75pt,draw=vibeyink,"
        r"line cap=round,line join=round,shorten >=1pt},"
        r"vibeyflow/.style={vibeyarrow,line width=1.1pt,draw=vibeyblue},"
        r"vibeyback/.style={-{Stealth[length=2.2mm,width=1.6mm,round]},densely dashed,line width=.75pt,"
        r"draw=vibeyred,line cap=round},"
        r"vibeydashed/.style={densely dashed,draw=vibeygray,line width=.6pt},"
        r"vibeyedge/.style={draw=vibeysilver,line width=.5pt},"
        r"vibeylink/.style={{Stealth[length=1.8mm,width=1.4mm,round]}-{Stealth[length=1.8mm,width=1.4mm,round]},"
        r"line width=.65pt,draw=vibeygray},"
        r"vibeyanchor/.style={circle,fill=vibeyink,inner sep=1.4pt}}"
    ),
    (
        r"\pgfplotsset{"
        r"vibeyaxis/.style={axis lines=left,axis line style={vibeygray!75,line width=.5pt},"
        r"grid=major,grid style={vibeyline,line width=.3pt},tick style={vibeygray!75,line width=.4pt},"
        r"tick label style={font=\sffamily\tiny,text=vibeygray},label style={font=\sffamily\scriptsize,text=vibeyink},"
        r"title style={font=\sffamily\scriptsize\bfseries,text=vibeyink,at={(0,1.02)},anchor=south west},"
        r"legend style={nodes={font=\sffamily\tiny,inner ysep=1.5pt},draw=none,fill=white,fill opacity=.9,"
        r"text opacity=1,inner xsep=3pt,inner ysep=2pt,row sep=-1.5pt},legend cell align=left,"
        r"every axis plot/.append style={line width=.8pt},clip=false,"
        r"cycle list={{vibeyblue,mark=*},{vibeyteal,mark=square*},{vibeygold,mark=triangle*},"
        r"{vibeyred,mark=diamond*},{vibeyviolet,mark=pentagon*},{vibeygreen,mark=o}}},"
        r"vibeybars/.style={vibeyaxis,ybar,bar width=4pt,draw=none,fill=vibeyblue}}"
    ),
)

#: The plain-words box: every section of the paper can restate itself for a reader who
#: is not a specialist, in a tinted box the eye can find. `\begin{plainwords}` in a
#: ```latex fence; an optional argument retitles it (`[The paper in plain words]`).
PLAIN_WORDS: tuple[str, ...] = (
    r"\usepackage[most]{tcolorbox}",
    (
        r"\newtcolorbox{plainwords}[1][In plain words]{enhanced,breakable,colback=vibeywash,"
        r"colframe=vibeyblue!55,boxrule=.5pt,arc=3pt,left=6pt,right=6pt,top=7pt,bottom=5pt,"
        r"before skip=8pt,after skip=10pt,fontupper=\small\sffamily,"
        r"title={#1},fonttitle=\sffamily\bfseries\footnotesize,coltitle=white,colbacktitle=vibeyblue,"
        r"attach boxed title to top left={yshift=-2.5pt,xshift=8pt},"
        r"boxed title style={size=small,arc=2pt,boxrule=0pt,left=5pt,right=5pt,top=1.5pt,bottom=1.5pt}}"
    ),
)

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
#: The one glyph the family's provenance line carries that a TeX text font does not: the
#: heart becomes a Zapf Dingbats heart in the family's red, so the line survives the PDF.
_HEART_TEX = r"{\color{vibeyred}\ding{170}}"


def _escape(text: str) -> str:
    escaped = _SPECIALS_RE.sub(lambda m: _SPECIALS[m.group(0)], text)
    return escaped.replace(HEART, _HEART_TEX).replace("❤", _HEART_TEX)


_MATH_SPLIT = re.compile(r"(\$\$.*?\$\$|\$[^$\n]+\$)", re.DOTALL)
_FIGURE_REF = re.compile(r"\[([^\]]+?)\]\(#(fig:[A-Za-z0-9:_-]+)\)")
_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"\\textbf{\1}"),
    (re.compile(r"\*(.+?)\*"), r"\\emph{\1}"),
    (re.compile(r"\[(.+?)\]\((.+?)\)"), r"\1\\footnote{\\url{\2}}"),
]
_CODE_SPAN = re.compile(r"`([^`]+)`")


def _breakable(code: str) -> str:
    """A path in a code span may break after its slashes; an identifier never breaks.

    Courier does not hyphenate, so a repository path set in one piece runs into the
    margin of a two-column page. Breaking only after `/` keeps every path segment whole.
    """
    return code.replace("/", "/\\allowbreak ") if "/" in code else code


def _inline(text: str) -> str:
    """Inline markdown to LaTeX, with math spans passed through untouched.

    Order is the correctness here: math is split out FIRST so `$O(n^2)$` is never
    escaped; code spans are lifted second so backticked text is never bolded; figure
    references `[Fig.](#fig:label)` are lifted third and become `\\ref`s; the remaining
    prose is escaped and then styled.
    """
    parts = _MATH_SPLIT.split(text)
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:  # a math span, verbatim
            out.append(part)
            continue
        spans: list[str] = []
        refs: list[tuple[str, str]] = []

        def lift(match: re.Match[str], spans: list[str] = spans) -> str:
            spans.append(match.group(1))
            return f"\x00{len(spans) - 1}\x00"

        def lift_ref(match: re.Match[str], refs: list[tuple[str, str]] = refs) -> str:
            refs.append((match.group(1), match.group(2)))
            return f"\x01{len(refs) - 1}\x01"

        lifted = _FIGURE_REF.sub(lift_ref, _CODE_SPAN.sub(lift, part))
        escaped = _escape(lifted)
        for pattern, repl in _INLINE:
            escaped = pattern.sub(repl, escaped)
        for j, span in enumerate(spans):
            escaped = escaped.replace(f"\x00{j}\x00", rf"\texttt{{{_breakable(_escape(span))}}}")
        for j, (label_text, target) in enumerate(refs):
            # `[Fig. 7](#fig:x)` reads well in Markdown; TeX numbers the figure itself, so
            # the digits are dropped and only the word survives beside the \ref.
            word = re.sub(r"\s*\d+\s*$", "", label_text).strip() or "Fig."
            escaped = escaped.replace(f"\x01{j}\x01", rf"{_escape(word)}~\ref{{{target}}}")
        out.append(escaped)
    return "".join(out)


@dataclass
class _Doc(PaperDocumentInterface):
    title: str = ""
    abstract: list[str] = None  # type: ignore[assignment]
    body: list[str] = None  # type: ignore[assignment]
    bibliography: list[str] = None  # type: ignore[assignment]
    tail: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.abstract = []
        self.body = []
        self.bibliography = []
        self.tail = []


@dataclass(frozen=True)
class Provenance(PaperProvenanceInterface):
    """The article's own statement of origin, computed by the caller and never typed."""

    author: str
    email: str = ""
    affiliation: str = ""
    author_url: str = ""
    site_url: str = ""
    repository_url: str = ""
    revision: str = ""
    committed_at: str = ""
    committed_unix: int = 0
    rendered_at: str = ""
    rendered_unix: int = 0


def provenance_markdown(provenance: PaperProvenanceInterface) -> str:
    """The provenance paragraph in the paper's own Markdown, so every renderer sees it.

    One paragraph, stated once in the source's grammar: the LaTeX path escapes it, the
    DOCX path styles it and the site renders it, and none of them can drift from the
    others because they all read the same sentence.
    """
    parts: list[str] = []
    if provenance.revision:
        where = (
            f"[{provenance.repository_url}]({provenance.repository_url})"
            if provenance.repository_url
            else "the repository"
        )
        committed = ""
        if provenance.committed_at:
            committed = (
                f", committed {provenance.committed_at} (Unix time {provenance.committed_unix})"
            )
        parts.append(f"Revision `{provenance.revision[:12]}` of {where}{committed}.")
    if provenance.rendered_at:
        parts.append(
            f"This document was rendered {provenance.rendered_at} (Unix time {provenance.rendered_unix})."
        )
    who = provenance.author
    if provenance.author_url:
        who = f"[{provenance.author}]({provenance.author_url})"
    if provenance.email:
        who += f" ({provenance.email})"
    site = f"[Vibey]({provenance.site_url})" if provenance.site_url else "Vibey"
    parts.append(f"Made with {HEART} by {site}, developed by {who}.")
    return "*Provenance.* " + " ".join(parts)


class RevisionReader(RevisionReaderInterface):
    """Reads a revision's identity and commit time from the git checkout it renders from.

    The one place the paper pipeline touches git, so the CLI stays a flag parser and a
    test can hand the renderer a fixed revision instead of a repository.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self, revision: str = "HEAD") -> tuple[str, str, int]:
        import subprocess

        try:
            done = subprocess.run(
                ["git", "log", "-1", "--format=%H%x09%ct", revision],
                cwd=self._root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise PaperError(
                f"cannot read revision {revision!r} from git in {self._root}: {error}"
            ) from error
        sha, _, stamp = done.stdout.strip().partition("\t")
        if not sha or not stamp.isdigit():
            raise PaperError(f"git returned no commit for revision {revision!r} in {self._root}")
        committed = datetime.fromtimestamp(int(stamp), UTC)
        return sha, committed.strftime("%Y-%m-%dT%H:%M:%SZ"), int(stamp)


def _expand_provenance(markdown: str, provenance: PaperProvenanceInterface | None) -> str:
    """Replace the provenance marker with its paragraph, or drop it when there is none."""
    if PROVENANCE_MARKER not in markdown:
        return markdown
    replacement = provenance_markdown(provenance) if provenance is not None else ""
    return "\n".join(
        replacement if line.strip() == PROVENANCE_MARKER else line for line in markdown.splitlines()
    ) + ("\n" if markdown.endswith("\n") else "")


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
    tail_start: int | None = None
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
        if line.startswith("<!--"):
            # An HTML comment is the source's own bookkeeping (generated-block markers,
            # the provenance marker before expansion); a journal never prints it.
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
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
            was_refs = in_refs
            in_refs = heading.lower() == "references"
            if was_refs and not in_refs and tail_start is None:
                # A section after the references (a closing call to action, say) is
                # printed after the bibliography, where the source puts it.
                tail_start = len(doc.body)
            if not in_refs:
                doc.body.append(
                    rf"\section*{{{_inline(heading)}}}"
                    if tail_start is not None
                    else rf"\section{{{_inline(heading)}}}"
                )
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
    if tail_start is not None:
        doc.tail = doc.body[tail_start:]
        del doc.body[tail_start:]
    if not doc.title:
        raise PaperError("paper.md needs a `# Title` heading")
    if not doc.abstract:
        raise PaperError("paper.md needs a paragraph opening with **Abstract**")
    return doc


def _author_block(author: str, provenance: PaperProvenanceInterface | None) -> str:
    """The IEEEtran author block: the name, then affiliation, site and email when known."""
    lines = [rf"\IEEEauthorblockN{{{_escape(author)}}}"]
    if provenance is not None:
        affiliation = [
            _escape(item)
            for item in (provenance.affiliation, provenance.site_url, provenance.email)
            if item
        ]
        if affiliation:
            lines.append(r"\IEEEauthorblockA{" + r"\\ ".join(affiliation) + "}")
    return "".join(lines)


def _url_macros(provenance: PaperProvenanceInterface | None) -> list[str]:
    """`\\urldef` lines for the addresses the first-page note cites.

    `\\url` cannot appear in a moving argument such as `\\thanks`, and an address set in
    teletype never breaks, so each address becomes a macro defined verbatim in the
    preamble and the note cites the macro.
    """
    if provenance is None:
        return []
    return [
        f"\\urldef{{\\vibey{name}url}}\\url{{{value}}}"
        for name, value in (
            ("repository", provenance.repository_url),
            ("site", provenance.site_url),
            ("author", provenance.author_url),
        )
        if value
    ]


def _thanks(provenance: PaperProvenanceInterface | None) -> str:
    """The first-page note a journal prints under the title: dates, revision, provenance."""
    if provenance is None:
        return ""
    sentences: list[str] = []
    origin: list[str] = []
    if provenance.rendered_at:
        origin.append(
            f"Manuscript rendered {provenance.rendered_at} (Unix time {provenance.rendered_unix})"
        )
    if provenance.revision:
        source = f"from revision {provenance.revision[:12]}"
        if provenance.repository_url:
            source += " of \\vibeyrepositoryurl{}"
        if provenance.committed_at:
            source += (
                f", committed {provenance.committed_at} (Unix time {provenance.committed_unix})"
            )
        origin.append(source if origin else source[0].upper() + source[1:])
    if origin:
        sentences.append(" ".join(origin))
    site = "\\vibeysiteurl{}" if provenance.site_url else "Vibey"
    who = _escape(provenance.author)
    if provenance.author_url:
        who += ", \\vibeyauthorurl{}"
    sentences.append(f"Made with {_HEART_TEX} by Vibey, {site}, developed by {who}")
    return r"\thanks{" + ". ".join(sentences) + ".}"


def render_paper(
    markdown: str,
    author: str,
    journal: bool = False,
    keywords: str = "",
    *,
    provenance: PaperProvenanceInterface | None = None,
) -> str:
    """The full IEEEtran document for docs/paper.md."""
    doc = convert(_expand_provenance(markdown, provenance))
    mode = "journal" if journal else "conference"
    parts = [
        rf"\documentclass[{mode}]{{IEEEtran}}",
        # Conference mode locks \thanks out; the first-page provenance note needs it.
        r"\IEEEoverridecommandlockouts",
        *PREAMBLE,
        r"\newtheorem{theorem}{Theorem}",
        r"\newtheorem{invariant}{Invariant}",
        r"\newtheorem{lemma}{Lemma}",
        *PLAIN_WORDS,
        *_url_macros(provenance),
        r"\begin{document}",
        rf"\title{{{doc.title}{_thanks(provenance)}}}",
        rf"\author{{{_author_block(author, provenance)}}}",
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
    parts += doc.tail
    parts.append(r"\end{document}")
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------------- the visual atlas

_FENCE = re.compile(r"^```latex\n(.*?)^```\n?", re.DOTALL | re.MULTILINE)
_FIGURE_ENV = re.compile(r"\\begin\{(figure\*?)\}(?:\[[^\]]*\])?(.*)\\end\{\1\}", re.DOTALL)
_PICTURE = re.compile(r"(\\begin\{tikzpicture\}.*\\end\{tikzpicture\})", re.DOTALL)
_LABEL = re.compile(r"\\label\{([^}]+)\}")


@dataclass(frozen=True)
class Figure(PaperFigureInterface):
    """One figure of the paper, read out of its ```latex fence."""

    label: str
    environment: str
    caption: str
    picture: str
    fence: str


def _caption_of(body: str) -> str:
    """The braces-balanced argument of `\\caption{...}`, or the empty string."""
    start = body.find(r"\caption{")
    if start < 0:
        return ""
    depth, i = 0, start + len(r"\caption")
    for j in range(i, len(body)):
        if body[j] == "{":
            depth += 1
        elif body[j] == "}":
            depth -= 1
            if depth == 0:
                return " ".join(body[i + 1 : j].split())
    return ""


def figures(markdown: str) -> list[Figure]:
    """Every ```latex fence that is a figure environment, in the order the paper shows it."""
    found: list[Figure] = []
    for fence in _FENCE.finditer(markdown):
        env = _FIGURE_ENV.search(fence.group(1))
        if env is None:
            continue
        picture = _PICTURE.search(env.group(2))
        label = _LABEL.search(env.group(2))
        if picture is None or label is None:
            raise PaperError(
                "a figure fence needs a tikzpicture and a \\label: "
                + fence.group(1).strip().splitlines()[0]
            )
        found.append(
            Figure(
                label=label.group(1),
                environment=env.group(1),
                caption=_caption_of(env.group(2)),
                picture=picture.group(1),
                fence=fence.group(0),
            )
        )
    return found


def figure_document(figure: PaperFigureInterface) -> str:
    """A standalone LaTeX document rendering one figure at the size the paper prints it.

    The class is `standalone` at the paper's 10pt, so `\\scriptsize` and `\\tiny` are the
    sizes the two-column page uses, and the page is cropped to the picture.
    """
    return "\n".join(
        [
            r"\documentclass[10pt,border=3pt]{standalone}",
            *PREAMBLE,
            r"\begin{document}",
            figure.picture,
            r"\end{document}",
            "",
        ]
    )


_CAPTION_TEX = [
    (re.compile(r"\\texttt\{([^{}]*)\}"), r"<code>\1</code>"),
    (re.compile(r"\\emph\{([^{}]*)\}"), r"<em>\1</em>"),
    (re.compile(r"\\textbf\{([^{}]*)\}"), r"<strong>\1</strong>"),
    (re.compile(r"\\%"), "%"),
    (re.compile(r"\\&"), "&amp;"),
    (re.compile(r"\\#"), "#"),
    (re.compile(r"\\_"), "_"),
    (re.compile(r"\\,"), "\u2009"),
    (re.compile(r"---"), "\u2014"),
    (re.compile(r"--"), "\u2013"),
    (re.compile(r"~"), "\u00a0"),
]


def _caption_html(caption: str) -> str:
    """A figure caption's TeX rendered as HTML, with its math left for MathJax."""
    parts = _MATH_SPLIT.split(caption)
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(f'<span class="arithmatex">\\({html.escape(part.strip("$"))}\\)</span>')
            continue
        text = html.escape(part, quote=False)
        for pattern, repl in _CAPTION_TEX:
            text = pattern.sub(repl, text)
        out.append(text)
    return "".join(out)


def inline_figures(markdown: str, svg: Mapping[str, str]) -> str:
    """The paper's Markdown with each rendered figure inlined for the site and the book.

    `svg` maps a figure label to the SVG document rendered from `figure_document()`. A
    figure with no rendering keeps its fence, so the page still carries the source rather
    than a broken image; a figure with one becomes an HTML `<figure>` holding the SVG
    inline — an image the EPUB and the print interior carry without a second file — and
    its caption, numbered in the order the PDF numbers it.
    """
    number = 0
    result = markdown
    numbers: dict[str, int] = {}
    for figure in figures(markdown):
        number += 1
        numbers[figure.label] = number
        document = svg.get(figure.label)
        if document is None:
            continue
        body = re.sub(r"^<\?xml[^>]*\?>\s*", "", document.strip())
        body = re.sub(r"^<!DOCTYPE[^>]*>\s*", "", body)
        wide = (
            "paper-figure paper-figure-wide" if figure.environment == "figure*" else "paper-figure"
        )
        block = (
            f'<figure class="{wide}" id="{html.escape(figure.label, quote=True)}">\n'
            f"{body}\n"
            f"<figcaption><strong>Figure {number}.</strong> {_caption_html(figure.caption)}</figcaption>\n"
            "</figure>\n"
        )
        result = result.replace(figure.fence, block, 1)
    # A reference's number follows the figure's place in this document, never the digits
    # the source happened to carry.
    return _FIGURE_REF.sub(
        lambda m: (
            f"[Fig. {numbers[m.group(2)]}](#{m.group(2)})" if m.group(2) in numbers else m.group(0)
        ),
        result,
    )


# ------------------------------------------------------------------- the editable form

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
            if href.startswith("#fig:"):
                runs.append({"text": label, **({"italic": True} if italic else {})})
            else:
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
    figure = _FIGURE_ENV.search(text)
    if figure is not None:
        # A drawing has no editable form; the caption is what the reader can act on.
        text = "Figure. " + _caption_of(figure.group(2))
    plain = re.match(
        r"\s*\\begin\{plainwords\}(?:\[([^\]]*)\])?(.*)\\end\{plainwords\}\s*$", text, re.DOTALL
    )
    if plain is not None:
        text = f"{plain.group(1) or 'In plain words'}. {plain.group(2).strip()}"
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
        if line.startswith("<!--"):
            flush_paragraph()
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
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
    provenance: PaperProvenanceInterface | None = None,
) -> bytes:
    """Return a Word version of the paper using the same Markdown source as the PDF."""
    del journal, keywords  # The editable form is deliberately single-column and prose-first.
    markdown = _expand_provenance(markdown, provenance)
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
    provenance: PaperProvenanceInterface | None = None,
) -> None:
    """Write the paper's DOCX form through an injectable writer."""
    del journal, keywords
    markdown = _expand_provenance(markdown, provenance)
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
