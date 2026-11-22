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
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar, Final

from vibey.domain.config import ConfigError
from vibey.infrastructure.web.bounded_request import BoundedRequest, DeadlineExceeded
from vibey.infrastructure.web.guarded_opener import GuardedOpener
from vibey.infrastructure.web.untrusted_text import UntrustedText

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
SEARXNG_INSTANCE_ENV: Final = "VIBEY_SEARXNG_INSTANCE"
"""The `instance_name` vibey's own SearXNG answers on `/config`. Optional; when set, a SearXNG
that names itself anything else is not believed. The person's own environment sets it (Task 9d
writes it beside the SearXNG it installs); a project's `vibey.toml` never can."""
SEARCH_IDENTITY_TTL_ENV: Final = "VIBEY_SEARCH_IDENTITY_TTL"

DEFAULT_SEARXNG_PORT: Final = 28180
"""vibey's own SearXNG port: uncommon on purpose (not 8080 or 8888, where other software listens
by default), and below every common ephemeral range, so an outgoing connection never holds it."""
DEFAULT_SEARXNG_URL: Final = f"http://127.0.0.1:{DEFAULT_SEARXNG_PORT}"
"""Where the local SearXNG is asked when `VIBEY_SEARXNG_URL` is unset: loopback only. Set
`VIBEY_SEARXNG_URL` to run it anywhere else."""
DEFAULT_IDENTITY_TTL_SECONDS: Final = 60.0
"""How long a SearXNG that proved it is one is believed before `/config` is asked again."""
DEFAULT_TIMEOUT_SECONDS: Final = 15.0
DEFAULT_RESULTS: Final = 5
MAX_RESULTS: Final = 20
_BRAVE_ENDPOINT: Final = "https://api.search.brave.com/res/v1/web/search"
_TAG = re.compile(r"<[^>]+>")
_RESPONSE_LIMIT: Final = 2_000_000
IMPOSTOR: Final = "something other than SearXNG is listening there"
STRANGER: Final = "a SearXNG other than the expected one is listening there"
_UNREACHABLE: Final = (OSError, ValueError, http.client.HTTPException)
_UNPARSABLE: Final = (ValueError, RecursionError)
"""JSON that cannot be read: malformed, or nested deeper than the parser will go."""
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
    searxng_instance: str | None = None
    """The `instance_name` the SearXNG must answer with, when one is expected."""
    identity_ttl_seconds: float = DEFAULT_IDENTITY_TTL_SECONDS
    in_session: bool = False
    """Read inside an engine session (vibey told it `WEBSEARCH_PROVIDER`): no Brave key can be
    there, so a failure never suggests one."""

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
            searxng_instance=_setting(environ, SEARXNG_INSTANCE_ENV) or None,
            identity_ttl_seconds=_positive_float(
                environ, SEARCH_IDENTITY_TTL_ENV, DEFAULT_IDENTITY_TTL_SECONDS
            ),
            in_session=f"{SESSION_PREFIX}PROVIDER" in environ,
        )

    def session_environment(self) -> dict[str, str]:
        """What an engine session is told about search: the local SearXNG's address, the identity
        it must prove, and the limits. Nothing secret: a session is never given the Brave key (a
        command the model chose could read it), so a session's `vibey search` has no backup. The
        instance marker is not a secret: it tells vibey's own SearXNG from another program, not
        from code running as you."""
        told = {
            f"{SESSION_PREFIX}PROVIDER": "searxng",
            f"{SESSION_PREFIX}SEARXNG_URL": self.searxng_url,
            f"{SESSION_PREFIX}TIMEOUT": str(self.timeout_seconds),
            f"{SESSION_PREFIX}RESULTS": str(self.results),
            _alias(SEARCH_IDENTITY_TTL_ENV): str(self.identity_ttl_seconds),
        }
        if self.searxng_instance is not None:
            told[_alias(SEARXNG_INSTANCE_ENV)] = self.searxng_instance
        return told


# The module-level functions below read the environment, check a value or shape a message for
# the settings and both backends alike; none holds state, so none is a method of one of them.


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
    """Refuse a SearXNG URL vibey cannot use as given. The value is never echoed: it may carry
    credentials. Credentials are refused outright, so none can reach a session's environment."""
    try:
        parts = urllib.parse.urlsplit(value)
        port = parts.port
    except ValueError:
        raise ConfigError(
            name, "must have a port from 1 to 65535 (the value is not shown)"
        ) from None
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ConfigError(name, "must be an http(s) URL with a host (the value is not shown)")
    if port == 0:
        raise ConfigError(name, "must have a port from 1 to 65535 (the value is not shown)")
    if "@" in parts.netloc:
        raise ConfigError(name, "must not carry a user name or password (the value is not shown)")
    if parts.query or parts.fragment or value.rstrip().endswith(("?", "#")):
        raise ConfigError(name, "must not carry a query or a fragment (the value is not shown)")
    if not UntrustedText.is_clean_url(value):
        raise ConfigError(name, "must not contain spaces or control characters")


def display_url(url: str) -> str:
    """`url` as it may be shown: scheme, host, port and path, never its credentials, query or
    fragment. Never raises: an unreadable port is left out."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    try:
        port = f":{parts.port}" if parts.port is not None else ""
    except ValueError:
        port = ""
    return f"{parts.scheme}://{host}{port}{UntrustedText.clean(parts.path)}"


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
    """A result's title or snippet as plain, printable text: no tags, entities decoded, and no
    terminal control (`UntrustedText`), in the terminal and in `--json` alike."""
    return UntrustedText.clean(html.unescape(_TAG.sub("", str(text or "")))).strip()


def _hit(title: object, url: object, snippet: object) -> SearchHit | None:
    """One result, or None when its URL is not a clean http(s) address."""
    address = str(url or "").strip()
    if not UntrustedText.is_clean_url(address):
        return None
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
    """The error a backend raises: its name, then the reason."""
    return WebSearchError(f"{backend} {reason}", reason=reason)


def _late(timeout: float) -> str:
    """The reason for an answer that did not finish within the total deadline."""
    return f"did not finish answering within {timeout:g}s"


def _get_json(
    opener: Callable[..., Any], request: urllib.request.Request, timeout: float, backend: str
) -> Mapping[str, Any]:
    """A backend's JSON object, read whole within `timeout` seconds in all, or a `WebSearchError`
    naming why not."""
    try:
        raw = BoundedRequest(opener).fetch(request, deadline=timeout, limit=_RESPONSE_LIMIT).body
    except urllib.error.HTTPError as exc:
        raise _failure(backend, f"answered HTTP {exc.code}") from None
    except DeadlineExceeded:
        raise _failure(backend, _late(timeout)) from None
    except _UNREACHABLE as exc:
        raise _failure(backend, _unreachable(exc)) from None
    try:
        body = json.loads(raw)
    except _UNPARSABLE:
        raise _failure(backend, "did not answer with JSON") from None
    if not isinstance(body, dict):
        raise _failure(backend, "did not answer with a JSON object")
    return body


class SearxngBackend:
    """A SearXNG's JSON API: no key, and on loopback the queries stay on your machine.

    Nothing listening at the address is believed until it proves it is a SearXNG: a GET of its
    `/config` (no query, no secret, no redirect) must answer SearXNG's JSON, with a string
    `instance_name` and `version` and lists of `engines` and `categories`, and, when an instance
    is expected (`VIBEY_SEARXNG_INSTANCE`), that `instance_name`. Anything else -- another
    program on the port, HTML, other JSON, an answer that came from anywhere but `/config` --
    is "something other than SearXNG", a failure like any other, and its search results are
    never read. A proof is kept for the whole process, per address and expected instance, for
    `identity_ttl_seconds`: a SearXNG replaced within that window is believed until it ends. A
    refusal is never kept.

    An empty answer is a failure only when SearXNG could not have answered: it has no engine
    enabled, or every engine it has enabled is among those it reports unresponsive. An empty
    answer with some engines unresponsive is a partial answer, and stays the answer: the query
    does not leave the machine for it."""

    name = "searxng"
    _verified: ClassVar[dict[tuple[str, str | None], tuple[float, frozenset[str]]]] = {}
    _verifying: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] | None = None,
        instance: str | None = None,
        identity_ttl_seconds: float = DEFAULT_IDENTITY_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._opener = opener if opener is not None else GuardedOpener(base_url)
        self._instance = instance
        self._ttl = identity_ttl_seconds
        self._clock = clock

    def search(self, query: str, limit: int) -> list[SearchHit]:
        enabled = self._believe()
        url = f"{self._base}/search?" + urllib.parse.urlencode({"q": query, "format": "json"})
        request = urllib.request.Request(url, headers={"Accept": "application/json"})  # nosec B310
        body = _get_json(self._opener, request, self._timeout, self.name)
        results = body.get("results")
        if not isinstance(results, list):
            raise _failure(self.name, "did not answer with a results list")
        if not results:
            self._check_empty(enabled, body.get("unresponsive_engines"))
        hits = [
            hit
            for item in results
            if isinstance(item, dict)
            and (hit := _hit(item.get("title"), item.get("url"), item.get("content")))
        ]
        return hits[:limit]

    def health(self) -> str | None:
        """None when a SearXNG (the expected one, when one is expected) answers here, else why
        not. Always asked afresh, for `vibey doctor`; it never raises."""
        return self._identify()

    @staticmethod
    def is_impostor(reason: str) -> bool:
        """Whether `reason` says something answered that is not (our) SearXNG."""
        return reason.startswith((IMPOSTOR, STRANGER))

    def _check_empty(self, enabled: frozenset[str], unresponsive: object) -> None:
        """Raise when an empty answer means SearXNG could not answer at all."""
        if not enabled:
            raise _failure(self.name, "has no engine enabled")
        # SearXNG lists each as `[name, why]`; anything else in the list names no engine.
        failed = {
            entry[0]
            for entry in (unresponsive if isinstance(unresponsive, list) else [])
            if isinstance(entry, list) and entry and isinstance(entry[0], str)
        }
        if enabled <= failed:
            raise _failure(self.name, f"every engine it asked failed ({len(enabled)} unresponsive)")

    def _believe(self) -> frozenset[str]:
        """The engines the proved SearXNG has enabled; raises when it is not proved."""
        key = (self._base, self._instance)
        with self._verifying:
            kept = self._verified.get(key)
        if kept is not None and self._clock() - kept[0] < self._ttl:
            return kept[1]
        reason, enabled = self._identity()
        if reason is not None:
            raise _failure(self.name, reason)
        with self._verifying:
            self._verified[key] = (self._clock(), enabled)
        return enabled

    def _identify(self) -> str | None:
        return self._identity()[0]

    def _identity(self) -> tuple[str | None, frozenset[str]]:
        """Why what answers at `/config` is not (our) SearXNG, or None and its enabled engines."""
        url = f"{self._base}/config"
        request = urllib.request.Request(  # nosec B310 - the configured SearXNG's own address
            url, headers={"Accept": "application/json"}
        )
        none: frozenset[str] = frozenset()
        try:
            answered = BoundedRequest(self._opener).fetch(
                request, deadline=self._timeout, limit=_RESPONSE_LIMIT
            )
        except urllib.error.HTTPError as exc:
            return f"answered HTTP {exc.code}", none
        except DeadlineExceeded:
            return _late(self._timeout), none
        except _UNREACHABLE as exc:
            return _unreachable(exc), none
        if answered.url != url:
            # A same-origin redirect was followed by the opener; the answer is refused here.
            return f"{IMPOSTOR} (its /config redirected)", none
        try:
            config = json.loads(answered.body)
        except _UNPARSABLE:
            return f"{IMPOSTOR} (its /config is not JSON)", none
        if not (
            isinstance(config, dict)
            and isinstance(config.get("instance_name"), str)
            and isinstance(config.get("version"), str)
            and isinstance(config.get("engines"), list)
            and isinstance(config.get("categories"), list)
        ):
            return f"{IMPOSTOR} (its /config is not SearXNG's)", none
        if self._instance is not None and config["instance_name"] != self._instance:
            # Neither name is said: the expected one is the person's, the other is untrusted.
            return f"{STRANGER} (its instance_name is not {SEARXNG_INSTANCE_ENV})", none
        enabled = frozenset(
            engine["name"]
            for engine in config["engines"]
            if isinstance(engine, dict)
            and isinstance(engine.get("name"), str)
            and engine.get("enabled", True) is True
        )
        return None, enabled


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
