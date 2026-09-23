# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The research-paper pipeline (#185): MD -> journal-class LaTeX.

The contract is a real publisher's: IEEEtran class, math passed through untouched so
the source can be as LaTeX-liberal as the doctrine demands, prose escaped so a stray
underscore never breaks a build three steps downstream, and actionable refusals when
the paper lacks the parts a journal requires.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibey_gh import paper
from vibey_gh.interfaces.paper_interface import PaperDocumentInterface, PaperErrorInterface

MD = """# A Sound System

**Abstract.** We prove $T(n) = O(n)$ with 100% coverage & no _fuss_.

## Model

Inline $a < A$ math, **bold**, *emphasis*, `code_span`, and a [link](https://x.example).

$$E = mc^2$$

- first item
- second item

### Detail

| col_a | col_b |
|---|---|
| 1 | $x^2$ |

```latex
\\begin{theorem}Raw LaTeX passes.\\end{theorem}
```

```python
print("verbatim")
```

## References

- A. Author, *Work*, 2026.
- B. Writer, *Other*, 2025.
"""


def test_the_document_is_ieeetran_shaped():
    tex = paper.render_paper(MD, author="A. Person", keywords="k1; k2")
    assert tex.startswith(r"\documentclass[conference]{IEEEtran}")
    assert r"\usepackage{amsmath,amssymb,amsthm}" in tex
    assert r"\usepackage{tikz}" in tex
    # The visual design system: TikZ with its drawing libraries, pgfplots for data, and
    # the palette and styles every figure shares, emitted once for the whole document.
    assert r"\usetikzlibrary{arrows.meta,backgrounds,calc,fit,positioning,shapes.geometric," in tex
    assert r"\usepackage{pgfplots}" in tex and r"\pgfplotsset{compat=1.18}" in tex
    assert r"\definecolor{vibeyink}{HTML}{17324D}" in tex
    assert "vibeybox/.style=" in tex and "vibeyaxis/.style=" in tex
    assert r"\title{A Sound System}" in tex
    assert r"\IEEEauthorblockN{A. Person}" in tex
    assert r"\begin{abstract}" in tex
    assert r"\begin{IEEEkeywords}" in tex and "k1; k2" in tex
    assert tex.rstrip().endswith(r"\end{document}")


def test_journal_mode_switches_the_class_option():
    tex = paper.render_paper(MD, author="A", journal=True)
    assert tex.startswith(r"\documentclass[journal]{IEEEtran}")


def test_math_passes_through_untouched():
    """The LaTeX-liberal channel: $...$ and $$...$$ reach the .tex byte-for-byte."""
    tex = paper.render_paper(MD, author="A")
    assert "$T(n) = O(n)$" in tex
    assert "$a < A$" in tex
    assert "$$E = mc^2$$" in tex
    assert "$x^2$" in tex


def test_prose_is_escaped_but_styled():
    tex = paper.render_paper(MD, author="A")
    assert r"coverage \& no \_fuss\_" in tex
    assert r"\textbf{bold}" in tex and r"\emph{emphasis}" in tex
    assert r"\texttt{code\_span}" in tex
    assert r"\footnote{\url{https://x.example}}" in tex


def test_structures_render_as_their_latex_counterparts():
    tex = paper.render_paper(MD, author="A")
    assert r"\section{Model}" in tex and r"\subsection{Detail}" in tex
    assert r"\begin{itemize}" in tex and r"\item first item" in tex
    assert r"\begin{tabular}{ll}" in tex and r"col\_a & col\_b" in tex
    assert r"\begin{theorem}Raw LaTeX passes.\end{theorem}" in tex
    assert r"\begin{verbatim}" in tex and 'print("verbatim")' in tex


def test_references_become_thebibliography():
    tex = paper.render_paper(MD, author="A")
    assert r"\begin{thebibliography}{2}" in tex
    assert r"\bibitem{ref1}" in tex and r"\bibitem{ref2}" in tex
    assert r"\section{References}" not in tex


@pytest.mark.parametrize(
    ("source", "missing"),
    [("no title\n\n**Abstract.** a\n", "Title"), ("# T\n\nbody only\n", "Abstract")],
)
def test_a_paper_missing_journal_essentials_is_refused(source, missing):
    with pytest.raises(paper.PaperError, match=missing):
        paper.render_paper(source, author="A")


def test_paper_document_and_error_have_declared_interfaces():
    assert isinstance(paper.convert(MD), PaperDocumentInterface)
    assert isinstance(paper.PaperError("x"), PaperErrorInterface)


def test_the_cli_writes_the_tex_and_reports_it(tmp_path, capsys):
    from vibey_gh import cli

    src = tmp_path / "paper.md"
    src.write_text(MD)
    out = tmp_path / "out" / "paper.tex"
    code = cli.main(["paper", "--source", str(src), "--output", str(out), "--author", "A. Person"])
    assert code == 0
    assert "paper.tex" in capsys.readouterr().out
    assert out.read_text().startswith(r"\documentclass")


def test_the_cli_refuses_a_missing_source_actionably(tmp_path, capsys):
    from vibey_gh import cli

    code = cli.main(
        [
            "paper",
            "--source",
            str(tmp_path / "nope.md"),
            "--output",
            str(tmp_path / "o.tex"),
            "--author",
            "A",
        ]
    )
    assert code == 1
    assert "vibey-gh paper:" in capsys.readouterr().err


def test_multiline_display_math_and_abstract_are_consumed_exactly():
    md = (
        "# T\n\n**Abstract.** First line\ncontinues here.\n\n"
        "$$\n\\sum_{i=0}^{n} i\n$$\n\nAfter math.\n"
    )
    tex = paper.render_paper(md, author="A")
    assert "\\sum_{i=0}^{n} i" in tex
    assert "First line continues here." in tex
    assert "After math." in tex


def test_two_lists_open_and_close_independently():
    md = "# T\n\n**Abstract.** A.\n\n- a\n- b\n\nprose\n\n- c\n"
    tex = paper.render_paper(md, author="A")
    assert tex.count(r"\begin{itemize}") == 2
    assert tex.count(r"\end{itemize}") == 2


def test_a_paper_without_references_gets_no_bibliography():
    md = "# T\n\n**Abstract.** A.\n\nBody.\n"
    tex = paper.render_paper(md, author="A")
    assert r"\begin{thebibliography}" not in tex


def test_an_unterminated_display_block_ends_at_the_file_not_in_a_loop():
    md = "# T\n\n**Abstract.** A.\n\n$$\n\\alpha + \\beta\n"
    tex = paper.render_paper(md, author="A")
    assert "\\alpha + \\beta" in tex


def test_the_paper_can_be_exported_as_an_editable_docx():
    import io
    import zipfile

    document = paper.render_docx(MD, author="A. Person")
    with zipfile.ZipFile(io.BytesIO(document)) as archive:
        xml = archive.read("word/document.xml").decode()
        relationships = archive.read("word/_rels/document.xml.rels").decode()
    assert "A Sound System" in xml
    assert "Abstract" in xml and "code_span" in xml
    assert "E = mc" in xml and "col_a" in xml
    assert "https://x.example" in relationships
    assert 'w:type="page"' not in xml


def test_docx_paper_handles_multiline_math_and_injected_writers(tmp_path):
    import io
    import zipfile

    markdown = "# T\n\n**Abstract.** First line\ncontinues here.\n\n$$\n\\alpha + \\beta\n$$\n"
    document = paper.render_docx(markdown, author="A")
    with zipfile.ZipFile(io.BytesIO(document)) as archive:
        xml = archive.read("word/document.xml")
    assert b"alpha" in xml and b"beta" in xml

    class Writer:
        def build(self, **kwargs):
            assert kwargs["title"] == "T"
            return b"injected"

        def write(self, path, **kwargs):
            assert kwargs["title"] == "T"
            path.write_bytes(b"injected")

    assert paper.render_docx(markdown, author="A", writer=Writer()) == b"injected"
    output = tmp_path / "paper.docx"
    paper.write_docx(markdown, output, author="A", writer=Writer())
    assert output.read_bytes() == b"injected"
    assert any(run.get("href") for run in paper._docx_runs("[link](https://example.test)"))
    unterminated = paper.render_docx("# T\n\n**Abstract.** A.\n\n$$\n\\alpha\n", author="A")
    assert b"alpha" in zipfile.ZipFile(io.BytesIO(unterminated)).read("word/document.xml")


def test_docx_paper_requires_a_title_for_both_facades(tmp_path, monkeypatch):
    monkeypatch.setattr(paper, "convert", lambda markdown: None)
    source = "**Abstract.** A.\n"
    with pytest.raises(paper.PaperError, match="Title"):
        paper.render_docx(source, author="A")
    with pytest.raises(paper.PaperError, match="Title"):
        paper.write_docx(source, tmp_path / "paper.docx", author="A")


def test_the_paper_cli_infers_and_accepts_the_docx_format(tmp_path, capsys):
    from vibey_gh import cli

    source = tmp_path / "paper.md"
    source.write_text(MD)
    inferred = tmp_path / "inferred.docx"
    assert (
        cli.main(["paper", "--source", str(source), "--output", str(inferred), "--author", "A"])
        == 0
    )
    assert inferred.is_file()
    assert "docx:" in capsys.readouterr().out

    explicit = tmp_path / "explicit.out"
    assert (
        cli.main(
            [
                "paper",
                "--source",
                str(source),
                "--output",
                str(explicit),
                "--format",
                "docx",
                "--author",
                "A",
            ]
        )
        == 0
    )
    assert explicit.is_file()


# ---------------------------------------------------------------- provenance

PROVENANCE = paper.Provenance(
    author="A. Person",
    email="a@example.test",
    affiliation="The Example Project",
    author_url="https://a.example",
    site_url="https://docs.example/main/",
    repository_url="https://forge.example/o/r",
    revision="0123456789abcdef0123456789abcdef01234567",
    committed_at="2026-09-23T13:28:00Z",
    committed_unix=1790170080,
    rendered_at="2026-09-23T14:24:59Z",
    rendered_unix=1790173499,
)

MD_WITH_MARKER = MD.replace("## Model", "<!-- vibey:provenance -->\n\n## Model")


def test_provenance_reaches_the_byline_the_first_page_note_and_the_marker():
    """A submitted article says who wrote it, from what revision, and when. Never typed:
    the paragraph is generated from one value the caller computed, and it appears in the
    IEEEtran author block, in the first-page \\thanks note and where the source marks it."""
    tex = paper.render_paper(MD_WITH_MARKER, author="A. Person", provenance=PROVENANCE)
    assert (
        r"\IEEEauthorblockA{The Example Project\\ https://docs.example/main/\\ a@example.test}"
        in tex
    )
    assert (
        r"\thanks{Manuscript rendered 2026-09-23T14:24:59Z (Unix time 1790173499) from revision 0123456789ab"
        in tex
    )
    assert r"committed 2026-09-23T13:28:00Z (Unix time 1790170080)" in tex
    # The family's own provenance line, heart included: the glyph is a Dingbats heart in
    # the family's red, because a TeX text font has no emoji.
    assert (
        r"Made with {\color{vibeyred}\ding{170}} by Vibey, \vibeysiteurl{}, developed by A. Person, \vibeyauthorurl{}."
        in tex
    )
    assert r"\urldef{\vibeysiteurl}\url{https://docs.example/main/}" in tex
    assert r"\urldef{\vibeyrepositoryurl}\url{https://forge.example/o/r}" in tex
    assert r"from revision 0123456789ab of \vibeyrepositoryurl{}, committed" in tex
    assert r"\emph{Provenance.} Revision \texttt{0123456789ab}" in tex
    assert "<!-- vibey:provenance -->" not in tex
    assert tex.count("Unix time 1790173499") == 2  # the note and the paragraph


def test_without_provenance_the_marker_and_every_html_comment_vanish():
    tex = paper.render_paper(
        MD_WITH_MARKER + "\n<!-- BEGIN GENERATED x -->\nkept\n<!-- END GENERATED x -->\n",
        author="A",
    )
    assert "<!--" not in tex and "vibey:provenance" not in tex and "kept" in tex
    assert r"\thanks" not in tex and r"\IEEEauthorblockA" not in tex


def test_provenance_markdown_omits_what_it_does_not_know():
    bare = paper.provenance_markdown(paper.Provenance(author="A"))
    assert bare == "*Provenance.* Made with ❤️ by Vibey, developed by A."
    partial = paper.provenance_markdown(paper.Provenance(author="A", revision="abcdef123456789"))
    assert "Revision `abcdef123456` of the repository." in partial and "rendered" not in partial


def test_provenance_flows_into_the_docx_form(tmp_path):
    import io
    import zipfile

    document = paper.render_docx(MD_WITH_MARKER, author="A. Person", provenance=PROVENANCE)
    xml = zipfile.ZipFile(io.BytesIO(document)).read("word/document.xml").decode()
    assert "Unix time 1790173499" in xml and "a@example.test" in xml
    output = tmp_path / "p.docx"
    paper.write_docx(MD_WITH_MARKER, output, author="A", provenance=PROVENANCE)
    assert b"1790170080" in zipfile.ZipFile(output).read("word/document.xml")


@pytest.fixture
def repo(tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, value in (
        ("user.email", "t@example.test"),
        ("user.name", "T"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(["git", "-C", str(tmp_path), "config", key, value], check=True)
    return tmp_path


def test_the_revision_reader_reads_git_and_refuses_actionably(repo):
    import subprocess

    subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-q", "-m", "x"], check=True)
    sha, committed_at, committed_unix = paper.RevisionReader(repo).read("HEAD")
    assert len(sha) == 40 and committed_at.endswith("Z") and committed_unix > 0
    with pytest.raises(paper.PaperError, match="cannot read revision"):
        paper.RevisionReader(repo).read("no-such-revision")
    with pytest.raises(paper.PaperError, match="cannot read revision"):
        paper.RevisionReader(repo / "missing").read()


def test_the_revision_reader_refuses_an_empty_answer(repo, monkeypatch):
    import subprocess

    class Done:
        stdout = "\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Done())
    with pytest.raises(paper.PaperError, match="no commit"):
        paper.RevisionReader(repo).read()


def test_the_cli_states_provenance_from_the_revision_reader(tmp_path, capsys, monkeypatch):
    from vibey_gh import cli

    class Reader:
        def __init__(self, root):
            assert root == Path.cwd()

        def read(self, revision="HEAD"):
            assert revision == "feedface"
            return "feedface" * 5, "2026-09-23T13:28:00Z", 1790170080

    original = paper.RevisionReader
    monkeypatch.setattr(paper, "RevisionReader", Reader)
    src = tmp_path / "paper.md"
    src.write_text(MD_WITH_MARKER)
    out = tmp_path / "paper.tex"
    code = cli.main(
        [
            "paper",
            "--source",
            str(src),
            "--output",
            str(out),
            "--author",
            "A. Person",
            "--provenance",
            "--revision",
            "feedface",
            "--email",
            "a@example.test",
            "--affiliation",
            "Example",
            "--author-url",
            "https://a.example",
            "--site",
            "https://docs.example/",
            "--repository",
            "https://forge.example/o/r",
        ]
    )
    assert code == 0
    tex = out.read_text()
    assert "feedfacefeed" in tex and "1790170080" in tex and "Unix time" in tex
    assert r"\IEEEauthorblockA{Example\\ https://docs.example/\\ a@example.test}" in tex
    assert "Manuscript rendered 20" in tex and r"\IEEEoverridecommandlockouts" in tex
    # The editable form states the same provenance from the same flags.
    docx = tmp_path / "paper.docx"
    assert (
        cli.main(
            [
                "paper",
                "--source",
                str(src),
                "--output",
                str(docx),
                "--author",
                "A",
                "--provenance",
                "--revision",
                "feedface",
            ]
        )
        == 0
    )
    import zipfile

    assert b"feedfacefeed" in zipfile.ZipFile(docx).read("word/document.xml")
    # Without --provenance nothing is stated, whatever else was passed.
    assert (
        cli.main(
            ["paper", "--source", str(src), "--output", str(out), "--author", "A", "--email", "x@y"]
        )
        == 0
    )
    assert r"\thanks" not in out.read_text()
    # A revision git cannot read is an actionable refusal, not a traceback.
    monkeypatch.setattr(paper, "RevisionReader", original)
    assert (
        cli.main(
            [
                "paper",
                "--source",
                str(src),
                "--output",
                str(out),
                "--author",
                "A",
                "--provenance",
                "--revision",
                "no-such-revision",
            ]
        )
        == 1
    )
    assert "vibey-gh paper:" in capsys.readouterr().err


# ---------------------------------------------------------------- the visual atlas

FIGURE_TAIL = """
```latex
\\begin{figure*}[t]
\\centering
\\begin{tikzpicture}
\\node[vibeybox] (a) {a};
\\end{tikzpicture}
\\caption{The first figure, with $x^2$ and \\texttt{code}, 100\\% shown---twice.}
\\label{fig:first}
\\end{figure*}
```

Prose that cites [Fig.](#fig:first) inline.

```latex
\\begin{figure}[t]
\\centering
\\begin{tikzpicture}
\\node {b};
\\end{tikzpicture}
\\caption{Second.}
\\label{fig:second}
\\end{figure}
```

```latex
\\begin{theorem}Not a figure.\\end{theorem}
```
"""
FIGURE_MD = MD + FIGURE_TAIL


def test_figures_are_read_out_of_their_fences_in_order():
    found = paper.figures(FIGURE_MD)
    assert [f.label for f in found] == ["fig:first", "fig:second"]
    assert found[0].environment == "figure*" and found[1].environment == "figure"
    assert (
        found[0].caption == "The first figure, with $x^2$ and \\texttt{code}, 100\\% shown---twice."
    )
    assert found[0].picture.startswith("\\begin{tikzpicture}") and found[0].picture.endswith(
        "\\end{tikzpicture}"
    )
    assert found[0].fence.startswith("```latex\n")


def test_a_figure_without_a_label_or_picture_is_refused():
    with pytest.raises(paper.PaperError, match="needs a tikzpicture"):
        paper.figures("```latex\n\\begin{figure}\n\\caption{x}\n\\end{figure}\n```\n")


def test_a_figure_document_stands_alone_with_the_design_system():
    figure = paper.figures(FIGURE_MD)[0]
    tex = paper.figure_document(figure)
    assert tex.startswith("\\documentclass[10pt,border=3pt]{standalone}\n")
    assert r"\definecolor{vibeyink}{HTML}{17324D}" in tex
    assert "\\begin{document}\n\\begin{tikzpicture}" in tex and tex.rstrip().endswith(
        "\\end{document}"
    )


def test_figure_references_become_refs_in_tex_and_plain_text_in_docx():
    tex = paper.render_paper(FIGURE_MD, author="A")
    assert r"Fig.~\ref{fig:first}" in tex
    assert r"\footnote{\url{#fig:first}}" not in tex
    runs = paper._docx_runs("see [Fig.](#fig:first) here")
    assert any(run.get("text") == "Fig." and "href" not in run for run in runs)


def test_inline_figures_embeds_the_svg_numbered_as_the_pdf_numbers_it():
    svg = '<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect/></svg>'
    result = paper.inline_figures(FIGURE_MD, {"fig:second": svg})
    # The first figure has no rendering and keeps its fence; the second is embedded as
    # Figure 2, because numbering follows the PDF, not the renderings available.
    assert "\\label{fig:first}" in result
    assert '<figure class="paper-figure" id="fig:second">' in result
    assert (
        "<?xml" not in result
        and '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><rect/></svg>' in result
    )
    assert "<figcaption><strong>Figure 2.</strong> Second.</figcaption>" in result
    assert "\\label{fig:second}" not in result
    wide = paper.inline_figures(FIGURE_MD, {"fig:first": svg})
    assert 'class="paper-figure paper-figure-wide" id="fig:first"' in wide
    caption = wide.split("<figcaption>")[1].split("</figcaption>")[0]
    assert '<span class="arithmatex">\\(x^2\\)</span>' in caption
    assert "<code>code</code>" in caption and "100% shown\u2014twice" in caption


def test_the_docx_form_keeps_only_a_figure_caption():
    text = paper._docx_latex_block(paper.figures(FIGURE_MD)[1].fence.splitlines()[1:-1])
    assert text == "Figure. Second."


def test_the_paper_figures_cli_emits_and_inlines(tmp_path, capsys):
    from vibey_gh import cli

    src = tmp_path / "paper.md"
    src.write_text(FIGURE_MD)
    emitted = tmp_path / "tex"
    assert cli.main(["paper-figures", "--source", str(src), "--emit", str(emitted)]) == 0
    assert (emitted / "fig-first.tex").is_file() and (emitted / "fig-second.tex").is_file()
    manifest = (emitted / "manifest.json").read_text()
    assert '"label": "fig:first"' in manifest and '"file": "fig-second.tex"' in manifest
    assert "2 emitted" in capsys.readouterr().out
    svgs = tmp_path / "svg"
    svgs.mkdir()
    (svgs / "fig-second.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    out = tmp_path / "inlined.md"
    assert (
        cli.main(
            ["paper-figures", "--source", str(src), "--inline", str(svgs), "--output", str(out)]
        )
        == 0
    )
    printed = capsys.readouterr().out
    assert "1 of 2 inlined" in printed and "kept as source: fig:first" in printed
    assert '<figure class="paper-figure" id="fig:second">' in out.read_text()
    # Inlining in place is the default output, and a missing source is refused actionably.
    assert cli.main(["paper-figures", "--source", str(src), "--inline", str(svgs)]) == 0
    assert "<figure" in src.read_text()
    assert (
        cli.main(["paper-figures", "--source", str(tmp_path / "nope.md"), "--emit", str(emitted)])
        == 1
    )
    assert "vibey-gh paper-figures:" in capsys.readouterr().err


# ---------------------------------------------------------------- the tail, the boxes, the numbers

CLOSING_TAIL = """
## A call to everyone

Join us at [the door](https://join.example).

```latex
\\begin{plainwords}[The paper in plain words]
A notebook nobody can erase.
\\end{plainwords}
```
"""
TAIL_MD = MD + CLOSING_TAIL


def test_sections_after_the_references_print_after_the_bibliography():
    tex = paper.render_paper(TAIL_MD, author="A")
    assert tex.index(r"\end{thebibliography}") < tex.index(r"\section*{A call to everyone}")
    assert tex.index(r"\section*{A call to everyone}") < tex.index(
        r"\begin{plainwords}[The paper in plain words]"
    )
    assert tex.rstrip().endswith(r"\end{document}")
    # The box is defined once, in the document preamble, not in the figures' preamble.
    assert r"\usepackage[most]{tcolorbox}" in tex and r"\newtcolorbox{plainwords}" in tex
    assert not any("tcolorbox" in line for line in paper.PREAMBLE)
    doc = paper.convert(TAIL_MD)
    assert doc.tail and doc.tail[0] == r"\section*{A call to everyone}"
    assert not any("call to everyone" in line for line in doc.body)


def test_a_plain_words_box_becomes_a_titled_paragraph_in_the_docx_form():
    lines = [
        "\\begin{plainwords}[The paper in plain words]",
        "A notebook nobody can erase.",
        "\\end{plainwords}",
    ]
    assert (
        paper._docx_latex_block(lines) == "The paper in plain words. A notebook nobody can erase."
    )
    assert (
        paper._docx_latex_block(["\\begin{plainwords}", "Short.", "\\end{plainwords}"])
        == "In plain words. Short."
    )


def test_figure_reference_digits_are_dropped_for_tex_and_recomputed_for_the_site():
    numbered = FIGURE_MD.replace("[Fig.](#fig:first)", "[Fig. 9](#fig:first)")
    tex = paper.render_paper(numbered, author="A")
    assert r"Fig.~\ref{fig:first}" in tex and "9~" not in tex
    assert r"Figure~\ref{fig:first}" in paper.render_paper(
        numbered.replace("[Fig. 9]", "[Figure 9]"), author="A"
    )
    site = paper.inline_figures(numbered, {})
    assert "[Fig. 1](#fig:first)" in site and "[Fig. 9]" not in site
    # A reference to a label the paper does not define is left alone, and a bare word
    # that is only digits falls back to the ordinary reference word.
    assert "[Fig. 3](#fig:absent)" in paper.inline_figures(
        numbered + "\nSee [Fig. 3](#fig:absent).\n", {}
    )
    assert r"Fig.~\ref{fig:first}" in paper.render_paper(
        FIGURE_MD.replace("[Fig.](#fig:first)", "[7](#fig:first)"), author="A"
    )


def test_multiline_html_comments_are_bookkeeping_in_every_form():
    md = MD + "\n<!-- a note\nthat spans\nlines -->\n\nAfter.\n"
    tex = paper.render_paper(md, author="A")
    assert "spans" not in tex and "After." in tex
    import io
    import zipfile

    xml = (
        zipfile.ZipFile(io.BytesIO(paper.render_docx(md, author="A")))
        .read("word/document.xml")
        .decode()
    )
    assert "spans" not in xml and "After." in xml


def test_a_caption_is_read_whole_or_not_at_all():
    assert paper._caption_of("no caption here") == ""
    assert paper._caption_of(r"\caption{nested {braces} kept}") == "nested {braces} kept"
    assert paper._caption_of(r"\caption{never closed") == ""


def test_the_byline_and_note_state_only_what_they_know():
    bare = paper.Provenance(author="A. Person")
    tex = paper.render_paper(MD, author="A. Person", provenance=bare)
    assert r"\IEEEauthorblockA" not in tex
    assert (
        r"\thanks{Made with {\color{vibeyred}\ding{170}} by Vibey, Vibey, developed by A. Person.}"
        in tex
    )
    # A revision without a render time opens the sentence itself.
    rev_only = paper.Provenance(author="A", revision="abcdef0123456789")
    assert r"\thanks{From revision abcdef012345. Made with" in paper.render_paper(
        MD, author="A", provenance=rev_only
    )
    dated = paper.Provenance(
        author="A",
        revision="abcdef0123456789",
        committed_at="2026-01-01T00:00:00Z",
        committed_unix=1,
    )
    assert (
        "From revision abcdef012345, committed 2026-01-01T00:00:00Z (Unix time 1)."
        in paper.render_paper(MD, author="A", provenance=dated)
    )
    rendered_only = paper.Provenance(
        author="A", rendered_at="2026-01-02T00:00:00Z", rendered_unix=2
    )
    assert (
        r"\thanks{Manuscript rendered 2026-01-02T00:00:00Z (Unix time 2). Made with"
        in paper.render_paper(MD, author="A", provenance=rendered_only)
    )


def test_the_figures_cli_reports_a_full_inlining(tmp_path, capsys):
    from vibey_gh import cli

    src = tmp_path / "paper.md"
    src.write_text(FIGURE_MD)
    svgs = tmp_path / "svg"
    svgs.mkdir()
    for stem in ("fig-first", "fig-second"):
        (svgs / f"{stem}.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    out = tmp_path / "inlined.md"
    assert (
        cli.main(
            ["paper-figures", "--source", str(src), "--inline", str(svgs), "--output", str(out)]
        )
        == 0
    )
    printed = capsys.readouterr().out
    assert "2 of 2 inlined" in printed and "kept as source" not in printed
