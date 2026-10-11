# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fetching a web page as plain text, for a model that named the URL.

A URL a model chose is attacker-influenced (it may have been read out of a page that was
itself written to steer it), so nothing about it is trusted:

- Only `http` and `https`, never credentials in the URL, and never `localhost` or an
  internal name. The host must resolve **only** to globally routable addresses
  (`webhook._resolve_safe_target`, the check the webhook publisher already stands on), and the
  connection is pinned to the address that was checked, so a DNS answer that changes between
  the check and the connection cannot steer it inward.
- A redirect is followed by hand, at most three times, and each hop is checked the same way: a
  public page that redirects to `http://169.254.169.254/` ends there, not in the metadata
  service.
- Only text types are read, at most one megabyte, and the answer is plain text with scripts,
  styles and navigation removed.

What comes back is untrusted data, and the caller says so.
"""

import http.client
import re
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Final
from urllib.parse import urljoin, urlsplit

from vibey.infrastructure.notify.webhook import _pinned_connection_class, _resolve_safe_target

DEFAULT_MAX_BYTES: Final = 1_000_000
DEFAULT_MAX_CHARS: Final = 20_000
DEFAULT_TIMEOUT_SECONDS: Final = 15.0
MAX_REDIRECTS: Final = 3
USER_AGENT: Final = "vibey-research/1.0 (+https://github.com/the-vibey-project/vibey)"
_TEXT_TYPES: Final = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "text/markdown",
    "application/json",
    "text/xml",
    "application/xml",
)
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


class PageFetcher:
    def __init__(
        self,
        *,
        resolve: Callable[[str], tuple[str, int, str] | None] = _resolve_safe_target,
        connect: Connect = pinned_connect,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_chars: int = DEFAULT_MAX_CHARS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._resolve = resolve
        self._connect = connect
        self._max_bytes = max_bytes
        self._max_chars = max_chars
        self._timeout = timeout_seconds

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        limit = self._max_chars if max_chars is None else max_chars
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            target = self._resolve(current)
            if target is None:
                raise WebFetchError("refused: not a public http(s) address")
            host, port, ip = target
            parts = urlsplit(current)
            path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
            connection = self._connect(parts.scheme.lower(), host, port, ip, self._timeout)
            try:
                connection.request(
                    "GET",
                    path,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"},
                )
                response = connection.getresponse()
                location = response.getheader("Location")
                if response.status in {301, 302, 303, 307, 308} and location:
                    current = urljoin(current, location)
                    continue
                return self._page(current, response, limit)
            except (OSError, http.client.HTTPException) as exc:
                raise WebFetchError(
                    f"the page could not be fetched ({type(exc).__name__})"
                ) from None
            finally:
                connection.close()
        raise WebFetchError(f"stopped after {MAX_REDIRECTS} redirects")

    def _page(self, url: str, response: http.client.HTTPResponse, limit: int) -> FetchedPage:
        if response.status != 200:
            raise WebFetchError(f"the page answered HTTP {response.status}")
        header = response.getheader("Content-Type") or ""
        kind = header.split(";")[0].strip().lower()
        if kind not in _TEXT_TYPES:
            raise WebFetchError(f"not a text page ({kind or 'no content type'})")
        raw = response.read(self._max_bytes + 1)
        clipped = len(raw) > self._max_bytes
        charset = re.search(r"charset=([\w-]+)", header)
        try:
            body = raw[: self._max_bytes].decode(
                charset.group(1) if charset else "utf-8", "replace"
            )
        except LookupError:
            body = raw[: self._max_bytes].decode("utf-8", "replace")
        title, text = (
            html_to_text(body)
            if kind in {"text/html", "application/xhtml+xml"}
            else ("", body.strip())
        )
        truncated = clipped or len(text) > limit
        return FetchedPage(url=url, title=title, text=text[:limit], truncated=truncated)
