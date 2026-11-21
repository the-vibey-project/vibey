# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hub and ledger text made safe to show to an ACP client (SP-ACP, one rule for all of it).

ACP clients render message text, tool-call titles and tool-call content as Markdown. Text that
workers, models or other people wrote -- ledger events, gate prompts and labels, project names
and paths, the hub chat's reply (which quotes all of those), a refusal's body, a tool's result
-- is shown through this class and nothing else, so it reads as text:

- **Whole characters only.** Every character Python does not count as printable (controls,
  format and bidi characters, line and paragraph separators) becomes a space. In a `block`,
  line breaks are kept; everything else is one line.
- **Cut.** At most `limit` characters as written, ending in "..." when it was cut. The cut
  comes first, so it never splits an escape; defanging and escaping can then make the text a
  little longer than `limit`.
- **No autolinks.** GFM links a URL, a `www.` host or an e-mail address with no Markdown at all,
  so those forms are broken with a visible bracket (`AUTOLINK_DEFANGS`): `https[:]//`,
  `mailto[:]`, `xmpp[:]`, `www[.]` and `name[@]host`. A bare domain (`example.com`) is not
  caught; a client may still choose to link it.
- **No Markdown.** Every character that could open a link, image, emphasis, code span or
  fence, heading, table cell, strikethrough, HTML tag or entity (`MARKDOWN_SPECIAL`) is
  backslash-escaped. At the start of a line (`line`, and each line of a `block`), leading
  spaces are dropped (no indented code block) and a list, quote or setext marker (`-`, `+`,
  `=`, `1.`) is escaped too.
- **A block keeps its lines.** Each line ends in a hard break, so the client shows the lines as
  they were written; a blank line stays a paragraph break.
- **Code is fenced.** A tool's result (JSON, or the hub's raw answer) is shown as a code block
  (`code`): nothing inside one renders as Markdown or becomes a link, and the fence is longer
  than any run of backticks in the text, so the text cannot close it. Its lines keep their
  indentation; non-printable characters still become spaces.

Pure: no I/O. Declared by `interfaces/untrusted_text_interface.py`.
"""

import re
from collections.abc import Sequence
from typing import Any, Final

ELLIPSIS: Final = "..."
MARKDOWN_SPECIAL: Final = frozenset("\\`*_[]()<>!#|~&")
"""Escaped everywhere in untrusted text: what opens a link, image, emphasis, code span or
fence, heading, table cell, strikethrough, HTML tag or entity, and the escape itself."""
AUTOLINK_DEFANGS: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"(?i)(mailto|xmpp):"), r"\1[:]"),
    (re.compile(r"://"), "[:]//"),
    (re.compile(r"(?i)(www)\."), r"\1[.]"),
    (re.compile(r"(?<=[\w.+-])@(?=[\w-]+\.)"), "[@]"),
)
"""The forms GFM links with no Markdown at all, each broken with a visible bracket. No word
boundary is required: GFM links `www.` after `_`, `*`, `~` or `(` too."""
_LINE_MARKER: Final = re.compile(r"[-+=]|\d+\.")
"""What makes a line a list item, a setext underline or an ordered item when it starts it
(`*`, `#`, `>` and `)` are escaped everywhere already)."""
_BACKTICKS: Final = re.compile(r"`+")
HARD_BREAK: Final = "\\\n"
"""A backslash before a line break: CommonMark's hard line break."""


class UntrustedText:
    """Declared by `interfaces/untrusted_text_interface.py::UntrustedTextInterface`."""

    def line(self, value: Any, *, limit: int) -> str:
        return self._line_start(self.render([(self._one_line(value).lstrip(), True)], limit))

    def block(self, value: Any, *, limit: int) -> str:
        text = self._text(value)
        cut = len(text) > limit
        if cut:
            text = text[: max(limit - len(ELLIPSIS), 0)]
        lines = [
            self._line_start(self.escape(self._one_line(raw).lstrip())) for raw in text.splitlines()
        ]
        pieces: list[str] = []
        for index, line in enumerate(lines):
            if index:
                # A blank line stays a paragraph break; any other line break is a hard one.
                pieces.append("\n" if not line or not lines[index - 1] else HARD_BREAK)
            pieces.append(line)
        return "".join(pieces) + (ELLIPSIS if cut else "")

    def code(self, value: Any, *, limit: int) -> str:
        text = self._text(value)
        if len(text) > limit:
            text = text[: max(limit - len(ELLIPSIS), 0)] + ELLIPSIS
        body = "\n".join(self._one_line(raw) for raw in text.splitlines())
        # A fence longer than any run of backticks inside it cannot be closed from inside.
        longest = max((len(run) for run in _BACKTICKS.findall(body)), default=0)
        fence = "`" * max(3, longest + 1)
        return f"{fence}\n{body}\n{fence}"

    def render(self, segments: Sequence[tuple[str, bool]], limit: int) -> str:
        total = sum(len(text) for text, _ in segments)
        budget = total if total <= limit else max(limit - len(ELLIPSIS), 0)
        out: list[str] = []
        for text, untrusted in segments:
            piece = text[:budget]
            budget -= len(piece)
            out.append(self.escape(piece) if untrusted else piece)
        if total > limit:
            out.append(ELLIPSIS)
        return "".join(out)

    def escape(self, text: str) -> str:
        for pattern, replacement in AUTOLINK_DEFANGS:
            text = pattern.sub(replacement, text)
        return "".join(f"\\{ch}" if ch in MARKDOWN_SPECIAL else ch for ch in text)

    def one_line(self, value: Any) -> str:
        return self._one_line(value)

    @classmethod
    def _one_line(cls, value: Any) -> str:
        return "".join(ch if ch.isprintable() else " " for ch in cls._text(value))

    @staticmethod
    def _text(value: Any) -> str:
        return value if isinstance(value, str) else "?" if value is None else str(value)

    @staticmethod
    def _line_start(line: str) -> str:
        """Escape a list, quote or setext marker that would start the line."""
        marker = _LINE_MARKER.match(line)
        if marker is None:
            return line
        end = marker.end()
        return f"{line[: end - 1]}\\{line[end - 1 :]}"


UNTRUSTED_TEXT: Final = UntrustedText()
