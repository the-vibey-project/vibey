# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Export the published documentation as a book: an EPUB 3.0 and a print-ready HTML.

Docs trapped in a browser cannot be printed as a desk reference or published on Amazon
KDP without a reformatting step, which is exactly the step nobody performs (#137). This
module removes it: chapters come from the site nav — so the copy doctrine's ordering
(beginner tier first, engineering reference second, scholarly material last) carries into
the book untouched, grouped under the nav's own section headings — content comes from the
already-built site's pages, and the output is KDP-shaped by construction. The EPUB is a
valid 3.0 package with Dublin Core metadata, a landmarks navigation and an identifier that
is the same for the same book on every build. The print HTML is a book interior (#162):
mirrored margins with the gutter on the binding side, a folio at the foot of every body
page, the chapter's title as its running head, numberless front matter, and justified,
hyphenated text in the language the book declares. The standard 6in x 9in trim is only
the default; every physical dimension is a constructor parameter (ADR-0018).

Deliberately stdlib-only, like everything else in this package: the EPUB container is
plain zipfile work, the nav parser reads only the constrained `nav:` block this family's
site configurations use, and content extraction is anchored on the built page's <main>
element. The one step that genuinely needs a browser — HTML to PDF — is left to the
caller's workflow, which prints with the runner's own headless Chrome or Chromium; the
package grows no dependency for it. The stylesheet is therefore written for what Chrome's
print engine implements — `@page` :left/:right, named pages, and margin boxes carrying
`counter(page)` — and not for the parts of CSS Paged Media it does not (`string-set`,
`running()`, `target-counter()`, `leaders()`).
"""

from __future__ import annotations

import datetime
import html as html_lib
import html.parser as html_parser
import re
import uuid
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from vibey_gh.chapter_sanitizer import ChapterSanitizer
from vibey_gh.interfaces.book_interface import (
    BookChapterInterface,
    EpubPackageInterface,
    MainExtractorInterface,
    PrintInteriorInterface,
)
from vibey_gh.interfaces.chapter_sanitizer_interface import ChapterSanitizerInterface

__all__ = [
    "BookChapter",
    "BookError",
    "EpubPackage",
    "MainExtractor",
    "NavReader",
    "PrintInterior",
    "TableOfContents",
    "build_book",
    "chapters_from_nav",
    "extract_main",
]


class BookError(RuntimeError):
    """A book cannot be built and the reason is actionable by the operator."""


@dataclass(frozen=True)
class BookChapter:
    title: str
    source: str  # docs-relative markdown path from the nav, e.g. "start/index.md"
    # The nav section headings enclosing this chapter, outermost first -- ("Architecture",
    # "Decision records") for an ADR. The contents groups chapters under them and the
    # print interior opens each group with a part page.
    sections: tuple[str, ...] = ()

    @property
    def depth(self) -> int:
        """The nav nesting level: how many section headings enclose this chapter.

        Derived rather than stored, so it cannot disagree with `sections`. It used to be
        a field capped at 1, which read a three-deep ADR entry as one level down and
        dropped the heading between.
        """
        return len(self.sections)

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.source.removesuffix(".md").lower()).strip("-")

    @property
    def site_page(self) -> str:
        """The built page for this source, mirroring mkdocs' directory URLs.

        README.md is an index page exactly like index.md — mkdocs builds
        `adr/README.md` to `adr/index.html`, not `adr/README/index.html` —
        discovered when the third dogfooded deploy could not find the ADR chapter.
        """
        stem = self.source.removesuffix(".md")
        parts = stem.rsplit("/", 1)
        name = parts[-1]
        if name in ("index", "README"):
            prefix = parts[0] + "/" if len(parts) == 2 else ""
            return f"{prefix}index.html"
        return f"{stem}/index.html"


# A nav title as YAML writes one: double-quoted (backslash escapes), single-quoted (a
# doubled quote is a literal one), or plain -- which cannot hold ": " and so ends at the
# first colon. A quoted title may carry a colon; a plain one never could.
_NAV_TITLE = r"\"(?:[^\"\\]|\\.)*\"|'(?:[^']|'')*'|[^\s\"'][^:]*?"
_NAV_ENTRY = re.compile(rf"^(\s*)-\s+({_NAV_TITLE})\s*:\s*(\S+\.md)\s*$")
_NAV_SECTION = re.compile(rf"^(\s*)-\s+({_NAV_TITLE})\s*:\s*$")
_YAML_ESCAPE = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|.)")


class NavReader:
    """Reads the ordered chapter list out of a site configuration's `nav:` block.

    Not a YAML parser on purpose: this package carries no dependencies, and the nav
    blocks this family writes are a constrained shape — `- Title: file.md` entries,
    nested under `- Section:` headings to any depth, in either the indented style a
    person writes or the indentless one `yaml.safe_dump` emits for the channel sites.
    Anything outside that shape is ignored rather than misread, and an empty result is an
    error the operator can act on, never an empty book.

    Its seam is declared beside it in `vibey_gh/interfaces/book_interface.py`, per
    ADR-0016.
    """

    def read(self, config_text: str) -> list[BookChapter]:
        chapters: list[BookChapter] = []
        in_nav = False
        # The section headings still open, innermost last, each with the column of its
        # `-`. A line closes every section it is not strictly deeper than.
        open_sections: list[tuple[int, str]] = []
        for line in config_text.splitlines():
            if re.match(r"^nav:\s*$", line):
                in_nav = True
                open_sections = []
                continue
            if not in_nav or not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith((" ", "-")):
                break  # a new top-level key ends the nav block
            match = _NAV_ENTRY.match(line) or _NAV_SECTION.match(line)
            if match is None:
                continue
            indent = len(match.group(1))
            while open_sections and open_sections[-1][0] >= indent:
                open_sections.pop()
            title = self._title(match.group(2))
            if match.re is _NAV_SECTION:
                open_sections.append((indent, title))
            else:
                enclosing = tuple(heading for _, heading in open_sections)
                chapters.append(BookChapter(title, match.group(3), enclosing))
        if not chapters:
            raise BookError(
                "no chapters: the site configuration has no `- Title: file.md` nav entries"
            )
        return chapters

    @classmethod
    def _title(cls, raw: str) -> str:
        """The title as plain text, wherever the book prints it.

        YAML's quotes are syntax, not title -- the ADR entries in this repository's own
        nav are double-quoted, and the book printed the quote marks. A markdown code span
        is rendered text on the site, but a book title is plain text in the running
        heads, the contents and the EPUB navigation, so its backticks were printed too
        ("0001 — Orchestrate the `*loop` runners…").
        """
        if raw.startswith('"'):
            text = _YAML_ESCAPE.sub(cls._unescape, raw[1:-1])
        elif raw.startswith("'"):
            text = raw[1:-1].replace("''", "'")
        else:
            text = raw
        return " ".join(text.replace("`", "").split())

    @staticmethod
    def _unescape(match: re.Match[str]) -> str:
        """One escape in a double-quoted YAML title, as the character it stands for.

        The hex forms carry any code point (`\\u2014` is the em dash every ADR title
        uses); `\\n`, `\\t` and `\\r` become the space a single-line title needs; any other
        escaped character stands for itself, which covers `\\"` and `\\\\`. A code point
        UTF-8 cannot encode -- a lone surrogate, or one past U+10FFFF -- becomes U+FFFD
        rather than failing the whole book when the file is written.
        """
        code = match.group(1)
        if len(code) > 1:
            codepoint = int(code[1:], 16)
            legal = codepoint <= 0x10FFFF and not 0xD800 <= codepoint <= 0xDFFF
            return chr(codepoint) if legal else "\ufffd"
        return " " if code in "ntr" else code


def chapters_from_nav(config_text: str) -> list[BookChapter]:
    """The ordered chapter list from a site configuration's `nav:` block.

    ADR-0016 method of last resort, and the reason: this is the module's published façade
    -- `build_book` and the tests call it by this name, and it predates the class. The
    reading itself is `NavReader`, a class with its interface beside it; this line only
    keeps the entry point every caller already knows.
    """
    return NavReader().read(config_text)


# Start tags that end an open element in HTML, as `tag -> the tags it closes`. HTML lets
# these end tags be omitted and `HTMLParser` synthesizes nothing, so without this a
# document's siblings become each other's children: well-formed XML, and a book showing a
# list nested inside its own first item. Deliberately the small set a documentation site
# emits rather than HTML's whole optional-end-tag table -- every entry here is one whose
# absence is visible on a rendered page.
_IMPLIED_END_TAGS: dict[str, frozenset[str]] = {
    "li": frozenset({"li"}),
    "dt": frozenset({"dt", "dd"}),
    "dd": frozenset({"dt", "dd"}),
    "td": frozenset({"td", "th"}),
    "th": frozenset({"td", "th"}),
    "tr": frozenset({"td", "th", "tr"}),
    "option": frozenset({"option"}),
    "p": frozenset({"p"}),
}


class MainExtractor(html_parser.HTMLParser):
    """Capture the subtree of the first <main>, <article>, or role="main" element.

    A parser, not a regex: the content element nests arbitrarily many <div>s (the
    ProperDocs theme wraps the body in a Bootstrap column carrying role="main"), and no
    regular expression balances that. Every decision about what survives capture and how
    it is written down belongs to the sanitizer -- this class only walks the tree.

    Its seam is declared beside it in `vibey_gh/interfaces/book_interface.py`, per
    ADR-0016.
    """

    def __init__(self, sanitizer: ChapterSanitizerInterface) -> None:
        super().__init__(convert_charrefs=False)
        self._sanitizer = sanitizer
        self.out: list[str] = []
        # The OPEN ELEMENTS, innermost last -- not a depth count. HTML permits an end tag
        # to be omitted (`<ul><li>one<li>two</ul>` is valid HTML), and `HTMLParser` does
        # not synthesize the missing ones, so a counter decremented per end tag closes
        # the wrong number of elements and emits a fragment XML cannot parse. Holding the
        # names lets an end tag close whatever it actually closes. Empty = not capturing;
        # the first entry is the content element itself, which is never emitted.
        self.open: list[str] = []
        self.strip_depth = 0  # nesting inside a chrome subtree being discarded
        self.done = False

    @property
    def depth(self) -> int:
        """How deep the walk is inside the content element.

        Kept as a read-only view over `open` because it reads better at the call sites
        that only ask "are we capturing" -- and because a second writable counter beside
        the stack is exactly the pair that would drift apart.
        """
        return len(self.open)

    def _is_target(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        return tag in ("main", "article") or ("role", "main") in [(k, v) for k, v in attrs]

    def _close_implied_by(self, tag: str) -> None:
        """Close the open element this start tag ends, where HTML says it ends one.

        `<li>one<li>two` is two SIBLINGS in HTML -- the second start tag closes the
        first item -- but `HTMLParser` reports both start tags and leaves the closing to
        the caller. Stacking them blindly would still be well-formed XML, so the EPUB
        would open; it would just show a list nested inside its own first item. Valid
        and wrong is not the bar, so the pairs below are honoured.

        Deliberately the small set a documentation site actually emits, not HTML's whole
        optional-end-tag table: each entry is a case that has a visible consequence in a
        rendered book.
        """
        closed_by = _IMPLIED_END_TAGS.get(tag)
        if not closed_by or len(self.open) <= 1 or self.open[-1] not in closed_by:
            return
        self.out.append(self._sanitizer.end_tag(self.open.pop()))

    def _emit(self, text: str) -> None:
        if self.depth and not self.strip_depth and not self.done:
            self.out.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done:
            return
        if self.depth == 0:
            if self._is_target(tag, attrs):
                self.open.append(tag)
            return
        if self.strip_depth:
            # Count every element, not only the chrome tags: a discarded subtree ends
            # where its own end tag arrives, whatever is nested inside it.
            if not self._sanitizer.is_void(tag):
                self.strip_depth += 1
            return
        if self._sanitizer.is_chrome(tag, attrs):
            if not self._sanitizer.is_void(tag):
                self.strip_depth = 1
            return
        self._close_implied_by(tag)
        self.out.append(self._sanitizer.start_tag(tag, attrs))
        if not self._sanitizer.is_void(tag):
            self.open.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.done or self.depth == 0 or self.strip_depth:
            return
        if self._sanitizer.is_chrome(tag, attrs):
            return
        self.out.append(self._sanitizer.start_tag(tag, attrs, self_closing=True))

    def handle_endtag(self, tag: str) -> None:
        if self.done or self.depth == 0:
            return
        if self.strip_depth:
            if not self._sanitizer.is_void(tag):
                self.strip_depth -= 1
            return
        if self._sanitizer.is_void(tag):
            return
        if tag not in self.open:
            # A stray end tag closing nothing this walk opened. Emitting it would put a
            # mismatched tag into the fragment; dropping it costs nothing, because there
            # is no open element it could have been meant for.
            return
        # Close everything this end tag implicitly closes, innermost first. For
        # `<ul><li>one<li>two</ul>` the `</ul>` arrives with two <li>s still open, and
        # both get the end tag HTML let the author omit.
        #
        # `while True` rather than `while self.open`, because the check above already
        # proved `tag` is on the stack: the loop always leaves through one of the two
        # returns below, and a condition that can never be false would be a branch no
        # test could ever take.
        while True:
            unclosed = self.open.pop()
            if not self.open:
                # The content element itself: its end tag ends the capture and is never
                # emitted, because the chapter is its CONTENTS, not the element.
                self.done = True
                return
            self.out.append(self._sanitizer.end_tag(unclosed))
            if unclosed == tag:
                return

    def close(self) -> None:
        """Finish the walk, closing anything the document left open.

        A truncated page -- or one whose final elements simply omit their end tags --
        would otherwise leave the fragment unbalanced, which fails the XHTML parse for
        the whole package rather than for the one chapter. Closing them here is the same
        repair `handle_endtag` makes, applied at end of input.
        """
        super().close()
        while len(self.open) > 1 and not self.done:
            self.out.append(self._sanitizer.end_tag(self.open.pop()))
        self.open.clear()

    def handle_data(self, data: str) -> None:
        self._emit(self._sanitizer.text(data))

    def handle_entityref(self, name: str) -> None:
        self._emit(self._sanitizer.entity_reference(name))

    def handle_charref(self, name: str) -> None:
        self._emit(self._sanitizer.character_reference(name))


def extract_main(page_html: str, sanitizer: ChapterSanitizerInterface | None = None) -> str:
    """The chapter body from a built page, as XHTML an EPUB reader will open.

    Anchored on <main>, <article>, or any element carrying role="main" -- the last is
    what the ProperDocs theme actually emits, discovered when the first dogfooded
    deploy refused every page. Site chrome is dropped because a book has no runtime and
    a printed page has nothing to click, and the markup that survives is rewritten for
    XML: a chapter is parsed as XHTML, and one `&para;` from a permalink anchor
    invalidates the entire package.

    ADR-0016 method of last resort, and the reason: the only decision a caller would ever
    vary here is already an injected seam -- `ChapterSanitizerInterface` judges what
    survives and writes it down -- and the walk itself is `MainExtractor`, a class with
    its interface beside it. A class wrapping these three lines would carry no state
    between calls and expose one method taking exactly these arguments: a namespace, not
    an object.
    """
    parser: MainExtractorInterface = MainExtractor(
        sanitizer if sanitizer is not None else ChapterSanitizer()
    )
    parser.feed(page_html)
    # Nothing more is coming, so anything still open is an omitted end tag rather than a
    # continuation. Closing before reading is what keeps the fragment parseable.
    parser.close()
    body = "".join(parser.out).strip()
    if not body:
        raise BookError(
            'page has no <main>, <article>, or role="main" element to take a chapter from'
        )
    return body


class TableOfContents:
    """The chapters as the nav groups them: its section headings, with what each holds.

    The contents used to be one flat column of forty-odd chapters, the nav's own grouping
    (Guides, Reference, Architecture > Decision records, the Governance canon) nowhere to
    be seen. One table now serves both the EPUB navigation document and the print
    interior's contents page, so the two cannot disagree.

    Its seam is declared beside it in `vibey_gh/interfaces/book_interface.py`, per
    ADR-0016.
    """

    def __init__(self, chapters: Sequence[BookChapterInterface]) -> None:
        self._chapters = chapters

    @staticmethod
    def opening(previous: Sequence[str], current: Sequence[str]) -> tuple[str, ...]:
        """The section headings `current` opens that `previous` did not already have open.

        A heading repeated later in the nav, after another section intervened, opens
        again: the nav order is the book's order, and it is never regrouped.
        """
        shared = 0
        while shared < min(len(previous), len(current)) and previous[shared] == current[shared]:
            shared += 1
        return tuple(current[shared:])

    def ordered_list(self, link: Callable[[BookChapterInterface], str]) -> str:
        """Nested <ol>s in the EPUB 3 navigation document's shape.

        A section is a `<li>` whose first child is a `<span>` heading and whose second is
        the `<ol>` it heads -- the form the EPUB specification requires of an unlinked
        heading -- and a section is only opened when a chapter follows, so no heading is
        ever left without the list it must be followed by.
        """
        e = html_lib.escape
        lines = ["<ol>"]
        open_path: tuple[str, ...] = ()
        for chapter in self._chapters:
            opened = self.opening(open_path, chapter.sections)
            still_open = len(chapter.sections) - len(opened)
            lines.extend("</ol></li>" for _ in range(len(open_path) - still_open))
            lines.extend(f"<li><span>{e(heading)}</span><ol>" for heading in opened)
            lines.append(f'<li><a href="{e(link(chapter))}">{e(chapter.title)}</a></li>')
            open_path = chapter.sections
        lines.extend("</ol></li>" for _ in open_path)
        lines.append("</ol>")
        return "\n".join(lines)


# The standard KDP paperback interior, lifted from a generator that has already passed
# KDP's printable-file review: a 6in x 9in trim, 0.75in top and bottom, 0.5in on both
# sides, an 11pt serif body at 1.5 leading. Each is a constructor parameter of
# `PrintInterior` and a `vibey-gh book` flag (ADR-0018); these are only the values nobody
# has to type.
#
# The inside margin -- the gutter -- is the one KDP scales with the book's thickness,
# because a thicker spine swallows more of every page into the binding. Its published
# minimums, by final page count: 24-150 pages 0.375in, 151-300 0.5in, 301-500 0.625in,
# 501-700 0.75in, 701-828 0.875in; outside, top and bottom need at least 0.25in without
# bleed. The 0.5in default is valid for 151-300 pages, and a longer interior needs its
# tier passed as `gutter`. The page count is only known once the browser has printed,
# so the tier is the caller's to choose -- it is not guessed here.
DEFAULT_TRIM_WIDTH = "6in"
DEFAULT_TRIM_HEIGHT = "9in"
DEFAULT_MARGIN_TOP = "0.75in"
DEFAULT_MARGIN_BOTTOM = "0.75in"
DEFAULT_MARGIN_OUTSIDE = "0.5in"
DEFAULT_GUTTER = "0.5in"
DEFAULT_FONT_SIZE = "11pt"
DEFAULT_LINE_HEIGHT = "1.5"
DEFAULT_FONT_FAMILY = "Georgia, serif"
DEFAULT_CODE_FONT_FAMILY = "monospace"
# Characters of a chapter title the running head keeps before cutting at a word. A head
# is one line of 9pt italic across the text block; an ADR title runs past 100 characters.
DEFAULT_RUNNING_HEAD_LENGTH = 60

# A length the interior accepts: a non-negative number with an optional CSS unit. Checked
# rather than passed through, because each one is interpolated into the stylesheet and a
# stray `;` or `}` in a flag would silently rewrite the rules around it.
_LENGTH = re.compile(r"(\d+(?:\.\d+)?|\.\d+)(in|mm|cm|q|pt|pc|px|em|rem|%)?", re.IGNORECASE)
_TRIM = re.compile(r"\s*(.+?)\s*[x×]\s*(\d.*|\.\d.*)", re.IGNORECASE)
# What a font stack may not contain for the same reason: it would end the declaration,
# the rule, or the <style> element it is written into.
_UNSAFE_IN_CSS = re.compile(r"[{};<>\\\x00-\x1f\x7f]")
# What a CSS string literal has to escape -- its own quote and backslash, and `<` and `>`
# so a title can never close the <style> element it is written into.
_CSS_STRING_ESCAPE = re.compile(r"[\"\\<>\x00-\x1f\x7f]")
# A <code> element and its contents, and inside those contents the characters a path or
# an identifier may break after -- where a technical typesetter would break one.
_CODE_ELEMENT = re.compile(r"(<code\b[^>]*>)(.*?)(</code>)", re.DOTALL)
_MARKUP = re.compile(r"(<[^>]*>)")
_CODE_BREAK_AFTER = re.compile(r"([/._:])(?=\w)")


class PrintInterior:
    """The paperback interior as one HTML document, for a headless browser to print.

    What a printed book needs and a web page never had: recto and verso pages with the
    gutter mirrored onto the binding side; a folio (page number) at the foot of every
    body page and none on the front matter or part openers; the chapter's title as the
    running head of its recto pages and its section's on the verso; justified,
    hyphenated text with widows and orphans held to three lines; and code blocks, tables
    and figures kept whole on a page wherever they fit.

    Chrome cannot copy a heading into a page margin (`string-set` and `running()` are
    not implemented), so every chapter gets a named page of its own whose margin boxes
    carry its title as a literal string. The same mechanism makes each chapter open on a
    fresh page.

    Its seam is declared beside it in `vibey_gh/interfaces/book_interface.py`, per
    ADR-0016.
    """

    def __init__(
        self,
        *,
        trim_width: str = DEFAULT_TRIM_WIDTH,
        trim_height: str = DEFAULT_TRIM_HEIGHT,
        margin_top: str = DEFAULT_MARGIN_TOP,
        margin_bottom: str = DEFAULT_MARGIN_BOTTOM,
        margin_outside: str = DEFAULT_MARGIN_OUTSIDE,
        gutter: str = DEFAULT_GUTTER,
        font_size: str = DEFAULT_FONT_SIZE,
        line_height: str = DEFAULT_LINE_HEIGHT,
        font_family: str = DEFAULT_FONT_FAMILY,
        code_font_family: str = DEFAULT_CODE_FONT_FAMILY,
        running_head_length: int = DEFAULT_RUNNING_HEAD_LENGTH,
    ) -> None:
        self.trim_width = self._length("trim width", trim_width, "in")
        self.trim_height = self._length("trim height", trim_height, "in")
        self.margin_top = self._length("top margin", margin_top, "in")
        self.margin_bottom = self._length("bottom margin", margin_bottom, "in")
        self.margin_outside = self._length("outside margin", margin_outside, "in")
        self.gutter = self._length("gutter", gutter, "in")
        self.font_size = self._length("font size", font_size, "pt")
        self.line_height = self._length("line height", line_height, "")
        self.font_family = self._font_stack("font family", font_family)
        self.code_font_family = self._font_stack("code font family", code_font_family)
        if running_head_length < 1:
            raise BookError(f"running head length {running_head_length} must be at least 1")
        self.running_head_length = running_head_length

    @staticmethod
    def parse_trim(text: str) -> tuple[str, str]:
        """`6x9`, `5.5 x 8.5`, `148mmx210mm` -> (width, height). Bare numbers are inches."""
        match = _TRIM.fullmatch(text)
        if match is None:
            raise BookError(f"trim {text!r} is not WIDTHxHEIGHT, such as 6x9 or 148mmx210mm")
        width = PrintInterior._length("trim width", match.group(1), "in")
        height = PrintInterior._length("trim height", match.group(2), "in")
        return width, height

    @staticmethod
    def _length(name: str, value: str, bare_unit: str) -> str:
        match = _LENGTH.fullmatch(value.strip())
        if match is None:
            raise BookError(f"{name} {value!r} is not a length such as 0.5in, 12mm or 11pt")
        number, unit = match.groups()
        return f"{number}{(unit or bare_unit).lower()}"

    @staticmethod
    def _font_stack(name: str, value: str) -> str:
        stack = value.strip()
        if not stack or _UNSAFE_IN_CSS.search(stack):
            raise BookError(
                f"{name} {value!r} is not a CSS font stack"
                " (no braces, semicolons, angle brackets or backslashes)"
            )
        return stack

    def css(self) -> str:
        font, outside, gutter = self.font_family, self.margin_outside, self.gutter
        return "\n".join(
            (
                # The page box. A recto (right-hand) page binds on its left edge and a
                # verso on its right, so the gutter mirrors onto whichever side is inside;
                # Chrome makes the first page a recto, as a printed book's is.
                (
                    f"@page{{size:{self.trim_width} {self.trim_height};"
                    f"margin:{self.margin_top} {outside} {self.margin_bottom} {gutter};"
                    f"@top-center{{font-family:{font};font-size:9pt;font-style:italic}}"
                    f"@bottom-center{{content:counter(page);font-family:{font};font-size:9pt}}}}"
                ),
                f"@page :right{{margin-left:{gutter};margin-right:{outside}}}",
                f"@page :left{{margin-left:{outside};margin-right:{gutter}}}",
                # Front matter and part openers carry no folio and no running head.
                "@page front{@bottom-center{content:none}}",
                "@page part{@bottom-center{content:none}}",
                (
                    f"body{{font-family:{font};font-size:{self.font_size};"
                    f"line-height:{self.line_height};margin:0;text-align:justify;"
                    "hyphens:auto;-webkit-hyphens:auto;orphans:3;widows:3;overflow-wrap:break-word}"
                ),
                (
                    "h1,h2,h3,h4,h5,h6{text-align:left;hyphens:manual;-webkit-hyphens:manual;"
                    "break-after:avoid;break-inside:avoid}"
                ),
                "h1{font-size:20pt;line-height:1.2;margin:0 0 .75em}",
                "h2{font-size:14pt;margin:1.5em 0 .75em}",
                "h3{font-size:12pt;margin:1.25em 0 .5em}",
                (
                    f"pre,code,kbd,samp{{font-family:{self.code_font_family};"
                    "hyphens:manual;-webkit-hyphens:manual}"
                ),
                "code,kbd,samp{font-size:.9em}",
                "pre code{font-size:inherit}",
                (
                    "pre{white-space:pre-wrap;overflow-wrap:anywhere;text-align:left;"
                    "font-size:8.5pt;background:#f4f4f4;padding:.6em}"
                ),
                "pre,table,figure,img,svg{break-inside:avoid}",
                "table{border-collapse:collapse;width:100%;font-size:9.5pt}",
                # `break-word`, not `anywhere`: only `anywhere` lowers a cell's minimum
                # width, and an auto-width table then squeezes a narrow column down to a
                # letter a line ("Documen / t").
                (
                    "td,th{border:1pt solid #666;padding:.3em;text-align:left;vertical-align:top;"
                    "overflow-wrap:break-word}"
                ),
                "img,svg{max-width:100%;height:auto}",
                # Nothing on a printed page is clickable: a link is its words, in the ink
                # the rest of the sentence is printed in.
                "a{color:inherit;text-decoration:none}",
                ".chapter,.part{break-before:page}",
                ".title-page,.copyright-page,.toc{page:front;break-after:page}",
                ".part{page:part;break-after:page;text-align:center;padding-top:2.5in}",
                ".part h1{font-size:24pt;text-align:center}",
                ".part p{font-size:14pt;font-style:italic;text-align:center}",
                ".title-page{text-align:center;padding-top:2.5in}",
                ".title-page h1{font-size:24pt;text-align:center}",
                ".copyright-page{font-size:9pt;padding-top:5in;text-align:left}",
                ".toc ol{list-style:none;padding-left:0;text-align:left}",
                ".toc ol ol{padding-left:1.25em}",
                ".toc li{margin:.2em 0}",
                ".toc span{display:block;font-weight:bold;margin-top:.6em}",
            )
        )

    def render(
        self,
        meta: Mapping[str, str],
        chapters: Sequence[BookChapterInterface],
        bodies: Mapping[str, str],
        year: int,
    ) -> str:
        e = html_lib.escape
        rules = [self.css()]
        body: list[str] = []
        previous: tuple[str, ...] = ()
        for number, chapter in enumerate(chapters, start=1):
            opened = TableOfContents.opening(previous, chapter.sections)
            if opened:
                headings = f"<h1>{e(opened[0])}</h1>" + "".join(
                    f"<p>{e(heading)}</p>" for heading in opened[1:]
                )
                body.append(f'<section class="part">{headings}</section>')
            previous = chapter.sections
            page = f"c{number}"
            verso = chapter.sections[-1] if chapter.sections else meta["title"]
            rules.append(
                f"@page {page}:left{{@top-center{{content:{self._running_head(verso)}}}}}\n"
                f"@page {page}:right{{@top-center{{content:"
                f"{self._running_head(chapter.title)}}}}}"
            )
            body.append(
                f'<section class="chapter" id="{chapter.slug}" style="page:{page}">'
                f"{self._breakable(bodies[chapter.slug])}</section>"
            )
        contents = TableOfContents(chapters).ordered_list(lambda chapter: f"#{chapter.slug}")
        subtitle = f"<p>{e(meta['subtitle'])}</p>" if meta.get("subtitle") else ""
        stylesheet = "\n".join(rules)
        return (
            "<!DOCTYPE html>\n"
            f'<html lang="{e(meta.get("language", "en"))}"><head><meta charset="utf-8">'
            f"<title>{e(meta['title'])}</title><style>\n{stylesheet}\n</style></head><body>\n"
            f'<section class="title-page"><h1>{e(meta["title"])}</h1>{subtitle}'
            f"<p>{e(meta['author'])}</p></section>\n"
            f'<section class="copyright-page"><p>Copyright &#169; {year} {e(meta["author"])}.'
            f" All rights reserved.</p><p>{e(meta.get('publisher', meta['author']))}</p>"
            "</section>\n"
            f'<nav class="toc"><h1>Table of Contents</h1>\n{contents}\n</nav>\n'
            + "\n".join(body)
            + "\n</body></html>\n"
        )

    @staticmethod
    def _breakable(body: str) -> str:
        """`body` with a line-break opportunity after each `/`, `.`, `_` and `:` in code.

        A path such as `infrastructure/config_loader.py` has no break opportunity in it,
        so justified text had to stretch the whole line before it into a row of gaps
        ("tested                    in"). A `<wbr>` breaks nothing unless the line needs
        it, and only text between tags is touched -- never a tag or its attributes.
        """

        def one(element: re.Match[str]) -> str:
            pieces = _MARKUP.split(element.group(2))
            pieces[::2] = [_CODE_BREAK_AFTER.sub(r"\1<wbr>", text) for text in pieces[::2]]
            return element.group(1) + "".join(pieces) + element.group(3)

        return _CODE_ELEMENT.sub(one, body)

    def _running_head(self, text: str) -> str:
        """`text` as a CSS string, cut at a word to fit one line of the page head."""
        if len(text) > self.running_head_length:
            cut = text[: self.running_head_length].rsplit(" ", 1)[0]
            text = cut.rstrip(" ,;:—–-") + "…"
        return '"' + _CSS_STRING_ESCAPE.sub(lambda m: f"\\{ord(m.group()):x} ", text) + '"'


DEFAULT_EPUB_CSS = """body{font-family:Georgia,serif;line-height:1.55;margin:1em}
h1,h2,h3{font-family:Georgia,serif;line-height:1.2}
pre{white-space:pre-wrap;font-size:.85em;background:#f4f4f4;padding:.75em}
code{font-size:.9em}
table{border-collapse:collapse;width:100%}
td,th{border:1px solid #999;padding:.35em;text-align:left;vertical-align:top}
nav ol{list-style:none;padding-left:1em}
nav span{display:block;font-weight:bold;margin-top:.5em}
"""

# The namespace every derived book identifier lives in. Fixed for good: changing it would
# hand every book this package has ever built a new identity on its next build.
_BOOK_IDENTITY_NAMESPACE = uuid.uuid5(
    uuid.NAMESPACE_URL, "https://github.com/the-vibey-project/vibey/tree/main/src/vibey_tools/gh"
)


class EpubPackage:
    """The EPUB 3 container: package document, navigation, and one XHTML per chapter.

    Its seam is declared beside it in `vibey_gh/interfaces/book_interface.py`, per
    ADR-0016.
    """

    def __init__(self, *, stylesheet: str = DEFAULT_EPUB_CSS) -> None:
        self._stylesheet = stylesheet

    def identifier(self, meta: Mapping[str, str]) -> str:
        """The package's `dc:identifier`: stable across builds of the same book.

        It used to be a fresh random UUID on every build, so every release looked to a
        reader -- and to a library that syncs highlights and positions by identifier --
        like a different book. EPUB wants the unique identifier to outlive revisions; the
        release is told apart by `dcterms:modified`. So it is derived from what makes the
        book this book -- title, author, language and edition -- and a new edition, or a
        translation, is a new identity. An explicit `identifier` (an ISBN URN, once one
        is chosen) is used as given.
        """
        explicit = meta.get("identifier", "")
        if explicit:
            return explicit
        identity = "\x1f".join(
            (
                meta.get("title", ""),
                meta.get("author", ""),
                meta.get("language", "en"),
                meta.get("edition", ""),
            )
        )
        return f"urn:uuid:{uuid.uuid5(_BOOK_IDENTITY_NAMESPACE, identity)}"

    def write(
        self,
        path: Path,
        meta: Mapping[str, str],
        chapters: Sequence[BookChapterInterface],
        bodies: Mapping[str, str],
        now: datetime.datetime,
    ) -> None:
        language = meta.get("language", "en")
        with zipfile.ZipFile(path, "w") as z:
            # The EPUB contract: `mimetype` first, STORED, no extra field — readers sniff
            # bytes 30..58 of the archive for this exact string.
            z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
            z.writestr(
                "META-INF/container.xml",
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<container version="1.0"'
                ' xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
                '<rootfiles><rootfile full-path="OEBPS/content.opf"'
                ' media-type="application/oebps-package+xml"/></rootfiles>\n'
                "</container>\n",
            )
            z.writestr("OEBPS/content.opf", self._package(meta, chapters, now))
            z.writestr("OEBPS/style.css", self._stylesheet)
            z.writestr("OEBPS/toc.xhtml", self._navigation(chapters, language))
            for chapter in chapters:
                z.writestr(
                    f"OEBPS/{chapter.slug}.xhtml",
                    self._document(chapter.title, bodies[chapter.slug], language),
                )

    def _document(self, title: str, body: str, language: str) -> str:
        """One XHTML content document, carrying the book's language for its readers.

        `xml:lang` is what a reading system hyphenates and a screen reader pronounces by;
        without it every chapter is in no language at all.
        """
        e = html_lib.escape
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
            f' xml:lang="{e(language)}" lang="{e(language)}">\n'
            f"<head><title>{e(title)}</title>"
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
            f"<body>{body}</body>\n</html>\n"
        )

    def _navigation(self, chapters: Sequence[BookChapterInterface], language: str) -> str:
        """The navigation document: the grouped contents, and the landmarks readers jump by.

        Landmarks are how a reading system finds "go to the beginning" and "go to the
        contents" -- without them, a Kindle opens the book on whatever the spine lists
        first and has nothing to offer from its menu.
        """
        e = html_lib.escape
        contents = TableOfContents(chapters).ordered_list(lambda chapter: f"{chapter.slug}.xhtml")
        first = chapters[0]
        return self._document(
            "Table of Contents",
            '<nav epub:type="toc" id="toc"><h1>Table of Contents</h1>\n'
            f"{contents}\n</nav>\n"
            '<nav epub:type="landmarks" id="landmarks" hidden="hidden"><h2>Landmarks</h2><ol>'
            '<li><a epub:type="toc" href="toc.xhtml">Table of Contents</a></li>'
            f'<li><a epub:type="bodymatter" href="{first.slug}.xhtml">{e(first.title)}</a></li>'
            "</ol></nav>",
            language,
        )

    def _package(
        self,
        meta: Mapping[str, str],
        chapters: Sequence[BookChapterInterface],
        now: datetime.datetime,
    ) -> str:
        manifest = [
            '<item id="css" href="style.css" media-type="text/css"/>',
            '<item id="toc" href="toc.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        ]
        spine = ['<itemref idref="toc"/>']
        for chapter in chapters:
            manifest.append(
                f'<item id="{chapter.slug}" href="{chapter.slug}.xhtml"'
                ' media-type="application/xhtml+xml"/>'
            )
            spine.append(f'<itemref idref="{chapter.slug}"/>')
        e = html_lib.escape
        language = e(meta.get("language", "en"))
        published = meta.get("date") or now.date().isoformat()
        description = (
            f"<dc:description>{e(meta['description'])}</dc:description>\n"
            if meta.get("description")
            else ""
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid"'
            f' xml:lang="{language}">\n'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f'<dc:identifier id="uid">{e(self.identifier(meta))}</dc:identifier>\n'
            f"<dc:title>{e(meta['title'])}</dc:title>\n"
            f"<dc:creator>{e(meta['author'])}</dc:creator>\n"
            f"<dc:language>{language}</dc:language>\n"
            f"<dc:date>{e(published)}</dc:date>\n"
            f"{description}"
            f"<dc:publisher>{e(meta.get('publisher', meta['author']))}</dc:publisher>\n"
            f'<meta property="dcterms:modified">{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</meta>\n'
            "</metadata>\n"
            "<manifest>\n" + "\n".join(manifest) + "\n</manifest>\n"
            "<spine>\n" + "\n".join(spine) + "\n</spine>\n"
            "</package>\n"
        )


# A BCP 47 language tag, loosely: what `lang` and `xml:lang` will be given verbatim.
_LANGUAGE_TAG = re.compile(r"[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*")


def build_book(
    site_dir: Path,
    config_text: str,
    output_dir: Path,
    meta: dict[str, str],
    sanitizer: ChapterSanitizerInterface | None = None,
    *,
    interior: PrintInteriorInterface | None = None,
    package: EpubPackageInterface | None = None,
) -> dict[str, Path]:
    """Build book.epub and book-print.html from a built site and its nav.

    Returns the paths written. Raises BookError with the missing piece named when a nav
    chapter has no built page — a book silently missing a chapter is worse than no book.
    `interior` is the print layout (its trim, margins and type are its constructor's
    parameters) and `package` the EPUB writer; both default to the standard ones.

    ADR-0016 method of last resort, and the reason: this is a one-shot pipeline with
    nothing to remember between calls, and every substitutable decision in it -- how a
    chapter's markup is judged and rewritten, how the interior is laid out, how the EPUB
    is written -- is an injected seam. A class around the rest would take these same
    arguments in a constructor and offer one method. It is also the package's published
    entry point, called from `cli.py`, so the shape is load-bearing past this module.
    """
    if "title" not in meta or not meta["title"]:
        raise BookError("book metadata needs at least a title")
    if "author" not in meta or not meta["author"]:
        raise BookError("book metadata needs an author")
    language = meta.get("language", "en")
    if not _LANGUAGE_TAG.fullmatch(language):
        raise BookError(f"language {language!r} is not a language tag such as en or en-GB")
    now = datetime.datetime.now(datetime.UTC)
    published = now.date()
    if meta.get("date"):
        try:
            published = datetime.date.fromisoformat(meta["date"])
        except ValueError:
            raise BookError(
                f"date {meta['date']!r} is not a calendar date such as 2026-09-18"
            ) from None
    chapters = chapters_from_nav(config_text)
    bodies: dict[str, str] = {}
    for chapter in chapters:
        page = site_dir / chapter.site_page
        if not page.is_file():
            raise BookError(f"nav names {chapter.source} but the built site has no {page}")
        bodies[chapter.slug] = extract_main(page.read_text(encoding="utf-8"), sanitizer)

    output_dir.mkdir(parents=True, exist_ok=True)
    epub_path = output_dir / "book.epub"
    epub = package if package is not None else EpubPackage()
    epub.write(epub_path, {**meta, "date": published.isoformat()}, chapters, bodies, now)

    layout = interior if interior is not None else PrintInterior()
    print_path = output_dir / "book-print.html"
    print_path.write_text(layout.render(meta, chapters, bodies, published.year), encoding="utf-8")
    return {"epub": epub_path, "print_html": print_path}
