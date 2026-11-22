# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The variables vibey itself puts in every engine session (the non-secret web search settings)."""

import pytest

from vibey.infrastructure.engines.descriptors import CLAUDELOOP, CODEXLOOP, GPTOSSLOOP
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.web.search import BRAVE_KEY_NAMES, WebSearchSettings

TOLD = {"WEBSEARCH_PROVIDER": "searxng", "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:8080"}
WORKER = {
    "PATH": "/usr/bin",
    "HOME": "/home/x",
    "VIBEY_SEARXNG_URL": "http://127.0.0.1:8080",
    "VIBEY_PG_URL": "postgresql://secret",
}


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, CODEXLOOP])
def test_every_engines_session_is_told_the_overlay_and_still_none_of_vibeys_own_variables(
    descriptor: object,
) -> None:
    policy = EngineEnvironmentPolicy().with_overlay(TOLD)
    env = policy.environment(descriptor, source=WORKER).build()  # type: ignore[arg-type]
    assert env["WEBSEARCH_SEARXNG_URL"] == "http://127.0.0.1:8080"
    assert "VIBEY_SEARXNG_URL" not in env and "VIBEY_PG_URL" not in env


def test_without_an_overlay_nothing_changes() -> None:
    env = EngineEnvironmentPolicy().environment(CLAUDELOOP, source=WORKER).build()
    assert not [name for name in env if name.startswith("WEBSEARCH_")]


def test_an_adapters_own_overlay_wins_over_the_policys() -> None:
    policy = EngineEnvironmentPolicy().with_overlay(
        {"WEBSEARCH_PROVIDER": "searxng", "WEBSEARCH_RESULTS": "5"}
    )
    env = policy.environment(CLAUDELOOP, overlay={"WEBSEARCH_RESULTS": "9"}, source=WORKER).build()
    assert env["WEBSEARCH_RESULTS"] == "9" and env["WEBSEARCH_PROVIDER"] == "searxng"


def test_overlays_accumulate_and_the_project_declaration_is_kept() -> None:
    base = EngineEnvironmentPolicy(allow=["EXTRA_TOOL_HOME"])
    policy = base.with_overlay({"WEBSEARCH_A": "1"}).with_overlay({"WEBSEARCH_B": "2"})
    env = policy.environment(CLAUDELOOP, source={**WORKER, "EXTRA_TOOL_HOME": "/opt/x"}).build()
    assert (
        env["WEBSEARCH_A"] == "1"
        and env["WEBSEARCH_B"] == "2"
        and env["EXTRA_TOOL_HOME"] == "/opt/x"
    )


def test_an_overlay_cannot_smuggle_in_a_forbidden_variable() -> None:
    policy = EngineEnvironmentPolicy().with_overlay({"VIBEY_PG_URL": "postgresql://x"})
    with pytest.raises(ValueError, match="can never be passed to a child process"):
        policy.environment(CLAUDELOOP, source=WORKER)


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, CODEXLOOP, GPTOSSLOOP])
def test_with_a_brave_backup_configured_no_session_receives_the_key(descriptor: object) -> None:
    """The backup is vibey's alone: the worker that holds a key under every one of its names
    tells a session the local SearXNG and nothing else, and no name of the key gets through."""
    keyed = {**WORKER, **{name: f"fake-{n}" for n, name in enumerate(BRAVE_KEY_NAMES)}}
    settings = WebSearchSettings.from_environment(keyed)
    assert settings.has_backup
    policy = EngineEnvironmentPolicy().with_overlay(settings.session_environment())
    env = policy.environment(descriptor, source=keyed).build()  # type: ignore[arg-type]
    assert env["WEBSEARCH_SEARXNG_URL"] == "http://127.0.0.1:8080"
    assert not set(BRAVE_KEY_NAMES) & set(env)
    assert not [value for value in env.values() if value.startswith("fake-")]
    assert policy.web_search_command() == "vibey"
