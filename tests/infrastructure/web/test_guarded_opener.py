# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The opener every search backend uses: a redirect is followed only to the same origin (so a
SearXNG cannot send a query, or Brave's key header, to another host), and a loopback SearXNG
is reached directly, never through a proxy. Runs against a real server on loopback."""

from __future__ import annotations

import http.server
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator

import pytest

from vibey.infrastructure.web.guarded_opener import GuardedOpener
from vibey.infrastructure.web.interfaces import GuardedOpenerInterface
from vibey.infrastructure.web.search import SearxngBackend

pytestmark = pytest.mark.web_network


class _Handler(http.server.BaseHTTPRequestHandler):
    seen: list[tuple[str, str | None]] = []
    elsewhere = ""

    def do_GET(self) -> None:  # noqa: N802 - the stdlib's name
        _Handler.seen.append((self.path, self.headers.get("X-Subscription-Token")))
        if self.path.startswith("/same"):
            self.send_response(302)
            self.send_header("Location", "/landed")
            self.end_headers()
            return
        if self.path.startswith("/drip"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "1000")
            self.end_headers()
            for _ in range(200):
                try:
                    self.wfile.write(b" ")
                    self.wfile.flush()
                except OSError:
                    return
                time.sleep(0.1)
            return
        if self.path == "/redir/config":
            self.send_response(302)
            self.send_header("Location", "/landed")
            self.end_headers()
            return
        if self.path.startswith("/away"):
            self.send_response(302)
            self.send_header("Location", f"{_Handler.elsewhere}/stolen")
            self.end_headers()
            return
        body = b'{"results": []}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return None


def _serve() -> tuple[http.server.HTTPServer, str]:
    # Threaded, daemon handlers: a trickling answer never holds the fixture's shutdown.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


@pytest.fixture
def servers() -> Iterator[tuple[str, str]]:
    _Handler.seen = []
    first, first_url = _serve()
    second, second_url = _serve()
    # Same address, another port: another origin, which is all a redirect check can see.
    _Handler.elsewhere = second_url
    try:
        yield first_url, second_url
    finally:
        first.shutdown()
        second.shutdown()


def test_the_opener_honours_its_interface() -> None:
    assert isinstance(GuardedOpener("http://127.0.0.1:8080"), GuardedOpenerInterface)


def test_a_redirect_to_the_same_origin_is_followed(servers: tuple[str, str]) -> None:
    base, _ = servers
    request = urllib.request.Request(f"{base}/same")  # noqa: S310 - a loopback test server
    with GuardedOpener(base)(request, timeout=5) as response:
        assert response.read() == b'{"results": []}'
    assert [path for path, _ in _Handler.seen] == ["/same", "/landed"]


def test_a_redirect_to_another_origin_is_refused_and_carries_nothing_there(
    servers: tuple[str, str],
) -> None:
    base, _ = servers
    request = urllib.request.Request(  # noqa: S310 - a loopback test server
        f"{base}/away", headers={"X-Subscription-Token": "fake-key"}
    )
    with pytest.raises(urllib.error.HTTPError) as caught:
        GuardedOpener(base)(request, timeout=5)
    assert caught.value.code == 302
    assert _Handler.seen == [("/away", "fake-key")]


def test_a_loopback_backend_is_reached_directly_never_through_a_proxy(
    servers: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    base, _ = servers
    # A proxy that does not exist: going through it would fail to connect.
    for name in ("http_proxy", "HTTP_PROXY", "all_proxy", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    request = urllib.request.Request(f"{base}/direct")  # noqa: S310 - a loopback test server
    with GuardedOpener(base)(request, timeout=5) as response:
        assert response.status == 200


@pytest.mark.parametrize(
    ("url", "loopback"),
    [
        ("http://127.0.0.1:8080", True),
        ("http://127.5.6.7/", True),
        ("http://localhost:8888", True),
        ("http://localhost.:8888", True),
        ("http://searx.localhost:8888", True),
        ("http://LOCALHOST", True),
        ("http://notlocalhost:8888", False),
        ("http://localhost.example:8888", False),
        ("http://[::1]:8080/", True),
        ("http://search.lan:8080", False),
        ("https://api.search.brave.com/res/v1/web/search", False),
        ("http://10.0.0.2", False),
        ("not a url", False),
    ],
)
def test_which_addresses_are_loopback(url: str, loopback: bool) -> None:
    assert GuardedOpener.is_loopback(url) is loopback
    assert GuardedOpener(url).direct is loopback


def test_a_searxng_identity_that_redirects_is_refused_even_within_the_origin(
    servers: tuple[str, str],
) -> None:
    base, _ = servers
    said = SearxngBackend(f"{base}/redir", opener=GuardedOpener(base)).health()
    assert said == "something other than SearXNG is listening there (its /config redirected)"


def test_a_listener_that_trickles_its_answer_is_cut_off_at_the_total_deadline(
    servers: tuple[str, str],
) -> None:
    base, _ = servers
    started = time.monotonic()
    said = SearxngBackend(f"{base}/drip", opener=GuardedOpener(base), timeout_seconds=0.5).health()
    assert said == "did not finish answering within 0.5s"
    assert time.monotonic() - started < 3
