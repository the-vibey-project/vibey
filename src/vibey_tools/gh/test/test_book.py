# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Exporting the built docs site as a book (#137, #162).

The contract under test is KDP's, not ours: an EPUB whose `mimetype` entry is first and
stored, a 3.0 package with Dublin Core metadata, chapters spined in nav order, and a
print HTML carrying the exact 6in x 9in trim — because "almost a valid EPUB" is a
rejection email three days after upload. And, since #162, a reader's: an interior with
the gutter on the binding side, folios, running heads and justified text, and a contents
that keeps the nav's own grouping.
"""

from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from vibey_gh import book
from vibey_gh.chapter_sanitizer import ChapterSanitizer
from vibey_gh.interfaces.book_interface import (
    BookChapterInterface,
    EpubPackageInterface,
    NavReaderInterface,
    PrintInteriorInterface,
    TableOfContentsInterface,
)

NAV = """site_name: demo
nav:
  - Home: index.md
  - Start here:
      - Welcome: start/index.md
  - Reference: reference.md
strict: true
"""

PAGE = "<html><body><nav>skip</nav><main><h1>T</h1><p>body<br></p><script>x()</script></main></body></html>"


def _site(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    for page in ("index.html", "start/index.html", "reference/index.html"):
        target = site / page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(PAGE)
    return site


def test_chapters_come_from_the_nav_in_order():
    chapters = book.chapters_from_nav(NAV)
    assert [c.source for c in chapters] == ["index.md", "start/index.md", "reference.md"]
    assert [c.title for c in chapters] == ["Home", "Welcome", "Reference"]
    # Nesting is recorded, order is never rearranged: the nav order IS the doctrine
    # order, and the book must inherit it untouched.
    assert [c.depth for c in chapters] == [0, 1, 0]


def test_a_navless_configuration_is_an_error_not_an_empty_book():
    with pytest.raises(book.BookError, match="no chapters"):
        book.chapters_from_nav("site_name: demo\nstrict: true\n")


def test_sources_map_to_the_built_sites_directory_urls():
    chapters = book.chapters_from_nav(NAV)
    assert chapters[0].site_page == "index.html"
    assert chapters[1].site_page == "start/index.html"
    assert chapters[2].site_page == "reference/index.html"


def test_readme_sources_are_index_pages():
    """mkdocs builds adr/README.md to adr/index.html — README is an index page, not a
    directory of its own. The third dogfooded deploy found this the hard way."""
    chapters = book.chapters_from_nav("nav:\n  - Decisions: adr/README.md\n  - Top: README.md\n")
    assert chapters[0].site_page == "adr/index.html"
    assert chapters[1].site_page == "index.html"


def test_extraction_takes_main_strips_chrome_and_closes_voids():
    body = book.extract_main(PAGE)
    assert "<h1>T</h1>" in body
    assert "script" not in body and "nav>" not in body
    assert "<br/>" in body, "a bare <br> is a hard error on a Kindle"


def test_extraction_falls_back_to_article_then_role_main_and_fails_on_none():
    assert "x" in book.extract_main("<article>x</article>")
    # The anchor the ProperDocs theme actually emits, discovered when the first
    # dogfooded deploy refused every page: a Bootstrap column carrying role="main",
    # with arbitrarily nested divs no regex can balance.
    themed = (
        '<body><div class="row"><div class="col-md-3"><nav>side</nav></div>'
        '<div class="col-md-9" role="main"><div class="inner"><h1>T</h1>'
        "<p>content</p></div></div></div><footer>f</footer></body>"
    )
    body = book.extract_main(themed)
    assert "<h1>T</h1>" in body and "content" in body
    assert "footer" not in body and "side" not in body
    with pytest.raises(book.BookError, match="role"):
        book.extract_main("<body>nothing</body>")


def test_the_epub_is_kdp_shaped(tmp_path):
    written = book.build_book(
        _site(tmp_path),
        NAV,
        tmp_path / "out",
        {"title": "Demo Book", "author": "A. Author", "publisher": "Pub", "description": "D"},
    )
    with zipfile.ZipFile(written["epub"]) as z:
        infos = z.infolist()
        # The byte-level contract readers sniff for: mimetype first, STORED.
        assert infos[0].filename == "mimetype"
        assert infos[0].compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype") == b"application/epub+zip"
        container = z.read("META-INF/container.xml").decode()
        assert 'full-path="OEBPS/content.opf"' in container
        opf = z.read("OEBPS/content.opf").decode()
        for needle in (
            '<package version="3.0"',
            "<dc:title>Demo Book</dc:title>",
            "<dc:creator>A. Author</dc:creator>",
            "<dc:publisher>Pub</dc:publisher>",
            "urn:uuid:",
            'properties="nav"',
        ):
            assert needle in opf
        # Spine order is nav order.
        spine = opf.split("<spine>")[1]
        assert spine.index("index") < spine.index("start-index") < spine.index("reference")
        toc = z.read("OEBPS/toc.xhtml").decode()
        assert 'epub:type="toc"' in toc and "Welcome" in toc


def test_the_print_html_carries_the_kdp_trim(tmp_path):
    written = book.build_book(
        _site(tmp_path),
        NAV,
        tmp_path / "out",
        {"title": "Demo Book", "subtitle": "Sub", "author": "A. Author"},
    )
    text = written["print_html"].read_text()
    # The trim and margins the generator that passed KDP's review used are still the
    # defaults (#162 made them parameters, not different numbers): 6x9in, 0.75in top and
    # bottom, 0.5in outside and 0.5in in the gutter, mirrored recto to verso.
    assert "size:6in 9in;margin:0.75in 0.5in 0.75in 0.5in" in text
    assert "@page :right{margin-left:0.5in;margin-right:0.5in}" in text
    assert "@page :left{margin-left:0.5in;margin-right:0.5in}" in text
    assert "font-size:11pt" in text and "font-family:Georgia, serif" in text
    assert "Table of Contents" in text and "Copyright" in text and "Sub" in text
    assert text.index('id="index"') < text.index('id="start-index"')


def test_a_missing_built_page_names_the_chapter(tmp_path):
    site = _site(tmp_path)
    (site / "reference" / "index.html").unlink()
    with pytest.raises(book.BookError, match="reference.md"):
        book.build_book(site, NAV, tmp_path / "out", {"title": "T", "author": "A"})


@pytest.mark.parametrize("missing", ["title", "author"])
def test_metadata_without_title_or_author_is_refused(tmp_path, missing):
    meta = {"title": "T", "author": "A"}
    meta.pop(missing)
    with pytest.raises(book.BookError, match=missing):
        book.build_book(_site(tmp_path), NAV, tmp_path / "out", meta)


def test_the_cli_builds_a_book_and_reports_the_paths(tmp_path, capsys, monkeypatch):
    from vibey_gh import cli

    site = _site(tmp_path)
    cfg = tmp_path / "properdocs.yml"
    cfg.write_text(NAV)
    code = cli.main(
        [
            "book",
            "--site-dir",
            str(site),
            "--config-file",
            str(cfg),
            "--output-dir",
            str(tmp_path / "book"),
            "--title",
            "Demo",
            "--author",
            "A.",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "book.epub" in out and "book-print.html" in out
    # No layout flag given, so the interior is the standard one.
    printed = (tmp_path / "book" / "book-print.html").read_text()
    assert "size:6in 9in;margin:0.75in 0.5in 0.75in 0.5in" in printed


def test_the_cli_reports_an_actionable_error(tmp_path, capsys):
    from vibey_gh import cli

    cfg = tmp_path / "properdocs.yml"
    cfg.write_text("site_name: x\n")
    code = cli.main(
        [
            "book",
            "--site-dir",
            str(tmp_path),
            "--config-file",
            str(cfg),
            "--output-dir",
            str(tmp_path / "book"),
            "--title",
            "T",
            "--author",
            "A",
        ]
    )
    assert code == 1
    assert "no chapters" in capsys.readouterr().err


def test_parser_edges_nested_strips_startend_voids_and_charrefs():
    """The extractor's less-traveled branches, orphaned when two green PRs squashed
    into one red develop: nested chrome subtrees (a form inside a nav), self-closing
    tags both inside capture and inside a strip, a non-strip end tag while stripping,
    void end tags, and entity/character references in prose."""
    page = (
        "<main>"
        "<nav>skip <form>deeper</form> <em>styled-skip</em> <img src='x'/> still-skipped</nav>"
        "<p>keep &amp; &#8594; <br/> this</p>"
        "</main>"
    )
    body = book.extract_main(page)
    assert "keep &amp; &#8594;" in body
    assert "<br/>" in body
    assert "skip" not in body and "deeper" not in body


def test_parser_ignores_content_after_capture_and_stray_end_tags():
    page = "<div><main><p>inside</p></main><p>after</p></div><em>tail</em>"
    body = book.extract_main(page)
    assert "inside" in body and "after" not in body and "tail" not in body
    # a stray end tag arriving before any capture begins is ignored
    assert "x" in book.extract_main("</div><article>x</article>")


def test_parser_handles_end_of_void_and_unclosed_capture():
    # explicit </br> end tags are void — never decrement capture depth
    body = book.extract_main("<main><p>a</p></br><p>b</p></main>")
    assert "a" in body and "b" in body
    # capture that never closes ends at EOF with what it gathered
    assert "tail-content" in book.extract_main("<main><p>tail-content</p>")


def test_an_omitted_end_tag_is_synthesized_so_the_chapter_is_xml():
    """HTML lets an end tag be omitted. XML does not, and one unbalanced chapter
    invalidates the whole package rather than the page it came from.

    `<ul><li>one<li>two</ul>` is valid HTML -- the second <li> closes the first -- and
    `HTMLParser` reports both start tags with a single `</ul>`, synthesizing nothing. A
    walk that counted depth emitted two <li>s it never closed.
    """
    body = book.extract_main("<main><ul><li>one<li>two</ul></main>")
    assert body.count("<li>") == 2 and body.count("</li>") == 2
    # Siblings, not one nested in the other: closing them anywhere satisfies XML and
    # still renders a list inside its own first item.
    assert body == "<ul><li>one</li><li>two</li></ul>"
    ET.fromstring(f"<root>{body}</root>")


def test_elements_still_open_at_end_of_input_are_closed():
    """A truncated page is unbalanced, and unbalanced fails the parse for the package."""
    body = book.extract_main("<main><div><p>truncated")
    assert "truncated" in body
    ET.fromstring(f"<root>{body}</root>")


def test_a_stray_end_tag_inside_capture_closes_nothing():
    """It matches no open element, so emitting it would be the mismatch this guards."""
    body = book.extract_main("<main><p>kept</p></section></main>")
    assert "kept" in body and "</section>" not in body
    ET.fromstring(f"<root>{body}</root>")


def test_a_literal_xml_forbidden_character_is_dropped_from_prose():
    """`character_reference` already refuses `&#0;`; a LITERAL one reached the output.

    NUL and form feed cannot be written in XML in any form -- `&#0;` is as illegal as
    the character itself -- so removal is the only thing that leaves a parseable
    document.
    """
    body = book.extract_main("<main><p>before\x00\x0cafter</p></main>")
    assert "\x00" not in body and "\x0c" not in body
    assert "before" in body and "after" in body
    ET.fromstring(f"<root>{body}</root>")


# --- #162: the book has to be valid before it can be beautiful ---------------------

# What mkdocs actually renders: a permalink anchor after every heading whose text is
# `&para;`, plus the ordinary named entities prose picks up. `&para;` is undefined in
# XHTML, so a chapter carrying one is not XML at all and the EPUB will not open.
MKDOCS_PAGE = """<!doctype html>
<html lang="en"><head><title>P</title></head><body>
<nav class="md-header">site nav</nav>
<main>
<h1 id="one">Chapter One<a class="headerlink" href="#one" title="Permanent link">&para;</a></h1>
<p>A caf&eacute; &rarr; a book &amp; back, 100&nbsp;% of the time.</p>
<h2 id="two">Section<a class="headerlink" href="#two" title="Permanent link">&para;</a></h2>
<p>Line<br>break, an arrow &#8594;, a <code>&lt;tag&gt;</code>, and R&amp;D.</p>
</main>
<footer>f</footer></body></html>
"""


def _mkdocs_site(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    for page in ("index.html", "start/index.html", "reference/index.html"):
        target = site / page
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(MKDOCS_PAGE)
    return site


def test_every_epub_chapter_parses_as_xml(tmp_path):
    """The whole point of an EPUB: a reader parses each chapter with an XML parser.

    Before the sanitizer this raised `undefined entity` on the first heading of every
    page, which is an invalid package -- a book that was built, published and could
    never be opened.
    """
    written = book.build_book(
        _mkdocs_site(tmp_path),
        NAV,
        tmp_path / "out",
        {"title": "Demo Book", "author": "A. Author"},
    )
    with zipfile.ZipFile(written["epub"]) as z:
        documents = [n for n in z.namelist() if n.endswith(".xhtml")]
        assert len(documents) == 4  # toc + three chapters
        for name in documents:
            ET.fromstring(z.read(name).decode())


def test_permalink_pilcrows_never_reach_the_interior(tmp_path):
    """Site chrome is furniture for a page you can click. A book is neither."""
    written = book.build_book(
        _mkdocs_site(tmp_path),
        NAV,
        tmp_path / "out",
        {"title": "Demo Book", "author": "A. Author"},
    )
    printed = written["print_html"].read_text()
    with zipfile.ZipFile(written["epub"]) as z:
        chapter = z.read("OEBPS/index.xhtml").decode()
    for text in (chapter, printed):
        assert "headerlink" not in text
        assert "¶" not in text and "&para;" not in text
        assert "Permanent link" not in text
        assert "Chapter One" in text  # the heading itself survives intact


def test_named_entities_survive_as_characters_not_as_undefined_entities():
    body = book.extract_main(MKDOCS_PAGE)
    assert "café → a book &amp; back, 100 % of the time." in body
    assert "&eacute;" not in body and "&rarr;" not in body and "&nbsp;" not in body
    # a numeric reference is already legal XML, so it is left alone
    assert "&#8594;" in body
    # and an escaped tag in prose stays escaped exactly once
    assert "<code>&lt;tag&gt;</code>" in body


def test_the_sanitizer_is_injectable_so_a_theme_can_describe_its_own_chrome():
    """ADR-0018: what counts as chrome is a key, not a decision taken away."""
    kept = book.extract_main(MKDOCS_PAGE, ChapterSanitizer(chrome_classes=frozenset({"pilcrow"})))
    assert 'class="headerlink"' in kept and "¶" in kept
    ET.fromstring(f"<body>{kept}</body>")  # still XML, just not de-chromed


def test_void_chrome_and_voids_inside_a_discarded_subtree():
    """The strip counter counts elements, not chrome tag names: a permalink anchor is
    an <a>, and </a> would never have decremented a tag-name counter."""
    page = (
        "<main>"
        '<img class="headerlink" src="p.png">'
        '<img class="headerlink" src="q.png"/>'
        "<nav><img src='x'>text</br><span>deep</span></nav>"
        "<p>kept</p>"
        "</main>"
    )
    body = book.extract_main(page)
    assert body == "<p>kept</p>"


def test_headerlink_anchors_do_not_swallow_the_rest_of_the_heading():
    body = book.extract_main(
        '<main><h2 id="s">Title<a class="headerlink" href="#s">&para;</a>'
        " and more</h2><p>after</p></main>"
    )
    assert body == '<h2 id="s">Title and more</h2><p>after</p>'


def test_inline_svg_keeps_the_case_a_renderer_needs(tmp_path):
    """Rebuilding a start tag must not cost the casing SVG depends on.

    `html.parser` folds every name to lower case, so rebuilding from the parsed
    attributes turned `viewBox` into `viewbox` -- an attribute an XHTML/SVG renderer
    ignores, scaling an inline diagram wrong or dropping it.
    """
    body = book.extract_main(
        '<main><p><svg viewBox="0 0 24 24" preserveAspectRatio="xMidYMid">'
        '<linearGradient id="g"/></svg></p></main>'
    )
    assert 'viewBox="0 0 24 24"' in body
    assert 'preserveAspectRatio="xMidYMid"' in body
    assert '<linearGradient id="g"/>' in body
    # and it is still what it has to be first of all: XML
    ET.fromstring(f"<root>{body}</root>")


# --- #162: the nav's own structure, and an interior a paperback needs -----------------

# The nav this repository actually writes, in both of the styles the reader meets: the
# indented one a person types in properdocs.yml, and the indentless one `yaml.safe_dump`
# writes for the channel sites -- which is the file the book is really built from.
NESTED_NAV = """nav:
  - Home: index.md
  - Guides:
      - Kubernetes: guides/kubernetes.md
  - Architecture:
      - Decision records:
          - "0001 — Orchestrate the `*loop` runners; do not reimplement them": adr/0001.md
          - '0002 — It''s: quoted': adr/0002.md
  - Research paper: paper.md
  - Governance:
      - The Constitution: governance/constitution.md
"""

DUMPED_NAV = """site_name: demo
nav:
- Home: index.md
- Guides:
  - Kubernetes: guides/kubernetes.md
- Architecture:
  - Decision records:
    - 0001 — Orchestrate the `*loop` runners; do not reimplement them: adr/0001.md
    - '0002 — It''s: quoted': adr/0002.md
- Research paper: paper.md
- Governance:
  - The Constitution: governance/constitution.md
theme: mkdocs
"""

NESTED_SOURCES = (
    "index.md",
    "guides/kubernetes.md",
    "adr/0001.md",
    "adr/0002.md",
    "paper.md",
    "governance/constitution.md",
)

CODE_PAGE = (
    "<main><h1>T</h1><p>See <code>infrastructure/config_loader.py</code> and"
    ' <a href="x/y.html">a.b</a>.</p><pre><code class="language-py">a.b_c'
    ' <span class="k">x.y</span></code></pre></main>'
)


def _nested_site(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    for source in NESTED_SOURCES:
        page = site / book.BookChapter("t", source).site_page
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(CODE_PAGE)
    return site


def _interior(tmp_path: Path, meta: dict[str, str] | None = None, **layout) -> str:
    written = book.build_book(
        _nested_site(tmp_path),
        NESTED_NAV,
        tmp_path / "out",
        meta or {"title": "Demo Book", "author": "A. Author"},
        interior=book.PrintInterior(**layout),
    )
    return written["print_html"].read_text()


def _opf(tmp_path: Path, meta: dict[str, str], name: str = "out") -> str:
    written = book.build_book(_mkdocs_site(tmp_path), NAV, tmp_path / name, meta)
    with zipfile.ZipFile(written["epub"]) as z:
        return z.read("OEBPS/content.opf").decode()


@pytest.mark.parametrize("nav", [NESTED_NAV, DUMPED_NAV], ids=["indented", "indentless"])
def test_the_nav_sections_survive_into_the_chapters(nav):
    """The section headings used to be dropped, and depth stopped at one."""
    chapters = book.chapters_from_nav(nav)
    adrs = ("Architecture", "Decision records")
    assert [(c.title, c.sections) for c in chapters] == [
        ("Home", ()),
        ("Kubernetes", ("Guides",)),
        ("0001 — Orchestrate the *loop runners; do not reimplement them", adrs),
        ("0002 — It's: quoted", adrs),
        ("Research paper", ()),
        ("The Constitution", ("Governance",)),
    ]
    assert [c.depth for c in chapters] == [0, 1, 2, 2, 0, 1]


def test_double_quoted_titles_are_unescaped_the_way_yaml_reads_them():
    nav = (
        "nav:\n"
        '  - "A\\u2014B \\"q\\" \\\\ \\x41\\U0001F600\\tC\\n": a.md\n'
        '  - "bad \\uD800 and \\U00110000 end": b.md\n'
        '  - "odd \\q: kept": c.md\n'
    )
    titles = [c.title for c in book.chapters_from_nav(nav)]
    assert titles == ['A—B "q" \\ A😀 C', "bad � and � end", "odd q: kept"]


def test_comments_and_foreign_entries_neither_end_the_nav_nor_become_chapters():
    nav = (
        "nav:\n"
        "# a comment at column zero is still inside the nav\n"
        "  - Home: index.md\n"
        "\n"
        "  - Links:\n"
        "      - GitHub: https://github.com/example\n"
        "  # an indented one\n"
        "  - Reference: reference.md\n"
        "theme: mkdocs\n"
        "  - After: after.md\n"
    )
    chapters = book.chapters_from_nav(nav)
    assert [(c.title, c.sections) for c in chapters] == [("Home", ()), ("Reference", ())]


def test_the_contents_groups_chapters_under_their_sections_in_nav_order():
    chapters = [
        book.BookChapter("One", "one.md"),
        book.BookChapter("Two", "a/two.md", ("A",)),
        book.BookChapter("Three & more", "a/b/three.md", ("A", "B")),
        book.BookChapter("Four", "c/four.md", ("C",)),
        book.BookChapter("Five", "a/five.md", ("A",)),
    ]
    listing = book.TableOfContents(chapters).ordered_list(lambda c: f"#{c.slug}")
    assert listing == (
        "<ol>\n"
        '<li><a href="#one">One</a></li>\n'
        "<li><span>A</span><ol>\n"
        '<li><a href="#a-two">Two</a></li>\n'
        "<li><span>B</span><ol>\n"
        '<li><a href="#a-b-three">Three &amp; more</a></li>\n'
        "</ol></li>\n"
        "</ol></li>\n"
        "<li><span>C</span><ol>\n"
        '<li><a href="#c-four">Four</a></li>\n'
        "</ol></li>\n"
        # A section the nav returns to after another is a second group, not a merge:
        # the nav order is the book's order.
        "<li><span>A</span><ol>\n"
        '<li><a href="#a-five">Five</a></li>\n'
        "</ol></li>\n"
        "</ol>"
    )
    ET.fromstring(listing)


@pytest.mark.parametrize(
    ("previous", "current", "opened"),
    [
        ((), (), ()),
        ((), ("A", "B"), ("A", "B")),
        (("A",), ("A", "B"), ("B",)),
        (("A", "B"), ("A",), ()),
        (("A", "B"), ("C",), ("C",)),
        (("A", "B"), ("A", "C"), ("C",)),
    ],
)
def test_opening_names_only_the_headings_a_chapter_newly_enters(previous, current, opened):
    assert book.TableOfContents.opening(previous, current) == opened


def test_the_interior_is_a_book_and_not_a_web_page(tmp_path):
    text = _interior(tmp_path)
    # A folio at the foot of every body page, and none on the front matter or a part
    # opener -- which is where the front matter's page names come in.
    assert "@bottom-center{content:counter(page)" in text
    assert "@page front{@bottom-center{content:none}}" in text
    assert "@page part{@bottom-center{content:none}}" in text
    assert ".title-page,.copyright-page,.toc{page:front;break-after:page}" in text
    # Justified and hyphenated, with widows and orphans held to three lines.
    for rule in ("text-align:justify", "hyphens:auto", "orphans:3", "widows:3"):
        assert rule in text
    assert "pre,table,figure,img,svg{break-inside:avoid}" in text
    # The modern fragmentation properties only; the legacy page-break-* are gone.
    assert "page-break" not in text
    # Hyphenation needs a language to hyphenate in.
    assert text.startswith('<!DOCTYPE html>\n<html lang="en">')
    # A narrow table column keeps whole words: `anywhere` would squeeze it to a letter.
    assert "overflow-wrap:break-word}" in text.split("td,th{", 1)[1].split("\n", 1)[0]


def test_every_chapter_has_a_named_page_carrying_its_running_heads(tmp_path):
    text = _interior(tmp_path)
    # No section above Home, so its verso carries the book's title.
    assert '@page c1:left{@top-center{content:"Demo Book"}}' in text
    assert '@page c1:right{@top-center{content:"Home"}}' in text
    # An ADR: the verso names its section, the recto its own title, cut at a word.
    assert '@page c3:left{@top-center{content:"Decision records"}}' in text
    head = "0001 — Orchestrate the *loop runners; do not reimplement…"
    assert f'@page c3:right{{@top-center{{content:"{head}"}}}}' in text
    assert '<section class="chapter" id="adr-0001" style="page:c3">' in text
    assert '@page c4:right{@top-center{content:"0002 — It\'s: quoted"}}' in text


def test_a_running_head_is_cut_at_a_word_and_escaped_for_css():
    title = 'Quote " back \\ and </style> then'
    chapters = [book.BookChapter(title, "q.md")]
    body = {"q": "<p>x</p>"}
    short = book.PrintInterior(running_head_length=20).render(
        {"title": "T", "author": "A"}, chapters, body, 2026
    )
    assert '@page c1:right{@top-center{content:"Quote \\22  back \\5c  and…"}}' in short
    whole = book.PrintInterior().render({"title": "T", "author": "A"}, chapters, body, 2026)
    assert "and \\3c /style\\3e  then" in whole
    # The title never closes the stylesheet it is written into.
    assert whole.count("</style>") == 1


def test_each_section_opens_with_a_part_page(tmp_path):
    text = _interior(tmp_path)
    assert '<section class="part"><h1>Guides</h1></section>' in text
    assert '<section class="part"><h1>Architecture</h1><p>Decision records</p></section>' in text
    assert '<section class="part"><h1>Governance</h1></section>' in text
    # A return to the top level opens nothing; a part comes before the chapters it holds.
    assert text.count('<section class="part">') == 3
    assert text.index("<h1>Architecture</h1>") < text.index('id="adr-0001"')
    # And the contents keeps the same grouping.
    assert "<li><span>Architecture</span><ol>\n<li><span>Decision records</span><ol>" in text


def test_code_gets_line_break_opportunities_and_nothing_else_does(tmp_path):
    """A path in justified text used to stretch the line before it into a row of gaps."""
    text = _interior(tmp_path)
    assert "<code>infrastructure/<wbr>config_<wbr>loader.<wbr>py</code>" in text
    # Prose, tags and attributes are untouched -- inside code as well as out of it.
    assert '<a href="x/y.html">a.b</a>' in text
    assert (
        '<code class="language-py">a.<wbr>b_<wbr>c <span class="k">x.<wbr>y</span></code>' in text
    )


def test_the_interior_is_written_in_the_books_language(tmp_path):
    text = _interior(tmp_path, {"title": "Buch", "author": "A", "language": "de-CH"})
    assert text.startswith('<!DOCTYPE html>\n<html lang="de-CH">')


def test_every_physical_dimension_is_a_constructor_parameter():
    css = book.PrintInterior(
        trim_width="5.5",
        trim_height="8.5IN",
        margin_top="0.8in",
        margin_bottom="20mm",
        margin_outside=".3",
        gutter="0.625",
        font_size="10",
        line_height="1.4",
        font_family='"Libre Baskerville", serif',
        code_font_family="Menlo, monospace",
    ).css()
    assert "size:5.5in 8.5in;margin:0.8in .3in 20mm 0.625in" in css
    # The gutter mirrors onto the binding side: left on a recto, right on a verso.
    assert "@page :right{margin-left:0.625in;margin-right:.3in}" in css
    assert "@page :left{margin-left:.3in;margin-right:0.625in}" in css
    assert 'font-family:"Libre Baskerville", serif;font-size:10pt;line-height:1.4' in css
    assert "pre,code,kbd,samp{font-family:Menlo, monospace" in css


@pytest.mark.parametrize(
    ("layout", "complaint"),
    [
        ({"gutter": "0.5in;}body{display:none"}, "gutter"),
        ({"trim_width": "-6in"}, "trim width"),
        ({"font_size": "large"}, "font size"),
        ({"font_family": "Georgia; color:red"}, "font family"),
        ({"code_font_family": "  "}, "code font family"),
        ({"running_head_length": 0}, "running head length"),
    ],
)
def test_a_parameter_that_would_rewrite_the_stylesheet_is_refused(layout, complaint):
    with pytest.raises(book.BookError, match=complaint):
        book.PrintInterior(**layout)


@pytest.mark.parametrize(
    ("trim", "size"),
    [
        ("6x9", ("6in", "9in")),
        ("5.5 X 8.5", ("5.5in", "8.5in")),
        ("148mmx210mm", ("148mm", "210mm")),
        ("600pxx900px", ("600px", "900px")),
        ("6×9", ("6in", "9in")),
    ],
)
def test_a_trim_is_read_as_width_by_height(trim, size):
    assert book.PrintInterior.parse_trim(trim) == size


@pytest.mark.parametrize("trim", ["6", "6x", "axb", "6x9x10"])
def test_a_trim_that_is_not_two_lengths_is_refused(trim):
    with pytest.raises(book.BookError, match="trim"):
        book.PrintInterior.parse_trim(trim)


def test_the_epub_identifier_is_the_same_book_on_every_build(tmp_path):
    """It was a fresh random UUID per build: every release looked like another book."""
    meta = {"title": "Demo Book", "author": "A. Author"}
    first = _opf(tmp_path, meta, "one")
    # Pinned, not merely compared: a change to the derivation would silently hand every
    # book already published a new identity.
    uid = "urn:uuid:848fbf17-d8fd-5e2e-9c5b-4ef0d0a2dac5"
    assert f'<dc:identifier id="uid">{uid}</dc:identifier>' in first
    assert uid in _opf(tmp_path, meta, "two")
    # A new edition, or a translation, is a new book.
    assert uid not in _opf(tmp_path, {**meta, "edition": "2"}, "three")
    assert uid not in _opf(tmp_path, {**meta, "language": "de"}, "four")
    # An explicit identifier -- an ISBN, once one is chosen -- is used as given.
    isbn = {**meta, "identifier": "urn:isbn:9780000000000"}
    assert '<dc:identifier id="uid">urn:isbn:9780000000000</dc:identifier>' in _opf(
        tmp_path, isbn, "five"
    )


def test_the_package_carries_a_publication_date_the_copyright_agrees_with(tmp_path):
    opf = _opf(tmp_path, {"title": "T", "author": "A", "date": "20270115"}, "given")
    assert "<dc:date>2027-01-15</dc:date>" in opf  # normalized to the calendar form
    printed = (tmp_path / "given" / "book-print.html").read_text()
    assert "Copyright &#169; 2027 A." in printed
    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    assert f"<dc:date>{today}</dc:date>" in _opf(tmp_path, {"title": "T", "author": "A"}, "b")
    # No description given, no empty element for a validator to flag.
    assert "<dc:description>" not in opf
    assert re.search(r'<meta property="dcterms:modified">\d{4}-\d\d-\d\dT[\d:]{8}Z</meta>', opf)


@pytest.mark.parametrize(
    ("meta", "complaint"),
    [
        ({"date": "next tuesday"}, "date"),
        ({"language": 'en" onload="x'}, "language"),
    ],
)
def test_metadata_that_cannot_be_written_down_is_refused(tmp_path, meta, complaint):
    with pytest.raises(book.BookError, match=complaint):
        book.build_book(
            _site(tmp_path), NAV, tmp_path / "out", {"title": "T", "author": "A", **meta}
        )


def test_the_navigation_has_landmarks_and_every_document_a_language(tmp_path):
    written = book.build_book(
        _mkdocs_site(tmp_path),
        NAV,
        tmp_path / "out",
        {"title": "T", "author": "A", "language": "en-GB"},
    )
    with zipfile.ZipFile(written["epub"]) as z:
        navigation = z.read("OEBPS/toc.xhtml").decode()
        chapter = z.read("OEBPS/index.xhtml").decode()
        opf = z.read("OEBPS/content.opf").decode()
    assert 'epub:type="landmarks"' in navigation
    assert '<a epub:type="toc" href="toc.xhtml">' in navigation
    assert '<a epub:type="bodymatter" href="index.xhtml">Home</a>' in navigation
    assert "<li><span>Start here</span><ol>" in navigation
    xml_lang = "{http://www.w3.org/XML/1998/namespace}lang"
    for document in (navigation, chapter):
        assert ET.fromstring(document).get(xml_lang) == "en-GB"
    assert "<dc:language>en-GB</dc:language>" in opf
    assert ET.fromstring(opf).get(xml_lang) == "en-GB"


def test_the_interior_and_the_package_are_injectable_seams(tmp_path):
    class Interior:
        def css(self) -> str:
            return ""

        def render(self, meta, chapters, bodies, year) -> str:
            return f"{len(chapters)} chapters, {year}"

    class Package:
        def identifier(self, meta) -> str:
            return "x"

        def write(self, path, meta, chapters, bodies, now) -> None:
            path.write_text(meta["date"])

    written = book.build_book(
        _site(tmp_path),
        NAV,
        tmp_path / "out",
        {"title": "T", "author": "A", "date": "2030-02-03"},
        interior=Interior(),
        package=Package(),
    )
    assert written["print_html"].read_text() == "3 chapters, 2030"
    assert written["epub"].read_text() == "2030-02-03"


def test_each_class_satisfies_the_interface_declared_beside_it():
    assert isinstance(book.NavReader(), NavReaderInterface)
    assert isinstance(book.TableOfContents([]), TableOfContentsInterface)
    assert isinstance(book.PrintInterior(), PrintInteriorInterface)
    assert isinstance(book.EpubPackage(), EpubPackageInterface)
    assert isinstance(book.BookChapter("t", "t.md"), BookChapterInterface)


def _cli_book(tmp_path: Path, *flags: str) -> int:
    from vibey_gh import cli

    cfg = tmp_path / "properdocs.yml"
    cfg.write_text(NAV)
    return cli.main(
        [
            "book",
            "--site-dir",
            str(_site(tmp_path)),
            "--config-file",
            str(cfg),
            "--output-dir",
            str(tmp_path / "book"),
            "--title",
            "Demo",
            "--author",
            "A.",
            *flags,
        ]
    )


def test_the_cli_hands_every_physical_parameter_to_the_interior(tmp_path):
    code = _cli_book(
        tmp_path,
        *("--trim", "5x8", "--gutter", "0.625", "--margin-outside", "0.4in"),
        *("--margin-top", "0.7in", "--margin-bottom", "0.8in", "--font-size", "10"),
        *("--line-height", "1.4", "--font-family", "Palatino, serif"),
        *("--code-font-family", "Menlo, monospace", "--running-head-length", "4"),
        *("--edition", "2", "--date", "2027-03-04", "--language", "de"),
    )
    assert code == 0
    text = (tmp_path / "book" / "book-print.html").read_text()
    assert "size:5in 8in;margin:0.7in 0.4in 0.8in 0.625in" in text
    assert "font-family:Palatino, serif;font-size:10pt;line-height:1.4" in text
    assert "pre,code,kbd,samp{font-family:Menlo, monospace" in text
    assert '@page c2:right{@top-center{content:"Welc…"}}' in text
    assert '<html lang="de">' in text and "Copyright &#169; 2027" in text
    with zipfile.ZipFile(tmp_path / "book" / "book.epub") as z:
        opf = z.read("OEBPS/content.opf").decode()
    assert "<dc:date>2027-03-04</dc:date>" in opf
    same = {"title": "Demo", "author": "A.", "language": "de", "edition": "2"}
    assert book.EpubPackage().identifier(same) in opf


def test_the_cli_passes_an_explicit_identifier_through(tmp_path):
    assert _cli_book(tmp_path, "--identifier", "urn:isbn:9780000000000") == 0
    with zipfile.ZipFile(tmp_path / "book" / "book.epub") as z:
        opf = z.read("OEBPS/content.opf").decode()
    assert '<dc:identifier id="uid">urn:isbn:9780000000000</dc:identifier>' in opf


@pytest.mark.parametrize(
    ("flag", "value", "complaint"),
    [("--trim", "6by9", "trim"), ("--gutter", "wide", "gutter"), ("--date", "soon", "date")],
)
def test_the_cli_reports_a_bad_flag_as_an_actionable_error(
    tmp_path, capsys, flag, value, complaint
):
    assert _cli_book(tmp_path, flag, value) == 1
    assert complaint in capsys.readouterr().err
