# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pieces a page fetch is made of: the pinned connection, HTML to text, and the page a
caller is handed.

The fetch itself is the hub's guarded one (`guarded_fetch.py`), and `vibey fetch` and the
DESIGN stage's research reach it through `page_fetcher.py` (SP-ACP Task 11a): this module keeps
only what both share. What a fetch returns is untrusted data, and the caller says so; its title
and text carry no terminal escape sequence or control character (`untrusted_text.py`).
"""

import http.client
import re
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Final

from vibey.infrastructure.notify.webhook import _pinned_connection_class

USER_AGENT: Final = "vibey-research/1.0 (+https://github.com/the-vibey-project/vibey)"
_SKIPPED: Final = frozenset(
    {"script", "style", "noscript", "nav", "header", "footer", "aside", "form", "svg", "template"}
)
_BLOCKS: Final = frozenset(
    {"p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article", "pre", "blockquote"}
    | {f"h{n}" for n in range(1, 7)}
)
_BLANKS = re.compile(r"[ \t\f\v]+")
_LINES = re.compile(r"\n\s*\n+")


class WebFetchError(RuntimeError):
    """A page could not be fetched. The message never carries the URL's credentials."""


@dataclass(frozen=True, slots=True)
class FetchedPage:
    url: str
    title: str
    text: str
    truncated: bool


Connect = Callable[[str, str, int, str, float], http.client.HTTPConnection]


def pinned_connect(
    scheme: str, host: str, port: int, ip: str, timeout: float
) -> http.client.HTTPConnection:
    """A connection to `ip` that still names `host` for the Host header and TLS. An https
    connection verifies the certificate against `host` with Python's default context."""
    if scheme == "https":
        return _pinned_connection_class(http.client.HTTPSConnection, ip)(
            host, port, timeout=timeout
        )
    return _pinned_connection_class(http.client.HTTPConnection, ip)(host, port, timeout=timeout)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._parts: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._in_title = True
        elif tag in _SKIPPED:
            self._skip += 1
        elif tag in _BLOCKS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in _SKIPPED:
            self._skip = max(self._skip - 1, 0)
        elif tag in _BLOCKS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif not self._skip:
            self._parts.append(data)

    def text(self) -> str:
        joined = "".join(self._parts)
        lines = (_BLANKS.sub(" ", line).strip() for line in joined.splitlines())
        return _LINES.sub("\n\n", "\n".join(lines)).strip()


def html_to_text(markup: str) -> tuple[str, str]:
    """`(title, text)` of an HTML document: no scripts, styles or navigation."""
    extractor = _TextExtractor()
    extractor.feed(markup)
    extractor.close()
    return " ".join(extractor.title.split()), extractor.text()
