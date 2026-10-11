# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fetching a page a model named: what is refused, what is followed, and what is returned."""

import http.client
import socket
from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import pytest

from vibey.infrastructure.web.fetch import (
    FetchedPage,
    PageFetcher,
    WebFetchError,
    html_to_text,
    pinned_connect,
)

HTML = (
    b"<html><head><title> The  Page </title><style>p{color:red}</style></head><body>"
    b"<nav>Menu Home About</nav><script>alert(1)</script><h1>Heading</h1>"
    b"<p>First   paragraph &amp; more.</p><p>Second.</p><footer>Copyright</footer></body></html>"
)


class FakeResponse:
    def __init__(
        self, status: int = 200, headers: dict[str, str] | None = None, body: bytes = b""
    ) -> None:
        self.status = status
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._body = body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name.lower(), default)

    def read(self, amount: int | None = None) -> bytes:
        return self._body if amount is None else self._body[:amount]


class FakeConnection:
    def __init__(
        self, response: FakeResponse | None = None, error: BaseException | None = None
    ) -> None:
        self._response = response
        self._error = error
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False

    def request(self, method: str, path: str, headers: dict[str, str]) -> None:
        self.requests.append((method, path, headers))
        if self._error is not None:
            raise self._error

    def getresponse(self) -> FakeResponse:
        assert self._response is not None
        return self._response

    def close(self) -> None:
        self.closed = True


def _world(
    connections: list[FakeConnection], unsafe: set[str] | None = None
) -> tuple[Callable[[str], tuple[str, int, str] | None], Callable[..., Any], list[tuple[Any, ...]]]:
    unsafe = unsafe or set()
    made: list[tuple[Any, ...]] = []
    queue = list(connections)

    def resolve(url: str) -> tuple[str, int, str] | None:
        host = urlsplit(url).hostname or ""
        return (
            None
            if host in unsafe
            else (host, 443 if url.startswith("https") else 80, "93.184.216.34")
        )

    def connect(scheme: str, host: str, port: int, ip: str, timeout: float) -> FakeConnection:
        made.append((scheme, host, port, ip, timeout))
        return queue.pop(0)

    return resolve, connect, made


def _fetcher(
    connections: list[FakeConnection], unsafe: set[str] | None = None, **kwargs: Any
) -> tuple[PageFetcher, list[tuple[Any, ...]]]:
    resolve, connect, made = _world(connections, unsafe)
    return PageFetcher(resolve=resolve, connect=connect, **kwargs), made


def test_html_becomes_plain_text_without_scripts_styles_or_navigation() -> None:
    title, text = html_to_text(HTML.decode())
    assert title == "The Page"
    assert text == "Heading\n\nFirst paragraph & more.\n\nSecond."
    assert (
        "alert" not in text
        and "Menu" not in text
        and "Copyright" not in text
        and "color" not in text
    )


def test_an_unclosed_skipped_tag_never_goes_below_zero() -> None:
    assert html_to_text("</nav></script>plain")[1] == "plain"


def test_a_page_is_fetched_over_the_checked_address_and_returned_as_text() -> None:
    conn = FakeConnection(FakeResponse(200, {"Content-Type": "text/html; charset=utf-8"}, HTML))
    fetcher, made = _fetcher([conn], timeout_seconds=7)

    page = fetcher.fetch("https://docs.example/a/b?x=1")

    assert page == FetchedPage("https://docs.example/a/b?x=1", "The Page", page.text, False)
    assert page.text.startswith("Heading")
    assert made == [("https", "docs.example", 443, "93.184.216.34", 7)]
    method, path, headers = conn.requests[0]
    assert (method, path) == ("GET", "/a/b?x=1") and "vibey-research" in headers["User-Agent"]
    assert conn.closed


def test_an_empty_path_is_asked_for_as_a_slash() -> None:
    conn = FakeConnection(FakeResponse(200, {"Content-Type": "text/plain"}, b"hi"))
    fetcher, _ = _fetcher([conn])
    assert fetcher.fetch("http://plain.example").text == "hi"
    assert conn.requests[0][1] == "/"


def test_plain_text_and_json_are_returned_as_they_are_and_long_text_is_cut() -> None:
    conn = FakeConnection(
        FakeResponse(200, {"Content-Type": "application/json"}, b'{"a": "' + b"x" * 500 + b'"}')
    )
    fetcher, _ = _fetcher([conn])
    page = fetcher.fetch("https://api.example/x", max_chars=100)
    assert page.text.startswith('{"a"') and len(page.text) == 100 and page.truncated


def test_a_body_over_the_byte_limit_is_clipped_and_said_to_be() -> None:
    conn = FakeConnection(FakeResponse(200, {"Content-Type": "text/plain"}, b"y" * 50))
    fetcher, _ = _fetcher([conn], max_bytes=10)
    page = fetcher.fetch("https://big.example/")
    assert page.text == "y" * 10 and page.truncated


def test_the_declared_charset_is_used_and_an_unknown_one_falls_back_to_utf8() -> None:
    latin = FakeConnection(
        FakeResponse(
            200, {"Content-Type": "text/plain; charset=iso-8859-1"}, "café".encode("latin-1")
        )
    )
    assert _fetcher([latin])[0].fetch("https://a.example").text == "café"
    odd = FakeConnection(
        FakeResponse(200, {"Content-Type": "text/plain; charset=nonsense-9"}, "café".encode())
    )
    assert _fetcher([odd])[0].fetch("https://b.example").text == "café"


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://169.254.169.254/latest/meta-data",
        "ftp://x.example/",
        "https://user:pw@host.example/",
    ],
)
def test_an_address_that_is_not_public_is_refused_before_any_connection(url: str) -> None:
    unsafe = {"localhost", "169.254.169.254", "host.example", "x.example"}
    fetcher, made = _fetcher([], unsafe)
    with pytest.raises(WebFetchError, match=r"not a public http\(s\) address"):
        fetcher.fetch(url)
    assert made == []


def test_the_real_resolver_refuses_internal_names_without_any_network() -> None:
    fetcher = PageFetcher()
    for url in (
        "http://localhost:8080/",
        "http://printer.local/",
        "http://db.internal/",
        "file:///etc/passwd",
        "https://u:p@example.org/",
    ):
        with pytest.raises(WebFetchError, match="not a public"):
            fetcher.fetch(url)


def test_a_redirect_is_followed_and_every_hop_is_checked_again() -> None:
    first = FakeConnection(FakeResponse(302, {"Location": "/moved"}))
    second = FakeConnection(FakeResponse(200, {"Content-Type": "text/plain"}, b"arrived"))
    fetcher, made = _fetcher([first, second])
    page = fetcher.fetch("https://start.example/old")
    assert page.url == "https://start.example/moved" and page.text == "arrived"
    assert len(made) == 2 and first.closed and second.closed


def test_a_public_page_that_redirects_into_the_metadata_service_stops_there() -> None:
    hop = FakeConnection(
        FakeResponse(301, {"Location": "http://169.254.169.254/latest/meta-data/"})
    )
    fetcher, made = _fetcher([hop], unsafe={"169.254.169.254"})
    with pytest.raises(WebFetchError, match=r"not a public http\(s\) address"):
        fetcher.fetch("https://innocent.example/")
    assert len(made) == 1  # the second connection was never made


def test_a_redirect_loop_stops_after_three_hops() -> None:
    loop = [
        FakeConnection(FakeResponse(302, {"Location": "https://loop.example/"})) for _ in range(4)
    ]
    fetcher, made = _fetcher(loop)
    with pytest.raises(WebFetchError, match="stopped after 3 redirects"):
        fetcher.fetch("https://loop.example/")
    assert len(made) == 4


def test_a_redirect_with_no_location_is_just_the_page_it_is() -> None:
    conn = FakeConnection(FakeResponse(302, {"Content-Type": "text/plain"}))
    with pytest.raises(WebFetchError, match="HTTP 302"):
        _fetcher([conn])[0].fetch("https://nowhere.example/")


@pytest.mark.parametrize(
    ("response", "needle"),
    [
        (FakeResponse(404, {"Content-Type": "text/html"}), "HTTP 404"),
        (
            FakeResponse(200, {"Content-Type": "application/pdf"}),
            r"not a text page \(application/pdf\)",
        ),
        (FakeResponse(200, {}), r"not a text page \(no content type\)"),
    ],
)
def test_a_page_that_is_not_readable_text_is_refused_and_its_connection_closed(
    response: FakeResponse, needle: str
) -> None:
    conn = FakeConnection(response)
    with pytest.raises(WebFetchError, match=needle):
        _fetcher([conn])[0].fetch("https://odd.example/")
    assert conn.closed


@pytest.mark.parametrize(
    "error", [ConnectionResetError("secret-host"), TimeoutError(), http.client.BadStatusLine("x")]
)
def test_a_connection_failure_is_named_by_type_and_never_shows_the_url(
    error: BaseException,
) -> None:
    conn = FakeConnection(error=error)
    with pytest.raises(WebFetchError, match="could not be fetched") as caught:
        _fetcher([conn])[0].fetch("https://u:pw@secret-host.example/")
    assert "secret-host" not in str(caught.value) and "pw" not in str(caught.value)
    assert conn.closed


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_the_real_connection_is_pinned_to_the_checked_ip_but_still_names_the_host(
    scheme: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    reached: list[tuple[str, int]] = []

    def create_connection(
        address: tuple[str, int], timeout: float | None = None, source_address: Any = None
    ) -> socket.socket:
        reached.append(address)
        raise OSError("stop here: no network in a unit test")

    monkeypatch.setattr(socket, "create_connection", create_connection)
    conn = pinned_connect(
        scheme, "docs.example", 443 if scheme == "https" else 80, "93.184.216.34", 5
    )

    assert conn.host == "docs.example"
    assert isinstance(conn, http.client.HTTPSConnection) == (scheme == "https")
    with pytest.raises(OSError, match="stop here"):
        conn.connect()
    assert reached == [("93.184.216.34", 443 if scheme == "https" else 80)]
