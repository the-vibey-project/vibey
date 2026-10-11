# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Search backends: a self-hosted SearXNG, or the Brave Search API.

Both are configured by the environment alone, never by a file the model could read or a
repository could commit (`VIBEY_SEARXNG_URL`, `VIBEY_BRAVE_API_KEY`). A search that is not
configured is not an error: `WebSearchSettings.from_environment` returns None, and every
caller then behaves as it did before search existed. A search that is configured and fails is
a `WebSearchError` that names the backend and the cause, never the URL or the key.

What comes back is untrusted text from the open web. It is returned as data (title, URL,
snippet) and every surface that shows it says so.
"""

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Final

from vibey.domain.config import ConfigError

#: An engine session never receives a `VIBEY_*` variable (doctrine: vibey's own configuration
#: and credentials stay out of model-driven processes), so a session reads the same settings
#: under `WEBSEARCH_*`. Vibey puts the non-secret ones there itself (`session_environment`);
#: the Brave key is never among them.
SESSION_PREFIX: Final = "WEBSEARCH_"

SEARCH_PROVIDER_ENV: Final = "VIBEY_SEARCH_PROVIDER"
SEARXNG_URL_ENV: Final = "VIBEY_SEARXNG_URL"
BRAVE_KEY_ENV: Final = "VIBEY_BRAVE_API_KEY"
SEARCH_TIMEOUT_ENV: Final = "VIBEY_SEARCH_TIMEOUT"
SEARCH_RESULTS_ENV: Final = "VIBEY_SEARCH_RESULTS"

DEFAULT_TIMEOUT_SECONDS: Final = 15.0
DEFAULT_RESULTS: Final = 5
MAX_RESULTS: Final = 20
_BRAVE_ENDPOINT: Final = "https://api.search.brave.com/res/v1/web/search"
_TAG = re.compile(r"<[^>]+>")
_RESPONSE_LIMIT: Final = 2_000_000


class WebSearchError(RuntimeError):
    """A configured search backend failed. The message never carries a URL or a key."""


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class WebSearchSettings:
    """Which backend to ask, and how long and how much to ask for."""

    provider: str
    searxng_url: str | None = None
    brave_key: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    results: int = DEFAULT_RESULTS

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "WebSearchSettings | None":
        """The settings the environment declares, or None when search is not configured.

        `VIBEY_SEARCH_PROVIDER` (`searxng` or `brave`) chooses; unset, whichever backend
        is configured is used, SearXNG first. Naming a provider whose setting is missing, or a
        value that cannot be read, is refused by name rather than falling back.
        """
        searxng = _setting(environ, SEARXNG_URL_ENV) or None
        brave = _setting(environ, BRAVE_KEY_ENV) or None
        chosen = _setting(environ, SEARCH_PROVIDER_ENV).lower()
        if chosen not in {"", "searxng", "brave"}:
            raise ConfigError(SEARCH_PROVIDER_ENV, f"must be searxng or brave, got {chosen!r}")
        if chosen == "searxng" and searxng is None:
            raise ConfigError(SEARCH_PROVIDER_ENV, f"searxng needs {SEARXNG_URL_ENV}")
        if chosen == "brave" and brave is None:
            raise ConfigError(SEARCH_PROVIDER_ENV, f"brave needs {BRAVE_KEY_ENV}")
        if not chosen:
            chosen = "searxng" if searxng is not None else "brave" if brave is not None else ""
        if not chosen:
            return None
        if searxng is not None:
            _check_http_url(searxng, SEARXNG_URL_ENV)
        return cls(
            provider=chosen,
            searxng_url=searxng,
            brave_key=brave,
            timeout_seconds=_positive_float(environ, SEARCH_TIMEOUT_ENV, DEFAULT_TIMEOUT_SECONDS),
            results=_bounded_int(environ, SEARCH_RESULTS_ENV, DEFAULT_RESULTS),
        )

    def session_environment(self) -> dict[str, str]:
        """What an engine session may be told about search: the SearXNG address and limits.

        Nothing secret. A session cannot be given the Brave key (a command the model chose
        could read it), so with Brave configured this is empty and search stays with vibey's own
        research stage."""
        if self.provider != "searxng" or self.searxng_url is None:
            return {}
        return {
            f"{SESSION_PREFIX}PROVIDER": "searxng",
            f"{SESSION_PREFIX}SEARXNG_URL": self.searxng_url,
            f"{SESSION_PREFIX}TIMEOUT": str(self.timeout_seconds),
            f"{SESSION_PREFIX}RESULTS": str(self.results),
        }


def _alias(name: str) -> str:
    """The `WEBSEARCH_*` name of a `VIBEY_*` setting: `VIBEY_SEARCH_TIMEOUT` is
    `WEBSEARCH_TIMEOUT`, `VIBEY_SEARXNG_URL` is `WEBSEARCH_SEARXNG_URL`."""
    return SESSION_PREFIX + name.removeprefix("VIBEY_").removeprefix("SEARCH_")


def _setting(environ: Mapping[str, str], name: str) -> str:
    """`name`'s value, else its `WEBSEARCH_*` alias, stripped; empty when neither is set."""
    return (environ.get(name) or environ.get(_alias(name)) or "").strip()


def _check_http_url(value: str, name: str) -> None:
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        # Never echoed: a URL can carry credentials.
        raise ConfigError(name, "must be an http(s) URL with a host (the value is not shown)")


def _positive_float(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = _setting(environ, name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(name, f"must be a number of seconds, got {raw!r}") from exc
    if value <= 0 or value != value or value == float("inf"):
        raise ConfigError(name, f"must be a finite number above zero, got {raw!r}")
    return value


def _bounded_int(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = _setting(environ, name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(name, f"must be a whole number, got {raw!r}") from exc
    if not 1 <= value <= MAX_RESULTS:
        raise ConfigError(name, f"must be between 1 and {MAX_RESULTS}, got {value}")
    return value


def _plain(text: object) -> str:
    return html.unescape(_TAG.sub("", str(text or ""))).strip()


def _hit(title: object, url: object, snippet: object) -> SearchHit | None:
    address = str(url or "").strip()
    if urllib.parse.urlsplit(address).scheme not in {"http", "https"}:
        return None
    return SearchHit(title=_plain(title) or address, url=address, snippet=_plain(snippet))


def _get_json(
    opener: Callable[..., Any], request: urllib.request.Request, timeout: float, backend: str
) -> Mapping[str, Any]:
    try:
        with opener(request, timeout=timeout) as response:
            body = json.loads(response.read(_RESPONSE_LIMIT))
    except urllib.error.HTTPError as exc:
        raise WebSearchError(f"{backend} answered HTTP {exc.code}") from None
    except (OSError, ValueError) as exc:
        raise WebSearchError(
            f"{backend} could not be reached or understood ({type(exc).__name__})"
        ) from None
    if not isinstance(body, dict):
        raise WebSearchError(f"{backend} did not answer with a JSON object")
    return body


class SearxngBackend:
    """A self-hosted SearXNG's JSON API: no key, and the queries stay on your machine."""

    name = "searxng"

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._opener = opener

    def search(self, query: str, limit: int) -> list[SearchHit]:
        url = f"{self._base}/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
        request = urllib.request.Request(url, headers={"Accept": "application/json"})  # nosec B310
        body = _get_json(self._opener, request, self._timeout, self.name)
        results = body.get("results")
        hits = [
            hit
            for item in (results if isinstance(results, list) else [])
            if isinstance(item, dict)
            and (hit := _hit(item.get("title"), item.get("url"), item.get("content")))
        ]
        return hits[:limit]


class BraveBackend:
    """The Brave Search API. It needs a key, and the query goes to Brave."""

    name = "brave"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        self._key = api_key
        self._timeout = timeout_seconds
        self._opener = opener

    def search(self, query: str, limit: int) -> list[SearchHit]:
        url = _BRAVE_ENDPOINT + "?" + urllib.parse.urlencode({"q": query, "count": limit})
        request = urllib.request.Request(  # nosec B310 - a fixed https endpoint
            url, headers={"Accept": "application/json", "X-Subscription-Token": self._key}
        )
        body = _get_json(self._opener, request, self._timeout, self.name)
        web = body.get("web")
        results = web.get("results") if isinstance(web, dict) else None
        hits = [
            hit
            for item in (results if isinstance(results, list) else [])
            if isinstance(item, dict)
            and (hit := _hit(item.get("title"), item.get("url"), item.get("description")))
        ]
        return hits[:limit]


def backend_for(
    settings: WebSearchSettings, *, opener: Callable[..., Any] = urllib.request.urlopen
) -> SearxngBackend | BraveBackend:
    """The backend the settings chose."""
    if settings.provider == "searxng" and settings.searxng_url is not None:
        return SearxngBackend(
            settings.searxng_url, timeout_seconds=settings.timeout_seconds, opener=opener
        )
    return BraveBackend(
        settings.brave_key or "", timeout_seconds=settings.timeout_seconds, opener=opener
    )
