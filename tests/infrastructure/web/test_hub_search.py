# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's own search (ADR-0102, SP-ACP Task 9b): the local-first rule of Task 9c, run in the
hub process -- the one that holds the Brave key -- and handed to the service as data.

Every opener is a fake, and every key a fake one. Module-level test functions rather than a class
with an interface beside it (ADR-0016)."""

import asyncio
import io
import logging
import urllib.error
import urllib.request
from typing import Any

import pytest

from tests.infrastructure.web.searxng_fakes import SEARXNG_CONFIG, FakeResponse, is_config
from vibey.application.hub.interfaces.web_tools_service_interface import WebSearchPortInterface
from vibey.domain.web_tools import WebToolFailed, WebToolUnavailable
from vibey.infrastructure.web.backup_notice import BackupNotice
from vibey.infrastructure.web.hub_search import HubWebSearch

FAKE_KEY = "fake-brave-key-9b-31415"
QUERY = "private codename 7781"


def _searxng(results: list[dict[str, str]]) -> Any:
    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        if is_config(request):
            return FakeResponse(SEARXNG_CONFIG, url=request.full_url)
        return FakeResponse({"results": results}, url=request.full_url)

    return opener


def _down_then(brave: Any) -> Any:
    """SearXNG refuses; Brave answers as `brave` says (a payload, or an exception to raise)."""
    seen: list[urllib.request.Request] = []

    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        seen.append(request)
        if "api.search.brave.com" not in request.full_url:
            raise urllib.error.URLError(ConnectionRefusedError("refused"))
        if isinstance(brave, BaseException):
            raise brave
        return FakeResponse(brave, url=request.full_url)

    opener.seen = seen  # type: ignore[attr-defined]
    return opener


def _search(environ: dict[str, str], opener: Any, said: list[str] | None = None) -> HubWebSearch:
    notice = BackupNotice(write=(said if said is not None else []).append)
    return HubWebSearch(environ=environ, opener=opener, notice=notice)


def test_the_search_meets_its_seam() -> None:
    assert isinstance(HubWebSearch(), WebSearchPortInterface)


def test_the_local_searxng_answers_first() -> None:
    hits = [{"title": "Doc", "url": "https://docs.example/", "content": "snippet"}]
    answer = asyncio.run(_search({}, _searxng(hits)).search(QUERY, 3))
    assert answer.backend == "searxng" and answer.notice is None
    assert [(h.title, h.url, h.snippet) for h in answer.hits] == [
        ("Doc", "https://docs.example/", "snippet")
    ]


def test_the_brave_backup_answers_with_the_once_per_process_notice_and_never_the_key() -> None:
    brave = {"web": {"results": [{"title": "B", "url": "https://b.example/", "description": "d"}]}}
    said: list[str] = []
    search = _search({"VIBEY_BRAVE_API_KEY": FAKE_KEY}, _down_then(brave), said)
    first = asyncio.run(search.search(QUERY, None))
    second = asyncio.run(search.search(QUERY, None))
    assert first.backend == second.backend == "brave"
    assert first.notice is not None and "went to Brave Search" in first.notice
    assert second.notice is None  # once per hub process
    assert said == [first.notice]
    for text in (repr(first), repr(second), *said):
        assert FAKE_KEY not in text and QUERY not in text


def test_a_failure_names_the_backends_asked_and_never_the_key_or_the_query(
    caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.DEBUG)
    failing = _down_then(urllib.error.HTTPError("https://x", 401, FAKE_KEY, None, io.BytesIO()))  # type: ignore[arg-type]
    with pytest.raises(WebToolFailed) as raised:
        asyncio.run(_search({"BRAVE_SEARCH_API_KEY": FAKE_KEY}, failing).search(QUERY, 5))
    assert raised.value.tried == ("searxng", "brave")
    captured = capsys.readouterr()
    for text in (str(raised.value), repr(raised.value), caplog.text, captured.out, captured.err):
        assert FAKE_KEY not in text and QUERY not in text
    # The key went to Brave in its header, and only there.
    (brave_request,) = [r for r in failing.seen if "brave" in r.full_url]
    assert brave_request.get_header("X-subscription-token") == FAKE_KEY


def test_with_no_backup_a_failure_names_searxng_alone() -> None:
    with pytest.raises(WebToolFailed) as raised:
        asyncio.run(_search({}, _down_then({})).search(QUERY, 5))
    assert raised.value.tried == ("searxng",)
    assert "SearXNG" in str(raised.value)


def test_search_set_up_wrongly_in_the_hubs_environment_is_unavailable_not_failed() -> None:
    with pytest.raises(WebToolUnavailable, match="VIBEY_SEARCH_PROVIDER"):
        asyncio.run(_search({"VIBEY_SEARCH_PROVIDER": "brave"}, _searxng([])).search(QUERY, 5))


def test_a_limit_left_out_is_the_configured_number_of_results() -> None:
    asked: list[str] = []
    hits = [{"title": f"T{n}", "url": f"https://t{n}.example/", "content": ""} for n in range(9)]

    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        asked.append(request.full_url)
        return _searxng(hits)(request, timeout)

    answer = asyncio.run(_search({"VIBEY_SEARCH_RESULTS": "2"}, opener).search("q", None))
    assert len(answer.hits) == 2


def test_the_default_reads_the_hubs_own_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Built with no environment, the search reads the process's at each call: the hub's."""
    monkeypatch.setenv("VIBEY_SEARCH_PROVIDER", "brave")
    with pytest.raises(WebToolUnavailable):
        asyncio.run(HubWebSearch().search("q", 1))
