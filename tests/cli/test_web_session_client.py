# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey search` and `vibey fetch` inside an engine session (SP-LOOPS Phase 6, Task 4; R1).

With `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE` set, both go through the hub with the session's
own token, read from its file on every call; with `VIBEY_WEB_STATE=none` they say there is no
hub and exit 78; a session marked any other way never searches in-process; and with none of
these set, a person at their own terminal gets exactly what they got before.

The hub is an `httpx.MockTransport`; the token file is real and POSIX-moded."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from tests.infrastructure.web.searxng_fakes import SEARXNG_CONFIG, FakeResponse, is_config
from tests.infrastructure.web.session_hub_fakes import (
    FETCH_ANSWER,
    HUB_URL,
    OTHER_TOKEN,
    SEARCH_ANSWER,
    TOKEN,
    StubHub,
    framed,
    raw_token_file,
    replace_token,
    token_file,
)
from vibey.cli import web
from vibey.cli.main import app
from vibey.cli.web import (
    EXIT_BUDGET,
    EXIT_CONFIG,
    EXIT_ENDED,
    EXIT_FORBIDDEN,
    EXIT_UNAVAILABLE,
    SESSION_EXIT_CODES,
    UNTRUSTED,
    run_fetch,
    run_search,
)
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.web.fetch import FetchedPage
from vibey.infrastructure.web.interfaces.session_web_access_interface import (
    SessionWebAccessInterface,
)
from vibey.infrastructure.web.session import (
    HUB_URL_VARIABLE,
    NO_HUB,
    STATE_VARIABLE,
    TOKEN_FILE_VARIABLE,
)
from vibey.infrastructure.web.session_hub_client import SessionHubClient

pytestmark = pytest.mark.skipif(os.name != "posix", reason="token file modes are POSIX")

runner = CliRunner()

type HubFactory = Callable[[SessionWebAccessInterface], SessionHubClient]


def _session(path: Path) -> dict[str, str]:
    return {HUB_URL_VARIABLE: HUB_URL, TOKEN_FILE_VARIABLE: str(path)}


def _through(hub: StubHub) -> HubFactory:
    def make(access: SessionWebAccessInterface) -> SessionHubClient:
        assert access.token_file is not None
        return SessionHubClient(
            access.hub_url, access.token_file, client=hub, web_settings=lambda: WebToolSettings()
        )

    return make


def _no_hub(access: SessionWebAccessInterface) -> SessionHubClient:
    raise AssertionError("no hub may be built for a person or a session without one")


def _never_opened(request: Any, timeout: float) -> Any:
    raise AssertionError("a session never searches in-process")


class _NeverFetches:
    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        raise AssertionError("a session never fetches in-process")


def test_with_the_hub_a_search_prints_the_hubs_answer_as_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = StubHub()
    code = run_search(
        "next js",
        3,
        True,
        environ=_session(token_file(tmp_path)),
        opener=_never_opened,
        hub=_through(hub),
    )

    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert code == 0
    assert document == {
        "untrusted": True,
        "backend": "searxng",
        "provider": "searxng",
        "query": "next js",
        "results": SEARCH_ANSWER["results"],
    }
    assert hub.bearer() == f"Bearer {TOKEN}" and hub.body() == {"query": "next js", "limit": 3}
    assert TOKEN not in captured.out + captured.err


def test_with_the_hub_a_search_prints_text_and_the_hubs_notice_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    notice = "local SearXNG unavailable (could not be reached); this query went to Brave Search"
    hub = StubHub(answer={**SEARCH_ANSWER, "backend": "brave", "notice": notice})
    code = run_search("q", None, False, environ=_session(token_file(tmp_path)), hub=_through(hub))

    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.splitlines()[:3] == [
        UNTRUSTED,
        "backend: brave (the backup: local SearXNG unavailable)",
        "1. Next.js",
    ]
    assert captured.err.strip() == notice


def test_the_json_answer_carries_the_hubs_notice(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = StubHub(answer={**SEARCH_ANSWER, "backend": "brave", "notice": "said once"})
    run_search("q", None, True, environ=_session(token_file(tmp_path)), hub=_through(hub))

    assert json.loads(capsys.readouterr().out)["notice"] == "said once"


def test_the_token_is_read_fresh_on_each_call(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = token_file(tmp_path)
    hub = StubHub()

    assert run_search("one", None, True, environ=_session(path), hub=_through(hub)) == 0
    replace_token(path, OTHER_TOKEN)
    assert run_search("two", None, True, environ=_session(path), hub=_through(hub)) == 0

    assert [r.headers["authorization"] for r in hub.requests] == [
        f"Bearer {TOKEN}",
        f"Bearer {OTHER_TOKEN}",
    ]
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err
    assert OTHER_TOKEN not in captured.out + captured.err


def test_a_missing_token_file_exits_78_and_names_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "run-x" / "web-token"
    hub = StubHub()

    assert run_search("q", None, False, environ=_session(missing), hub=_through(hub)) == 78
    assert str(missing) in capsys.readouterr().out
    assert (
        run_fetch("https://a.example/", None, False, environ=_session(missing), hub=_through(hub))
        == 78
    )
    assert str(missing) in capsys.readouterr().out
    assert hub.requests == []


def test_an_empty_token_file_exits_78_and_names_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = raw_token_file(tmp_path, b"")

    assert run_search("q", None, False, environ=_session(path), hub=_through(StubHub())) == 78
    out = capsys.readouterr().out
    assert str(path) in out and "holds no token" in out


@pytest.mark.parametrize(
    ("status", "detail", "code", "said"),
    [
        (401, "Unauthorized", EXIT_ENDED, "this session's web access has ended"),
        (403, "session:x may not do that", EXIT_FORBIDDEN, "session:x may not do that"),
        (
            429,
            "web budget exhausted: session:x has used [web] session_searches = 30 for this session",
            EXIT_BUDGET,
            "web budget exhausted: session:x has used [web] session_searches = 30 for this session",
        ),
        (502, "no search backend answered", 1, "no search backend answered"),
    ],
)
def test_the_hubs_refusals_are_shown_plainly_with_their_own_exit_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    status: int,
    detail: str,
    code: int,
    said: str,
) -> None:
    hub = StubHub(status, {"detail": detail})
    path = token_file(tmp_path)

    assert run_search("q", None, True, environ=_session(path), hub=_through(hub)) == code
    searched = capsys.readouterr()
    assert (
        run_fetch("https://a.example/", None, True, environ=_session(path), hub=_through(hub))
        == code
    )
    fetched = capsys.readouterr()

    for captured in (searched, fetched):
        assert captured.out.startswith("error: ") and said in captured.out
        assert TOKEN not in captured.out + captured.err


def test_a_hub_that_cannot_be_reached_exits_69_with_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = StubHub(fail=httpx.ConnectError("refused"))

    assert (
        run_search("q", None, False, environ=_session(token_file(tmp_path)), hub=_through(hub))
        == EXIT_UNAVAILABLE
    )
    out = capsys.readouterr().out
    assert out.count("\n") == 1 and out.startswith("error: ") and "ConnectError" in out
    assert TOKEN not in out


def test_the_exit_codes_are_distinct_and_documented_in_each_commands_help() -> None:
    codes = [EXIT_ENDED, EXIT_FORBIDDEN, EXIT_BUDGET, EXIT_UNAVAILABLE, EXIT_CONFIG]
    assert len(set(codes)) == len(codes) and 0 not in codes and 1 not in codes
    assert (EXIT_ENDED, EXIT_FORBIDDEN, EXIT_BUDGET, EXIT_UNAVAILABLE, EXIT_CONFIG) == (
        67,
        77,
        75,
        69,
        78,
    )
    assert SESSION_EXIT_CODES == {
        "unconfigured": 78,
        "refused": 2,
        "ended": 67,
        "forbidden": 77,
        "budget": 75,
        "unreachable": 69,
        "failed": 1,
    }
    for command in ("search", "fetch"):
        shown = " ".join(runner.invoke(app, [command, "--help"], terminal_width=200).output.split())
        for code in (67, 69, 75, 77, 78):
            assert str(code) in shown, (command, code)
        assert HUB_URL_VARIABLE in shown and TOKEN_FILE_VARIABLE in shown


def test_with_no_hub_search_and_fetch_say_so_and_exit_78(
    capsys: pytest.CaptureFixture[str],
) -> None:
    environ = {STATE_VARIABLE: "none", "WEBSEARCH_PROVIDER": "searxng"}

    assert run_search("q", None, False, environ=environ, opener=_never_opened, hub=_no_hub) == 78
    assert capsys.readouterr().out == (
        f"error: web search is unavailable in this session: {NO_HUB}\n"
    )
    assert (
        run_fetch(
            "https://a.example/", None, False, environ=environ, fetcher=_NeverFetches(), hub=_no_hub
        )
        == 78
    )
    assert capsys.readouterr().out == (
        f"error: fetching a web page is unavailable in this session: {NO_HUB}\n"
    )


@pytest.mark.parametrize(
    "environ",
    [
        {"WEBSEARCH_PROVIDER": "searxng", "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:28180"},
        {"WEBSEARCH_COMMAND": "/opt/vibey"},
        {HUB_URL_VARIABLE: HUB_URL},
        {TOKEN_FILE_VARIABLE: "/runs/x/web-token"},
        {STATE_VARIABLE: "hub"},
    ],
)
def test_a_session_without_the_hub_never_searches_or_fetches_in_process(
    capsys: pytest.CaptureFixture[str], environ: dict[str, str]
) -> None:
    assert run_search("q", None, True, environ=environ, opener=_never_opened, hub=_no_hub) == 78
    assert (
        run_fetch(
            "https://a.example/", None, True, environ=environ, fetcher=_NeverFetches(), hub=_no_hub
        )
        == 78
    )
    assert "unavailable in this session" in capsys.readouterr().out


def test_with_nothing_set_a_person_still_searches_the_local_searxng(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []

    def opener(request: Any, timeout: float) -> Any:
        if is_config(request):
            return FakeResponse(SEARXNG_CONFIG, url=request.full_url)
        seen.append(request.full_url)
        return FakeResponse(
            {"results": [{"title": "T", "url": "https://t.example", "content": "c"}]}
        )

    assert run_search("q", None, True, environ={}, opener=opener, hub=_no_hub) == 0
    assert seen == ["http://127.0.0.1:28180/search?q=q&format=json"]
    assert json.loads(capsys.readouterr().out)["backend"] == "searxng"


def test_with_nothing_set_a_person_still_fetches_through_the_guarded_fetch(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Fetcher:
        def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
            return FetchedPage(url=url, title="T", text="Body", truncated=False)

    assert (
        run_fetch("https://a.example/", None, True, environ={}, fetcher=Fetcher(), hub=_no_hub) == 0
    )
    assert json.loads(capsys.readouterr().out)["title"] == "T"


def test_with_the_hub_a_fetch_keeps_its_answers_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = StubHub()
    path = token_file(tmp_path)

    assert (
        run_fetch(
            "https://a.example/",
            None,
            True,
            environ=_session(path),
            fetcher=_NeverFetches(),
            hub=_through(hub),
        )
        == 0
    )
    document = json.loads(capsys.readouterr().out)
    assert document == {
        "untrusted": True,
        "url": "https://a.example/",
        "title": "",
        "truncated": False,
        "text": FETCH_ANSWER["text"],
    }
    assert (
        run_fetch("https://a.example/", None, False, environ=_session(path), hub=_through(hub)) == 0
    )
    out = capsys.readouterr().out
    assert out.startswith(f"{UNTRUSTED}\nhttps://a.example/\nhttps://a.example/\n")
    assert "Body of the page" in out and TOKEN not in out


def test_with_the_hub_max_chars_cuts_inside_the_frame(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = StubHub(answer={**FETCH_ANSWER, "text": framed("x" * 500)})

    assert (
        run_fetch(
            "https://a.example/",
            100,
            True,
            environ=_session(token_file(tmp_path)),
            hub=_through(hub),
        )
        == 0
    )
    document = json.loads(capsys.readouterr().out)
    assert document["text"] == framed("x" * 100) and document["truncated"] is True


def test_a_query_the_hub_would_refuse_exits_with_usage_and_sends_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    hub = StubHub()

    assert (
        run_search(
            "q" * 10_000, None, False, environ=_session(token_file(tmp_path)), hub=_through(hub)
        )
        == 2
    )
    assert hub.requests == [] and "query" in capsys.readouterr().out


def test_the_commands_reach_the_hub_from_the_session_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub = StubHub()
    monkeypatch.setattr(web, "SESSION_HUB", _through(hub))
    path = token_file(tmp_path)

    searched = runner.invoke(app, ["search", "q", "--json"], env=_session(path))
    fetched = runner.invoke(app, ["fetch", "https://a.example/", "--json"], env=_session(path))
    ended = StubHub(401, {"detail": "Unauthorized"})
    monkeypatch.setattr(web, "SESSION_HUB", _through(ended))
    refused = runner.invoke(app, ["search", "q"], env=_session(path))
    off = runner.invoke(app, ["fetch", "https://a.example/"], env={STATE_VARIABLE: "none"})

    assert searched.exit_code == 0 and json.loads(searched.output)["backend"] == "searxng"
    assert fetched.exit_code == 0 and json.loads(fetched.output)["url"] == "https://a.example/"
    assert refused.exit_code == EXIT_ENDED and "web access has ended" in refused.output
    assert off.exit_code == EXIT_CONFIG and NO_HUB in off.output
    for result in (searched, fetched, refused, off):
        assert TOKEN not in result.output


def test_the_default_hub_factory_is_the_session_client(tmp_path: Path) -> None:
    from vibey.infrastructure.web.session import SessionWebAccess

    path = token_file(tmp_path)
    access = SessionWebAccess.from_environment(_session(path))

    assert isinstance(web.SESSION_HUB(access), SessionHubClient)
