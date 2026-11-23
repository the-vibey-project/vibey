# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One page as plain text, for a model that named the URL, through the hub's guarded fetch.

`vibey fetch` (and so the local runners' `web_fetch` tool, which runs it) and the DESIGN stage's
web research read a page here (SP-ACP Task 11a, P-9b-2). A URL a model chose is attacker-
influenced, so this is never weaker than what the hub serves an agent (`GuardedPageFetch`, read
with the same policy, `domain/web_tools.py`):

- the URL must be a public http(s) target, every spelling of an address read the way the hub
  reads it (no decimal, octal or hex IPv4, no local, internal or metadata name, IPv4-mapped and
  NAT64 addresses judged by the address inside them);
- every address a name resolves to must be public, and the one checked is the one connected to;
- every redirect is a new target, checked again, never from https down to http;
- fixed headers, nothing compressed, only the person's content types, bounded in bytes,
  characters, hops and one deadline in all.

The bounds and host lists are `[web]` from the person's own `vibey.toml`, narrowed by the one in
the folder this runs in (`WEB_SETTINGS.load_trusted`): a session's worktree may only tighten
them. `max_chars` a caller asks for may lower `[web] max_chars`, never raise it.

Unlike the hub's fetch it spends no budget and writes no ledger record: it runs in a session or
a worker, where the act is the session's own. Declared by
`interfaces/page_fetcher_interface.py` (ADR-0016).
"""

import asyncio
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from vibey.application.hub.interfaces.web_tools_service_interface import WebFetchPortInterface
from vibey.domain.config import ConfigError
from vibey.domain.interfaces.web_tools_interface import WebToolPolicyInterface
from vibey.domain.web_tools import WEB_TOOL_POLICY, WebToolFailed, WebToolRefused, WebToolSettings
from vibey.infrastructure.user_config_folder import UserConfigFolder
from vibey.infrastructure.web.fetch import FetchedPage, WebFetchError
from vibey.infrastructure.web.guarded_fetch import GuardedPageFetch
from vibey.infrastructure.web.web_settings_loader import WEB_SETTINGS


def own_web_settings() -> WebToolSettings:
    """`[web]` from the person's own `vibey.toml`, narrowed by the current folder's.

    Module-level by design: the default of `PageFetcher`'s `settings` seam, kept here so the test
    suite can stand another in for the developer's own file."""
    return WEB_SETTINGS.load_trusted(UserConfigFolder().vibey_toml(), Path.cwd() / "vibey.toml")


class PageFetcher:
    """Declared by `interfaces/page_fetcher_interface.py::PageFetcherInterface`."""

    def __init__(
        self,
        *,
        settings: Callable[[], WebToolSettings] = lambda: own_web_settings(),
        fetch: WebFetchPortInterface | None = None,
        policy: WebToolPolicyInterface = WEB_TOOL_POLICY,
    ) -> None:
        self._settings = settings
        self._fetch = fetch if fetch is not None else GuardedPageFetch(policy=policy)
        self._policy = policy

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        """The page at `url` as text. Raises `WebFetchError`, naming the cause and never the
        URL, when it is refused or cannot be read. Never call it from inside a running event
        loop: it runs the guarded fetch's own."""
        try:
            settings = self._settings()
        except ConfigError as exc:
            raise WebFetchError(f"[web] cannot be read: {exc}") from None
        if max_chars is not None and max_chars < settings.max_chars:
            try:
                settings = replace(settings, max_chars=max_chars)
            except ValueError as exc:  # below what `[web] max_chars` allows (review 1 N-3)
                raise WebFetchError(str(exc)) from None
        try:
            target = self._policy.target(url, settings)
            page = asyncio.run(self._fetch.fetch(target, settings))
        except (WebToolRefused, WebToolFailed) as exc:
            raise WebFetchError(str(exc)) from None
        return FetchedPage(url=page.url, title=page.title, text=page.text, truncated=page.truncated)
