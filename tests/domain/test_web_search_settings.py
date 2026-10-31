# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import os

import pytest

from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider
from vibey.infrastructure.web.search import (
    SEARXNG_URL_ENV,
    WebSearchSettings,
    backend_for,
)


@pytest.fixture
def dummy_env(monkeypatch):
    monkeypatch.setenv(SEARXNG_URL_ENV, "http://dummy")
    # Ensure any other env that might affect is unset
    monkeypatch.delenv("VIBEY_BRAVE_API_KEY", raising=False)
    return os.environ


def test_gptossloop_design_web_search_configured(dummy_env):
    # Create provider
    provider = GptossloopDesignProvider.from_environment(dummy_env)
    # Provider should have a web backend
    assert provider._web is not None
    # The backend should be from settings
    settings = WebSearchSettings.from_environment(dummy_env)
    assert settings is not None
    backend = backend_for(settings)
    # The provider's backend should match the constructed one
    assert provider._web._backend.name == backend.name


# Verify that backend uses SearXNG provider name


def test_searxng_backend_name(dummy_env):
    settings = WebSearchSettings.from_environment(dummy_env)
    assert settings is not None
    backend = backend_for(settings)
    assert backend.name == "searxng"


"""
These tests exercise the configuration path used by the gptossloop design provider
to ensure that it properly uses the web search backend when the environment is set.
"""
