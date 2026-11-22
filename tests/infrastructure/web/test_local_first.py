# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Local-first search: every query asks the local SearXNG; Brave answers only when SearXNG
failed and a key is configured, and that is never silent (operator ruling 2026-11-21).

Every key here is a fake. The query text is treated as private: no notice or error repeats it."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Any

import pytest

from vibey.infrastructure.web.backup_notice import PROCESS_BACKUP_NOTICE, BackupNotice
from vibey.infrastructure.web.interfaces import (
    BackupNoticeInterface,
    LocalFirstSearchInterface,
)
from vibey.infrastructure.web.local_first import LocalFirstSearch
from vibey.infrastructure.web.search import (
    SearchAnswer,
    SearchHit,
    WebSearchError,
    WebSearchSettings,
)

FAKE_KEY = "fake-brave-key-7a1b"
QUERY = "acme merger codename bluebird"
HIT = SearchHit("T", "https://t.example", "s")


class _Backend:
    def __init__(
        self,
        name: str,
        *,
        hits: list[SearchHit] | None = None,
        error: Exception | None = None,
        log: list[str] | None = None,
    ) -> None:
        self.name = name
        self.hits = hits or []
        self.error = error
        self.asked: list[tuple[str, int]] = []
        self.log = log if log is not None else []

    def search(self, query: str, limit: int) -> list[SearchHit]:
        self.asked.append((query, limit))
        self.log.append(f"{self.name} asked")
        if self.error is not None:
            raise self.error
        return list(self.hits)


class _Notice:
    """A notice that records what it said, in order with the backends' calls."""

    def __init__(self, log: list[str]) -> None:
        self._inner = BackupNotice(write=lambda text: log.append(f"said: {text}"))

    def announce(self, reason: str) -> str | None:
        return self._inner.announce(reason)


def _down(reason: str = "could not be reached (ConnectionRefusedError)") -> WebSearchError:
    return WebSearchError(f"searxng {reason}", reason=reason)


def _search(primary: _Backend, backup: _Backend | None, log: list[str]) -> LocalFirstSearch:
    return LocalFirstSearch(
        primary, backup, notice=_Notice(log), searxng_url="http://127.0.0.1:8080"
    )


def test_the_classes_honour_their_interfaces() -> None:
    log: list[str] = []
    assert isinstance(_search(_Backend("searxng"), None, log), LocalFirstSearchInterface)
    assert isinstance(BackupNotice(write=log.append), BackupNoticeInterface)
    assert isinstance(PROCESS_BACKUP_NOTICE, BackupNoticeInterface)


# -- the policy table -----------------------------------------------------------------------


def test_a_healthy_searxng_answers_and_brave_is_never_asked() -> None:
    log: list[str] = []
    brave = _Backend("brave", hits=[HIT], log=log)
    answer = _search(_Backend("searxng", hits=[HIT], log=log), brave, log).answer(QUERY, 3)
    assert answer == SearchAnswer(hits=(HIT,), backend="searxng")
    assert brave.asked == [] and log == ["searxng asked"]


def test_an_empty_answer_from_a_healthy_searxng_is_not_a_failure() -> None:
    log: list[str] = []
    brave = _Backend("brave", hits=[HIT], log=log)
    answer = _search(_Backend("searxng", hits=[], log=log), brave, log).answer(QUERY, 3)
    assert answer.hits == () and answer.backend == "searxng"
    assert brave.asked == [] and not any(entry.startswith("said") for entry in log)


@pytest.mark.parametrize(
    "reason",
    [
        "could not be reached (ConnectionRefusedError)",
        "could not be reached (TimeoutError)",
        "answered HTTP 502",
        "did not answer with JSON",
        "every engine it asked failed (3 unresponsive)",
    ],
)
def test_a_failed_searxng_with_a_key_goes_to_brave_and_says_so_first(reason: str) -> None:
    log: list[str] = []
    brave = _Backend("brave", hits=[HIT], log=log)
    search = _search(_Backend("searxng", error=_down(reason), log=log), brave, log)

    answer = search.answer(QUERY, 4)

    notice = f"local SearXNG unavailable ({reason}); this query went to Brave Search"
    assert answer == SearchAnswer(
        hits=(HIT,), backend="brave", notice=notice, fallback_reason=reason
    )
    assert brave.asked == [(QUERY, 4)]
    assert log == ["searxng asked", f"said: {notice}", "brave asked"]


def test_a_failed_searxng_with_no_key_says_what_was_tried_and_how_to_fix_it() -> None:
    log: list[str] = []
    search = LocalFirstSearch(
        _Backend("searxng", error=_down(), log=log),
        None,
        notice=_Notice(log),
        searxng_url="http://me:pw@127.0.0.1:8080/?token=t",
    )
    with pytest.raises(WebSearchError) as caught:
        search.answer(QUERY, 2)
    said = str(caught.value)
    assert said.startswith(
        "the local SearXNG at http://127.0.0.1:8080/ did not answer "
        "(could not be reached (ConnectionRefusedError)) and no Brave backup is configured"
    )
    assert "vibey doctor" in said and "VIBEY_SEARXNG_URL" in said
    assert "VIBEY_BRAVE_API_KEY" in said and "BRAVE_SEARCH_API_KEY" in said
    assert "pw" not in said and "token" not in said and QUERY not in said
    assert log == ["searxng asked"]


def test_when_brave_fails_too_both_failures_are_named_and_nothing_private() -> None:
    log: list[str] = []
    brave_down = WebSearchError("brave answered HTTP 429", reason="answered HTTP 429")
    search = _search(
        _Backend("searxng", error=_down(), log=log), _Backend("brave", error=brave_down), log
    )
    with pytest.raises(WebSearchError) as caught:
        search.answer(QUERY, 2)
    assert str(caught.value) == (
        "local SearXNG unavailable (could not be reached (ConnectionRefusedError)); "
        "the Brave backup failed too (brave answered HTTP 429)"
    )
    assert any(entry.startswith("said: ") for entry in log)


def test_every_query_asks_searxng_first_again() -> None:
    log: list[str] = []
    searx = _Backend("searxng", error=_down(), log=log)
    brave = _Backend("brave", hits=[HIT], log=log)
    search = _search(searx, brave, log)
    search.answer("one", 1)
    searx.error = None
    searx.hits = [HIT]
    assert search.answer("two", 1).backend == "searxng"
    assert [q for q, _ in searx.asked] == ["one", "two"] and [q for q, _ in brave.asked] == ["one"]


# -- never silent, said once ----------------------------------------------------------------


def test_the_notice_is_said_once_and_later_brave_answers_carry_only_the_marker() -> None:
    log: list[str] = []
    search = _search(
        _Backend("searxng", error=_down(), log=log), _Backend("brave", hits=[HIT], log=log), log
    )
    first = search.answer("one", 1)
    second = search.answer("two", 1)
    assert first.notice is not None and second.notice is None
    assert (second.backend, second.fallback_reason) == (
        "brave",
        "could not be reached (ConnectionRefusedError)",
    )
    assert sum(entry.startswith("said: ") for entry in log) == 1


def test_the_notice_says_this_query_and_never_the_query_or_a_url() -> None:
    log: list[str] = []
    # A naive implementation would put the error's own text in the notice; it carries both.
    leaky = WebSearchError(
        f"searxng failed for http://127.0.0.1:8080/search?q={QUERY}",
        reason="could not be reached (URLError)",
    )
    search = _search(
        _Backend("searxng", error=leaky, log=log), _Backend("brave", hits=[HIT], log=log), log
    )
    answer = search.answer(QUERY, 1)
    said = [entry for entry in log if entry.startswith("said: ")]
    assert said == [
        "said: local SearXNG unavailable (could not be reached (URLError)); "
        "this query went to Brave Search"
    ]
    assert QUERY not in said[0] and "?q=" not in said[0] and "http" not in said[0]
    assert answer.notice is not None and QUERY not in answer.notice


def test_the_notice_object_says_it_once_per_process_even_across_threads() -> None:
    said: list[str] = []
    notice = BackupNotice(write=said.append)
    results: list[str | None] = []

    def announce() -> None:
        results.append(notice.announce("answered HTTP 500"))

    threads = [threading.Thread(target=announce) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(said) == 1 and sum(result is not None for result in results) == 1
    assert (
        said[0] == "local SearXNG unavailable (answered HTTP 500); this query went to Brave Search"
    )


def test_by_default_the_notice_goes_to_standard_error(capsys: pytest.CaptureFixture[str]) -> None:
    BackupNotice().announce("answered HTTP 503")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "local SearXNG unavailable (answered HTTP 503); this query went to Brave Search\n"
    )


def test_a_reason_is_cleaned_to_one_short_line() -> None:
    said: list[str] = []
    BackupNotice(write=said.append).announce("bad\nsecond line \x1b[2J" + "x" * 400)
    assert "\n" not in said[0] and "\x1b" not in said[0] and "second" not in said[0]
    assert len(said[0]) < 260


# -- built from the settings; the key never shows ---------------------------------------------


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, amount: int | None = None) -> bytes:
        return self._payload


def _routing(searx_error: BaseException | None, brave_body: object) -> tuple[Any, list[Any]]:
    """An opener that plays SearXNG (failing as told) and Brave (answering as told)."""
    sent: list[Any] = []

    def opener(request: urllib.request.Request, timeout: float) -> _Response:
        sent.append(request)
        if request.full_url.startswith("https://api.search.brave.com/"):
            return _Response(json.dumps(brave_body).encode())
        if searx_error is not None:
            raise searx_error
        return _Response(b'{"results": []}')

    return opener, sent


BRAVE_BODY = {"web": {"results": [{"title": "B", "url": "https://b.example", "description": ""}]}}


@pytest.mark.parametrize(
    "name", ["VIBEY_BRAVE_API_KEY", "WEBSEARCH_BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY"]
)
def test_from_the_settings_the_fallback_sends_the_key_only_to_brave_and_shows_it_nowhere(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    said: list[str] = []
    settings = WebSearchSettings.from_environment({name: FAKE_KEY})
    opener, sent = _routing(urllib.error.URLError(ConnectionRefusedError()), BRAVE_BODY)
    search = LocalFirstSearch.from_settings(
        settings, opener=opener, notice=BackupNotice(write=said.append)
    )

    answer = search.answer(QUERY, 2)

    assert answer.backend == "brave" and [h.url for h in answer.hits] == ["https://b.example"]
    first, second = sent
    assert first.full_url.startswith("http://127.0.0.1:28180/")
    assert first.get_header("X-subscription-token") is None
    assert second.get_header("X-subscription-token") == FAKE_KEY
    shown = " ".join([*said, repr(answer), repr(search), repr(settings), str(answer.notice)])
    captured = capsys.readouterr()
    assert FAKE_KEY not in shown and FAKE_KEY not in captured.out + captured.err


def test_from_the_settings_a_failed_brave_never_echoes_the_key() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> _Response:
        raise OSError(f"boom {request.get_header('X-subscription-token')}")

    settings = WebSearchSettings.from_environment({"BRAVE_SEARCH_API_KEY": FAKE_KEY})
    search = LocalFirstSearch.from_settings(
        settings, opener=opener, notice=BackupNotice(write=lambda _: None)
    )
    with pytest.raises(WebSearchError) as caught:
        search.answer(QUERY, 1)
    assert FAKE_KEY not in str(caught.value) and QUERY not in str(caught.value)


def test_from_the_settings_without_a_key_there_is_no_backup() -> None:
    opener, sent = _routing(urllib.error.URLError(ConnectionRefusedError()), BRAVE_BODY)
    search = LocalFirstSearch.from_settings(WebSearchSettings.from_environment({}), opener=opener)
    with pytest.raises(WebSearchError, match="no Brave backup is configured"):
        search.answer(QUERY, 1)
    assert len(sent) == 1


def test_from_the_settings_the_process_notice_is_the_default() -> None:
    search = LocalFirstSearch.from_settings(WebSearchSettings.from_environment({}))
    assert search._notice is PROCESS_BACKUP_NOTICE


def test_from_the_settings_a_squatter_is_unavailable_and_the_backup_answers() -> None:
    said: list[str] = []
    sent: list[Any] = []

    def squatter(request: urllib.request.Request, timeout: float) -> _Response:
        sent.append(request.full_url)
        if request.full_url.startswith("https://api.search.brave.com/"):
            return _Response(json.dumps(BRAVE_BODY).encode())
        if request.full_url.endswith("/config"):
            return _Response(b'{"status": "ok"}')
        return _Response(b'{"results": [{"title": "Poison", "url": "https://poison.example"}]}')

    settings = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": FAKE_KEY})
    search = LocalFirstSearch.from_settings(
        settings, opener=squatter, notice=BackupNotice(write=said.append)
    )
    answer = search.answer(QUERY, 2)
    assert answer.backend == "brave" and [h.url for h in answer.hits] == ["https://b.example"]
    assert not [url for url in sent if "/search?" in url and "brave" not in url]
    assert said == [
        "local SearXNG unavailable (something other than SearXNG is listening there"
        " (its /config is not SearXNG's)); this query went to Brave Search"
    ]
    plain = LocalFirstSearch.from_settings(WebSearchSettings.from_environment({}), opener=squatter)
    with pytest.raises(WebSearchError, match="something other than SearXNG is listening there"):
        plain.answer(QUERY, 2)
