# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The settings the gptossloop DESIGN provider builds its web search from: the local SearXNG the
environment names, and a Brave backup only when a key is set. Every key here is a fake."""

import pytest

from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider
from vibey.infrastructure.web.local_first import LocalFirstSearch
from vibey.infrastructure.web.search import SEARXNG_URL_ENV, BraveBackend, SearxngBackend


@pytest.fixture
def dummy_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setenv(SEARXNG_URL_ENV, "http://dummy")
    return {SEARXNG_URL_ENV: "http://dummy"}


def test_gptossloop_design_web_search_configured(dummy_env: dict[str, str]) -> None:
    provider = GptossloopDesignProvider.from_environment(dummy_env)
    assert provider._web is not None
    search = provider._web._search
    assert isinstance(search, LocalFirstSearch)
    assert isinstance(search._primary, SearxngBackend) and search._backup is None


def test_a_brave_key_adds_the_backup_behind_searxng(dummy_env: dict[str, str]) -> None:
    provider = GptossloopDesignProvider.from_environment(
        {**dummy_env, "VIBEY_BRAVE_API_KEY": "fake-key"}
    )
    assert provider._web is not None
    search = provider._web._search
    assert isinstance(search, LocalFirstSearch)
    assert isinstance(search._primary, SearxngBackend)
    assert isinstance(search._backup, BraveBackend)
