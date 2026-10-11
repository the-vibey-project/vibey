# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The search backends and the environment that chooses between them."""

import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from vibey.domain.config import ConfigError
from vibey.infrastructure.web.search import (
    BraveBackend,
    SearxngBackend,
    WebSearchError,
    WebSearchSettings,
    backend_for,
)


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, amount: int | None = None) -> bytes:
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


def test_nothing_configured_is_not_an_error_and_means_no_search() -> None:
    assert WebSearchSettings.from_environment({}) is None
    assert (
        WebSearchSettings.from_environment({"VIBEY_SEARXNG_URL": "  ", "VIBEY_BRAVE_API_KEY": ""})
        is None
    )


def test_whichever_backend_is_configured_is_used_and_searxng_wins_a_tie() -> None:
    only_brave = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": "k"})
    assert only_brave is not None and only_brave.provider == "brave"
    both = WebSearchSettings.from_environment(
        {"VIBEY_BRAVE_API_KEY": "k", "VIBEY_SEARXNG_URL": "http://localhost:8080"}
    )
    assert both is not None and both.provider == "searxng"
    chosen = WebSearchSettings.from_environment(
        {
            "VIBEY_BRAVE_API_KEY": "k",
            "VIBEY_SEARXNG_URL": "http://localhost:8080",
            "VIBEY_SEARCH_PROVIDER": " Brave ",
        }
    )
    assert chosen is not None and chosen.provider == "brave"


@pytest.mark.parametrize(
    ("environ", "needle"),
    [
        ({"VIBEY_SEARCH_PROVIDER": "bing", "VIBEY_BRAVE_API_KEY": "k"}, "must be searxng or brave"),
        ({"VIBEY_SEARCH_PROVIDER": "searxng"}, "searxng needs VIBEY_SEARXNG_URL"),
        ({"VIBEY_SEARCH_PROVIDER": "brave"}, "brave needs VIBEY_BRAVE_API_KEY"),
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
    base = {"VIBEY_BRAVE_API_KEY": "k"}
    settings = WebSearchSettings.from_environment(
        {**base, "VIBEY_SEARCH_TIMEOUT": "7.5", "VIBEY_SEARCH_RESULTS": "8"}
    )
    assert settings is not None and (settings.timeout_seconds, settings.results) == (7.5, 8)
    default = WebSearchSettings.from_environment(base)
    assert default is not None and (default.timeout_seconds, default.results) == (15.0, 5)
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
            WebSearchSettings.from_environment({**base, name: value})


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


def test_brave_sends_its_key_as_a_header_and_never_in_the_url() -> None:
    seen: list[tuple[str, dict[str, str], float]] = []
    body = {
        "web": {
            "results": [
                {"title": "T", "url": "https://t.example", "description": "<strong>D</strong>"}
            ]
        }
    }
    backend = BraveBackend("secret-key", opener=_opener(body, seen))

    hits = backend.search("q", 3)

    assert [(h.title, h.snippet) for h in hits] == [("T", "D")]
    url, headers, _ = seen[0]
    assert url == "https://api.search.brave.com/res/v1/web/search?q=q&count=3"
    assert "secret-key" not in url and headers["X-subscription-token"] == "secret-key"


@pytest.mark.parametrize(
    "body", [{}, {"results": "no"}, {"web": "no"}, {"web": {"results": 3}}, {"web": {}}]
)
def test_an_answer_without_results_is_no_results_not_a_failure(body: object) -> None:
    assert SearxngBackend("http://h", opener=_opener(body)).search("q", 5) == []
    assert BraveBackend("k", opener=_opener(body)).search("q", 5) == []


def test_a_failing_backend_is_named_and_never_leaks_the_url_or_key() -> None:
    http_error = urllib.error.HTTPError("https://api/?key=sekret", 503, "x", {}, None)  # type: ignore[arg-type]
    with pytest.raises(WebSearchError, match="brave answered HTTP 503") as caught:
        BraveBackend("sekret", opener=_raising(http_error)).search("q", 1)
    assert "sekret" not in str(caught.value)
    with pytest.raises(WebSearchError, match="searxng could not be reached or understood"):
        SearxngBackend("http://h", opener=_raising(ConnectionRefusedError())).search("q", 1)
    with pytest.raises(WebSearchError, match="could not be reached or understood"):
        SearxngBackend("http://h", opener=_opener(b"not json")).search("q", 1)
    with pytest.raises(WebSearchError, match="did not answer with a JSON object"):
        SearxngBackend("http://h", opener=_opener([1, 2])).search("q", 1)


def test_the_settings_choose_the_backend() -> None:
    searx = WebSearchSettings.from_environment({"VIBEY_SEARXNG_URL": "http://h:1"})
    brave = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": "k"})
    assert searx is not None and brave is not None
    assert backend_for(searx).name == "searxng" and backend_for(brave).name == "brave"


def test_a_session_reads_the_same_settings_under_websearch_names() -> None:
    settings = WebSearchSettings.from_environment(
        {
            "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:8080",
            "WEBSEARCH_TIMEOUT": "3",
            "WEBSEARCH_RESULTS": "2",
        }
    )
    assert settings is not None
    assert (settings.provider, settings.timeout_seconds, settings.results) == ("searxng", 3.0, 2)


def test_the_vibey_name_wins_over_its_websearch_alias() -> None:
    settings = WebSearchSettings.from_environment(
        {"VIBEY_SEARXNG_URL": "http://a:1", "WEBSEARCH_SEARXNG_URL": "http://b:2"}
    )
    assert settings is not None and settings.searxng_url == "http://a:1"


def test_what_a_session_is_told_is_enough_to_rebuild_the_same_settings() -> None:
    worker = WebSearchSettings.from_environment(
        {
            "VIBEY_SEARXNG_URL": "http://127.0.0.1:8080",
            "VIBEY_SEARCH_TIMEOUT": "9",
            "VIBEY_SEARCH_RESULTS": "6",
        }
    )
    assert worker is not None
    told = worker.session_environment()
    assert set(told) == {
        "WEBSEARCH_PROVIDER",
        "WEBSEARCH_SEARXNG_URL",
        "WEBSEARCH_TIMEOUT",
        "WEBSEARCH_RESULTS",
    }
    assert not any(name.startswith("VIBEY_") for name in told)
    assert WebSearchSettings.from_environment(told) == worker


def test_the_brave_key_is_never_among_what_a_session_is_told() -> None:
    brave = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": "sekret"})
    assert brave is not None and brave.session_environment() == {}
    chosen_brave = WebSearchSettings.from_environment(
        {
            "VIBEY_BRAVE_API_KEY": "sekret",
            "VIBEY_SEARXNG_URL": "http://h:1",
            "VIBEY_SEARCH_PROVIDER": "brave",
        }
    )
    assert chosen_brave is not None and chosen_brave.session_environment() == {}
    both = WebSearchSettings.from_environment(
        {"VIBEY_BRAVE_API_KEY": "sekret", "VIBEY_SEARXNG_URL": "http://h:1"}
    )
    assert both is not None and "sekret" not in "".join(both.session_environment().values())
