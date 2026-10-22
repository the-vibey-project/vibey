# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""pr-af's control-plane client, its workflow command, and its declaration."""

from __future__ import annotations

import io
import json
import subprocess
import urllib.error
from pathlib import Path
from typing import Any, Self

import pytest

from vibey_gh import pr_af
from vibey_gh.config import GhConfig, PrAfConfig, PrAutomationConfig, load_config
from vibey_gh.install import WORKFLOWS, installation_notices, render_workflow

SHA = "421fbd23bf1c5a2c3916d7046c97b5273958e1f4"


def cfg(tmp_path: Path, **pr_af_config: Any) -> GhConfig:
    return GhConfig(
        root=tmp_path,
        pr_automation=PrAutomationConfig(pr_af=PrAfConfig(**pr_af_config)),
    )


def result(*, event: str, blocking: int, total: int = 0, exhausted: bool = False) -> dict:
    return {
        "review_id": "r1",
        "review": {"body": "summary", "event": event, "comments": []},
        "findings": [],
        "summary": {
            "total_findings": total,
            "blocking_count": blocking,
            "budget_exhausted": exhausted,
            "cost_usd": 0.5,
            "duration_seconds": 120.0,
        },
        "metadata": {},
    }


class Response:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class Transport:
    def __init__(self, details: object) -> None:
        self.details = details
        self.urls: list[str] = []

    def __call__(self, request: Any, timeout: float) -> Response:
        self.urls.append(request.full_url)
        if "/execute/async/" in request.full_url:
            return Response({"execution_id": "exec-1"})
        return Response(self.details)


def client(details: object, **kwargs: Any) -> tuple[pr_af.PrAfClient, Transport]:
    transport = Transport(details)
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    return (
        pr_af.PrAfClient(
            "http://cp",
            transport=transport,
            poll_seconds=1,
            startup_seconds=30,
            timeout_seconds=60,
            sleep=sleep,
            clock=lambda: now[0],
            **kwargs,
        ),
        transport,
    )


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"enabled": True, "ref": "main"}, "full 40-character commit SHA"),
        ({"enabled": True, "ref": SHA, "repository": "not a repo"}, "owner/name"),
        ({"enabled": True, "ref": SHA, "runs_on": "a b"}, "runner label"),
        ({"enabled": True, "ref": SHA, "model": "not a model"}, "model id"),
        ({"enabled": True, "ref": SHA, "depth": "forever"}, "depth must be one of"),
        ({"enabled": True, "ref": SHA, "max_cost_usd": 0}, "max_cost_usd"),
        ({"enabled": True, "ref": SHA, "max_cost_usd": 1000}, "max_cost_usd"),
        ({"enabled": True, "ref": SHA, "max_duration_seconds": 59}, "max_duration_seconds"),
        ({"enabled": True, "ref": SHA, "timeout_minutes": 1}, "timeout_minutes"),
        ({"enabled": True, "ref": SHA, "timeout_minutes": 70}, "at least 15 minutes"),
        ({"enabled": True, "ref": SHA, "openrouter_secret": "not-a-name"}, "secret name"),
        ({"enabled": "yes"}, "enabled must be true or false"),
        ({"default": "yes"}, "default must be true or false"),
        ({"host_enabled": "yes"}, "host_enabled must be true or false"),
    ],
)
def test_config_refuses_unsafe_values(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        PrAfConfig(**kwargs)


def test_config_defaults_off_for_adopters() -> None:
    value = PrAfConfig()
    assert not value.enabled and value.default
    assert value.ref == ""


def test_config_parses_the_table(tmp_path: Path) -> None:
    (tmp_path / ".vibey-gh.toml").write_text(
        f"""[pr_automation.pr_af]
enabled = true
default = false
repository = "Agent-Field/pr-af"
ref = "{SHA}"
model = "vendor/model:tag"
depth = "deep"
host_enabled = true
""",
        encoding="utf-8",
    )
    value = load_config(tmp_path).pr_automation.pr_af
    assert value.enabled and not value.default
    assert value.ref == SHA
    assert value.model == "vendor/model:tag"
    assert value.depth == "deep"
    assert value.host_enabled


def test_config_refuses_an_unknown_key(tmp_path: Path) -> None:
    (tmp_path / ".vibey-gh.toml").write_text(
        '[pr_automation.pr_af]\nenabled = true\nmodle = "typo"\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="does not know modle"):
        load_config(tmp_path)


@pytest.mark.parametrize(
    "payload,passed,event",
    [
        (result(event="APPROVE", blocking=0), True, "APPROVE"),
        (result(event="COMMENT", blocking=0, total=2), True, "COMMENT"),
        (result(event="REQUEST_CHANGES", blocking=1, total=1), False, "REQUEST_CHANGES"),
        (result(event="APPROVE", blocking=1, total=1), False, "APPROVE"),
        (result(event="APPROVE", blocking=0, exhausted=True), None, "APPROVE"),
        ({"review": {"body": "x"}, "summary": {}}, None, ""),
        ({"review": {"event": "APPROVE"}, "summary": {}}, None, "APPROVE"),
        ({"review": {"body": "x"}, "summary": {"blocking_count": 0}}, None, ""),
    ],
)
def test_verdict_reads_the_merge_gate(payload: dict, passed: bool | None, event: str) -> None:
    verdict = pr_af.PrAfVerdict.from_result(payload)
    assert verdict.passed is passed
    assert verdict.event == event


def test_find_result_searches_strings_and_lists() -> None:
    payload = {"data": [{"x": json.dumps(result(event="APPROVE", blocking=0))}]}
    found = pr_af._find_result(payload)
    assert found is not None and found["review"]["event"] == "APPROVE"
    assert pr_af._find_result("not json") is None
    assert pr_af._find_result({"other": 1}) is None


def test_client_dispatches_polls_and_reads_the_result() -> None:
    value, transport = client(
        {"status": "succeeded", "result": result(event="APPROVE", blocking=0)}
    )
    verdict = value.review(
        "https://github.com/o/r/pull/1",
        depth="standard",
        dry_run=False,
        max_cost_usd=2.0,
        max_duration_seconds=3600,
    )
    assert verdict.passed is True and verdict.findings == 0
    assert transport.urls[0].endswith("/api/v1/execute/async/pr-af.review")
    assert transport.urls[1].endswith("/api/ui/v1/executions/exec-1/details")


def test_client_reports_a_failed_execution() -> None:
    value, _ = client({"status": "failed", "error": "model refused"})
    verdict = value.review(
        "https://github.com/o/r/pull/1",
        depth="standard",
        dry_run=False,
        max_cost_usd=2.0,
        max_duration_seconds=3600,
    )
    assert verdict.passed is None
    assert "failed" in verdict.reason and "model refused" in verdict.reason


def test_client_reports_a_missing_result() -> None:
    value, _ = client({"status": "succeeded", "result": {"unrelated": True}})
    verdict = value.review(
        "https://github.com/o/r/pull/1",
        depth="standard",
        dry_run=False,
        max_cost_usd=2.0,
        max_duration_seconds=3600,
    )
    assert verdict.passed is None
    assert "no review result" in verdict.reason


class FakeClient:
    def __init__(self, verdict: pr_af.PrAfVerdict) -> None:
        self.verdict = verdict
        self.calls: list[dict[str, Any]] = []

    def review(self, pr_url: str, **kwargs: Any) -> pr_af.PrAfVerdict:
        self.calls.append({"pr_url": pr_url, **kwargs})
        return self.verdict


def test_command_writes_outputs_and_summary(tmp_path: Path) -> None:
    output = tmp_path / "output"
    summary = tmp_path / "summary"
    fake = FakeClient(pr_af.PrAfVerdict(False, 2, "REQUEST_CHANGES", "blocked"))
    command = pr_af.PrAfCommand(
        cfg(tmp_path, enabled=True, ref=SHA),
        client=fake,
        env={
            "PR_URL": "https://github.com/o/r/pull/1",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
            "PR_AF_VENUE": "host",
        },
        out=io.StringIO(),
    )
    assert command.run() == 0
    written = dict(line.split("=", 1) for line in output.read_text().splitlines())
    assert written["passed"] == "false" and written["findings"] == "2"
    assert written["event"] == "REQUEST_CHANGES" and written["venue"] == "host"
    assert "blocked" in summary.read_text()
    assert fake.calls[0]["max_duration_seconds"] == 3600


def test_command_derives_the_url_from_the_workflow_context(tmp_path: Path) -> None:
    fake = FakeClient(pr_af.PrAfVerdict(True, 0, "APPROVE", "ok"))
    command = pr_af.PrAfCommand(
        cfg(tmp_path, enabled=True, ref=SHA),
        client=fake,
        env={"PR": "7", "GITHUB_REPOSITORY": "o/r", "GITHUB_SERVER_URL": "https://github.com"},
        out=io.StringIO(),
    )
    assert command.run() == 0
    assert fake.calls[0]["pr_url"] == "https://github.com/o/r/pull/7"


def test_command_skips_when_not_declared(tmp_path: Path) -> None:
    output = tmp_path / "output"
    command = pr_af.PrAfCommand(
        cfg(tmp_path),
        client=FakeClient(pr_af.PrAfVerdict(True)),
        env={"PR_URL": "https://github.com/o/r/pull/1", "GITHUB_OUTPUT": str(output)},
        out=io.StringIO(),
    )
    assert command.run() == 0
    assert "passed=" in output.read_text()


def test_command_refuses_without_a_url(tmp_path: Path) -> None:
    output = tmp_path / "output"
    command = pr_af.PrAfCommand(
        cfg(tmp_path, enabled=True, ref=SHA),
        env={"GITHUB_OUTPUT": str(output)},
        out=io.StringIO(),
    )
    assert command.run() == 1
    assert "passed=\n" in output.read_text()


def test_rendered_review_workflow_declares_pr_af(tmp_path: Path) -> None:
    text = render_workflow(
        WORKFLOWS / "pr-review.yml", cfg(tmp_path, enabled=True, ref=SHA, host_enabled=True)
    )
    assert "review-pr-af:" in text and "review-pr-af-host:" in text
    assert "pr-af review (hosted)" in text and "pr-af review (host)" in text
    assert f"ref: {SHA}" in text
    assert "OPENROUTER_API_KEY" in text
    assert "__VIBEY_GH_" not in text


def test_small_parsers_accept_the_shapes_the_control_plane_sends() -> None:
    assert pr_af._as_int(True, 7) == 7
    assert pr_af._as_int(3.9) == 3
    assert pr_af._as_int("4") == 4
    assert pr_af._as_int(object(), 5) == 5
    assert pr_af._as_float(True, 1.5) == 1.5
    assert pr_af._as_float("2.5") == 2.5
    assert pr_af._as_float(object(), 3.5) == 3.5


def test_status_reads_a_nested_execution_and_ignores_everything_else() -> None:
    assert pr_af._status({"status": "RUNNING"}) == "running"
    assert pr_af._status({"execution": {"status": "succeeded"}}) == "succeeded"
    assert pr_af._status({"execution": "not a mapping"}) == ""
    assert pr_af._status("not a mapping") == ""


def test_find_result_ignores_bad_json_and_lists_without_a_result() -> None:
    assert pr_af._find_result("{not json") is None
    assert pr_af._find_result("") is None
    assert pr_af._find_result("7") is None
    assert pr_af._find_result([{"unrelated": 1}]) is None
    assert pr_af._find_result({"data": [{"unrelated": 1}]}) is None


def test_urlopen_is_the_real_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[object, float]] = []

    def fake(request: object, timeout: float) -> Response:
        seen.append((request, timeout))
        return Response({"ok": True})

    monkeypatch.setattr(pr_af.urllib.request, "urlopen", fake)
    response = pr_af._urlopen(pr_af.urllib.request.Request("http://cp"), 9.0)
    assert response.read() == b'{"ok": true}'
    assert seen[0][1] == 9.0


class Raising:
    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls = 0

    def __call__(self, request: object, timeout: float) -> Response:
        self.calls += 1
        raise self.error


def review_with(transport: object, **kwargs: Any) -> pr_af.PrAfVerdict:
    value = pr_af.PrAfClient("http://cp", transport=transport, poll_seconds=1, **kwargs)
    return value.review(
        "https://github.com/o/r/pull/1",
        depth="standard",
        dry_run=False,
        max_cost_usd=2.0,
        max_duration_seconds=3600,
    )


def test_dispatch_refuses_a_non_retryable_http_error() -> None:
    verdict = review_with(
        Raising(urllib.error.HTTPError("http://cp", 400, "bad request", None, None)),
        startup_seconds=2,
        timeout_seconds=10,
    )
    assert verdict.passed is None
    assert "did not accept" in verdict.reason


def test_dispatch_retries_a_retryable_http_error_until_the_deadline() -> None:
    transport = Raising(urllib.error.HTTPError("http://cp", 503, "busy", None, None))
    verdict = review_with(transport, startup_seconds=2, timeout_seconds=10)
    assert verdict.passed is None
    assert transport.calls == 3


def test_dispatch_reports_an_unreachable_control_plane() -> None:
    verdict = review_with(
        Raising(urllib.error.URLError("down")), startup_seconds=1, timeout_seconds=10
    )
    assert verdict.passed is None
    assert "did not accept" in verdict.reason


class NoExecutionId:
    def __call__(self, request: object, timeout: float) -> Response:
        return Response({"unrelated": True})


def test_dispatch_reports_a_missing_execution_id() -> None:
    verdict = review_with(NoExecutionId(), startup_seconds=1, timeout_seconds=10)
    assert verdict.passed is None
    assert "did not accept" in verdict.reason


def test_wait_reports_an_execution_that_never_settles() -> None:
    verdict = review_with(Transport({"status": "pending"}), startup_seconds=10, timeout_seconds=2)
    assert verdict.passed is None
    assert "no verdict" in verdict.reason


class DetailsRaises:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: object, timeout: float) -> Response:
        self.calls += 1
        if self.calls == 1:
            return Response({"execution_id": "exec-1"})
        raise urllib.error.URLError("details down")


def test_wait_reports_details_it_cannot_read() -> None:
    verdict = review_with(DetailsRaises(), startup_seconds=10, timeout_seconds=2)
    assert verdict.passed is None
    assert "no verdict" in verdict.reason


def test_wait_names_the_failure_error_message() -> None:
    value, _ = client({"status": "failed", "error_message": "model refused"})
    verdict = value.review(
        "https://github.com/o/r/pull/1",
        depth="standard",
        dry_run=False,
        max_cost_usd=2.0,
        max_duration_seconds=3600,
    )
    assert verdict.passed is None
    assert "model refused" in verdict.reason


def test_summary_renders_every_outcome_and_the_counters(tmp_path: Path) -> None:
    summary = tmp_path / "summary"
    command = pr_af.PrAfCommand(
        cfg(tmp_path, enabled=True, ref=SHA),
        env={"GITHUB_STEP_SUMMARY": str(summary)},
        out=io.StringIO(),
    )
    command._write_summary(pr_af.PrAfVerdict(None, reason="nothing"), "hosted")
    command._write_summary(pr_af.PrAfVerdict(True, reason="clean"), "hosted")
    command._write_summary(pr_af.PrAfVerdict(False, 3, reason="blocked"), "host")
    command._write_summary(
        pr_af.PrAfVerdict(True, reason="clean", cost_usd=0.5, duration_seconds=60),
        "hosted",
    )
    text = summary.read_text()
    assert "no verdict" in text
    assert "**passed**" in text
    assert "blocked (3 blocking finding(s))" in text
    assert "$0.50" in text and "1.0 min" in text


def test_command_passes_the_dry_run_switch(tmp_path: Path) -> None:
    fake = FakeClient(pr_af.PrAfVerdict(True, reason="clean"))
    command = pr_af.PrAfCommand(
        cfg(tmp_path, enabled=True, ref=SHA),
        client=fake,
        env={"PR_URL": "https://github.com/o/r/pull/1", "PR_AF_DRY_RUN": "yes"},
        out=io.StringIO(),
    )
    assert command.run() == 0
    assert fake.calls[0]["dry_run"] is True


def test_installation_notices_include_the_declared_router_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess([], 0, "[]", ""),
    )
    notices = installation_notices(cfg(tmp_path, enabled=True, ref=SHA))
    assert any("OPENROUTER_API_KEY" in item for item in notices)
    assert not any("OPENROUTER_API_KEY" in item for item in installation_notices(cfg(tmp_path)))


def test_rendered_review_workflow_honours_a_second_opinion_and_the_host_venue(
    tmp_path: Path,
) -> None:
    text = render_workflow(
        WORKFLOWS / "pr-review.yml",
        cfg(
            tmp_path,
            enabled=True,
            ref=SHA,
            default=False,
            host_enabled=True,
        ),
    )
    assert "PR_AF_DEFAULT: false" in text
    assert "[self-hosted, vibey-local]" in text
    assert "__VIBEY_GH_" not in text
