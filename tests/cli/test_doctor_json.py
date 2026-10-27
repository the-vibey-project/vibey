# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`doctor --json` (#1686): one document, the same findings, the same exit code.

The text form's own tests are in test_operational_commands.py and are untouched; the parity
tests here pin that both forms say the same thing about the same run.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from vibey.application.dto import ConformanceCheckResult, ConformanceReport, PreflightResult
from vibey.cli.doctor_output import (
    DoctorFinding,
    DoctorFormat,
    DoctorLineParser,
    JsonDoctorOutput,
    TextDoctorOutput,
)
from vibey.cli.interfaces.doctor_output_interface import DoctorOutputInterface
from vibey.cli.main import app
from vibey.domain.engine import EngineId
from vibey.infrastructure.postgres import PostgresInstallResult, PostgresStatus

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})

PREFLIGHT = "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight"


def preflight(**changes: object) -> AsyncMock:
    fields: dict[str, object] = {"installed": True, "version": "1.2.3", "auth_ok": True}
    fields.update(changes)
    return AsyncMock(return_value=PreflightResult(**fields))  # type: ignore[arg-type]


# ----------------------------------------------------------------------------- the grammar


@pytest.mark.parametrize(
    "line, expected",
    [
        ("PASS sabbath  window ok", DoctorFinding("sabbath", "PASS", "window ok")),
        (
            "FAIL supervisor           none running",
            DoctorFinding("supervisor", "FAIL", "none running"),
        ),
        ("UNKNOWN ledger-guard      not set", DoctorFinding("ledger-guard", "UNKNOWN", "not set")),
        ("WARN host-health", DoctorFinding("host-health", "WARN", "")),
        ("ollama   WARN: holds 32k", DoctorFinding("ollama", "WARN", "holds 32k")),
        ("ollama   OK: fine", DoctorFinding("ollama", "OK", "fine")),
        ("ollama   SKIP: off", DoctorFinding("ollama", "SKIP", "off")),
    ],
)
def test_a_line_in_a_known_grammar_is_read_as_a_finding(line, expected):
    assert DoctorLineParser().parse(line) == expected


def test_a_line_in_no_grammar_is_kept_verbatim_never_dropped():
    found = DoctorLineParser().parse("something doctor has never said")
    assert found == DoctorFinding(None, None, "something doctor has never said", line=found.line)
    assert found.document()["line"] == "something doctor has never said"


def test_an_indented_line_continues_the_finding_before_it():
    out = JsonDoctorOutput()
    out.lines(["WARN supervisor  not kept running", "  start it with systemd", "free text"])
    out.lines(["  orphan continuation"])
    assert [f.name for f in out._findings] == ["supervisor", None, None]
    assert out._findings[0].detail == "not kept running\nstart it with systemd"
    assert out._findings[2].line == "  orphan continuation"


def test_both_outputs_honour_their_interface():
    assert isinstance(TextDoctorOutput(), DoctorOutputInterface)
    assert isinstance(JsonDoctorOutput(), DoctorOutputInterface)


def test_the_line_builders_match_the_lines_doctor_has_always_printed():
    assert DoctorFormat.engine_line("claudeloop", True, "1.2.3", True) == (
        "claudeloop       installed      v1.2.3      auth OK"
    )
    assert DoctorFormat.engine_line("x", False, None, False).startswith(
        "x                NOT INSTALLED  v?"
    )
    assert DoctorFormat.conformance_line("a", False, "why") == "  FAIL a — why"
    assert DoctorFormat.conformance_line("a", True, "") == "  PASS a"
    for status, state in [
        (PostgresStatus(False, False, False, None, "d"), "NOT INSTALLED"),
        (PostgresStatus(True, True, False, 12, "d"), "UNSUPPORTED"),
        (PostgresStatus(True, False, True, 16, "d"), "NOT READY"),
        (PostgresStatus(True, True, True, 16, "d"), "READY"),
    ]:
        assert DoctorFormat.postgres_state(status) == state
    assert DoctorFormat.postgres_line(PostgresStatus(True, True, True, 16, "up")) == (
        "postgresql      READY          v16      up"
    )


def test_a_recorded_health_row_is_noted_on_the_engine_just_reported():
    out = JsonDoctorOutput()
    out.engine("claudeloop", True, "1", True)
    out.recorded("claudeloop", "preflight")
    assert out._engines[0]["recorded"] == "preflight"


def test_json_postgres_entry_carries_state_version_readiness_and_detail():
    out = JsonDoctorOutput()
    out.postgres(PostgresStatus(True, True, True, 16, "up"))
    out.postgres_detail("ignored")  # already the entry's detail
    out.finish(True)
    # no engines, nothing recorded
    assert out._postgres == {"state": "READY", "version": "16", "ready": True, "detail": "up"}


# ----------------------------------------------------------------------------- local doctor


def run_json(*args: str, expect: int = 0):
    result = runner.invoke(app, ["doctor", "--json", *args])
    assert result.exit_code == expect, result.output
    return result


def test_local_doctor_prints_one_document_with_engine_and_postgres_findings(monkeypatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    with patch(PREFLIGHT, new=preflight()):
        result = run_json("--engine", "claudeloop")
    document = json.loads(result.stdout)
    assert document["ok"] is True and document["mode"] == "local"
    assert document["engines"] == [
        {
            "engine_id": "claudeloop",
            "installed": True,
            "version": "1.2.3",
            "auth_ok": True,
            "detail": None,
            "conformance": [],
            "recorded": None,
        }
    ]
    assert set(document["postgresql"]) == {"state", "version", "ready", "detail"}
    assert document["notes"] == []
    names = {check["name"] for check in document["checks"]}
    assert "db-passwordless" in names
    unknown = next(c for c in document["checks"] if c["name"] == "db-passwordless")
    assert unknown["mark"] == "UNKNOWN" and "VIBEY_PG_URL is not set" in unknown["detail"]


def test_engine_detail_is_in_the_document(monkeypatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    with patch(
        PREFLIGHT, new=preflight(installed=False, auth_ok=False, version=None, detail="no binary")
    ):
        document = json.loads(run_json("--engine", "claudeloop").stdout)
    engine = document["engines"][0]
    assert engine["installed"] is False and engine["version"] is None
    assert engine["detail"] == "no binary"


def test_a_failed_conformance_check_fails_the_document_and_the_exit_code(monkeypatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    report = ConformanceReport(
        engine_id=EngineId.CLAUDELOOP,
        checks=(
            ConformanceCheckResult(name="preflight", ok=True),
            ConformanceCheckResult(name="start_stop", ok=False, detail="did not stop"),
        ),
    )
    with (
        patch(PREFLIGHT, new=preflight()),
        patch("vibey.application.conformance.run_conformance", new=AsyncMock(return_value=report)),
    ):
        result = run_json("--conformance", "--engine", "claudeloop", expect=1)
    document = json.loads(result.stdout)
    assert document["ok"] is False
    assert document["engines"][0]["conformance"] == [
        {"name": "preflight", "ok": True, "detail": ""},
        {"name": "start_stop", "ok": False, "detail": "did not stop"},
    ]


def test_the_json_and_text_forms_say_the_same_thing_about_the_same_run(monkeypatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    with patch(PREFLIGHT, new=preflight()):
        text = runner.invoke(app, ["doctor", "--engine", "claudeloop"])
        document = json.loads(run_json("--engine", "claudeloop").stdout)
    engine = document["engines"][0]
    shown = DoctorFormat.engine_line(
        engine["engine_id"], engine["installed"], engine["version"], engine["auth_ok"]
    )
    assert shown in text.stdout.splitlines()
    postgres = document["postgresql"]
    assert f"postgresql      {postgres['state']:<14}" in text.stdout
    # every finding doctor printed as a line appears in the document under its own name
    for check in document["checks"]:
        if check["name"]:
            assert check["name"] in text.stdout
    assert text.exit_code == 0


def test_notes_go_to_stderr_and_into_the_document(monkeypatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    from pathlib import Path

    from vibey.cli.main import _local_engines_from_toml

    class WithNotices:
        """The real settings, with a notice the operator would have been given."""

        def __init__(self, real: object) -> None:
            self._real = real
            self.notices = ("something to know",)

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

    real = _local_engines_from_toml(Path("/nonexistent"))
    with (
        patch(PREFLIGHT, new=preflight()),
        patch("vibey.cli.main._local_engines_from_toml", return_value=WithNotices(real)),
    ):
        result = runner.invoke(app, ["doctor", "--json", "--engine", "claudeloop"])
    document = json.loads(result.stdout)
    assert document["notes"] == ["something to know"]
    assert "note: something to know" in result.stderr


def test_a_refusal_goes_to_stderr_with_no_document_and_the_text_exit_code():
    result = runner.invoke(app, ["doctor", "--json", "--engine", "nope"])
    assert result.exit_code == 1
    assert result.stdout == "" and "Unknown engine: nope" in result.stderr


def test_usage_errors_keep_their_exit_code_under_json():
    for args in (["--cluster", "--install-postgres"], ["--engines", "claudeloop"]):
        result = runner.invoke(app, ["doctor", "--json", *args])
        assert result.exit_code == 2 and result.stdout == ""


def test_a_postgres_install_that_failed_still_prints_a_document_saying_so(monkeypatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    status = PostgresStatus(False, False, False, None, "could not install")
    install = PostgresInstallResult(False, True, "could not install", status, ())
    with (
        patch("vibey.cli.main.PostgresLocalService") as service,
        patch(PREFLIGHT, new=preflight()),
    ):
        service.return_value.install.return_value = install
        result = run_json("--install-postgres", "--engine", "claudeloop", expect=1)
    document = json.loads(result.stdout)
    assert document["ok"] is False
    assert document["postgresql"]["ready"] is False
    assert document["postgresql"]["detail"] == "could not install"


# ---------------------------------------------------------------------------- cluster doctor


def test_cluster_doctor_prints_its_checks_as_findings():
    fake = [
        type("C", (), {"mark": "PASS", "name": "database", "detail": "connected", "ok": True})(),
        type("C", (), {"mark": "FAIL", "name": "non-root", "detail": "uid 0", "ok": False})(),
    ]
    with (
        patch(
            "vibey.infrastructure.cluster_preflight.ClusterPreflight.run",
            new=AsyncMock(return_value=fake),
        ),
        patch("vibey.infrastructure.cluster_preflight.all_ok", return_value=False),
    ):
        result = run_json("--cluster", expect=1)
    document = json.loads(result.stdout)
    assert document == {
        "ok": False,
        "mode": "cluster",
        "checks": [
            {"name": "database", "mark": "PASS", "detail": "connected"},
            {"name": "non-root", "mark": "FAIL", "detail": "uid 0"},
        ],
        "notes": [],
    }
