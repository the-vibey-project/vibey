# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's guarded fetch (ADR-0102, SP-ACP Task 9b): it connects only to an address it checked,
checks every address a name resolves to and every redirect again, asks for and reads only
uncompressed text, and is bounded in bytes, characters, hops and total time.

Every resolver and connection is a fake; nothing here touches a network. Module-level test
functions rather than a class with an interface beside it (ADR-0016)."""

import asyncio
import http.client
import socket
import threading
from collections.abc import Sequence
from typing import Any

import pytest

from vibey.application.hub.interfaces.web_tools_service_interface import WebFetchPortInterface
from vibey.domain.web_tools import (
    WEB_TOOL_POLICY,
    WebTarget,
    WebToolFailed,
    WebToolRefused,
    WebToolSettings,
)
from vibey.infrastructure.web.guarded_fetch import USER_AGENT, GuardedPageFetch

SETTINGS = WebToolSettings()
PUBLIC = "93.184.216.34"
SYSTEM_ADDRESSES = GuardedPageFetch.system_addresses
"""The real resolver, taken before the suite's hermetic fixture stands a refusing one in."""


def _target(url: str, settings: WebToolSettings = SETTINGS) -> WebTarget:
    return WEB_TOOL_POLICY.target(url, settings)


class Response:
    def __init__(
        self, status: int = 200, headers: dict[str, str] | None = None, body: bytes = b""
    ) -> None:
        self.status = status
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._body = body
        self.asked: list[int | None] = []

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name.lower(), default)

    def read(self, amount: int | None = None) -> bytes:
        self.asked.append(amount)
        size = len(self._body) if amount is None else amount
        chunk, self._body = self._body[:size], self._body[size:]
        return chunk


class Connection:
    def __init__(self, response: Response | None = None, error: BaseException | None = None):
        self._response = response
        self._error = error
        self.requests: list[tuple[str, str, dict[str, str]]] = []
        self.closed = False
        self.sock: Any = None

    def request(self, method: str, path: str, headers: dict[str, str]) -> None:
        self.requests.append((method, path, headers))
        if self._error is not None:
            raise self._error

    def getresponse(self) -> Response:
        assert self._response is not None
        return self._response

    def close(self) -> None:
        self.closed = True


class World:
    """Names resolve as `answers` says (any other to the one public address); connections are
    handed out in order and every one is recorded."""

    def __init__(
        self, connections: Sequence[Connection], answers: dict[str, list[str]] | None = None
    ) -> None:
        self.queue = list(connections)
        self.answers = answers or {}
        self.resolved: list[tuple[str, int]] = []
        self.made: list[tuple[str, str, int, str, float]] = []

    def resolve(self, host: str, port: int) -> list[str]:
        self.resolved.append((host, port))
        return self.answers.get(host, [PUBLIC])

    def connect(self, scheme: str, host: str, port: int, ip: str, timeout: float) -> Connection:
        self.made.append((scheme, host, port, ip, timeout))
        return self.queue.pop(0)


def _fetch(world: World, url: str, settings: WebToolSettings = SETTINGS) -> Any:
    fetcher = GuardedPageFetch(resolve=world.resolve, connect=world.connect)
    return asyncio.run(fetcher.fetch(_target(url, settings), settings))


def _page(body: bytes = b"<title>T</title><p>Hello</p>", kind: str = "text/html") -> Connection:
    return Connection(Response(200, {"Content-Type": f"{kind}; charset=utf-8"}, body))


def test_the_fetch_meets_its_seam() -> None:
    assert isinstance(GuardedPageFetch(), WebFetchPortInterface)


def test_a_page_is_read_over_the_address_that_was_checked_with_fixed_headers_only() -> None:
    conn = _page()
    world = World([conn])
    page = _fetch(world, "https://docs.example/a?b=c")
    ((scheme, host, port, ip, timeout),) = world.made
    assert (scheme, host, port, ip) == ("https", "docs.example", 443, PUBLIC)
    assert timeout == pytest.approx(15.0, abs=1.0)  # the time left of the one deadline
    ((method, path, headers),) = conn.requests
    assert (method, path) == ("GET", "/a?b=c")
    assert headers == {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
        "Accept-Encoding": "identity",
    }
    assert not any(h.lower() in {"cookie", "authorization"} for h in headers)
    assert (page.title, page.text, page.hosts) == ("T", "Hello", ("docs.example",))
    assert page.url == "https://docs.example/a?b=c" and page.content_type == "text/html"
    assert conn.closed


def test_an_address_literal_is_connected_to_without_asking_a_resolver() -> None:
    world = World([_page()])
    _fetch(world, f"http://{PUBLIC}/")
    assert world.resolved == [] and world.made[0][3] == PUBLIC


@pytest.mark.parametrize(
    "answers",
    [
        ["127.0.0.1"],
        ["10.0.0.5"],
        ["169.254.169.254"],
        ["::1"],
        ["fd00:ec2::254"],
        ["::ffff:127.0.0.1"],
        [PUBLIC, "192.168.0.10"],  # one inward answer is enough to refuse
        ["not-an-address"],
    ],
)
def test_a_name_that_resolves_to_any_address_that_is_not_public_is_never_connected_to(
    answers: list[str],
) -> None:
    world = World([], {"rebind.example": answers})
    with pytest.raises(WebToolRefused, match="not a public address") as raised:
        _fetch(world, "https://rebind.example/")
    assert world.made == []
    assert raised.value.hosts == ("rebind.example",)


def test_a_name_that_resolves_to_nothing_fails_without_a_connection() -> None:
    world = World([], {"void.example": []})
    with pytest.raises(WebToolFailed, match="could not be resolved"):
        _fetch(world, "https://void.example/")
    assert world.made == []


def test_dns_rebinding_between_hops_is_caught_at_the_hop_it_happens() -> None:
    """The first answer is public; the redirect's host answers inward. The fetch connects to the
    first, then refuses the second before any connection."""
    hop = Connection(Response(302, {"Location": "https://second.example/"}))
    world = World([hop], {"first.example": [PUBLIC], "second.example": ["127.0.0.1"]})
    with pytest.raises(WebToolRefused) as raised:
        _fetch(world, "https://first.example/")
    assert len(world.made) == 1 and world.made[0][3] == PUBLIC
    assert raised.value.hosts == ("first.example", "second.example")


def test_the_same_name_resolved_twice_is_checked_twice() -> None:
    """A name that answered public for the first hop and inward for its own redirect is refused:
    no answer is cached between hops."""

    class Flipping(World):
        def resolve(self, host: str, port: int) -> list[str]:
            self.resolved.append((host, port))
            return [PUBLIC] if len(self.resolved) == 1 else ["10.0.0.1"]

    hop = Connection(Response(301, {"Location": "/again"}))
    world = Flipping([hop])
    with pytest.raises(WebToolRefused):
        _fetch(world, "https://flip.example/")
    assert world.resolved == [("flip.example", 443), ("flip.example", 443)]
    assert len(world.made) == 1


@pytest.mark.parametrize(
    "location",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://[::ffff:169.254.169.254]/",
        "https://localhost/",
        "file:///etc/passwd",
        "https://user:pw@example.com/",
        "http://docs.example/",  # https down to http
    ],
)
def test_a_redirect_is_checked_again_before_it_is_followed(location: str) -> None:
    hop = Connection(Response(302, {"Location": location}))
    world = World([hop])
    with pytest.raises(WebToolRefused):
        _fetch(world, "https://docs.example/")
    assert len(world.made) == 1 and hop.closed


def test_redirects_stop_at_the_persons_bound() -> None:
    hops = [Connection(Response(302, {"Location": "/next"})) for _ in range(3)]
    world = World(hops)
    with pytest.raises(WebToolFailed, match="stopped after 2 redirects"):
        _fetch(world, "https://loop.example/", WebToolSettings(max_redirects=2))
    assert len(world.made) == 3


def test_a_followed_redirect_names_every_host_it_reached() -> None:
    hop = Connection(Response(307, {"Location": "https://cdn.example/x"}))
    world = World([hop, _page(b"ok", "text/plain")])
    page = _fetch(world, "https://docs.example/")
    assert page.hosts == ("docs.example", "cdn.example")
    assert page.url == "https://cdn.example/x" and page.text == "ok"


def test_a_redirect_to_a_host_the_person_denies_is_refused() -> None:
    hop = Connection(Response(302, {"Location": "https://paste.example/"}))
    settings = WebToolSettings(deny_hosts=("paste.example",))
    with pytest.raises(WebToolRefused, match="deny_hosts"):
        _fetch(World([hop]), "https://docs.example/", settings)


@pytest.mark.parametrize(
    ("response", "needle"),
    [
        (Response(404, {"Content-Type": "text/html"}), "HTTP 404"),
        (Response(302, {"Content-Type": "text/plain"}), "HTTP 302"),
    ],
)
def test_a_page_that_did_not_answer_200_fails(response: Response, needle: str) -> None:
    with pytest.raises(WebToolFailed, match=needle):
        _fetch(World([Connection(response)]), "https://odd.example/")


@pytest.mark.parametrize(
    ("headers", "needle"),
    [
        ({"Content-Type": "application/pdf"}, r"application/pdf"),
        ({"Content-Type": "image/png"}, r"image/png"),
        ({"Content-Type": "application/octet-stream"}, "octet-stream"),
        ({}, "no content type"),
        ({"Content-Type": "text/html\x1b[2J"}, "an unreadable type"),
    ],
)
def test_a_page_that_is_not_text_is_refused_never_extracted(
    headers: dict[str, str], needle: str
) -> None:
    conn = Connection(Response(200, headers, b"%PDF-1.7 ..."))
    with pytest.raises(WebToolRefused, match=needle) as raised:
        _fetch(World([conn]), "https://odd.example/")
    assert "\x1b" not in str(raised.value) and conn.closed


def test_a_content_type_the_person_dropped_is_refused() -> None:
    settings = WebToolSettings(content_types=("text/plain",))
    with pytest.raises(WebToolRefused, match="text/html"):
        _fetch(World([_page()]), "https://docs.example/", settings)


@pytest.mark.parametrize("encoding", ["gzip", "br", "deflate", "gzip, gzip", "zstd"])
def test_a_compressed_answer_is_refused_so_nothing_is_ever_decompressed(encoding: str) -> None:
    conn = Connection(
        Response(200, {"Content-Type": "text/html", "Content-Encoding": encoding}, b"\x1f\x8b")
    )
    response = conn._response
    with pytest.raises(WebToolRefused, match="compressed"):
        _fetch(World([conn]), "https://bomb.example/")
    assert response is not None and response.asked == []  # not one byte of the body read


def test_an_identity_encoding_is_read() -> None:
    conn = Connection(
        Response(200, {"Content-Type": "text/plain", "Content-Encoding": "Identity"}, b"plain")
    )
    assert _fetch(World([conn]), "https://plain.example/").text == "plain"


def test_the_body_is_read_to_the_byte_bound_and_the_text_cut_to_the_character_bound() -> None:
    body = b"x" * 5_000
    conn = Connection(Response(200, {"Content-Type": "text/plain"}, body))
    page = _fetch(
        World([conn]), "https://big.example/", WebToolSettings(max_bytes=1_000, max_chars=100)
    )
    # One receive at a time, never more than the bound plus the one byte that says it was cut.
    assert conn._response is not None and conn._response.asked == [1_001]
    assert page.text == "x" * 100 and page.truncated
    short = Connection(Response(200, {"Content-Type": "text/plain"}, b"short"))
    assert not _fetch(World([short]), "https://small.example/").truncated


def test_a_declared_charset_is_used_and_an_unknown_one_falls_back() -> None:
    latin = Connection(
        Response(200, {"Content-Type": "text/plain; charset=latin-1"}, "café".encode("latin-1"))
    )
    assert _fetch(World([latin]), "https://a.example/").text == "café"
    odd = Connection(
        Response(200, {"Content-Type": "text/plain; charset=nonsense"}, "café".encode())
    )
    assert _fetch(World([odd]), "https://b.example/").text == "café"


def test_a_page_reaches_its_reader_with_no_terminal_control() -> None:
    body = b"<title>T\x1b]0;owned\x07</title><p>a\x1b]52;c;ZXZpbA==\x07b\x1b[2Jc</p>"
    page = _fetch(World([_page(body)]), "https://evil.example/")
    assert page.text == "abc" and "\x1b" not in page.title + page.text


@pytest.mark.parametrize(
    "error", [ConnectionResetError("secret-host"), TimeoutError(), http.client.BadStatusLine("x")]
)
def test_a_connection_failure_is_named_by_type_and_never_shows_the_url(
    error: BaseException,
) -> None:
    conn = Connection(error=error)
    with pytest.raises(WebToolFailed, match="could not be fetched") as raised:
        _fetch(World([conn]), "https://secret-host.example/p?token=t0k")
    assert "secret-host" not in str(raised.value) and "t0k" not in str(raised.value)
    assert raised.value.hosts == ("secret-host.example",) and conn.closed


def test_the_whole_fetch_is_bounded_in_time_and_its_socket_is_shut_when_it_runs_out() -> None:
    """A page that answers a byte at a time just inside every socket timeout would hold a
    per-read bound for ever; the fetch has one deadline in all, and closes its socket when it
    passes so the thread holding it ends too."""
    released = threading.Event()

    class Sock:
        def __init__(self) -> None:
            self.shut = False

        def settimeout(self, value: float) -> None:
            assert 0 < value <= 0.2

        def shutdown(self, how: int) -> None:
            assert how == socket.SHUT_RDWR
            self.shut = True
            released.set()

    class Trickle(Connection):
        def getresponse(self) -> Response:
            released.wait(5)
            raise ConnectionAbortedError("shut")

    conn = Trickle()
    conn.sock = Sock()
    world = World([conn])
    with pytest.raises(WebToolFailed, match="within 0.2s") as raised:
        _fetch(world, "https://slow.example/", WebToolSettings(timeout_seconds=0.2))
    assert conn.sock.shut
    assert raised.value.hosts == ("slow.example",)


def test_a_socket_that_will_not_shut_still_lets_the_deadline_pass() -> None:
    class Sock:
        def settimeout(self, value: float) -> None:
            return None

        def shutdown(self, how: int) -> None:
            raise OSError("already gone")

    gate = threading.Event()

    class Stuck(Connection):
        def getresponse(self) -> Response:
            gate.wait(5)
            raise ConnectionAbortedError("released")

        def close(self) -> None:
            super().close()
            gate.set()  # the close after the failed shutdown is what lets the thread go

    conn = Stuck()
    conn.sock = Sock()
    try:
        with pytest.raises(WebToolFailed, match="within"):
            _fetch(World([conn]), "https://stuck.example/", WebToolSettings(timeout_seconds=0.1))
    finally:
        gate.set()


def test_the_default_resolver_asks_the_system_for_every_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[tuple[Any, ...]] = []

    def getaddrinfo(host: str, port: int, *args: Any, **kwargs: Any) -> list[Any]:
        asked.append((host, port, kwargs.get("type")))
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, port)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", port, 0, 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    assert SYSTEM_ADDRESSES("docs.example", 443) == [PUBLIC, "::1"]
    assert asked == [("docs.example", 443, socket.SOCK_STREAM)]


def test_the_default_resolver_reads_a_lookup_failure_as_no_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def getaddrinfo(*_: Any, **__: Any) -> list[Any]:
        raise socket.gaierror("no such name")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    assert SYSTEM_ADDRESSES("void.example", 443) == []


def test_the_default_connection_is_pinned_to_the_checked_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reached: list[tuple[str, int]] = []

    def create_connection(address: tuple[str, int], *_: Any, **__: Any) -> socket.socket:
        reached.append(address)
        raise OSError("stop here: no network in a unit test")

    monkeypatch.setattr(socket, "create_connection", create_connection)
    fetcher = GuardedPageFetch(resolve=lambda host, port: [PUBLIC])
    with pytest.raises(WebToolFailed, match="OSError"):
        asyncio.run(fetcher.fetch(_target("https://docs.example/"), SETTINGS))
    assert reached == [(PUBLIC, 443)]


def test_a_deadline_that_passes_while_the_name_is_resolving_has_no_socket_to_shut() -> None:
    gate = threading.Event()

    class Slow(World):
        def resolve(self, host: str, port: int) -> list[str]:
            gate.wait(5)
            return ["10.0.0.1"]

    world = Slow([])
    try:
        with pytest.raises(WebToolFailed, match="within") as raised:
            _fetch(world, "https://slow-dns.example/", WebToolSettings(timeout_seconds=0.1))
        assert raised.value.hosts == ("slow-dns.example",)
    finally:
        gate.set()
    assert world.made == []


def test_a_connection_with_no_socket_yet_is_closed_when_the_deadline_passes() -> None:
    gate = threading.Event()

    class Unopened(Connection):
        def getresponse(self) -> Response:
            gate.wait(5)
            raise ConnectionAbortedError("closed")

        def close(self) -> None:
            super().close()
            gate.set()

    conn = Unopened()
    with pytest.raises(WebToolFailed, match="within"):
        _fetch(World([conn]), "https://unopened.example/", WebToolSettings(timeout_seconds=0.1))
    assert conn.closed


def test_a_fetch_that_ends_after_its_caller_has_gone_says_nothing_to_anyone() -> None:
    """The caller gave up at the deadline and its loop has closed; the thread's late answer has
    nowhere to go and is dropped quietly."""
    gate = threading.Event()

    class Late(Connection):
        def getresponse(self) -> Response:
            gate.wait(5)
            return Response(200, {"Content-Type": "text/plain"}, b"late")

        def close(self) -> None:
            self.closed = True  # a close that does not release it: the answer comes later

    with pytest.raises(WebToolFailed, match="within"):
        _fetch(World([Late()]), "https://late.example/", WebToolSettings(timeout_seconds=0.1))
    gate.set()
    for thread in threading.enumerate():
        if thread.name == "vibey-web-fetch":
            thread.join(5)
            assert not thread.is_alive()


class Clock:
    """A clock the fakes move forward: real time never passes in these tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _joined() -> None:
    """Every thread the fetch started has ended: nothing outlives a cancelled fetch."""
    for thread in threading.enumerate():
        if thread.name in {"vibey-web-fetch", "vibey-web-resolve"}:
            thread.join(5)
            assert not thread.is_alive(), thread.name


def test_a_resolver_that_answers_after_the_deadline_is_never_followed_by_a_connection() -> None:
    gate = threading.Event()

    class Late(World):
        def resolve(self, host: str, port: int) -> list[str]:
            gate.wait(5)
            return [PUBLIC]

    world = Late([_page()])
    with pytest.raises(WebToolFailed, match="within 0.1s"):
        _fetch(world, "https://late-dns.example/", WebToolSettings(timeout_seconds=0.1))
    # The fetch's own thread is gone while the resolver still hangs: resolving has its own bound.
    for thread in threading.enumerate():
        if thread.name == "vibey-web-fetch":
            thread.join(2)
            assert not thread.is_alive()
    gate.set()
    _joined()
    assert world.made == []


def test_a_connection_made_after_the_caller_gave_up_is_closed_and_sends_nothing() -> None:
    gate = threading.Event()
    conn = _page()

    class SlowConnect(World):
        def connect(self, scheme: str, host: str, port: int, ip: str, timeout: float) -> Connection:
            gate.wait(5)
            return super().connect(scheme, host, port, ip, timeout)

    world = SlowConnect([conn])
    with pytest.raises(WebToolFailed, match="within"):
        _fetch(world, "https://slow-connect.example/", WebToolSettings(timeout_seconds=0.1))
    gate.set()
    _joined()
    assert conn.closed and conn.requests == []


def test_every_step_is_bounded_by_the_time_left_of_the_one_deadline() -> None:
    clock = Clock()

    class Ticking(World):
        def connect(self, scheme: str, host: str, port: int, ip: str, timeout: float) -> Connection:
            clock.now += 4.0  # each connection takes four of the fifteen seconds
            return super().connect(scheme, host, port, ip, timeout)

    hops = [Connection(Response(302, {"Location": "/next"})) for _ in range(3)]
    world = Ticking([*hops, _page()])
    fetcher = GuardedPageFetch(resolve=world.resolve, connect=world.connect, clock=clock)
    settings = WebToolSettings(timeout_seconds=15.0, max_redirects=5)
    with pytest.raises(WebToolFailed, match="within 15s") as raised:
        asyncio.run(fetcher.fetch(_target("https://hops.example/", settings), settings))
    # Each connection was given only what was left, never a fresh fifteen seconds.
    assert [made[4] for made in world.made] == [15.0, 11.0, 7.0, 3.0]
    assert raised.value.hosts == ("hops.example",) * 4
    _joined()


def test_a_page_that_trickles_stops_when_the_deadline_passes() -> None:
    clock = Clock()

    class Trickling(Response):
        def read(self, amount: int | None = None) -> bytes:
            clock.now += 1.0  # one byte a second, for ever
            self.asked.append(amount)
            return b"x"

    conn = Connection(Trickling(200, {"Content-Type": "text/plain"}))
    world = World([conn])
    fetcher = GuardedPageFetch(resolve=world.resolve, connect=world.connect, clock=clock)
    settings = WebToolSettings(timeout_seconds=5.0)
    with pytest.raises(WebToolFailed, match="within 5s"):
        asyncio.run(fetcher.fetch(_target("https://trickle.example/", settings), settings))
    assert conn._response is not None and len(conn._response.asked) == 5
    assert conn.closed
    _joined()


def test_a_socket_is_given_the_time_left_before_each_blocking_step() -> None:
    clock = Clock()
    timeouts: list[float] = []

    class Sock:
        def settimeout(self, value: float) -> None:
            timeouts.append(value)

    class Measured(Connection):
        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            timeouts.append(self.timeout)  # what a lazy connect would be bounded by
            clock.now += 2.0
            super().request(method, path, headers)

    conn = Measured(Response(200, {"Content-Type": "text/plain"}, b"ok"))
    conn.sock = Sock()
    world = World([conn])
    fetcher = GuardedPageFetch(resolve=world.resolve, connect=world.connect, clock=clock)
    settings = WebToolSettings(timeout_seconds=10.0)
    asyncio.run(fetcher.fetch(_target("https://measured.example/", settings), settings))
    # The socket and the connection before the request, then the socket before the response and
    # before each receive.
    assert timeouts == [10.0, 10.0, 8.0, 8.0, 8.0]
    _joined()


def test_a_resolver_that_raises_is_a_host_that_did_not_resolve() -> None:
    class Broken(World):
        def resolve(self, host: str, port: int) -> list[str]:
            raise OSError("resolver down")

    with pytest.raises(WebToolFailed, match="could not be resolved"):
        _fetch(Broken([]), "https://broken.example/")


@pytest.mark.parametrize(
    "charset", ["idna", "punycode", "undefined", "rot13", "base64", "zlib", "nonsense", "utf-7"]
)
def test_a_charset_that_is_not_a_text_codec_falls_back_to_utf8_and_never_raises(
    charset: str,
) -> None:
    """The page's server names the charset; a codec that raises (`idna`, `punycode`,
    `undefined`) or that is not text must never decide whether the fetch is recorded."""
    body = "café \xff\xfe".encode("utf-8", "surrogateescape") + b"\xff\xfe\x80"
    conn = Connection(Response(200, {"Content-Type": f"text/plain; charset={charset}"}, body))
    page = _fetch(World([conn]), "https://odd-charset.example/")
    assert page.text.startswith("café")
    assert GuardedPageFetch.decoded(b"\x80abc", f"text/plain; charset={charset}") == "�abc"


@pytest.mark.parametrize(
    ("charset", "raw", "text"),
    [
        ("windows-1252", "café €".encode("cp1252"), "café €"),
        ("ISO-8859-15", "€".encode("iso8859-15"), "€"),
        ("shift_jis", "日本".encode("shift_jis"), "日本"),
        ("utf-16", "hi".encode("utf-16"), "hi"),
        ("gbk", "中".encode("gbk"), "中"),
    ],
)
def test_a_declared_text_codec_is_used(charset: str, raw: bytes, text: str) -> None:
    assert GuardedPageFetch.decoded(raw, f"text/plain; charset={charset}") == text


def test_a_long_server_chosen_content_type_is_never_repeated() -> None:
    kind = "text/" + "a" * 5_000
    conn = Connection(Response(200, {"Content-Type": kind}, b"x"))
    with pytest.raises(WebToolRefused) as raised:
        _fetch(World([conn]), "https://long-type.example/")
    assert "aaaa" not in str(raised.value) and "an unreadable type" in str(raised.value)
    assert len(str(raised.value)) < 200


def test_a_title_is_cut_to_its_bound() -> None:
    body = b"<title>" + b"T" * 5_000 + b"</title><p>x</p>"
    page = _fetch(World([_page(body)]), "https://long-title.example/")
    assert page.title == "T" * 300
    small = WebToolSettings(max_chars=120)
    assert _fetch(World([_page(body)]), "https://long-title.example/", small).title == "T" * 120


def test_the_real_lazy_connection_sends_nothing_once_the_caller_gave_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real `pinned_connect` opens its socket only when asked; the fetch asks for it before
    it checks the deadline, so a socket that opens after the cancel carries no request."""
    opened = threading.Event()
    release = threading.Event()
    sent: list[bytes] = []

    class Sock:
        def sendall(self, data: bytes) -> None:
            sent.append(data)

        def settimeout(self, value: float) -> None:
            return None

        def setsockopt(self, *args: Any) -> None:
            return None

        def shutdown(self, how: int) -> None:
            return None

        def close(self) -> None:
            return None

    def create_connection(address: tuple[str, int], *_: Any, **__: Any) -> Sock:
        opened.set()
        release.wait(5)  # the connect completes only after the caller has given up
        return Sock()

    monkeypatch.setattr(socket, "create_connection", create_connection)
    fetcher = GuardedPageFetch(resolve=lambda host, port: [PUBLIC])
    settings = WebToolSettings(timeout_seconds=0.2)
    try:
        with pytest.raises(WebToolFailed, match="within"):
            asyncio.run(fetcher.fetch(_target("http://lazy.example/", settings), settings))
        assert opened.is_set()
    finally:
        release.set()
    _joined()
    assert sent == []


def test_a_text_codec_that_still_raises_falls_back_to_utf8(monkeypatch: pytest.MonkeyPatch) -> None:
    """The allowlist is the first guard; the decode itself is the second."""
    import vibey.infrastructure.web.guarded_fetch as guarded

    monkeypatch.setattr(guarded, "TEXT_CODECS", guarded.TEXT_CODECS | {"idna"})
    assert GuardedPageFetch.decoded(b"\x80ok", "text/plain; charset=idna") == "�ok"


def test_a_malformed_location_is_a_refusal_with_the_host_it_came_from() -> None:
    hop = Connection(Response(302, {"Location": "http://[::1"}))
    reached: list[str] = []
    fetcher = GuardedPageFetch(resolve=World([]).resolve, connect=World([hop]).connect)
    with pytest.raises(WebToolRefused) as raised:
        asyncio.run(fetcher.fetch(_target("https://drop.example/?d=x"), SETTINGS, reached))
    assert raised.value.hosts == ("drop.example",) and reached == ["drop.example"]


def test_an_unexpected_failure_after_a_redirect_keeps_both_hosts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Text extraction (or anything else the hub did not expect) failing after the page answered
    is a failure that still names every host the fetch reached."""
    import vibey.infrastructure.web.guarded_fetch as guarded

    def broken(markup: str) -> tuple[str, str]:
        raise RecursionError("too deep")

    monkeypatch.setattr(guarded, "html_to_text", broken)
    hop = Connection(Response(302, {"Location": "https://cdn.example/x"}))
    world = World([hop, _page()])
    reached: list[str] = []
    fetcher = GuardedPageFetch(resolve=world.resolve, connect=world.connect)
    with pytest.raises(WebToolFailed, match="RecursionError") as raised:
        asyncio.run(fetcher.fetch(_target("https://docs.example/"), SETTINGS, reached))
    assert raised.value.hosts == ("docs.example", "cdn.example")
    assert reached == ["docs.example", "cdn.example"]
    assert "too deep" not in str(raised.value)


def test_a_cancelled_request_cancels_the_fetch_so_nothing_more_is_sent() -> None:
    """The hub shutting down cancels the request's task; the fetch's thread is cancelled with
    it, and a connection it makes afterwards carries no request."""
    gate = threading.Event()
    entered = threading.Event()
    conn = _page()

    class Slow(World):
        def connect(self, scheme: str, host: str, port: int, ip: str, timeout: float) -> Connection:
            entered.set()  # the connection is being made when the request is cancelled
            gate.wait(5)
            return super().connect(scheme, host, port, ip, timeout)

    world = Slow([conn])
    fetcher = GuardedPageFetch(resolve=world.resolve, connect=world.connect)

    async def drive() -> None:
        task = asyncio.ensure_future(fetcher.fetch(_target("https://slow.example/"), SETTINGS))
        assert await asyncio.to_thread(entered.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(drive())
    gate.set()
    _joined()
    assert conn.closed and conn.requests == []
