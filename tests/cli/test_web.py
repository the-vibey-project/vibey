# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey search` and `vibey fetch`: the web for any loop that can run a command."""

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from vibey.cli.main import app
from vibey.cli.web import UNTRUSTED, run_fetch, run_search
from vibey.infrastructure.web.fetch import FetchedPage, WebFetchError

runner = CliRunner()
SEARX = {"VIBEY_SEARXNG_URL": "http://127.0.0.1:8080"}


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, amount: int | None = None) -> bytes:
        return self._payload


def _opener(payload: object) -> Any:
    return lambda request, timeout: _Response(payload)


RESULTS = {
    "results": [{"title": "Next.js", "url": "https://nextjs.org", "content": "The React framework"}]
}


def test_an_unconfigured_search_says_how_to_configure_one_and_exits_with_usage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_search("q", None, False, environ={}) == 2
    out = capsys.readouterr().out
    assert (
        "web search is not configured" in out
        and "VIBEY_SEARXNG_URL" in out
        and "VIBEY_BRAVE_API_KEY" in out
    )


def test_a_setting_that_cannot_be_read_exits_with_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        run_search(
            "q", None, False, environ={"VIBEY_SEARCH_PROVIDER": "bing", "VIBEY_BRAVE_API_KEY": "k"}
        )
        == 2
    )
    assert "VIBEY_SEARCH_PROVIDER" in capsys.readouterr().out


def test_results_are_printed_under_the_untrusted_banner(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_search("react", None, False, environ=SEARX, opener=_opener(RESULTS)) == 0
    out = capsys.readouterr().out
    assert out.startswith(UNTRUSTED)
    assert "1. Next.js\n   https://nextjs.org\n   The React framework" in out


def test_no_results_and_a_result_without_a_snippet_print_cleanly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_search("q", None, False, environ=SEARX, opener=_opener({"results": []})) == 0
    assert "no results" in capsys.readouterr().out
    bare = {"results": [{"title": "T", "url": "https://t.example", "content": ""}]}
    assert run_search("q", 1, False, environ=SEARX, opener=_opener(bare)) == 0
    assert capsys.readouterr().out.count("\n") == 3


def test_json_output_is_marked_untrusted_for_the_loop_that_reads_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_search("react", 3, True, environ=SEARX, opener=_opener(RESULTS)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["untrusted"] is True and data["provider"] == "searxng" and data["query"] == "react"
    assert data["results"] == [
        {"title": "Next.js", "url": "https://nextjs.org", "snippet": "The React framework"}
    ]


def test_a_backend_that_fails_exits_one_and_names_why(capsys: pytest.CaptureFixture[str]) -> None:
    def refusing(request: object, timeout: float) -> _Response:
        raise ConnectionRefusedError

    assert run_search("q", None, False, environ=SEARX, opener=refusing) == 1
    assert "searxng could not be reached or understood" in capsys.readouterr().out


class FakeFetcher:
    def __init__(self, page: FetchedPage | None = None) -> None:
        self.page = page
        self.limit: int | None = None

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        self.limit = max_chars
        if self.page is None:
            raise WebFetchError("refused: not a public http(s) address")
        return self.page


def test_a_page_is_printed_as_text_under_the_banner_and_a_cut_is_said(
    capsys: pytest.CaptureFixture[str],
) -> None:
    page = FetchedPage("https://a.example/x", "A page", "Body text", True)
    fetcher = FakeFetcher(page)
    assert run_fetch("https://a.example/x", 500, False, fetcher=fetcher) == 0  # type: ignore[arg-type]
    out = capsys.readouterr().out
    assert out.startswith(UNTRUSTED) and "A page\nhttps://a.example/x\n\nBody text" in out
    assert out.rstrip().endswith("[truncated]") and fetcher.limit == 500
    untitled = FakeFetcher(FetchedPage("https://b.example", "", "t", False))
    assert run_fetch("https://b.example", None, False, fetcher=untitled) == 0  # type: ignore[arg-type]
    assert "https://b.example\nhttps://b.example" in capsys.readouterr().out


def test_fetch_json_and_a_refusal(capsys: pytest.CaptureFixture[str]) -> None:
    page = FetchedPage("https://a.example", "T", "Body", False)
    assert run_fetch("https://a.example", None, True, fetcher=FakeFetcher(page)) == 0  # type: ignore[arg-type]
    data = json.loads(capsys.readouterr().out)
    assert data == {
        "untrusted": True,
        "url": "https://a.example",
        "title": "T",
        "truncated": False,
        "text": "Body",
    }
    assert run_fetch("http://localhost/", None, False, fetcher=FakeFetcher()) == 1  # type: ignore[arg-type]
    assert "not a public" in capsys.readouterr().out


def test_the_commands_are_wired_into_vibey_and_exit_with_their_codes() -> None:
    unconfigured = runner.invoke(
        app, ["search", "react"], env={"VIBEY_SEARXNG_URL": "", "VIBEY_BRAVE_API_KEY": ""}
    )
    assert unconfigured.exit_code == 2 and "web search is not configured" in unconfigured.output
    refused = runner.invoke(app, ["fetch", "http://localhost:9/", "--max-chars", "500"])
    assert refused.exit_code == 1 and "not a public http(s) address" in refused.output


def test_a_command_that_succeeds_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vibey.cli.web.run_search", lambda *args, **kwargs: 0)
    monkeypatch.setattr("vibey.cli.web.run_fetch", lambda *args, **kwargs: 0)
    assert runner.invoke(app, ["search", "react", "--limit", "3", "--json"]).exit_code == 0
    assert runner.invoke(app, ["fetch", "https://a.example", "--json"]).exit_code == 0


def test_the_worker_says_where_web_search_reaches() -> None:
    from vibey.cli.web import web_search_line
    from vibey.infrastructure.web.search import WebSearchSettings

    assert "not configured" in web_search_line(None)
    searx = WebSearchSettings.from_environment(SEARX)
    brave = WebSearchSettings.from_environment({"VIBEY_BRAVE_API_KEY": "k"})
    assert "searxng for DESIGN research and for every engine session" in web_search_line(searx)
    line = web_search_line(brave)
    assert "brave for DESIGN research only" in line and "key is never passed" in line


def test_vibey_command_is_the_running_console_script_when_it_is_absolute() -> None:
    from vibey.cli.web import vibey_command

    assert vibey_command("/venv/bin/vibey", which=lambda _: "/other/vibey") == "/venv/bin/vibey"


def test_vibey_command_falls_back_to_path_then_the_bare_name() -> None:
    from vibey.cli.web import vibey_command

    assert vibey_command("python", which=lambda _: "/other/vibey") == "/other/vibey"
    assert vibey_command("vibey", which=lambda _: None) == "vibey"
