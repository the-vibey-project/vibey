# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Web search as the hub serves it (ADR-0102, SP-ACP Task 9b): Task 9c's local-first rule, run in
the hub's own process.

The hub is a vibey process like any other: its search settings are its own environment's
(`WebSearchSettings.from_environment`), read at each search, so the local SearXNG answers first
and the Brave backup -- whose key is in the hub's environment and nowhere else -- answers only when
SearXNG failed. The first query of the hub's life to go to Brave says so once
(`PROCESS_BACKUP_NOTICE`, on the hub's standard error) and the sentence is handed back with that
answer as its `notice`. The key is never in an answer, an error or a log line: 9c's backends name a
failure by its cause alone.

A search setting the hub's environment gets wrong (`VIBEY_SEARCH_PROVIDER=brave`, a malformed
`VIBEY_SEARXNG_URL`) is `WebToolUnavailable`, not a failure: nothing was sent. Declared by
`interfaces/hub_search_interface.py`; the port it fills is the application's
`WebSearchPortInterface`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Mapping
from typing import Any

from vibey.application.dto import WebHit, WebSearchAnswer
from vibey.domain.config import ConfigError
from vibey.domain.web_tools import WebToolFailed, WebToolUnavailable
from vibey.infrastructure.web.backup_notice import PROCESS_BACKUP_NOTICE
from vibey.infrastructure.web.interfaces.backup_notice_interface import BackupNoticeInterface
from vibey.infrastructure.web.local_first import LocalFirstSearch
from vibey.infrastructure.web.search import WebSearchError, WebSearchSettings


class HubWebSearch:
    """Declared by `interfaces/hub_search_interface.py::HubWebSearchInterface`."""

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        opener: Callable[..., Any] | None = None,
        notice: BackupNoticeInterface = PROCESS_BACKUP_NOTICE,
    ) -> None:
        self._environ = environ
        self._opener = opener
        self._notice = notice

    async def search(self, query: str, limit: int | None) -> WebSearchAnswer:
        try:
            settings = WebSearchSettings.from_environment(
                self._environ if self._environ is not None else os.environ
            )
        except ConfigError as exc:
            raise WebToolUnavailable(f"search is not set up on the hub: {exc}") from None
        engine = LocalFirstSearch.from_settings(settings, opener=self._opener, notice=self._notice)
        try:
            answer = await asyncio.to_thread(engine.answer, query, limit or settings.results)
        except WebSearchError as exc:
            tried = ("searxng", "brave") if settings.has_backup else ("searxng",)
            raise WebToolFailed(str(exc), tried=tried) from None
        return WebSearchAnswer(
            hits=tuple(WebHit(hit.title, hit.url, hit.snippet) for hit in answer.hits),
            backend=answer.backend,
            notice=answer.notice,
        )
