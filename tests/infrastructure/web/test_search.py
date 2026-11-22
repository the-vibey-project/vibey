# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The search backends and the environment that configures them: a local SearXNG first, always,
and Brave only as a backup (operator ruling 2026-11-21). Every key here is a fake."""

import http.client
import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

import pytest

from tests.infrastructure.web.searxng_fakes import SEARXNG_CONFIG, FakeResponse, is_config
from vibey.domain.config import ConfigError
from vibey.infrastructure.web.guarded_opener import GuardedOpener
from vibey.infrastructure.web.search import (
    DEFAULT_SEARXNG_URL,
    IMPOSTOR,
    BraveBackend,
    SearxngBackend,
    WebSearchError,
    WebSearchSettings,
    display_url,
)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.asked: list[int | None] = []

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, amount: int | None = None) -> bytes:
        self.asked.append(amount)
        return self._payload


def _opener(body: object, seen: list[tuple[str, dict[str, str], float]] | None = None) -> Any:
    """A SearXNG that identifies as one on `/config` and answers every other request with
    `body`; `seen` records those other requests."""
    payload = body if isinstance(body, bytes) else json.dumps(body).encode()

    def opener(request: urllib.request.Request, timeout: float) -> Any:
        if is_config(request):
            return FakeResponse(SEARXNG_CONFIG, url=request.full_url)
        if seen is not None:
            seen.append((request.full_url, dict(request.header_items()), timeout))
        return _Response(payload)

    return opener


def _raising(error: BaseException) -> Any:
    def opener(request: urllib.request.Request, timeout: float) -> _Response:
        raise error

    return opener


# -- the settings ---------------------------------------------------------------------------


def test_with_nothing_set_search_is_the_local_searxng_on_loopback() -> None:
    settings = WebSearchSettings.from_environment({})
    assert DEFAULT_SEARXNG_URL == "http://127.0.0.1:28180"
    assert settings.searxng_url == DEFAULT_SEARXNG_URL
    assert settings.searxng_url_env is None
    assert settings.brave_key is None and settings.brave_key_env is None
    assert not settings.has_backup
    blank = WebSearchSettings.from_environment(
        {"VIBEY_SEARXNG_URL": "  ", "VIBEY_BRAVE_API_KEY": ""}
    )
    assert blank.searxng_url == DEFAULT_SEARXNG_URL and not blank.has_backup


def test_a_configured_url_replaces_the_default_and_says_where_it_came_from() -> None:
    settings = WebSearchSettings.from_environment({"VIBEY_SEARXNG_URL": "http://search.lan:8888"})
    assert settings.searxng_url == "http://search.lan:8888"
    assert settings.searxng_url_env == "VIBEY_SEARXNG_URL"


def test_a_brave_key_is_a_backup_and_never_the_primary() -> None:
    settings = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": "fake-k"})
    assert settings.searxng_url == DEFAULT_SEARXNG_URL
    assert settings.has_backup and settings.brave_key_env == "VIBEY_BRAVE_API_KEY"


@pytest.mark.parametrize("value", ["", "searxng", " SearXNG "])
def test_the_provider_setting_accepts_searxng_or_nothing(value: str) -> None:
    settings = WebSearchSettings.from_environment({"VIBEY_SEARCH_PROVIDER": value})
    assert settings.searxng_url == DEFAULT_SEARXNG_URL


@pytest.mark.parametrize("environ", [{}, {"VIBEY_BRAVE_API_KEY": "fake-k"}])
def test_choosing_brave_as_the_provider_is_refused_and_says_how_to_use_it(
    environ: dict[str, str],
) -> None:
    with pytest.raises(ConfigError) as caught:
        WebSearchSettings.from_environment({**environ, "VIBEY_SEARCH_PROVIDER": "brave"})
    said = str(caught.value)
    assert said.startswith("VIBEY_SEARCH_PROVIDER: ")
    assert "backup" in said and "VIBEY_BRAVE_API_KEY" in said and "BRAVE_SEARCH_API_KEY" in said
    assert "unset" in said and "fake-k" not in said


@pytest.mark.parametrize(
    ("environ", "needle"),
    [
        ({"VIBEY_SEARCH_PROVIDER": "bing"}, "must be searxng"),
        ({"VIBEY_SEARXNG_URL": "ftp://host"}, r"must be an http\(s\) URL"),
        ({"VIBEY_SEARXNG_URL": "http://"}, r"must be an http\(s\) URL"),
    ],
)
def test_a_setting_that_cannot_be_honoured_is_refused_by_name(
    environ: dict[str, str], needle: str
) -> None:
    with pytest.raises(ConfigError, match=needle):
        WebSearchSettings.from_environment(environ)


def test_a_bad_url_is_never_echoed_because_it_can_carry_credentials() -> None:
    with pytest.raises(ConfigError) as caught:
        WebSearchSettings.from_environment({"VIBEY_SEARXNG_URL": "ftp://user:sekret@host"})
    assert "sekret" not in str(caught.value)


def test_timeout_and_result_count_are_read_and_checked() -> None:
    settings = WebSearchSettings.from_environment(
        {"VIBEY_SEARCH_TIMEOUT": "7.5", "VIBEY_SEARCH_RESULTS": "8"}
    )
    assert (settings.timeout_seconds, settings.results) == (7.5, 8)
    default = WebSearchSettings.from_environment({})
    assert (default.timeout_seconds, default.results) == (15.0, 5)
    for name, value, needle in [
        ("VIBEY_SEARCH_TIMEOUT", "soon", "must be a number of seconds"),
        ("VIBEY_SEARCH_TIMEOUT", "0", "finite number above zero"),
        ("VIBEY_SEARCH_TIMEOUT", "nan", "finite number above zero"),
        ("VIBEY_SEARCH_TIMEOUT", "inf", "finite number above zero"),
        ("VIBEY_SEARCH_RESULTS", "many", "must be a whole number"),
        ("VIBEY_SEARCH_RESULTS", "0", "between 1 and 20"),
        ("VIBEY_SEARCH_RESULTS", "21", "between 1 and 20"),
    ]:
        with pytest.raises(ConfigError, match=needle):
            WebSearchSettings.from_environment({name: value})


def test_a_session_reads_the_same_settings_under_websearch_names() -> None:
    settings = WebSearchSettings.from_environment(
        {
            "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:8081",
            "WEBSEARCH_TIMEOUT": "3",
            "WEBSEARCH_RESULTS": "2",
        }
    )
    assert (settings.searxng_url, settings.timeout_seconds, settings.results) == (
        "http://127.0.0.1:8081",
        3.0,
        2,
    )
    assert settings.searxng_url_env == "WEBSEARCH_SEARXNG_URL"


def test_the_vibey_name_wins_over_its_websearch_alias() -> None:
    settings = WebSearchSettings.from_environment(
        {"VIBEY_SEARXNG_URL": "http://a:1", "WEBSEARCH_SEARXNG_URL": "http://b:2"}
    )
    assert settings.searxng_url == "http://a:1"


def test_what_a_session_is_told_is_enough_to_rebuild_the_same_settings_without_the_key() -> None:
    worker = WebSearchSettings.from_environment(
        {
            "VIBEY_SEARXNG_URL": "http://127.0.0.1:8080",
            "VIBEY_SEARCH_TIMEOUT": "9",
            "VIBEY_SEARCH_RESULTS": "6",
            "BRAVE_SEARCH_API_KEY": "fake-sekret",
        }
    )
    told = worker.session_environment()
    assert told == {
        "WEBSEARCH_PROVIDER": "searxng",
        "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:8080",
        "WEBSEARCH_TIMEOUT": "9.0",
        "WEBSEARCH_RESULTS": "6",
        "WEBSEARCH_IDENTITY_TTL": "60.0",
    }
    rebuilt = WebSearchSettings.from_environment(told)
    assert (rebuilt.searxng_url, rebuilt.timeout_seconds, rebuilt.results) == (
        worker.searxng_url,
        worker.timeout_seconds,
        worker.results,
    )
    assert not rebuilt.has_backup and "fake-sekret" not in repr(told)


def test_a_session_is_told_the_default_url_when_none_is_set() -> None:
    told = WebSearchSettings.from_environment({}).session_environment()
    assert told["WEBSEARCH_SEARXNG_URL"] == DEFAULT_SEARXNG_URL
    assert told["WEBSEARCH_PROVIDER"] == "searxng"


@pytest.mark.parametrize(
    ("url", "shown"),
    [
        ("http://127.0.0.1:8080", "http://127.0.0.1:8080"),
        ("https://me:pw@search.lan/searx/?token=t#x", "https://search.lan/searx/"),
        ("http://[::1]:8888/", "http://[::1]:8888/"),
        ("http://search.lan", "http://search.lan"),
    ],
)
def test_a_url_is_shown_without_credentials_a_query_or_a_fragment(url: str, shown: str) -> None:
    assert display_url(url) == shown


# -- the backends ---------------------------------------------------------------------------


def test_searxng_is_asked_for_json_and_its_results_are_cleaned() -> None:
    seen: list[tuple[str, dict[str, str], float]] = []
    body = {
        "results": [
            {
                "title": "<b>Next.js</b> docs",
                "url": "https://nextjs.org/docs",
                "content": "Use &amp; <i>read</i>",
            },
            {"title": "ftp thing", "url": "ftp://x/y", "content": "dropped"},
            {"url": "https://no-title.example", "content": ""},
            "not a dict",
            {"title": "third", "url": "https://c.example", "content": "c"},
        ]
    }
    backend = SearxngBackend(
        "http://127.0.0.1:8080/", timeout_seconds=9, opener=_opener(body, seen)
    )

    hits = backend.search("next intl rtl", 2)

    assert [h.url for h in hits] == ["https://nextjs.org/docs", "https://no-title.example"]
    assert hits[0].title == "Next.js docs" and hits[0].snippet == "Use & read"
    assert hits[1].title == "https://no-title.example"
    url, headers, timeout = seen[0]
    assert url == "http://127.0.0.1:8080/search?q=next+intl+rtl&format=json"
    assert headers["Accept"] == "application/json" and timeout == 9


def test_a_healthy_searxng_with_no_results_is_no_results_not_a_failure() -> None:
    assert SearxngBackend("http://h", opener=_opener({"results": []})).search("q", 5) == []
    ok = {"results": [], "unresponsive_engines": []}
    assert SearxngBackend("http://h", opener=_opener(ok)).search("q", 5) == []


@pytest.mark.parametrize("body", [{}, {"results": "no"}, {"results": None}])
def test_a_searxng_answer_without_a_results_list_is_malformed(body: object) -> None:
    with pytest.raises(WebSearchError, match="searxng did not answer with a results list"):
        SearxngBackend("http://h", opener=_opener(body)).search("q", 5)


def test_a_searxng_whose_engines_all_failed_has_failed() -> None:
    body = {
        "results": [],
        "unresponsive_engines": [["duckduckgo", "timeout"], ["brave", "CAPTCHA"]],
    }
    with pytest.raises(WebSearchError) as caught:
        SearxngBackend("http://h", opener=_opener(body)).search("q", 5)
    assert caught.value.reason == "every engine it asked failed (1 unresponsive)"
    assert str(caught.value) == "searxng every engine it asked failed (1 unresponsive)"


def test_a_searxng_with_results_and_some_failed_engines_still_answers() -> None:
    body = {
        "results": [{"title": "T", "url": "https://t.example", "content": ""}],
        "unresponsive_engines": [["duckduckgo", "timeout"]],
    }
    hits = SearxngBackend("http://h", opener=_opener(body)).search("q", 5)
    assert [h.url for h in hits] == ["https://t.example"]


def test_brave_sends_its_key_as_a_header_and_never_in_the_url() -> None:
    seen: list[tuple[str, dict[str, str], float]] = []
    body = {
        "web": {
            "results": [
                {"title": "T", "url": "https://t.example", "description": "<strong>D</strong>"}
            ]
        }
    }
    backend = BraveBackend("fake-secret-key", opener=_opener(body, seen))

    hits = backend.search("q", 3)

    assert [(h.title, h.snippet) for h in hits] == [("T", "D")]
    url, headers, _ = seen[0]
    assert url == "https://api.search.brave.com/res/v1/web/search?q=q&count=3"
    assert "fake-secret-key" not in url and headers["X-subscription-token"] == "fake-secret-key"


def test_the_brave_key_is_not_in_the_backends_repr() -> None:
    assert "fake-secret-key" not in repr(BraveBackend("fake-secret-key", opener=_opener({})))


@pytest.mark.parametrize("body", [{}, {"web": "no"}, {"web": {"results": 3}}, {"web": {}}])
def test_a_brave_answer_without_results_is_no_results(body: object) -> None:
    assert BraveBackend("k", opener=_opener(body)).search("q", 5) == []


def test_a_failing_backend_is_named_and_never_leaks_the_url_query_or_key() -> None:
    http_error = urllib.error.HTTPError(
        "https://api/?q=private+thing&key=sekret",
        503,
        "x",
        {},  # type: ignore[arg-type]
        None,
    )
    with pytest.raises(WebSearchError, match="brave answered HTTP 503") as caught:
        BraveBackend("sekret", opener=_raising(http_error)).search("private thing", 1)
    assert caught.value.reason == "answered HTTP 503"
    assert "sekret" not in str(caught.value) and "private" not in str(caught.value)
    refused = urllib.error.URLError(ConnectionRefusedError("http://h/search?q=private"))
    with pytest.raises(WebSearchError) as unreachable:
        SearxngBackend("http://h", opener=_raising(refused)).search("private", 1)
    assert unreachable.value.reason == "could not be reached (ConnectionRefusedError)"
    assert "private" not in str(unreachable.value)
    with pytest.raises(WebSearchError, match="searxng could not be reached"):
        SearxngBackend("http://h", opener=_raising(TimeoutError("q=private"))).search("q", 1)
    with pytest.raises(WebSearchError, match=r"could not be reached \(RemoteDisconnected\)"):
        bad = _raising(http.client.RemoteDisconnected("q=private"))
        SearxngBackend("http://h", opener=bad).search("q", 1)
    with pytest.raises(WebSearchError, match=r"could not be reached \(BadStatusLine\)"):
        SearxngBackend("http://h", opener=_raising(http.client.BadStatusLine("x"))).search("q", 1)
    with pytest.raises(WebSearchError, match="did not answer with JSON"):
        SearxngBackend("http://h", opener=_opener(b"not json")).search("q", 1)
    with pytest.raises(WebSearchError, match="did not answer with a JSON object"):
        SearxngBackend("http://h", opener=_opener([1, 2])).search("q", 1)


def test_a_url_error_without_an_exception_reason_is_named_by_its_own_type() -> None:
    with pytest.raises(WebSearchError) as caught:
        SearxngBackend("http://h", opener=_raising(urllib.error.URLError("no"))).search("q", 1)
    assert caught.value.reason == "could not be reached (URLError)"


def test_what_is_read_from_a_backend_is_bounded() -> None:
    response = _Response(b'{"results": []}')

    def opener(request: urllib.request.Request, timeout: float) -> Any:
        if is_config(request):
            return FakeResponse(SEARXNG_CONFIG, url=request.full_url)
        return response

    SearxngBackend("http://h", opener=opener).search("q", 1)
    assert response.asked == [2_000_000]


def test_each_backend_opens_through_the_guarded_opener_by_default() -> None:
    searx = SearxngBackend("http://127.0.0.1:8080")
    brave = BraveBackend("fake-k")
    assert isinstance(searx._opener, GuardedOpener) and isinstance(brave._opener, GuardedOpener)


# -- the identity check: only a SearXNG is believed ----------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _site(config: object, body: object = None, *, redirected: bool = False) -> Any:
    """Something listening where SearXNG should be: `config` on `/config`, `body` elsewhere."""
    asked: list[str] = []

    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        asked.append(request.full_url)
        if is_config(request):
            landed = request.full_url + ("/login" if redirected else "")
            return FakeResponse(config, url=landed)
        return FakeResponse({"results": [{"title": "P", "url": "https://poison.example"}]}
                            if body is None else body, url=request.full_url)  # fmt: skip

    opener.asked = asked  # type: ignore[attr-defined]
    return opener


@pytest.mark.parametrize(
    ("config", "why"),
    [
        (b"<html><body>Jenkins</body></html>", "its /config is not JSON"),
        ({"status": "ok", "app": "something"}, "its /config is not SearXNG's"),
        ([1, 2, 3], "its /config is not SearXNG's"),
        ({**SEARXNG_CONFIG, "engines": "all"}, "its /config is not SearXNG's"),
        ({**SEARXNG_CONFIG, "instance_name": 7}, "its /config is not SearXNG's"),
    ],
)
def test_a_squatter_on_the_searxng_port_is_refused_and_its_results_never_read(
    config: object, why: str
) -> None:
    site = _site(config)
    with pytest.raises(WebSearchError) as caught:
        SearxngBackend("http://127.0.0.1:28180", opener=site).search("q", 5)
    assert caught.value.reason == f"something other than SearXNG is listening there ({why})"
    assert [url.rsplit("/", 1)[-1] for url in site.asked] == ["config"]


def test_a_config_that_redirects_is_refused() -> None:
    site = _site(SEARXNG_CONFIG, redirected=True)
    with pytest.raises(WebSearchError, match=r"its /config redirected"):
        SearxngBackend("http://127.0.0.1:28180", opener=site).search("q", 5)


def test_a_real_looking_searxng_is_believed_and_its_results_used() -> None:
    site = _site(SEARXNG_CONFIG, {"results": [{"title": "R", "url": "https://r.example"}]})
    hits = SearxngBackend("http://127.0.0.1:28180", opener=site).search("q", 5)
    assert [h.url for h in hits] == ["https://r.example"]
    assert site.asked[0] == "http://127.0.0.1:28180/config"


def test_with_a_marker_only_the_marked_instance_is_believed() -> None:
    copied = {**SEARXNG_CONFIG, "instance_name": "SearXNG"}
    with pytest.raises(WebSearchError) as caught:
        SearxngBackend("http://h", opener=_site(copied), instance="vibey-7f3a").search("q", 5)
    assert caught.value.reason == (
        "a SearXNG other than the expected one is listening there"
        " (its instance_name is not VIBEY_SEARXNG_INSTANCE)"
    )
    assert 'SearXNG"' not in str(caught.value) and "vibey-7f3a" not in str(caught.value)
    ours = {**SEARXNG_CONFIG, "instance_name": "vibey-7f3a"}
    assert SearxngBackend("http://h", opener=_site(ours), instance="vibey-7f3a").search("q", 5)


def test_an_identity_that_is_believed_is_kept_for_the_ttl_then_checked_again() -> None:
    clock = _Clock()
    site = _site(SEARXNG_CONFIG)
    first = SearxngBackend("http://h", opener=site, identity_ttl_seconds=60, clock=clock)
    first.search("a", 1)
    # Another backend in the same process, at the same address, shares the verdict.
    SearxngBackend("http://h", opener=site, identity_ttl_seconds=60, clock=clock).search("b", 1)
    clock.now += 61
    first.search("c", 1)
    assert [url.split("?")[0].rsplit("/", 1)[-1] for url in site.asked] == [
        "config", "search", "search", "config", "search",
    ]  # fmt: skip


def test_a_refused_identity_is_not_kept_so_a_real_searxng_is_noticed_at_once() -> None:
    clock = _Clock()
    squatter = _site({"app": "other"})
    with pytest.raises(WebSearchError):
        SearxngBackend("http://h", opener=squatter, clock=clock).search("q", 1)
    real = _site(SEARXNG_CONFIG)
    assert SearxngBackend("http://h", opener=real, clock=clock).search("q", 1)
    assert real.asked[0] == "http://h/config"


def test_a_marker_is_part_of_what_was_verified() -> None:
    clock = _Clock()
    SearxngBackend("http://h", opener=_site(SEARXNG_CONFIG), clock=clock).search("q", 1)
    with pytest.raises(WebSearchError, match="other than the expected one"):
        SearxngBackend(
            "http://h", opener=_site(SEARXNG_CONFIG), clock=clock, instance="vibey-7f3a"
        ).search("q", 1)


def test_the_identity_request_is_a_bounded_get_with_no_query_and_no_secret() -> None:
    seen: list[tuple[str, dict[str, str], float, bytes | None, str]] = []
    response = FakeResponse(SEARXNG_CONFIG)

    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        seen.append(
            (request.full_url, dict(request.header_items()), timeout, request.data, request.get_method())
        )  # fmt: skip
        return response

    probe = SearxngBackend("http://127.0.0.1:28180/", timeout_seconds=4, opener=opener)
    assert probe.health() is None
    assert seen == [
        ("http://127.0.0.1:28180/config", {"Accept": "application/json"}, 4, None, "GET")
    ]
    assert response.asked == [2_000_000]


@pytest.mark.parametrize(
    ("error", "said"),
    [
        (
            urllib.error.HTTPError("http://h/config", 502, "x", {}, None),  # type: ignore[arg-type]
            "answered HTTP 502",
        ),
        (
            urllib.error.URLError(ConnectionRefusedError()),
            "could not be reached (ConnectionRefusedError)",
        ),
        (TimeoutError(), "could not be reached (TimeoutError)"),
        (http.client.BadStatusLine("garbage q=private"), "could not be reached (BadStatusLine)"),
    ],
)
def test_the_health_probe_says_why_searxng_is_not_answering(
    error: BaseException, said: str
) -> None:
    def raising(request: urllib.request.Request, timeout: float) -> FakeResponse:
        raise error

    assert SearxngBackend("http://h", opener=raising).health() == said


def test_the_health_probe_says_when_something_else_is_listening() -> None:
    said = SearxngBackend("http://h", opener=_site(b"<html>")).health()
    assert said == "something other than SearXNG is listening there (its /config is not JSON)"
    assert SearxngBackend.is_impostor(said)
    assert not SearxngBackend.is_impostor("answered HTTP 502")
    marked = SearxngBackend("http://h", opener=_site(SEARXNG_CONFIG), instance="m").health()
    assert marked is not None and SearxngBackend.is_impostor(marked)


def test_the_health_probe_never_uses_a_kept_verdict() -> None:
    clock = _Clock()
    site = _site(SEARXNG_CONFIG)
    backend = SearxngBackend("http://h", opener=site, clock=clock)
    backend.search("q", 1)
    assert backend.health() is None
    assert [u for u in site.asked if u.endswith("/config")] == ["http://h/config"] * 2


def test_the_identity_marker_and_ttl_are_read_from_the_environment() -> None:
    settings = WebSearchSettings.from_environment(
        {"VIBEY_SEARXNG_INSTANCE": " vibey-7f3a ", "VIBEY_SEARCH_IDENTITY_TTL": "5"}
    )
    assert (settings.searxng_instance, settings.identity_ttl_seconds) == ("vibey-7f3a", 5.0)
    told = settings.session_environment()
    assert told["WEBSEARCH_SEARXNG_INSTANCE"] == "vibey-7f3a"
    assert told["WEBSEARCH_IDENTITY_TTL"] == "5.0"
    rebuilt = WebSearchSettings.from_environment(told)
    assert (rebuilt.searxng_instance, rebuilt.identity_ttl_seconds) == ("vibey-7f3a", 5.0)
    plain = WebSearchSettings.from_environment({})
    assert plain.searxng_instance is None and plain.identity_ttl_seconds == 60.0
    assert "WEBSEARCH_SEARXNG_INSTANCE" not in plain.session_environment()
    with pytest.raises(ConfigError, match="VIBEY_SEARCH_IDENTITY_TTL"):
        WebSearchSettings.from_environment({"VIBEY_SEARCH_IDENTITY_TTL": "0"})


# -- review fix round 1 ------------------------------------------------------------------------

DEEP = b"[" * 100_000 + b"]" * 100_000
"""JSON nested deeper than Python's parser will go: it raises RecursionError, not ValueError."""


def test_deeply_nested_json_at_config_is_not_searxng_and_never_raises() -> None:
    backend = SearxngBackend("http://h", opener=_site(DEEP))
    assert backend.health() == f"{IMPOSTOR} (its /config is not JSON)"
    with pytest.raises(WebSearchError, match="its /config is not JSON"):
        backend.search("q", 1)


def test_deeply_nested_json_from_search_or_brave_is_a_failure() -> None:
    with pytest.raises(WebSearchError, match="searxng did not answer with JSON"):
        SearxngBackend("http://h", opener=_opener(DEEP)).search("q", 1)
    with pytest.raises(WebSearchError, match="brave did not answer with JSON"):
        BraveBackend("fake-k", opener=_opener(DEEP)).search("q", 1)


ENGINES = {
    **SEARXNG_CONFIG,
    "engines": [
        {"name": "duckduckgo", "enabled": True},
        {"name": "wikipedia", "enabled": True},
        {"name": "google", "enabled": False},
        {"name": 7, "enabled": True},
        "not an engine",
    ],
}


@pytest.mark.parametrize(
    "unresponsive",
    [
        [["duckduckgo", "timeout"]],
        [["duckduckgo", "timeout"], ["google", "CAPTCHA"]],
        [["duckduckgo"], "wikipedia", [], [7, "x"], {"wikipedia": 1}],
    ],
)
def test_an_empty_answer_with_some_engines_unresponsive_is_a_partial_answer(
    unresponsive: object,
) -> None:
    site = _site(ENGINES, {"results": [], "unresponsive_engines": unresponsive})
    assert SearxngBackend("http://h", opener=site).search("q", 5) == []


def test_an_empty_answer_with_every_enabled_engine_unresponsive_is_a_failure() -> None:
    every = {"results": [], "unresponsive_engines": [["wikipedia", "x"], ["duckduckgo", "y"]]}
    with pytest.raises(WebSearchError) as caught:
        SearxngBackend("http://h", opener=_site(ENGINES, every)).search("q", 5)
    assert caught.value.reason == "every engine it asked failed (2 unresponsive)"


def test_an_empty_answer_from_a_searxng_with_no_engine_enabled_is_a_failure() -> None:
    none_on = {**SEARXNG_CONFIG, "engines": [{"name": "google", "enabled": False}]}
    with pytest.raises(WebSearchError, match="searxng has no engine enabled"):
        SearxngBackend("http://h", opener=_site(none_on, {"results": []})).search("q", 5)
    answered = {"results": [{"title": "T", "url": "https://t.example"}]}
    hits = SearxngBackend("http://h2", opener=_site(none_on, answered)).search("q", 5)
    assert [h.url for h in hits] == ["https://t.example"]


@pytest.mark.parametrize(
    ("key", "wrong"),
    [
        (key, wrong)
        for key in ("instance_name", "version", "engines", "categories")
        for wrong in (None, 7, "x" if key in {"engines", "categories"} else [])
    ],
)
def test_every_identity_key_and_its_type_is_checked(key: str, wrong: object) -> None:
    config = dict(SEARXNG_CONFIG)
    if wrong is None:
        del config[key]
    else:
        config[key] = wrong
    assert SearxngBackend("http://h", opener=_site(config)).health() == (
        f"{IMPOSTOR} (its /config is not SearXNG's)"
    )


@pytest.mark.parametrize(
    ("url", "needle"),
    [
        ("http://127.0.0.1:abc", "port from 1 to 65535"),
        ("http://127.0.0.1:99999", "port from 1 to 65535"),
        ("http://127.0.0.1:0", "port from 1 to 65535"),
        ("http://user:pw@127.0.0.1:28180", "user name or password"),
        ("http://token@127.0.0.1:28180", "user name or password"),
        ("http://127.0.0.1:28180/?x=1", "query or a fragment"),
        ("http://127.0.0.1:28180/#f", "query or a fragment"),
        ("http://127.0.0.1:28180/?", "query or a fragment"),
        ("http://127.0.0.1:28180/a b", "spaces or control characters"),
        ("http://:28180", "with a host"),
    ],
)
def test_a_searxng_url_vibey_cannot_use_as_given_is_refused_without_echoing_it(
    url: str, needle: str
) -> None:
    with pytest.raises(ConfigError, match=needle) as caught:
        WebSearchSettings.from_environment({"VIBEY_SEARXNG_URL": url})
    assert "pw" not in str(caught.value) and "token" not in str(caught.value)


@pytest.mark.parametrize("url", ["http://127.0.0.1:abc/x", "http://127.0.0.1:99999", "nonsense"])
def test_showing_a_url_never_raises(url: str) -> None:
    assert display_url(url).startswith(("http://127.0.0.1/", "http://127.0.0.1", ":"))


def test_a_result_carries_no_terminal_control_and_a_dirty_url_is_dropped() -> None:
    body = {
        "results": [
            {
                "title": "A\x1b]52;c;ZXZpbA==\x07B\x1b[2J",
                "url": "https://a.example",
                "content": "x\x9b31my\u202e\x7fz\tq\nr",
            },
            {"title": "evil", "url": "https://b.example/\x1b]8;;x\x07", "content": ""},
            {"title": "spaced", "url": "https://c.example/a b", "content": ""},
        ]
    }
    hits = SearxngBackend("http://h", opener=_opener(body)).search("q", 5)
    assert [(h.title, h.url, h.snippet) for h in hits] == [("AB", "https://a.example", "xyz\tq\nr")]


def test_an_answer_that_is_still_arriving_at_the_deadline_is_a_failure() -> None:
    release = threading.Event()

    def stuck(request: urllib.request.Request, timeout: float) -> FakeResponse:
        release.wait(10)
        return FakeResponse(SEARXNG_CONFIG)

    try:
        backend = SearxngBackend("http://h", opener=stuck, timeout_seconds=0.2)
        started = time.monotonic()
        assert backend.health() == "did not finish answering within 0.2s"
        with pytest.raises(WebSearchError, match="searxng did not finish answering within 0.2s"):
            backend.search("q", 1)
        with pytest.raises(WebSearchError, match="brave did not finish answering within 0.2s"):
            BraveBackend("fake-k", opener=stuck, timeout_seconds=0.2).search("q", 1)
        assert time.monotonic() - started < 3
    finally:
        release.set()
