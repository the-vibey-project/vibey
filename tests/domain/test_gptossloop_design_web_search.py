import os
from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider

# Helper to build provider

def build_provider(env_vars):
    env = dict(os.environ)
    env.update(env_vars)
    return GptossloopDesignProvider.from_environment(env)


def test_searxng_backend_configured(monkeypatch):
    env = {"VIBEY_SEARXNG_URL": "https://search.example.com"}
    provider = build_provider(env)
    assert provider._web is not None
    assert provider._web._backend.name.lower() == "searxng"


def test_brave_backend_configured(monkeypatch):
    env = {"VIBEY_BRAVE_API_KEY": "fake-key"}
    provider = build_provider(env)
    assert provider._web is not None
    assert provider._web._backend.name.lower() == "brave"


def test_no_backend_configured(monkeypatch):
    env = {}
    provider = build_provider(env)
    assert provider._web is None
