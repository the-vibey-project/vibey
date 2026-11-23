# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey fetch`, the DESIGN research and the local runners' `web_fetch` read a page through the
hub's guarded fetch, never a weaker one (SP-ACP Task 11a, P-9b-2).

The SSRF table is the Task 9b review's: every spelling of an address, every name that only ever
reaches this computer or a cloud's metadata service, a DNS answer that changes, and redirects
inward or down to http. Every resolver and connection is a fake: nothing touches a network, and
nothing here depends on how threads are scheduled (the fakes answer at once)."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from vibey.domain.config import ConfigError
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.web import page_fetcher as module
from vibey.infrastructure.web.fetch import WebFetchError
from vibey.infrastructure.web.guarded_fetch import GuardedPageFetch
from vibey.infrastructure.web.interfaces.page_fetcher_interface import PageFetcherInterface
from vibey.infrastructure.web.page_fetcher import PageFetcher

PUBLIC = "93.184.216.34"
_OWN_WEB_SETTINGS = module.own_web_settings
"""The real lookup, taken before the suite's hermetic fixture stands another in."""


class Response:
    def __init__(
        self, status: int = 200, headers: dict[str, str] | None = None, body: bytes = b""
    ) -> None:
        self.status = status
        self._headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._body = body

    def getheader(self, name: str, default: str | None = None) -> str | None:
        return self._headers.get(name.lower(), default)

    def read(self, amount: int | None = None) -> bytes:
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
    def __init__(
        self,
        connections: Sequence[Connection] = (),
        answers: dict[str, list[list[str]]] | None = None,
    ) -> None:
        self.queue = list(connections)
        self.answers = {name: list(seq) for name, seq in (answers or {}).items()}
        self.made: list[tuple[str, str, int, str]] = []

    def resolve(self, host: str, port: int) -> list[str]:
        answers = self.answers.get(host)
        return answers.pop(0) if answers else [PUBLIC]

    def connect(self, scheme: str, host: str, port: int, ip: str, timeout: float) -> Connection:
        self.made.append((scheme, host, port, ip))
        return self.queue.pop(0)


def _fetcher(world: World, settings: WebToolSettings | None = None) -> PageFetcher:
    chosen = settings or WebToolSettings()
    return PageFetcher(
        settings=lambda: chosen,
        fetch=GuardedPageFetch(resolve=world.resolve, connect=world.connect),
    )


def _text(body: bytes = b"<title>T</title><p>Hello</p>", kind: str = "text/html") -> Connection:
    return Connection(Response(200, {"Content-Type": f"{kind}; charset=utf-8"}, body))


def test_the_fetcher_meets_its_seam() -> None:
    assert isinstance(PageFetcher(), PageFetcherInterface)


def test_a_page_comes_back_as_text_over_the_checked_address() -> None:
    conn = _text()
    world = World([conn])
    page = _fetcher(world).fetch("https://docs.example/a?b=c")
    assert (page.url, page.title, page.text, page.truncated) == (
        "https://docs.example/a?b=c",
        "T",
        "Hello",
        False,
    )
    assert world.made == [("https", "docs.example", 443, PUBLIC)]
    ((_, _, headers),) = conn.requests
    assert headers["Accept-Encoding"] == "identity" and "Cookie" not in headers


SSRF = [
    "http://127.0.0.1/",
    "http://2130706433/",
    "http://017700000001/",
    "http://0x7f000001/",
    "http://0x7f.0.0.1/",
    "http://127.1/",
    "http://0177.0.0.1/",
    "http://[::1]/",
    "http://[::]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[::ffff:7f00:1]/",
    "http://[::ffff:169.254.169.254]/",
    "http://[64:ff9b::7f00:1]/",
    "http://[64:ff9b::a9fe:a9fe]/",
    "http://[64:ff9b:1::a00:1]/",
    "http://[2002:7f00:1::1]/",
    "http://[fe80::1]/",
    "http://[fc00::1]/",
    "http://[fec0::1]/",
    "http://10.0.0.1/",
    "http://192.168.1.1/",
    "http://172.16.0.1/",
    "http://100.64.0.1/",
    "http://0.0.0.0/",
    "http://169.254.169.254/latest/meta-data/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "http://metadata/",
    "http://instance-data/",
    "http://localhost/",
    "http://LOCALHOST./",
    "http://evil.localhost/",
    "http://printer.local/",
    "http://db.internal/",
    "http://router.lan/",
    "https://user:pw@example.org/",
    "ftp://example.org/",
    "file:///etc/passwd",
    "gopher://example.org/",
    "http://example.org:0/",
    "http://exa mple.org/",
]


@pytest.mark.parametrize("url", SSRF)
def test_no_spelling_of_a_private_or_local_target_is_ever_connected_to(url: str) -> None:
    world = World()
    with pytest.raises(WebFetchError, match="refused") as caught:
        _fetcher(world).fetch(url)
    assert world.made == []
    assert "pw" not in str(caught.value)


@pytest.mark.parametrize(
    "answer",
    [
        ["127.0.0.1"],
        [PUBLIC, "127.0.0.1"],
        ["169.254.169.254"],
        ["10.0.0.5"],
        ["::1"],
        ["::ffff:127.0.0.1"],
        ["64:ff9b::a00:1"],
        ["fd00::1"],
    ],
)
def test_a_name_that_resolves_to_any_private_address_is_refused(answer: list[str]) -> None:
    world = World(answers={"rebind.example": [answer]})
    with pytest.raises(WebFetchError, match="not a public address"):
        _fetcher(world).fetch("https://rebind.example/")
    assert world.made == []


def test_dns_rebinding_cannot_steer_the_connection_inward() -> None:
    """The name answers public once and private after: the connection goes to the address that
    was checked, and the name is never asked again within a hop."""
    world = World([_text()], answers={"rebind.example": [[PUBLIC], ["127.0.0.1"]]})
    _fetcher(world).fetch("https://rebind.example/")
    assert world.made == [("https", "rebind.example", 443, PUBLIC)]


@pytest.mark.parametrize(
    "location",
    [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:8765/api/v1/",
        "http://[::1]/",
        "http://localhost/",
        "http://2130706433/",
        "http://innocent.example/downgraded",
    ],
)
def test_a_redirect_inward_or_down_to_http_stops_there(location: str) -> None:
    hop = Connection(Response(302, {"Location": location}))
    world = World([hop])
    with pytest.raises(WebFetchError, match="refused"):
        _fetcher(world).fetch("https://innocent.example/")
    assert len(world.made) == 1 and hop.closed


def test_a_redirect_to_a_name_resolving_inward_is_refused() -> None:
    hop = Connection(Response(301, {"Location": "https://inside.example/"}))
    world = World([hop], answers={"inside.example": [["10.1.2.3"]]})
    with pytest.raises(WebFetchError, match="not a public address"):
        _fetcher(world).fetch("https://innocent.example/")
    assert len(world.made) == 1


def test_redirects_are_followed_within_the_bound_and_each_is_checked() -> None:
    first = Connection(Response(302, {"Location": "/moved"}))
    world = World([first, _text(b"arrived", "text/plain")])
    page = _fetcher(world).fetch("https://start.example/old")
    assert page.url == "https://start.example/moved" and page.text == "arrived"
    loop = [Connection(Response(302, {"Location": "https://loop.example/"})) for _ in range(4)]
    with pytest.raises(WebFetchError, match="stopped after 3 redirects"):
        _fetcher(World(loop)).fetch("https://loop.example/")


def test_a_compressed_page_is_refused_before_its_body_is_read() -> None:
    conn = Connection(
        Response(200, {"Content-Type": "text/html", "Content-Encoding": "gzip"}, b"\x1f\x8b")
    )
    with pytest.raises(WebFetchError, match="compressed"):
        _fetcher(World([conn])).fetch("https://zip.example/")


def test_a_binary_type_is_refused_never_extracted() -> None:
    conn = Connection(Response(200, {"Content-Type": "application/pdf"}, b"%PDF"))
    with pytest.raises(WebFetchError, match="binary types are refused"):
        _fetcher(World([conn])).fetch("https://doc.example/a.pdf")


def test_the_persons_web_hosts_are_honoured() -> None:
    denied = WebToolSettings(deny_hosts=("blocked.example",))
    with pytest.raises(WebFetchError, match="deny_hosts"):
        _fetcher(World(), denied).fetch("https://www.blocked.example/")
    allowed = WebToolSettings(allow_hosts=("docs.example",))
    with pytest.raises(WebFetchError, match="allow_hosts"):
        _fetcher(World(), allowed).fetch("https://elsewhere.example/")
    world = World([_text()])
    assert _fetcher(world, allowed).fetch("https://api.docs.example/").text == "Hello"


def test_a_caller_may_lower_max_chars_never_raise_it() -> None:
    body = b"x" * 500
    narrow = WebToolSettings(max_chars=200)
    page = _fetcher(World([_text(body, "text/plain")]), narrow).fetch(
        "https://a.example/", max_chars=10_000
    )
    assert len(page.text) == 200 and page.truncated
    page = _fetcher(World([_text(body, "text/plain")])).fetch("https://a.example/", max_chars=150)
    assert len(page.text) == 150 and page.truncated


def test_a_failure_is_named_by_type_and_never_shows_the_url() -> None:
    conn = Connection(error=ConnectionResetError("secret-host"))
    with pytest.raises(WebFetchError, match="could not be fetched") as caught:
        _fetcher(World([conn])).fetch("https://secret-host.example/?token=abc")
    assert "secret-host" not in str(caught.value) and "abc" not in str(caught.value)


def test_web_settings_that_cannot_be_read_refuse_the_fetch() -> None:
    def broken() -> WebToolSettings:
        raise ConfigError("vibey.toml", "[web] max_chars must be a whole number")

    world = World()
    with pytest.raises(WebFetchError, match=r"\[web\] cannot be read"):
        PageFetcher(settings=broken, fetch=GuardedPageFetch(connect=world.connect)).fetch(
            "https://a.example/"
        )
    assert world.made == []


def test_the_settings_are_the_persons_own_narrowed_by_the_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "config"
    home.mkdir()
    (home / "vibey.toml").write_text("[web]\nmax_chars = 5000\n")
    project = tmp_path / "project"
    project.mkdir()
    (project / "vibey.toml").write_text("[web]\nmax_chars = 900000\ndeny_hosts = ['bad.example']\n")
    monkeypatch.setattr(module.UserConfigFolder, "path", lambda self: home)
    monkeypatch.chdir(project)
    settings = _OWN_WEB_SETTINGS()
    assert settings.max_chars == 5000 and settings.deny_hosts == ("bad.example",)


@pytest.mark.parametrize(
    ("kind", "body"),
    [
        ("text/html", b"<title>T\x1b]0;owned\x07</title><p>a\x1b]52;c;ZXZpbA==\x07b\x1b[2Jc</p>"),
        ("text/plain", b"a\x1b]52;c;ZXZpbA==\x07b\x1b[2Jc"),
    ],
)
def test_a_page_reaches_its_reader_with_no_terminal_control(kind: str, body: bytes) -> None:
    page = _fetcher(World([_text(body, kind)])).fetch("https://evil.example/")
    assert page.text == "abc" and "\x1b" not in page.title + page.text
