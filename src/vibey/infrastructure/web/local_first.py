# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Local-first search: the rule every search vibey controls follows (operator ruling 2026-11-21).

Per query, with no state carried between queries but the once-per-process notice:

1. The local SearXNG is asked. Its answer is the answer, **including an empty one**: a healthy
   SearXNG that found nothing has not failed, and Brave is not asked.
2. Only when SearXNG failed (refused, timed out, any HTTP error, not JSON, no results list, or
   every engine it asked failed) **and** a Brave key is configured does the query go to Brave.
   Before it is sent, the first such query in the process is said on standard error
   (`BackupNotice`); every Brave answer says `backend: brave` and why.
3. With no key, the failure is raised: what was tried, where, and how to fix it.

The key is only ever in this process. A session's `vibey search` runs without it (no child is
given it), so inside an engine session search is the local SearXNG alone.

Declared by `interfaces/local_first_search_interface.py` (ADR-0016).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from vibey.infrastructure.web.backup_notice import PROCESS_BACKUP_NOTICE
from vibey.infrastructure.web.interfaces.backup_notice_interface import BackupNoticeInterface
from vibey.infrastructure.web.interfaces.search_backend_interface import SearchBackendInterface
from vibey.infrastructure.web.search import (
    BRAVE_KEY_ALIAS_ENV,
    BRAVE_KEY_ENV,
    SEARXNG_URL_ENV,
    BraveBackend,
    SearchAnswer,
    SearxngBackend,
    WebSearchError,
    WebSearchSettings,
    display_url,
)


class LocalFirstSearch:
    """Declared by `interfaces/local_first_search_interface.py::LocalFirstSearchInterface`."""

    def __init__(
        self,
        primary: SearchBackendInterface,
        backup: SearchBackendInterface | None,
        *,
        searxng_url: str,
        notice: BackupNoticeInterface = PROCESS_BACKUP_NOTICE,
    ) -> None:
        self._primary = primary
        self._backup = backup
        self._searxng_url = searxng_url
        self._notice = notice

    def __repr__(self) -> str:
        backup = "brave" if self._backup is not None else "none"
        return f"LocalFirstSearch(searxng={display_url(self._searxng_url)!r}, backup={backup!r})"

    @classmethod
    def from_settings(
        cls,
        settings: WebSearchSettings,
        *,
        opener: Callable[..., Any] | None = None,
        notice: BackupNoticeInterface = PROCESS_BACKUP_NOTICE,
    ) -> LocalFirstSearch:
        """The local SearXNG the settings name, with Brave behind it when they hold a key."""
        primary = SearxngBackend(
            settings.searxng_url, timeout_seconds=settings.timeout_seconds, opener=opener
        )
        backup = (
            BraveBackend(
                settings.brave_key, timeout_seconds=settings.timeout_seconds, opener=opener
            )
            if settings.brave_key is not None
            else None
        )
        return cls(primary, backup, searxng_url=settings.searxng_url, notice=notice)

    def answer(self, query: str, limit: int) -> SearchAnswer:
        try:
            hits = self._primary.search(query, limit)
        except WebSearchError as failure:
            return self._fall_back(query, limit, failure.reason)
        return SearchAnswer(hits=tuple(hits), backend="searxng")

    def _fall_back(self, query: str, limit: int, reason: str) -> SearchAnswer:
        if self._backup is None:
            raise WebSearchError(
                f"the local SearXNG at {display_url(self._searxng_url)} did not answer ({reason})"
                " and no Brave backup is configured: start SearXNG there (`vibey doctor` says"
                f" whether it answers) or point {SEARXNG_URL_ENV} at yours; a Brave key"
                f" ({BRAVE_KEY_ENV} or {BRAVE_KEY_ALIAS_ENV}) is used only as a backup",
                reason=reason,
            )
        # Said before the query is sent: from here on it has left the machine.
        notice = self._notice.announce(reason)
        try:
            hits = self._backup.search(query, limit)
        except WebSearchError as second:
            raise WebSearchError(
                f"local SearXNG unavailable ({reason}); the Brave backup failed too ({second})",
                reason=reason,
            ) from None
        return SearchAnswer(
            hits=tuple(hits), backend="brave", notice=notice, fallback_reason=reason
        )
