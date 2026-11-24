# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The variables vibey itself puts in every engine session, and what never reaches one.

Since SP-LOOPS Phase 6 a session is told nothing about a search backend: no SearXNG address, no
key and no `WEBSEARCH_*` name. Its web is the hub's, through the run's own overlay
(`test_session_web_overlay.py`)."""

import pytest

from vibey.infrastructure.engines.descriptors import CLAUDELOOP, CODEXLOOP, GPTOSSLOOP, QWENLOOP
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.web.search import BRAVE_KEY_NAMES

TOLD = {"X_VIBEY_TOLD": "1", "X_ENDPOINT": "http://127.0.0.1:11434"}
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
    assert env["X_ENDPOINT"] == "http://127.0.0.1:11434"
    assert "VIBEY_SEARXNG_URL" not in env and "VIBEY_PG_URL" not in env


def test_without_an_overlay_nothing_changes() -> None:
    env = EngineEnvironmentPolicy().environment(CLAUDELOOP, source=WORKER).build()
    assert "X_VIBEY_TOLD" not in env


def test_an_adapters_own_overlay_wins_over_the_policys() -> None:
    policy = EngineEnvironmentPolicy().with_overlay({"X_A": "1", "X_B": "5"})
    env = policy.environment(CLAUDELOOP, overlay={"X_B": "9"}, source=WORKER).build()
    assert env["X_B"] == "9" and env["X_A"] == "1"


def test_overlays_accumulate_and_the_project_declaration_is_kept() -> None:
    base = EngineEnvironmentPolicy(allow=["EXTRA_TOOL_HOME"])
    policy = base.with_overlay({"X_A": "1"}).with_overlay({"X_B": "2"})
    env = policy.environment(CLAUDELOOP, source={**WORKER, "EXTRA_TOOL_HOME": "/opt/x"}).build()
    assert env["X_A"] == "1" and env["X_B"] == "2" and env["EXTRA_TOOL_HOME"] == "/opt/x"


def test_the_vibey_command_survives_an_overlay_and_the_overlay_a_command() -> None:
    policy = EngineEnvironmentPolicy().with_overlay({"X_A": "1"}).with_vibey_command("/v/vibey")
    env = policy.environment(CLAUDELOOP, source=WORKER).build()
    assert env["X_A"] == "1" and policy.vibey_command() == "/v/vibey"
    assert "/v/vibey" not in env.values()


def test_an_overlay_cannot_smuggle_in_a_forbidden_variable() -> None:
    policy = EngineEnvironmentPolicy().with_overlay({"VIBEY_PG_URL": "postgresql://x"})
    with pytest.raises(ValueError, match="can never be passed to a child process"):
        policy.environment(CLAUDELOOP, source=WORKER)


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, CODEXLOOP, GPTOSSLOOP, QWENLOOP])
def test_with_a_search_backend_configured_no_session_receives_any_of_it(
    descriptor: object,
) -> None:
    """The worker that holds a SearXNG address, a Brave key under every one of its names and the
    old session names gives a session none of them."""
    keyed = {
        **WORKER,
        **{name: f"fake-{n}" for n, name in enumerate(BRAVE_KEY_NAMES)},
        "WEBSEARCH_PROVIDER": "searxng",
        "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:8080",
        "WEBSEARCH_COMMAND": "/v/vibey",
    }
    policy = EngineEnvironmentPolicy()
    env = policy.environment(descriptor, source=keyed).build()  # type: ignore[arg-type]
    assert not [n for n in env if n.startswith("WEBSEARCH_") or "SEARXNG" in n or "BRAVE" in n]
    assert not [value for value in env.values() if value.startswith("fake-")]
