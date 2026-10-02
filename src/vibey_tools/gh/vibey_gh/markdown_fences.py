# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Find the fenced code block a Markdown document never closes, the way CommonMark reads it.

The documentation deep scan failed every night from 2026-09-28 on
`docs/plans/qwenstorm-3.0.0/specs/seo-cli-reference-examples.md`, a file every CommonMark
parser renders correctly. Its check was `text.count("```") % 2`: the file writes a fence
inside inline code spans (`` ` ```bash ` ``) and inside a regex in a fenced Python block
(`r"^```bash$"`), and none of those is a fence delimiter, so the count came out odd.

What a fence is, per CommonMark 0.31 (section 4.5), and what this reads:

- An opener is a run of at least three backticks or three tildes, indented at most three
  columns past its container; a backtick opener's info string holds no backtick.
- Only a closer ends it: a line holding nothing but a run of the SAME character, at least
  as long as the opener, indented at most three columns. A shorter run, the other
  character, or a run with text after it is content.
- A fence belongs to the block quotes and list items it opened in, and ends where they
  end. That is not an error, and is not reported: the fence that matters is the one that
  runs on to the end of the document and swallows everything after it.
- Block quotes and list items are followed the way CommonMark follows containers, lazy
  paragraph continuation included, and HTML blocks (sections 4.6) are skipped, because a
  fence written inside `<pre>` or an HTML comment is raw HTML, not a fence.

Indented code needs no rule of its own: four columns of indentation is never an opener.
Not modelled: link reference definitions and the finer points of tab stops inside a
container (a tab is expanded to the next multiple of four); neither decides whether a
fence closes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from vibey_gh.interfaces.markdown_fences_interface import MarkdownFencesInterface, UnclosedFence

__all__ = ["MarkdownFences", "UnclosedFence"]

_QUOTE = re.compile(r" {0,3}> ?")
# A bullet, or an ordered marker of up to nine digits, followed by a space or the line end.
_ITEM = re.compile(r"(?P<indent> {0,3})(?P<marker>[-+*]|(?P<number>\d{1,9})[.)])(?= |$)")
_OPEN = re.compile(r" {0,3}(?P<run>`{3,}|~{3,})(?P<info>.*)$")
_CLOSE = re.compile(r" {0,3}(?P<run>`{3,}|~{3,}) *$")
_THEMATIC = re.compile(r" {0,3}(?P<char>[-*_])(?: *(?P=char)){2,} *$")
_HEADING = re.compile(r" {0,3}#{1,6}(?: |$)")
# HTML block start conditions 1-5, each with the text that ends it (on any line, this one
# included); 6 and 7 end at the first blank line.
_HTML_ENDS = (
    (
        re.compile(r" {0,3}<(?:pre|script|style|textarea)(?:[ >]|$)", re.IGNORECASE),
        r"</(?:pre|script|style|textarea)>",
    ),
    (re.compile(r" {0,3}<!--"), r"-->"),
    (re.compile(r" {0,3}<\?"), r"\?>"),
    (re.compile(r" {0,3}<![A-Za-z]"), r">"),
    (re.compile(r" {0,3}<!\[CDATA\["), r"\]\]>"),
)
_HTML_BLOCK_TAGS = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd"
    "|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset"
    "|h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav"
    "|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th"
    "|thead|title|tr|track|ul"
)
_HTML_BLOCK = re.compile(rf" {{0,3}}</?(?:{_HTML_BLOCK_TAGS})(?:[ >]|/>|$)", re.IGNORECASE)
_ATTRIBUTE = r"""\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"'=<>`]+|'[^']*'|"[^"]*"))?"""
_HTML_TAG = re.compile(
    rf" {{0,3}}(?:<[A-Za-z][A-Za-z0-9-]*(?:{_ATTRIBUTE})*\s*/?>|</[A-Za-z][A-Za-z0-9-]*\s*>)\s*$"
)


@dataclass
class _Block:
    """The leaf block a line is inside: a fence, or an HTML block (`end` is the text that
    closes it, `None` for one a blank line closes)."""

    fence: UnclosedFence | None = None
    char: str = ""
    end: re.Pattern[str] | None = None


class MarkdownFences(MarkdownFencesInterface):
    """Implements `MarkdownFencesInterface`."""

    def unclosed(self, text: str) -> UnclosedFence | None:
        # Each open container: ("quote", 0), or ("item", the columns its content starts at).
        stack: list[tuple[str, int]] = []
        block: _Block | None = None
        paragraph = False
        for number, raw in enumerate(text.splitlines(), 1):
            line = raw.expandtabs(4)
            rest, matched = self._continue(stack, line)
            if block is not None:
                if matched == len(stack):
                    if not self._ends(block, rest):
                        continue
                    block = None
                    continue
                # A container ended under the block, so the block ended with it.
                block = None
            if matched < len(stack):
                if not rest.strip():
                    del stack[matched:]
                    paragraph = False
                    continue
                if paragraph and not self._interrupts(rest):
                    continue  # lazy continuation: every container stays open
                del stack[matched:]
                paragraph = False  # it was inside a container that just ended
            rest, opened = self._open(stack, rest, paragraph)
            paragraph = paragraph and not opened
            block, paragraph = self._leaf(rest, number, paragraph)
        return block.fence if block is not None else None

    @staticmethod
    def _continue(stack: list[tuple[str, int]], line: str) -> tuple[str, int]:
        """What is left of `line` after the containers it continues, and how many it does."""
        pos = 0
        for matched, (kind, width) in enumerate(stack):
            rest = line[pos:]
            if kind == "quote":
                quote = _QUOTE.match(rest)
                if quote is None:
                    return rest, matched
                pos += quote.end()
            elif rest.strip():
                if len(rest) - len(rest.lstrip(" ")) < width:
                    return rest, matched
                pos += width
        return line[pos:], len(stack)

    @staticmethod
    def _ends(block: _Block, rest: str) -> bool:
        """Whether `rest` closes the fence or HTML block it is inside."""
        if block.fence is not None:
            close = _CLOSE.match(rest)
            return (
                close is not None
                and close["run"][0] == block.char
                and len(close["run"]) >= len(block.fence.marker)
            )
        if block.end is None:
            return not rest.strip()
        return block.end.search(rest) is not None

    @staticmethod
    def _item(rest: str, paragraph: bool) -> tuple[int, str] | None:
        """(the item's content width, what follows the marker) when `rest` opens a list
        item here, or `None` -- including a marker that may not interrupt a paragraph."""
        item = _ITEM.match(rest)
        if item is None or _THEMATIC.match(rest):
            return None
        after = rest[item.end() :]
        if paragraph and (not after.strip() or item["number"] not in (None, "1")):
            return None
        spaces = len(after) - len(after.lstrip(" "))
        gap = spaces if after.strip() and spaces <= 4 else 1
        return item.end() + gap, after[gap:]

    def _interrupts(self, rest: str) -> bool:
        """Whether `rest` starts a block, so it cannot be a paragraph's lazy continuation.

        Asked only of a line that did not continue every container, so the paragraph is
        not what it would be read inside: any block start counts, an ordered item numbered
        other than 1 and a lone HTML tag included (cmark's `open_new_blocks`)."""
        return bool(
            _QUOTE.match(rest)
            or _OPEN.match(rest)
            or _HEADING.match(rest)
            or _THEMATIC.match(rest)
            or _HTML_BLOCK.match(rest)
            or _HTML_TAG.match(rest)
            or any(start.match(rest) for start, _ in _HTML_ENDS)
            or self._item(rest, False)
        )

    def _open(self, stack: list[tuple[str, int]], rest: str, paragraph: bool) -> tuple[str, bool]:
        """Push every container `rest` opens; what is left of it, and whether any opened."""
        opened = False
        while True:
            quote = _QUOTE.match(rest)
            if quote is not None:
                stack.append(("quote", 0))
                rest = rest[quote.end() :]
            else:
                item = self._item(rest, paragraph and not opened)
                if item is None:
                    return rest, opened
                stack.append(("item", item[0]))
                rest = item[1]
            opened = True

    @staticmethod
    def _leaf(rest: str, number: int, paragraph: bool) -> tuple[_Block | None, bool]:
        """The fence or HTML block `rest` opens, if any, and whether a paragraph goes on."""
        if not rest.strip():
            return None, False
        fence = _OPEN.match(rest)
        if fence is not None and not (fence["run"][0] == "`" and "`" in fence["info"]):
            run = fence["run"]
            return _Block(fence=UnclosedFence(number, run), char=run[0]), False
        for start, end in _HTML_ENDS:
            if start.match(rest):
                closing = re.compile(end, re.IGNORECASE)
                return (None if closing.search(rest) else _Block(end=closing)), False
        if _HTML_BLOCK.match(rest) or (not paragraph and _HTML_TAG.match(rest)):
            return _Block(), False
        if _HEADING.match(rest) or _THEMATIC.match(rest):
            return None, False
        # Four columns in, outside a paragraph, is indented code: it never continues one.
        return None, paragraph or len(rest) - len(rest.lstrip(" ")) < 4
