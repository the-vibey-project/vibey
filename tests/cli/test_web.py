# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey search` and `vibey fetch`: the web for any loop that can run a command."""

import json
from typing import Any

import pytest
from typer.testing import CliRunner

from vibey.cli.main import app
from vibey.cli.web import UNTRUSTED, run_fetch, run_search
from vibey.infrastructure.web.backup_notice import BackupNotice
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


def _opener(payload: object, seen: list[str] | None = None) -> Any:
    def opener(request: Any, timeout: float) -> _Response:
        if seen is not None:
            seen.append(request.full_url)
        return _Response(payload)

    return opener


def _searx_down(brave_payload: object, seen: list[str] | None = None) -> Any:
    """SearXNG refuses the connection; Brave answers with `brave_payload`."""

    def opener(request: Any, timeout: float) -> _Response:
        if seen is not None:
            seen.append(request.full_url)
        if request.full_url.startswith("https://api.search.brave.com/"):
            return _Response(brave_payload)
        raise ConnectionRefusedError

    return opener


BRAVE = {"web": {"results": [{"title": "B", "url": "https://b.example", "description": "bd"}]}}
KEY = {"BRAVE_SEARCH_API_KEY": "fake-cli-key-3d4e"}


RESULTS = {
    "results": [{"title": "Next.js", "url": "https://nextjs.org", "content": "The React framework"}]
}


def test_with_nothing_set_a_search_asks_the_local_searxng_on_loopback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []
    assert run_search("q", None, True, environ={}, opener=_opener(RESULTS, seen)) == 0
    assert seen == ["http://127.0.0.1:8080/search?q=q&format=json"]
    assert json.loads(capsys.readouterr().out)["backend"] == "searxng"


def test_with_searxng_down_and_no_key_the_search_fails_and_says_how_to_fix_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []
    assert (
        run_search("private words", None, False, environ={}, opener=_searx_down(BRAVE, seen)) == 1
    )
    captured = capsys.readouterr()
    assert captured.out.startswith(
        "error: the local SearXNG at http://127.0.0.1:8080 did not answer"
    )
    assert "no Brave backup is configured" in captured.out and "vibey doctor" in captured.out
    assert "private words" not in captured.out + captured.err
    assert len(seen) == 1


def test_choosing_brave_as_the_provider_exits_with_usage_and_says_it_is_a_backup(
    capsys: pytest.CaptureFixture[str],
) -> None:
    environ = {**KEY, "VIBEY_SEARCH_PROVIDER": "brave"}
    assert run_search("q", None, False, environ=environ, opener=_opener(RESULTS)) == 2
    out = capsys.readouterr().out
    assert "VIBEY_SEARCH_PROVIDER" in out and "backup" in out and "fake-cli-key" not in out


def test_with_searxng_down_and_a_key_brave_answers_and_it_is_said_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    notice = BackupNotice()
    assert run_search("q", None, False, environ=KEY, opener=_searx_down(BRAVE), notice=notice) == 0
    captured = capsys.readouterr()
    assert captured.err == (
        "local SearXNG unavailable (could not be reached (ConnectionRefusedError)); "
        "this query went to Brave Search\n"
    )
    assert captured.out.startswith(
        f"{UNTRUSTED}\nbackend: brave (the backup: local SearXNG unavailable)\n"
    )
    assert "1. B\n   https://b.example\n   bd" in captured.out
    assert "fake-cli-key" not in captured.out + captured.err


def test_the_json_answer_carries_the_backend_and_the_notice_when_it_fell_back(
    capsys: pytest.CaptureFixture[str],
) -> None:
    notice = BackupNotice()
    assert run_search("q", None, True, environ=KEY, opener=_searx_down(BRAVE), notice=notice) == 0
    first = json.loads(capsys.readouterr().out)
    assert (first["backend"], first["provider"]) == ("brave", "brave")
    assert first["notice"] == (
        "local SearXNG unavailable (could not be reached (ConnectionRefusedError)); "
        "this query went to Brave Search"
    )
    assert run_search("q", None, True, environ=KEY, opener=_searx_down(BRAVE), notice=notice) == 0
    captured = capsys.readouterr()
    second = json.loads(captured.out)
    assert second["backend"] == "brave" and "notice" not in second and captured.err == ""


def test_a_healthy_searxng_with_a_key_set_never_asks_brave(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []
    assert run_search("q", None, True, environ=KEY, opener=_opener({"results": []}, seen)) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["results"] == [] and captured.err == ""
    assert [url for url in seen if "brave" in url] == []


def test_a_project_vibey_toml_cannot_point_search_anywhere(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "vibey.toml").write_text(
        '[project]\nname = "x"\n[search]\nsearxng_url = "http://evil.example"\n'
        'provider = "brave"\nbrave_api_key = "fake-planted"\n'
        '[env]\nVIBEY_SEARXNG_URL = "http://evil.example"\n'
    )
    monkeypatch.chdir(tmp_path)
    seen: list[str] = []
    import os

    assert run_search("q", None, True, environ=os.environ, opener=_opener(RESULTS, seen)) == 0
    assert seen == ["http://127.0.0.1:8080/search?q=q&format=json"]
    assert "evil" not in capsys.readouterr().out


def test_a_setting_that_cannot_be_read_exits_with_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_search("q", None, False, environ={"VIBEY_SEARCH_PROVIDER": "bing"}) == 2
    assert "VIBEY_SEARCH_PROVIDER" in capsys.readouterr().out


def test_results_are_printed_under_the_untrusted_banner(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_search("react", None, False, environ=SEARX, opener=_opener(RESULTS)) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"{UNTRUSTED}\nbackend: searxng\n")
    assert "1. Next.js\n   https://nextjs.org\n   The React framework" in out


def test_no_results_and_a_result_without_a_snippet_print_cleanly(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_search("q", None, False, environ=SEARX, opener=_opener({"results": []})) == 0
    assert "no results" in capsys.readouterr().out
    bare = {"results": [{"title": "T", "url": "https://t.example", "content": ""}]}
    assert run_search("q", 1, False, environ=SEARX, opener=_opener(bare)) == 0
    assert capsys.readouterr().out.count("\n") == 4


def test_json_output_is_marked_untrusted_for_the_loop_that_reads_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_search("react", 3, True, environ=SEARX, opener=_opener(RESULTS)) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["untrusted"] is True and data["query"] == "react"
    assert data["backend"] == "searxng" and data["provider"] == "searxng" and "notice" not in data
    assert data["results"] == [
        {"title": "Next.js", "url": "https://nextjs.org", "snippet": "The React framework"}
    ]


def test_a_backend_that_fails_exits_one_and_names_why(capsys: pytest.CaptureFixture[str]) -> None:
    def refusing(request: object, timeout: float) -> _Response:
        raise ConnectionRefusedError

    assert run_search("q", None, False, environ=SEARX, opener=refusing) == 1
    assert "could not be reached (ConnectionRefusedError)" in capsys.readouterr().out


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
    refused_provider = runner.invoke(
        app, ["search", "react"], env={"VIBEY_SEARCH_PROVIDER": "brave"}
    )
    assert refused_provider.exit_code == 2 and "backup" in refused_provider.output
    # The hermetic opener (tests/conftest.py) refuses every connection: SearXNG is down here.
    down = runner.invoke(app, ["search", "react"])
    assert down.exit_code == 1 and "no Brave backup is configured" in down.output
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

    plain = web_search_line(WebSearchSettings.from_environment({}))
    assert plain == (
        "web search: the local SearXNG at http://127.0.0.1:8080 first, for DESIGN research and"
        " every engine session (vibey search, vibey fetch); no Brave backup configured"
        " (VIBEY_BRAVE_API_KEY or BRAVE_SEARCH_API_KEY sets one)"
    )
    backed = web_search_line(
        WebSearchSettings.from_environment(
            {
                "VIBEY_SEARXNG_URL": "http://me:pw@search.lan:8888/?t=1",
                "VIBEY_BRAVE_API_KEY": "fake-k",
            }
        )
    )
    assert backed.startswith("web search: the local SearXNG at http://search.lan:8888/ first")
    assert "Brave backup configured via VIBEY_BRAVE_API_KEY" in backed
    assert "only in vibey's own processes" in backed and "never reaches a session" in backed
    assert "pw" not in backed and "fake-k" not in backed


def test_vibey_command_is_the_running_console_script_when_it_is_absolute() -> None:
    from vibey.cli.web import vibey_command

    assert vibey_command("/venv/bin/vibey", which=lambda _: "/other/vibey") == "/venv/bin/vibey"


def test_vibey_command_falls_back_to_path_then_the_bare_name() -> None:
    from vibey.cli.web import vibey_command

    assert vibey_command("python", which=lambda _: "/other/vibey") == "/other/vibey"
    assert vibey_command("vibey", which=lambda _: None) == "vibey"
