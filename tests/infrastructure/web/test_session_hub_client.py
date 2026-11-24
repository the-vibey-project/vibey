# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An engine session's own client to the hub (SP-LOOPS Phase 6, Task 4; R1): search and fetch
as `POST /api/v1/web/{search,fetch}` with the session's token, read from its file on every call,
to a hub on this computer's loopback only, and never the token in an error, a repr or a log.

The hub is an `httpx.MockTransport`; the token file is real (0600 in a 0700 folder), so the
module is POSIX only, as the store is."""

from __future__ import annotations

import logging
import os
import ssl
from pathlib import Path

import httpx
import pytest

from tests.infrastructure.web.session_hub_fakes import (
    FETCH_ANSWER,
    HUB_URL,
    OTHER_TOKEN,
    SEARCH_ANSWER,
    TOKEN,
    StubHub,
    framed,
    raw_token_file,
    replace_token,
    token_file,
)
from vibey.application.dto import WebHit
from vibey.domain.config import ConfigError
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.mcp.hub_gateway import WEB_TIMEOUT_MARGIN
from vibey.infrastructure.web.interfaces.session_hub_client_interface import (
    SessionHubClientInterface,
)
from vibey.infrastructure.web.search import DEFAULT_TIMEOUT_SECONDS
from vibey.infrastructure.web.session import (
    HUB_URL_VARIABLE,
    TOKEN_FILE_VARIABLE,
    SessionWebAccess,
)
from vibey.infrastructure.web.session_hub_client import SessionHubClient, SessionHubError

pytestmark = pytest.mark.skipif(os.name != "posix", reason="token file modes are POSIX")


def _client(path: Path, hub: StubHub, url: str = HUB_URL, **seams: object) -> SessionHubClient:
    return SessionHubClient(
        url,
        path,
        client=hub,
        web_settings=lambda: WebToolSettings(),
        **seams,  # type: ignore[arg-type]
    )


def _refused(call: object) -> SessionHubError:
    with pytest.raises(SessionHubError) as caught:
        call()  # type: ignore[operator]
    return caught.value


def test_the_client_meets_its_seam(tmp_path: Path) -> None:
    assert isinstance(_client(token_file(tmp_path), StubHub()), SessionHubClientInterface)


def test_a_search_posts_to_the_hub_with_the_sessions_token_and_returns_its_answer(
    tmp_path: Path,
) -> None:
    hub = StubHub()
    answer = _client(token_file(tmp_path), hub).search("next js", 3)

    assert answer.backend == "searxng" and answer.notice is None
    assert answer.hits == (
        WebHit("Next.js", "https://nextjs.org", "The React framework"),
        WebHit("Bare", "https://bare.example", ""),
    )
    (request,) = hub.requests
    assert request.method == "POST"
    assert str(request.url) == "http://127.0.0.1:8765/api/v1/web/search"
    assert hub.bearer() == f"Bearer {TOKEN}"
    assert hub.body() == {"query": "next js", "limit": 3}


def test_a_search_without_a_limit_leaves_it_to_the_hub_and_carries_its_notice(
    tmp_path: Path,
) -> None:
    hub = StubHub(answer={**SEARCH_ANSWER, "backend": "brave", "notice": "local SearXNG gone"})
    answer = _client(token_file(tmp_path), hub).search("q", None)

    assert hub.body() == {"query": "q"}
    assert (answer.backend, answer.notice) == ("brave", "local SearXNG gone")


def test_the_token_is_read_from_its_file_on_every_call(tmp_path: Path) -> None:
    path = token_file(tmp_path)
    hub = StubHub()
    client = _client(path, hub)

    client.search("one", None)
    replace_token(path, OTHER_TOKEN)
    client.fetch("https://a.example/")

    assert [r.headers["authorization"] for r in hub.requests] == [
        f"Bearer {TOKEN}",
        f"Bearer {OTHER_TOKEN}",
    ]


def test_a_fetch_returns_the_hubs_framed_page(tmp_path: Path) -> None:
    hub = StubHub()
    page = _client(token_file(tmp_path), hub).fetch("https://a.example/")

    assert str(hub.requests[0].url) == "http://127.0.0.1:8765/api/v1/web/fetch"
    assert hub.body() == {"url": "https://a.example/"}
    assert (page.url, page.title, page.truncated) == ("https://a.example/", "", False)
    assert page.text == FETCH_ANSWER["text"]


def test_max_chars_cuts_the_pages_words_inside_the_frame_never_the_frame(tmp_path: Path) -> None:
    hub = StubHub(answer={**FETCH_ANSWER, "text": framed("abcdefghij")})
    client = _client(token_file(tmp_path), hub)

    cut = client.fetch("https://a.example/", max_chars=4)
    whole = client.fetch("https://a.example/", max_chars=10)

    assert (cut.text, cut.truncated) == (framed("abcd"), True)
    assert (whole.text, whole.truncated) == (framed("abcdefghij"), False)


def test_a_cut_asked_of_an_unframed_page_is_refused_as_unreadable(tmp_path: Path) -> None:
    hub = StubHub(answer={**FETCH_ANSWER, "text": "no frame at all"})
    client = _client(token_file(tmp_path), hub)

    assert client.fetch("https://a.example/").text == "no frame at all"
    refused = _refused(lambda: client.fetch("https://a.example/", max_chars=3))
    assert refused.kind == "failed" and "could not be read" in str(refused)


@pytest.mark.parametrize(
    ("url", "connected"),
    [
        ("http://localhost:9", "http://127.0.0.1:9"),
        ("http://[::1]:9/", "http://[::1]:9"),
        ("http://127.0.0.2:9", "http://127.0.0.2:9"),
    ],
)
def test_only_a_loopback_hub_is_reached_and_by_its_literal(
    tmp_path: Path, url: str, connected: str
) -> None:
    hub = StubHub()
    _client(token_file(tmp_path), hub, url).search("q", None)

    assert hub.opened[0]["base_url"] == connected
    assert hub.opened[0]["verify"] is True


@pytest.mark.parametrize(
    "url",
    [
        "ftp://127.0.0.1:9",
        "http://example.com:9",
        "http://10.0.0.1:9",
        "http://127.0.0.1",
        "http://127.0.0.1:0",
        "http://127.0.0.1:99999",
        "http://user:pw@127.0.0.1:9",
        "http://127.0.0.1:9/api",
        "http://127.0.0.1:9?x=1",
        "http://127.0.0.1:9#f",
        "not a url",
    ],
)
def test_a_hub_address_that_is_not_this_computers_loopback_sends_nothing(
    tmp_path: Path, url: str
) -> None:
    reads: list[Path] = []

    class Tokens:
        def read(self, path: Path) -> str:
            reads.append(path)
            return TOKEN

    hub = StubHub()
    refused = _refused(
        lambda: _client(token_file(tmp_path), hub, url, tokens=Tokens()).search("q", None)
    )

    assert refused.kind == "unconfigured" and HUB_URL_VARIABLE in str(refused)
    assert hub.opened == [] and reads == []


def test_an_https_hub_is_verified_by_its_own_certificate_alone(tmp_path: Path) -> None:
    context = ssl.create_default_context()
    hub = StubHub()
    _client(token_file(tmp_path), hub, "https://127.0.0.1:9", certificate=lambda: context).search(
        "q", None
    )

    assert hub.opened[0]["base_url"] == "https://127.0.0.1:9"
    assert hub.opened[0]["verify"] is context


@pytest.mark.parametrize("error", [OSError("gone"), ValueError("bad"), ConfigError("k", "v")])
def test_an_https_hub_whose_certificate_cannot_be_read_is_sent_nothing(
    tmp_path: Path, error: Exception
) -> None:
    def certificate() -> ssl.SSLContext:
        raise error

    hub = StubHub()
    refused = _refused(
        lambda: _client(
            token_file(tmp_path), hub, "https://127.0.0.1:9", certificate=certificate
        ).search("q", None)
    )

    assert refused.kind == "unconfigured" and "certificate" in str(refused)
    assert hub.opened == []


def test_the_default_certificate_is_the_persons_own_hubs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    config = tmp_path / "vibey.toml"
    config.write_text(f"[hub]\nstate_dir = '{state}'\n")
    monkeypatch.setattr(
        "vibey.infrastructure.web.session_hub_client.personal_config", lambda: config
    )
    monkeypatch.chdir(tmp_path)
    seen: list[Path] = []

    class Certificate:
        def __init__(self, folder: Path) -> None:
            seen.append(folder)

        def client_context(self) -> ssl.SSLContext:
            return ssl.create_default_context()

    monkeypatch.setattr("vibey.infrastructure.web.session_hub_client.HubCertificate", Certificate)

    assert isinstance(SessionHubClient.own_certificate(), ssl.SSLContext)
    assert seen == [state]


def test_the_wait_outlasts_the_hubs_own_web_deadline(tmp_path: Path) -> None:
    hub = StubHub()
    slow = WebToolSettings(timeout_seconds=100.0)
    SessionHubClient(HUB_URL, token_file(tmp_path), client=hub, web_settings=lambda: slow).search(
        "q", None
    )

    assert hub.opened[0]["timeout"] == 100.0 + WEB_TIMEOUT_MARGIN


def test_a_web_setting_that_cannot_be_read_waits_as_long_as_the_defaults(tmp_path: Path) -> None:
    def unreadable() -> WebToolSettings:
        raise ConfigError("web", "broken")

    hub = StubHub()
    SessionHubClient(HUB_URL, token_file(tmp_path), client=hub, web_settings=unreadable).search(
        "q", None
    )

    expected = max(WebToolSettings().timeout_seconds, 3 * DEFAULT_TIMEOUT_SECONDS)
    assert hub.opened[0]["timeout"] == expected + WEB_TIMEOUT_MARGIN


def test_the_default_web_settings_are_the_persons_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "vibey.infrastructure.web.session_hub_client.own_web_settings",
        lambda: WebToolSettings(timeout_seconds=70.0),
    )
    hub = StubHub()
    SessionHubClient(HUB_URL, token_file(tmp_path), client=hub).search("q", None)

    assert hub.opened[0]["timeout"] == 70.0 + WEB_TIMEOUT_MARGIN


def test_a_missing_token_file_is_named_and_nothing_is_sent(tmp_path: Path) -> None:
    missing = tmp_path / "gone" / "web-token"
    hub = StubHub()
    refused = _refused(lambda: _client(missing, hub).search("q", None))

    assert refused.kind == "unconfigured"
    assert str(missing) in str(refused) and "does not exist" in str(refused)
    assert hub.opened == []


@pytest.mark.parametrize(
    ("content", "said"),
    [
        (b"", "holds no token"),
        (b"   \n", "holds no token"),
        (b"\xff\xfe", "holds no usable token"),
        (b"tok en", "holds no usable token"),
        ("tök".encode(), "holds no usable token"),
    ],
)
def test_a_token_file_without_a_usable_token_is_named_and_nothing_is_sent(
    tmp_path: Path, content: bytes, said: str
) -> None:
    path = raw_token_file(tmp_path, content)
    hub = StubHub()
    refused = _refused(lambda: _client(path, hub).fetch("https://a.example/"))

    assert refused.kind == "unconfigured"
    assert str(path) in str(refused) and said in str(refused)
    assert hub.opened == []


def test_a_token_file_open_to_others_is_refused_by_the_store(tmp_path: Path) -> None:
    path = token_file(tmp_path)
    os.chmod(path, 0o644)
    hub = StubHub()
    refused = _refused(lambda: _client(path, hub).search("q", None))

    assert refused.kind == "unconfigured" and "open to other accounts" in str(refused)
    assert TOKEN not in str(refused) and hub.opened == []


def test_an_argument_the_hub_would_refuse_is_refused_before_anything_is_read(
    tmp_path: Path,
) -> None:
    hub = StubHub()
    refused = _refused(lambda: _client(token_file(tmp_path), hub).search("q" * 10_000, None))

    assert refused.kind == "refused" and "query" in str(refused)
    assert hub.opened == []


@pytest.mark.parametrize(
    ("status", "answer", "kind", "said"),
    [
        (401, {"detail": "Unauthorized"}, "ended", "web access has ended"),
        (403, {"detail": "a session may not do that"}, "forbidden", "a session may not do that"),
        (403, b"", "forbidden", "HTTP 403"),
        (
            429,
            {"detail": "web budget exhausted: session:x has used [web] session_searches = 30"},
            "budget",
            "web budget exhausted: session:x has used [web] session_searches = 30",
        ),
        (429, b"slow down", "budget", "HTTP 429"),
        (502, {"detail": "no search backend answered"}, "failed", "no search backend answered"),
        (503, {"detail": "\x1b]0;x\x07search is not set up"}, "failed", "search is not set up"),
        (422, {"detail": [{"loc": ["body"], "msg": "bad"}]}, "failed", "HTTP 422"),
    ],
)
def test_the_hubs_refusals_are_said_plainly_by_kind(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    status: int,
    answer: object,
    kind: str,
    said: str,
) -> None:
    caplog.set_level(logging.DEBUG)
    hub = StubHub(status, answer)
    refused = _refused(lambda: _client(token_file(tmp_path), hub).search("q", None))

    assert refused.kind == kind and said in str(refused)
    assert "\x1b" not in str(refused) and TOKEN not in str(refused)
    assert TOKEN not in caplog.text and TOKEN not in repr(refused.args)


def test_a_call_that_succeeds_logs_nothing_of_the_token(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client = _client(token_file(tmp_path), StubHub())
    client.search("q", None)
    client.fetch("https://a.example/")

    assert TOKEN not in caplog.text


def test_a_budget_refusal_is_the_hubs_own_words(tmp_path: Path) -> None:
    words = "web budget exhausted: agent has used [web] fetches_per_hour = 5 for this hour"
    hub = StubHub(429, {"detail": words})
    refused = _refused(lambda: _client(token_file(tmp_path), hub).fetch("https://a.example/"))

    assert str(refused) == words


@pytest.mark.parametrize(
    ("error", "said"),
    [
        (httpx.ConnectError("refused"), "ConnectError"),
        (httpx.ReadTimeout("slow"), "not sent again"),
    ],
)
def test_a_hub_that_does_not_answer_is_one_line_and_is_never_asked_twice(
    tmp_path: Path, error: Exception, said: str
) -> None:
    hub = StubHub(fail=error)
    refused = _refused(lambda: _client(token_file(tmp_path), hub).search("q", None))

    assert refused.kind == "unreachable" and said in str(refused)
    assert "\n" not in str(refused) and len(hub.requests) == 1
    assert TOKEN not in str(refused) and TOKEN not in repr(refused)
    assert refused.__cause__ is None and refused.__suppress_context__


@pytest.mark.parametrize(
    "answer",
    [
        b"not json",
        b"[1, 2]",
        {"backend": 1, "results": []},
        {"backend": "searxng", "results": "x"},
        {"backend": "searxng", "results": [], "notice": 3},
        {"backend": "searxng", "results": [{"title": "t", "url": "u"}]},
        {"backend": "searxng", "results": ["x"]},
    ],
)
def test_a_search_answer_that_cannot_be_read_fails(tmp_path: Path, answer: object) -> None:
    refused = _refused(lambda: _client(token_file(tmp_path), StubHub(200, answer)).search("q", 1))

    assert refused.kind == "failed" and "could not be read" in str(refused)


@pytest.mark.parametrize(
    "answer",
    [
        {"url": 1, "truncated": False, "text": "t"},
        {"url": "u", "truncated": "no", "text": "t"},
        {"url": "u", "truncated": False, "text": None},
    ],
)
def test_a_fetch_answer_that_cannot_be_read_fails(tmp_path: Path, answer: object) -> None:
    refused = _refused(
        lambda: _client(token_file(tmp_path), StubHub(200, answer)).fetch("https://a.example/")
    )

    assert refused.kind == "failed"


def test_the_token_is_never_in_a_repr(tmp_path: Path) -> None:
    client = _client(token_file(tmp_path), StubHub())
    client.search("q", None)

    assert TOKEN not in repr(client) and "SessionHubClient(" in repr(client)


def test_a_client_is_made_from_the_sessions_access(tmp_path: Path) -> None:
    path = token_file(tmp_path)
    access = SessionWebAccess.from_environment(
        {HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: str(path)}
    )

    client = SessionHubClient.for_access(access)

    assert isinstance(client, SessionHubClient)
    assert str(path) in repr(client) and "127.0.0.1:8765" in repr(client)


def test_a_client_is_never_made_for_access_that_has_no_hub() -> None:
    with pytest.raises(ValueError, match="no hub"):
        SessionHubClient.for_access(SessionWebAccess.from_environment({}))
