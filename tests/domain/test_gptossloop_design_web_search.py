# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The configuration path the gptossloop DESIGN provider takes to its web search: the local
SearXNG named by the environment (or the loopback default), with Brave only as a backup."""

import pytest

from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider
from vibey.infrastructure.web.local_first import LocalFirstSearch
from vibey.infrastructure.web.search import SEARXNG_URL_ENV, SearxngBackend


def test_the_provider_asks_the_configured_searxng(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = GptossloopDesignProvider.from_environment({SEARXNG_URL_ENV: "http://dummy"})
    assert provider._web is not None
    search = provider._web._search
    assert isinstance(search, LocalFirstSearch)
    assert isinstance(search._primary, SearxngBackend) and search._primary.name == "searxng"
    assert search._searxng_url == "http://dummy"
