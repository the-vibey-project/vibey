# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Search backends: a local SearXNG first, always, and the Brave Search API only as a backup.

Operator ruling (2026-11-21): all search vibey controls asks a **local** SearXNG. Its address is
`VIBEY_SEARXNG_URL`, else `DEFAULT_SEARXNG_URL` (loopback). Brave answers a query only when that
SearXNG failed and a key is configured (`local_first.LocalFirstSearch` applies the rule), and is
never the primary: `VIBEY_SEARCH_PROVIDER=brave` is refused. Search is therefore always
configured; whether the local SearXNG actually answers is what `vibey doctor` reports.

Both are configured by the person's own environment alone, never by a file the model could read
or a repository could commit (`VIBEY_SEARXNG_URL`; `VIBEY_BRAVE_API_KEY`, or
`BRAVE_SEARCH_API_KEY`, the name Brave's own tools read; vibey's own name wins when both are
set). A project's `vibey.toml` cannot point search anywhere. A backend that fails raises
`WebSearchError`, which names the backend and the cause, never the query, a URL's credentials
or query string, or the key.

The Brave key stays in vibey's own processes. A session never receives it: not under
`VIBEY_BRAVE_API_KEY` (no `VIBEY_*` name reaches one), and not under the alias, which the rule
under every child's allow-list names (`process/child_environment.py`). Its value is never in a
`repr`, a log line, an error or `vibey doctor`; what is said is which variable configured it.

What comes back is untrusted text from the open web. It is returned as data (title, URL,
snippet), read at most `_RESPONSE_LIMIT` bytes within the configured timeout, and every surface
that shows it says so.
"""

import html
import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from vibey.domain.config import ConfigError
from vibey.infrastructure.web.guarded_opener import GuardedOpener

#: An engine session never receives a `VIBEY_*` variable (doctrine: vibey's own configuration
#: and credentials stay out of model-driven processes), so a session reads the same settings
#: under `WEBSEARCH_*`. Vibey puts the non-secret ones there itself (`session_environment`);
#: the Brave key is never among them.
SESSION_PREFIX: Final = "WEBSEARCH_"

SEARCH_PROVIDER_ENV: Final = "VIBEY_SEARCH_PROVIDER"
SEARXNG_URL_ENV: Final = "VIBEY_SEARXNG_URL"
BRAVE_KEY_ENV: Final = "VIBEY_BRAVE_API_KEY"
BRAVE_KEY_ALIAS_ENV: Final = "BRAVE_SEARCH_API_KEY"
"""The name Brave's own tools read the key from; `VIBEY_BRAVE_API_KEY` wins when both are set."""
BRAVE_KEY_NAMES: Final = (BRAVE_KEY_ENV, "WEBSEARCH_BRAVE_API_KEY", BRAVE_KEY_ALIAS_ENV)
"""Every name the Brave key is read under, in order: vibey's own, the `WEBSEARCH_*` form every
`VIBEY_*` search setting has, and Brave's. None of them can reach a child process
(`process/child_environment.py`)."""
SEARCH_TIMEOUT_ENV: Final = "VIBEY_SEARCH_TIMEOUT"
SEARCH_RESULTS_ENV: Final = "VIBEY_SEARCH_RESULTS"

DEFAULT_SEARXNG_URL: Final = "http://127.0.0.1:8080"
"""Where the local SearXNG is asked when `VIBEY_SEARXNG_URL` is unset: loopback, SearXNG's own
default port. Set `VIBEY_SEARXNG_URL` to run it anywhere else."""
DEFAULT_TIMEOUT_SECONDS: Final = 15.0
DEFAULT_RESULTS: Final = 5
MAX_RESULTS: Final = 20
_BRAVE_ENDPOINT: Final = "https://api.search.brave.com/res/v1/web/search"
_TAG = re.compile(r"<[^>]+>")
_RESPONSE_LIMIT: Final = 2_000_000
_HEALTH_LIMIT: Final = 1024
_UNREACHABLE: Final = (OSError, ValueError, http.client.HTTPException)
"""A request that did not complete: refused, timed out, reset, or a malformed status line."""


class WebSearchError(RuntimeError):
    """A search backend failed. The message never carries the query, a URL's credentials or
    query string, or a key; `reason` is the cause alone, without the backend's name."""

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = message if reason is None else reason


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True, slots=True)
class SearchAnswer:
    """One query's hits, and which backend answered them.

    `backend` is `searxng`, or `brave` when the local SearXNG failed and the backup answered;
    then `fallback_reason` says why (cleaned, never the query), and `notice` is the sentence said
    on standard error when this was the first query of the process to go to Brave."""

    hits: tuple[SearchHit, ...]
    backend: str
    notice: str | None = None
    fallback_reason: str | None = None


@dataclass(frozen=True, slots=True)
class WebSearchSettings:
    """Where the local SearXNG is, whether there is a Brave backup, and how long and how much to
    ask for."""

    searxng_url: str = DEFAULT_SEARXNG_URL
    brave_key: str | None = field(default=None, repr=False)
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    results: int = DEFAULT_RESULTS
    brave_key_env: str | None = None
    """Which variable the Brave key came from: what may be said, never the key."""
    searxng_url_env: str | None = None
    """Which variable set the SearXNG URL; None when it is the default."""

    @property
    def has_backup(self) -> bool:
        return self.brave_key is not None

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> "WebSearchSettings":
        """The settings the environment declares. Never None: search is always the local
        SearXNG, at `VIBEY_SEARXNG_URL` or the loopback default.

        The Brave key is `VIBEY_BRAVE_API_KEY`, else `WEBSEARCH_BRAVE_API_KEY`, else
        `BRAVE_SEARCH_API_KEY`, and is only ever a backup. `VIBEY_SEARCH_PROVIDER` may be unset
        or `searxng`; `brave`, or a value that cannot be read, is refused by name."""
        chosen = _setting(environ, SEARCH_PROVIDER_ENV).lower()
        if chosen == "brave":
            raise ConfigError(
                SEARCH_PROVIDER_ENV,
                "Brave is a backup only, never the primary: leave this unset (or searxng) and set"
                f" {BRAVE_KEY_ENV} or {BRAVE_KEY_ALIAS_ENV}; vibey then asks Brave only when the"
                " local SearXNG fails, and says so",
            )
        if chosen not in {"", "searxng"}:
            raise ConfigError(SEARCH_PROVIDER_ENV, f"must be searxng (or unset), got {chosen!r}")
        url_env = _setting_name(environ, SEARXNG_URL_ENV)
        searxng = _setting(environ, SEARXNG_URL_ENV) or DEFAULT_SEARXNG_URL
        _check_http_url(searxng, SEARXNG_URL_ENV)
        # Exactly three names, first wins: vibey's own, its `WEBSEARCH_*` form, then Brave's.
        brave_env, brave = next(
            (
                (name, value)
                for name in BRAVE_KEY_NAMES
                if (value := (environ.get(name) or "").strip())
            ),
            (None, None),
        )
        return cls(
            searxng_url=searxng,
            brave_key=brave,
            timeout_seconds=_positive_float(environ, SEARCH_TIMEOUT_ENV, DEFAULT_TIMEOUT_SECONDS),
            results=_bounded_int(environ, SEARCH_RESULTS_ENV, DEFAULT_RESULTS),
            brave_key_env=brave_env,
            searxng_url_env=url_env,
        )

    def session_environment(self) -> dict[str, str]:
        """What an engine session is told about search: the local SearXNG's address and the
        limits. Nothing secret: a session is never given the Brave key (a command the model chose
        could read it), so a session's `vibey search` has no backup."""
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


def _setting_name(environ: Mapping[str, str], name: str) -> str | None:
    """Which of `name` and its alias `_setting` read, or None when neither is set."""
    for candidate in (name, _alias(name)):
        if (environ.get(candidate) or "").strip():
            return candidate
    return None


def _check_http_url(value: str, name: str) -> None:
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        # Never echoed: a URL can carry credentials.
        raise ConfigError(name, "must be an http(s) URL with a host (the value is not shown)")


def display_url(url: str) -> str:
    """`url` as it may be shown: scheme, host, port and path, never its credentials, query or
    fragment (a SearXNG URL is the person's own configuration, and may carry any of them)."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port is not None else ""
    return f"{parts.scheme}://{host}{port}{parts.path}"


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


def _unreachable(exc: BaseException) -> str:
    """Why a request did not complete, by exception type alone: an error's own text can carry
    the URL, and so the query."""
    cause = exc.reason if isinstance(exc, urllib.error.URLError) else None
    kind = type(cause if isinstance(cause, BaseException) else exc).__name__
    return f"could not be reached ({kind})"


def _failure(backend: str, reason: str) -> WebSearchError:
    return WebSearchError(f"{backend} {reason}", reason=reason)


def _get_json(
    opener: Callable[..., Any], request: urllib.request.Request, timeout: float, backend: str
) -> Mapping[str, Any]:
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read(_RESPONSE_LIMIT)
    except urllib.error.HTTPError as exc:
        raise _failure(backend, f"answered HTTP {exc.code}") from None
    except _UNREACHABLE as exc:
        raise _failure(backend, _unreachable(exc)) from None
    try:
        body = json.loads(raw)
    except ValueError:
        raise _failure(backend, "did not answer with JSON") from None
    if not isinstance(body, dict):
        raise _failure(backend, "did not answer with a JSON object")
    return body


class SearxngBackend:
    """A SearXNG's JSON API: no key, and on loopback the queries stay on your machine."""

    name = "searxng"

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._opener = opener if opener is not None else GuardedOpener(base_url)

    def search(self, query: str, limit: int) -> list[SearchHit]:
        url = f"{self._base}/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
        request = urllib.request.Request(url, headers={"Accept": "application/json"})  # nosec B310
        body = _get_json(self._opener, request, self._timeout, self.name)
        results = body.get("results")
        if not isinstance(results, list):
            raise _failure(self.name, "did not answer with a results list")
        failed = body.get("unresponsive_engines")
        if not results and isinstance(failed, list) and failed:
            # A SearXNG whose every engine errored answers an empty list; that is a failure,
            # not "nothing found". An empty list with no failed engine is an honest nothing.
            raise _failure(self.name, f"every engine it asked failed ({len(failed)} unresponsive)")
        hits = [
            hit
            for item in results
            if isinstance(item, dict)
            and (hit := _hit(item.get("title"), item.get("url"), item.get("content")))
        ]
        return hits[:limit]

    def health(self) -> str | None:
        """None when the SearXNG answers its `/healthz`, else why not. A bounded GET with no
        query and no secret, for `vibey doctor`; it never raises."""
        request = urllib.request.Request(  # nosec B310 - the configured SearXNG's own address
            f"{self._base}/healthz", headers={"Accept": "text/plain"}
        )
        try:
            with self._opener(request, timeout=self._timeout) as response:
                response.read(_HEALTH_LIMIT)
        except urllib.error.HTTPError as exc:
            return f"answered HTTP {exc.code}"
        except _UNREACHABLE as exc:
            return _unreachable(exc)
        return None


class BraveBackend:
    """The Brave Search API: the backup. It needs a key, and the query goes to Brave."""

    name = "brave"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self._key = api_key
        self._timeout = timeout_seconds
        self._opener = opener if opener is not None else GuardedOpener(_BRAVE_ENDPOINT)

    def __repr__(self) -> str:
        return "BraveBackend(api_key=<hidden>)"

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
