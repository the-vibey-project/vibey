# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The search backends and the environment that configures them: a local SearXNG first, always,
and Brave only as a backup (operator ruling 2026-11-21). Every key here is a fake."""

import http.client
import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from vibey.domain.config import ConfigError
from vibey.infrastructure.web.guarded_opener import GuardedOpener
from vibey.infrastructure.web.search import (
    DEFAULT_SEARXNG_URL,
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
    payload = body if isinstance(body, bytes) else json.dumps(body).encode()

    def opener(request: urllib.request.Request, timeout: float) -> _Response:
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
    assert DEFAULT_SEARXNG_URL == "http://127.0.0.1:8080"
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
    assert caught.value.reason == "every engine it asked failed (2 unresponsive)"
    assert str(caught.value) == "searxng every engine it asked failed (2 unresponsive)"


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

    def opener(request: urllib.request.Request, timeout: float) -> _Response:
        return response

    SearxngBackend("http://h", opener=opener).search("q", 1)
    assert response.asked == [2_000_000]


def test_each_backend_opens_through_the_guarded_opener_by_default() -> None:
    searx = SearxngBackend("http://127.0.0.1:8080")
    brave = BraveBackend("fake-k")
    assert isinstance(searx._opener, GuardedOpener) and isinstance(brave._opener, GuardedOpener)


# -- the health probe -----------------------------------------------------------------------


def test_the_health_probe_is_a_bounded_get_of_healthz_with_no_secret() -> None:
    seen: list[tuple[str, dict[str, str], float]] = []
    response = _Response(b"OK")

    def opener(request: urllib.request.Request, timeout: float) -> _Response:
        seen.append((request.full_url, dict(request.header_items()), timeout))
        assert request.get_method() == "GET" and request.data is None
        return response

    probe = SearxngBackend("http://127.0.0.1:8080/", timeout_seconds=4, opener=opener)
    assert probe.health() is None
    url, headers, timeout = seen[0]
    assert url == "http://127.0.0.1:8080/healthz" and timeout == 4
    assert set(headers) == {"Accept"} and response.asked == [1024]


@pytest.mark.parametrize(
    ("error", "said"),
    [
        (
            urllib.error.HTTPError("http://h/healthz", 502, "x", {}, None),  # type: ignore[arg-type]
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
    assert SearxngBackend("http://h", opener=_raising(error)).health() == said
