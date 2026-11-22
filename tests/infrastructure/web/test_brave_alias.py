# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`BRAVE_SEARCH_API_KEY`, the name Brave's own tools use, as an alias of `VIBEY_BRAVE_API_KEY`.

`VIBEY_BRAVE_API_KEY` wins when both are set. The key configures only the **backup**: every query
asks the local SearXNG first, and Brave answers only when SearXNG failed. The key stays in
vibey's own processes: it is never put in a session's environment (the alias is not a `VIBEY_*`
name, so the rule under every allow-list names it), never printed, never in an error, including
on the fallback path. Every value here is a fake."""

from __future__ import annotations

from typing import Any

import pytest

from vibey.cli.web import run_search, web_search_line
from vibey.domain.config import ConfigError
from vibey.infrastructure.process.child_environment import (
    GATE_FORBIDDEN,
    MODEL_SESSION_FORBIDDEN,
    SYSTEM_ENVIRONMENT,
    ChildEnvironment,
    EnvironmentAllowList,
)
from vibey.infrastructure.web.backup_notice import BackupNotice
from vibey.infrastructure.web.local_first import LocalFirstSearch
from vibey.infrastructure.web.search import (
    BRAVE_KEY_ALIAS_ENV,
    DEFAULT_SEARXNG_URL,
    BraveBackend,
    WebSearchSettings,
)

FAKE = "fake-alias-key-9f3e"
OTHER = "fake-vibey-key-1c2d"


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, _limit: int) -> bytes:
        return self._payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_the_alias_alone_configures_the_brave_backup_and_says_where_it_came_from() -> None:
    settings = WebSearchSettings.from_environment({"BRAVE_SEARCH_API_KEY": FAKE})
    assert BRAVE_KEY_ALIAS_ENV == "BRAVE_SEARCH_API_KEY"
    assert (settings.searxng_url, settings.brave_key, settings.brave_key_env) == (
        DEFAULT_SEARXNG_URL,
        FAKE,
        "BRAVE_SEARCH_API_KEY",
    )
    search = LocalFirstSearch.from_settings(settings)
    assert isinstance(search._backup, BraveBackend)


def test_vibeys_own_name_wins_when_both_are_set() -> None:
    settings = WebSearchSettings.from_environment(
        {"BRAVE_SEARCH_API_KEY": FAKE, "VIBEY_BRAVE_API_KEY": OTHER}
    )
    assert (settings.brave_key, settings.brave_key_env) == (OTHER, "VIBEY_BRAVE_API_KEY")


def test_searxng_stays_the_primary_and_the_session_is_told_nothing_of_the_key() -> None:
    settings = WebSearchSettings.from_environment(
        {"BRAVE_SEARCH_API_KEY": FAKE, "VIBEY_SEARXNG_URL": "http://127.0.0.1:8080"}
    )
    assert settings.session_environment()["WEBSEARCH_PROVIDER"] == "searxng"
    assert FAKE not in repr(settings.session_environment())


def test_choosing_brave_as_the_provider_is_refused_even_with_the_alias_set() -> None:
    with pytest.raises(ConfigError, match="VIBEY_BRAVE_API_KEY or BRAVE_SEARCH_API_KEY"):
        WebSearchSettings.from_environment(
            {"BRAVE_SEARCH_API_KEY": FAKE, "VIBEY_SEARCH_PROVIDER": "brave"}
        )


def test_a_blank_alias_is_not_a_key() -> None:
    assert not WebSearchSettings.from_environment({"BRAVE_SEARCH_API_KEY": "  "}).has_backup


def test_the_key_is_never_in_a_repr_a_session_environment_or_the_workers_line() -> None:
    settings = WebSearchSettings.from_environment({"BRAVE_SEARCH_API_KEY": FAKE})
    assert FAKE not in repr(settings)
    assert FAKE not in repr(settings.session_environment())
    line = web_search_line(settings)
    assert "configured via BRAVE_SEARCH_API_KEY" in line and FAKE not in line
    vibey = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": OTHER})
    assert "configured via VIBEY_BRAVE_API_KEY" in web_search_line(vibey)


def test_the_no_backup_hint_names_the_alias() -> None:
    assert "BRAVE_SEARCH_API_KEY" in web_search_line(WebSearchSettings.from_environment({}))


def _searx_down_brave_up(sent: list[Any]) -> Any:
    def opener(request: Any, timeout: float) -> _Response:
        sent.append(request)
        if request.full_url.startswith("https://api.search.brave.com/"):
            return _Response(b'{"web": {"results": [{"title": "t", "url": "https://a.example"}]}}')
        raise ConnectionRefusedError

    return opener


def test_a_fallback_through_the_alias_sends_the_key_to_brave_and_prints_it_nowhere(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sent: list[Any] = []
    environ = {"BRAVE_SEARCH_API_KEY": FAKE}
    for as_json in (False, True):
        notice = BackupNotice()
        assert (
            run_search(
                "q",
                None,
                as_json,
                environ=environ,
                opener=_searx_down_brave_up(sent),
                notice=notice,
            )
            == 0
        )
    brave = [r for r in sent if r.full_url.startswith("https://api.search.brave.com/")]
    assert len(brave) == 2 and all(r.get_header("X-subscription-token") == FAKE for r in brave)
    assert all(r.get_header("X-subscription-token") is None for r in sent if r not in brave)
    captured = capsys.readouterr()
    assert FAKE not in captured.out and FAKE not in captured.err
    assert "this query went to Brave Search" in captured.err


def test_a_failed_or_refused_search_never_echoes_the_key(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def failing(request: Any, timeout: float) -> _Response:
        raise OSError(f"boom {request.get_header('X-subscription-token')}")

    environ = {"BRAVE_SEARCH_API_KEY": FAKE}
    notice = BackupNotice()
    assert run_search("q", None, False, environ=environ, opener=failing, notice=notice) == 1
    refused = {**environ, "VIBEY_SEARCH_PROVIDER": "brave"}
    assert run_search("q", None, False, environ=refused) == 2
    captured = capsys.readouterr()
    assert FAKE not in captured.out and FAKE not in captured.err


@pytest.mark.parametrize("forbidden", [MODEL_SESSION_FORBIDDEN, GATE_FORBIDDEN])
def test_no_allow_list_can_pass_the_alias_to_a_child(forbidden: Any) -> None:
    assert forbidden.forbids("BRAVE_SEARCH_API_KEY")
    with pytest.raises(ValueError, match="BRAVE_SEARCH_API_KEY can never be passed"):
        EnvironmentAllowList(["BRAVE_SEARCH_API_KEY"], forbidden=forbidden)
    wide = EnvironmentAllowList(["PATH"], ["BRAVE_", "B"], forbidden=forbidden)
    source = {"PATH": "/bin", "BRAVE_SEARCH_API_KEY": FAKE, "BRAVE_OTHER": "ok"}
    env = ChildEnvironment(wide, source=source).build()
    assert "BRAVE_SEARCH_API_KEY" not in env and FAKE not in env.values()
    assert env["BRAVE_OTHER"] == "ok"
    with pytest.raises(ValueError, match="can never be passed"):
        ChildEnvironment(wide, overlay={"BRAVE_SEARCH_API_KEY": FAKE})


def test_the_system_environment_every_child_starts_from_drops_it() -> None:
    source = {"PATH": "/bin", "HOME": "/h", "BRAVE_SEARCH_API_KEY": FAKE}
    assert (
        ChildEnvironment(SYSTEM_ENVIRONMENT, source=source).build().get("BRAVE_SEARCH_API_KEY")
        is None
    )


def test_there_is_no_fourth_name_for_the_key() -> None:
    settings = WebSearchSettings.from_environment({"WEBSEARCH_BRAVE_SEARCH_API_KEY": FAKE})
    assert not settings.has_backup


def test_the_websearch_form_is_read_and_named_as_itself() -> None:
    settings = WebSearchSettings.from_environment({"WEBSEARCH_BRAVE_API_KEY": FAKE})
    assert settings.brave_key_env == "WEBSEARCH_BRAVE_API_KEY"
    line = web_search_line(settings)
    assert "configured via WEBSEARCH_BRAVE_API_KEY" in line and FAKE not in line
    both = WebSearchSettings.from_environment(
        {"WEBSEARCH_BRAVE_API_KEY": FAKE, "BRAVE_SEARCH_API_KEY": OTHER}
    )
    assert both.brave_key == FAKE


@pytest.mark.parametrize("forbidden", [MODEL_SESSION_FORBIDDEN, GATE_FORBIDDEN])
def test_no_allow_list_can_pass_the_websearch_form_to_a_child(forbidden: Any) -> None:
    assert forbidden.forbids("WEBSEARCH_BRAVE_API_KEY")
    with pytest.raises(ValueError, match="can never be passed"):
        EnvironmentAllowList(["WEBSEARCH_BRAVE_API_KEY"], forbidden=forbidden)
    wide = EnvironmentAllowList([], ["WEBSEARCH_"], forbidden=forbidden)
    source = {"WEBSEARCH_BRAVE_API_KEY": FAKE, "WEBSEARCH_SEARXNG_URL": "http://h"}
    env = ChildEnvironment(wide, source=source).build()
    assert "WEBSEARCH_BRAVE_API_KEY" not in env and env["WEBSEARCH_SEARXNG_URL"] == "http://h"
