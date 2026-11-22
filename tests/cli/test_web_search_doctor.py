# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s and `vibey acp`'s web-search lines: whether the local SearXNG answers, and
whether a Brave backup is configured (by which variable, never the key).

A SearXNG that does not answer is a `WARN` with the fix, never a `FAIL`; only a setting the
worker would refuse to start with fails. Every key here is a fake."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from tests.infrastructure.web.searxng_fakes import SEARXNG_CONFIG, FakeResponse
from vibey.application.dto import PreflightResult
from vibey.cli.doctor_output import DoctorLineParser
from vibey.cli.interfaces.web_search_doctor_interface import WebSearchDoctorInterface
from vibey.cli.main import app
from vibey.cli.web_search_doctor import WEB_SEARCH_DOCTOR, WebSearchDoctor

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
PREFLIGHT = "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight"
FAKE = "fake-doctor-key-5e6f"


def _answering(seen: list[Any] | None = None, config: object = None) -> Any:
    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        if seen is not None:
            seen.append(request)
        return FakeResponse(SEARXNG_CONFIG if config is None else config, url=request.full_url)

    return opener


def _refusing(request: urllib.request.Request, timeout: float) -> FakeResponse:
    raise urllib.error.URLError(ConnectionRefusedError())


def _doctor(environ: Mapping[str, str], opener: Any) -> WebSearchDoctor:
    return WebSearchDoctor(environ=lambda: environ, opener=opener)


def test_the_section_honours_its_interface() -> None:
    assert isinstance(WEB_SEARCH_DOCTOR, WebSearchDoctorInterface)


def test_a_local_searxng_that_answers_passes_and_the_probe_sends_no_secret() -> None:
    seen: list[Any] = []
    lines, ok = _doctor({"BRAVE_SEARCH_API_KEY": FAKE}, _answering(seen)).doctor_lines()
    assert ok is True
    assert lines == [
        f"PASS {'web-search':<26} local SearXNG answering at http://127.0.0.1:28180",
        f"PASS {'web-search-backup':<26} Brave backup configured via BRAVE_SEARCH_API_KEY:"
        " asked only when the local SearXNG fails, and never given to an engine session",
    ]
    (request,) = seen
    assert request.full_url == "http://127.0.0.1:28180/config" and request.get_method() == "GET"
    assert FAKE not in repr(request.header_items()) and FAKE not in " ".join(lines)


def test_a_local_searxng_that_does_not_answer_is_a_warning_with_the_fix() -> None:
    lines, ok = _doctor({}, _refusing).doctor_lines()
    assert ok is True
    assert lines[0] == (
        f"WARN {'web-search':<26} local SearXNG not answering at http://127.0.0.1:28180"
        " (could not be reached (ConnectionRefusedError)): start SearXNG there with its JSON"
        " format enabled, or point VIBEY_SEARXNG_URL at yours; until then vibey's searches"
        " fail, or go to Brave when a backup key is set"
    )
    assert lines[1] == (
        f"UNKNOWN {'web-search-backup':<26} no Brave backup configured (optional:"
        " VIBEY_BRAVE_API_KEY or BRAVE_SEARCH_API_KEY; used only when the local SearXNG fails)"
    )


def test_the_url_is_shown_without_credentials_or_a_query() -> None:
    environ = {"VIBEY_SEARXNG_URL": "http://me:pw@search.lan:8888/searx?token=t"}
    lines, _ = _doctor(environ, _answering()).doctor_lines()
    assert "at http://search.lan:8888/searx" in lines[0]
    assert "pw" not in lines[0] and "token" not in lines[0]


def test_brave_named_as_the_provider_fails_doctor_because_the_worker_refuses_it() -> None:
    environ = {"VIBEY_SEARCH_PROVIDER": "brave", "VIBEY_BRAVE_API_KEY": FAKE}
    lines, ok = _doctor(environ, _answering()).doctor_lines()
    assert ok is False and len(lines) == 1
    assert lines[0].startswith(f"FAIL {'web-search':<26} VIBEY_SEARCH_PROVIDER: ")
    assert "backup" in lines[0] and FAKE not in lines[0]


def test_a_probe_that_breaks_is_one_unknown_line_and_never_fails_doctor() -> None:
    def broken() -> Mapping[str, str]:
        raise RuntimeError("cannot read\x1b[2J the environment")

    lines, ok = WebSearchDoctor(environ=broken, opener=_answering()).doctor_lines()
    assert ok is True
    assert lines == [
        f"UNKNOWN {'web-search':<26} could not check web search"
        " (RuntimeError: cannot read [2J the environment)"
    ]


def test_each_line_is_a_finding_in_doctors_grammar() -> None:
    lines, _ = _doctor({"VIBEY_BRAVE_API_KEY": FAKE}, _refusing).doctor_lines()
    parsed = [DoctorLineParser().parse(line) for line in lines]
    assert [(p.mark, p.name) for p in parsed] == [
        ("WARN", "web-search"),
        ("PASS", "web-search-backup"),
    ]


# -- through `vibey doctor` --------------------------------------------------------------------


def _run_doctor(args: list[str], monkeypatch: pytest.MonkeyPatch, doctor: WebSearchDoctor) -> Any:
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    with (
        patch(PREFLIGHT, new=AsyncMock(return_value=PreflightResult(True, "1", True))),
        patch("vibey.cli.main.WEB_SEARCH_DOCTOR", doctor),
    ):
        return runner.invoke(app, ["doctor", "--engine", "claudeloop", *args])


def test_doctor_prints_the_web_search_lines_before_llm_tooling_and_a_down_searxng_passes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _run_doctor([], monkeypatch, _doctor({}, _refusing))
    lines = result.stdout.splitlines()
    names = [line.split()[1] for line in lines if len(line.split()) > 1]
    first = names.index("web-search")
    assert names[first : first + 2] == ["web-search", "web-search-backup"]
    assert first > names.index("host-health")
    assert all(not name.endswith(("acp-agent", "mcp-server")) for name in names[:first])
    web = next(line for line in lines if line.split()[1:2] == ["web-search"])
    assert web.startswith("WARN web-search")


def test_doctor_json_carries_the_web_search_checks_and_no_new_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    environ = {"BRAVE_SEARCH_API_KEY": FAKE}
    result = _run_doctor(["--json"], monkeypatch, _doctor(environ, _answering()))
    document = json.loads(result.stdout)
    assert set(document) == {"ok", "mode", "engines", "postgresql", "checks", "notes"}
    checks = {c["name"]: c["mark"] for c in document["checks"] if "web-search" in (c["name"] or "")}
    assert checks == {"web-search": "PASS", "web-search-backup": "PASS"}
    assert FAKE not in result.stdout


def test_doctor_by_default_probes_the_environments_searxng(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Any] = []
    monkeypatch.setenv("VIBEY_SEARXNG_URL", "http://127.0.0.1:8099")
    lines, _ = WebSearchDoctor(opener=_answering(seen)).doctor_lines()
    assert seen[0].full_url == "http://127.0.0.1:8099/config"
    assert "answering at http://127.0.0.1:8099" in lines[0]


def test_by_default_the_probe_goes_through_the_guarded_opener() -> None:
    # The hermetic opener (tests/conftest.py) stands in for the network and refuses.
    lines, ok = WebSearchDoctor(environ=lambda: {}).doctor_lines()
    assert ok is True and lines[0].startswith("WARN web-search")


def test_something_else_listening_on_the_searxng_port_is_said_as_such() -> None:
    lines, ok = _doctor({}, _answering(config=b"<html>other app</html>")).doctor_lines()
    assert ok is True
    assert lines[0] == (
        f"WARN {'web-search':<26} something other than SearXNG is listening at"
        " http://127.0.0.1:28180 (its /config is not JSON): vibey will not use its answers;"
        " stop it, or run SearXNG elsewhere and point VIBEY_SEARXNG_URL there"
    )


def test_a_searxng_that_is_not_the_marked_instance_is_said_as_such() -> None:
    environ = {"VIBEY_SEARXNG_INSTANCE": "vibey-7f3a"}
    lines, ok = _doctor(environ, _answering()).doctor_lines()
    assert ok is True and lines[0].startswith(
        f"WARN {'web-search':<26} a SearXNG other than the expected one is listening at"
    )
    assert "vibey-7f3a" not in lines[0]
    ours = {**SEARXNG_CONFIG, "instance_name": "vibey-7f3a"}
    lines, _ = _doctor(environ, _answering(config=ours)).doctor_lines()
    assert lines[0] == (
        f"PASS {'web-search':<26} local SearXNG answering at http://127.0.0.1:28180"
        " (the expected instance)"
    )
