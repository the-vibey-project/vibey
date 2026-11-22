# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`cli/doctor_probes.py`: `vibey doctor`'s local sections as `DoctorProbeInterface`s.

Two promises are held here. A probe never writes to stdout: a section that prints is captured,
so under `vibey acp` nothing reaches the protocol stream. And `vibey doctor` prints, from the
results, exactly the bytes each section printed before, in text and in `--json` (the existing
doctor tests are the end-to-end proof). Module-level test functions rather than a class with an
interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import io
import json
from contextlib import redirect_stdout
from typing import Any

import pytest
import typer

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.application.acp.dto import DoctorResult
from vibey.application.acp.interfaces.doctor_probe_interface import DoctorProbeInterface
from vibey.cli.doctor_output import JsonDoctorOutput, TextDoctorOutput
from vibey.cli.doctor_probes import (
    LOCAL_DATABASE_DOCTOR,
    LOCAL_DOCTOR,
    LOCAL_DOCTOR_PROBES,
    LocalDatabaseDoctor,
    SectionProbe,
)
from vibey.cli.interfaces.doctor_probes_interface import (
    LocalDatabaseDoctorInterface,
    LocalDoctorProbeInterface,
    LocalDoctorProbesInterface,
)
from vibey.infrastructure.cluster_preflight import ClusterCheck
from vibey.infrastructure.db.passwordless_reach import (
    PasswordlessReachFinding,
    PasswordlessReachProbe,
    ReachVerdict,
)
from vibey.infrastructure.engines.ollama_residency import OllamaResidency


def _quiet_ollama(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    asked: list[int] = []

    async def line(self: OllamaResidency, environ: Any) -> str:
        asked.append(1)
        return "ollama   OK: nothing held"

    monkeypatch.setattr(OllamaResidency, "line", line)
    return asked


async def test_printing_helpers_are_captured_not_leaked(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _quiet_ollama(monkeypatch)
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)

    results = await DoctorChecks(LOCAL_DOCTOR_PROBES).run()

    assert capsys.readouterr().out == ""
    names = {r.name for r in results}
    assert {"hub-exposure", "sabbath", "gate-notices", "ledger-guard", "db-passwordless"} <= names
    assert all(r.mark in {"PASS", "WARN", "FAIL", "UNKNOWN"} for r in results)


def test_the_editor_probes_run_in_doctors_order() -> None:
    assert [p.name for p in LOCAL_DOCTOR_PROBES] == [
        "database-security",
        "db-passwordless",
        "hub-exposure",
        "ollama",
        "sabbath",
        "gate-notices",
        "supervisor",
        "host-health",
        "web-search",
        "llm-tooling",
    ]


# -- reprinting exactly -------------------------------------------------------------------


async def _printed_ok() -> bool:
    typer.echo("PASS ledger-guard         in force")
    typer.echo("WARN local-auth           trust on the socket\n  set scram-sha-256")
    return True


def _printed_sync() -> bool:
    typer.echo("FAIL hub-exposure         listening on 0.0.0.0 (  odd)")
    return False


def _listed() -> tuple[list[str], bool]:
    return ["sabbath  zone: Europe/Paris", "sabbath  FAIL: no location source answered"], False


async def _one_line() -> str:
    return "WARN gate-notices         2 gates waiting, nobody will be told"


def _probes() -> tuple[SectionProbe, ...]:
    return (
        SectionProbe.printed("database-security", _printed_ok),
        SectionProbe.printed_sync("hub-exposure", _printed_sync),
        SectionProbe.listed("sabbath", _listed, prefix="sabbath"),
        SectionProbe.single("gate-notices", _one_line),
    )


def _old_text() -> str:
    """What doctor printed before: each section straight to stdout."""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        asyncio.run(_printed_ok())
        _printed_sync()
        for line in _listed()[0]:
            typer.echo(line)
        typer.echo(asyncio.run(_one_line()))
    return buffer.getvalue()


def _old_json() -> list[dict[str, object]]:
    """What `--json` found before: the printed sections captured, the rest as lines."""
    out = JsonDoctorOutput()
    printed = io.StringIO()  # as `JsonDoctorOutput.captured` read an async section
    with redirect_stdout(printed):
        asyncio.run(_printed_ok())
    out.lines(printed.getvalue().splitlines())
    out.captured_sync(_printed_sync)
    out.lines(_listed()[0])
    out.say(asyncio.run(_one_line()))
    return [finding.document() for finding in out._findings]


async def _show(out: Any) -> list[DoctorResult]:
    found: list[DoctorResult] = []
    async for probe, results in DoctorChecks(_probes()).each():
        probe.show(out, results)
        found.extend(results)
    return found


def test_doctor_reprints_every_section_byte_for_byte() -> None:
    expected = _old_text()
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        asyncio.run(_show(TextDoctorOutput()))

    assert buffer.getvalue() == expected


def test_doctor_json_finds_the_same_findings_as_before() -> None:
    out = JsonDoctorOutput()
    asyncio.run(_show(out))

    assert [finding.document() for finding in out._findings] == _old_json()


async def test_results_carry_each_sections_marks_and_lines() -> None:
    found = await DoctorChecks(_probes()).run()

    assert [(r.mark, r.name) for r in found] == [
        ("PASS", "ledger-guard"),
        ("WARN", "local-auth"),
        ("FAIL", "hub-exposure"),
        ("PASS", "sabbath"),
        ("FAIL", "sabbath"),
        ("WARN", "gate-notices"),
    ]
    auth = found[1]
    assert auth.detail == "trust on the socket\nset scram-sha-256"
    assert auth.lines == ("WARN local-auth           trust on the socket", "  set scram-sha-256")
    assert found[3].detail == "zone: Europe/Paris"
    assert found[4].detail == "no location source answered"
    assert not DoctorChecks.passed(found)


# -- a result agrees with its section's own verdict ----------------------------------------


async def test_a_section_that_failed_without_a_fail_line_still_fails() -> None:
    async def quiet_failure() -> bool:
        typer.echo("UNKNOWN ledger-guard      could not tell")
        return False

    async def silent_failure() -> bool:
        return False

    said = await SectionProbe.printed("db", quiet_failure).run()
    unsaid = await SectionProbe.printed("db", silent_failure).run()

    assert [r.mark for r in said] == ["FAIL"]
    assert said[0].lines == ("UNKNOWN ledger-guard      could not tell",)
    assert [(r.mark, r.name, r.lines) for r in unsaid] == [("FAIL", "db", ())]


async def test_a_section_that_passed_never_reads_as_failed() -> None:
    def odd() -> tuple[list[str], bool]:
        return ["FAIL supervisor-worker      stopped"], True

    results = await SectionProbe.listed("supervisor", odd).run()

    assert [r.mark for r in results] == ["WARN"]


async def test_a_line_in_no_grammar_is_kept_as_unknown_and_a_stray_continuation_too() -> None:
    def lines() -> tuple[list[str], bool]:
        return ["  orphan continuation", "free text from a section"], True

    results = await SectionProbe.listed("x", lines).run()

    assert [(r.mark, r.name, r.detail) for r in results] == [
        ("UNKNOWN", "x", "orphan continuation"),
        ("UNKNOWN", "x", "free text from a section"),
    ]


async def test_the_ollama_line_marks_and_its_switch() -> None:
    async def ok() -> str:
        return "ollama   OK: nothing held"

    async def skipped() -> str:
        return "ollama   SKIP: no endpoint"

    async def warned() -> str:
        return "ollama   WARN: holds 32k"

    off_calls: list[int] = []

    async def never() -> str:
        off_calls.append(1)
        return "never"

    assert [(r.mark, r.name) for r in await SectionProbe.single("ollama", ok).run()] == [
        ("PASS", "ollama")
    ]
    assert [r.mark for r in await SectionProbe.single("ollama", skipped).run()] == ["UNKNOWN"]
    assert [r.mark for r in await SectionProbe.single("ollama", warned).run()] == ["WARN"]
    assert await SectionProbe.single("ollama", never, when=lambda: False).run() == ()
    assert off_calls == []


def test_a_probe_that_found_nothing_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    SectionProbe.printed_sync("hub", lambda: True).show(TextDoctorOutput(), ())
    SectionProbe.listed("s", lambda: ([], True)).show(TextDoctorOutput(), ())

    assert capsys.readouterr().out == ""


# -- the database sections, moved here from cli/main.py ------------------------------------


async def test_without_a_dsn_both_database_sections_are_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)

    security = await LOCAL_DATABASE_DOCTOR.security_lines()
    reach = await LOCAL_DATABASE_DOCTOR.passwordless_lines()

    assert security == (
        [f"UNKNOWN {'ledger-guard':<20} VIBEY_PG_URL is not set; nothing to check"],
        True,
    )
    assert reach == (
        [f"UNKNOWN {'db-passwordless':<20} VIBEY_PG_URL is not set; nothing to check"],
        True,
    )


async def test_a_database_that_cannot_be_reached_fails_the_security_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://nobody@127.0.0.1:1/none")

    lines, ok = await LOCAL_DATABASE_DOCTOR.security_lines()

    assert not ok and lines[0].startswith(f"FAIL {'ledger-guard':<20} cannot connect")


async def test_the_security_section_says_each_check_and_closes_its_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[bool] = []

    class _Conn:
        async def close(self) -> None:
            closed.append(True)

    async def connected(dsn: str) -> tuple[ClusterCheck, Any]:
        return ClusterCheck("database", True), _Conn()

    class _Checks:
        async def run(self, conn: Any, dsn: str) -> tuple[ClusterCheck, ...]:
            return (
                ClusterCheck("ledger-guard", True, "in force"),
                ClusterCheck("local-auth", False, "trusted"),
            )

    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://app@db/x")
    doctor = LocalDatabaseDoctor(connect=connected, checks=_Checks)

    lines, ok = await doctor.security_lines()

    assert lines == [f"PASS {'ledger-guard':<20} in force", f"FAIL {'local-auth':<20} trusted"]
    assert not ok and closed == [True]


@pytest.mark.parametrize(("verdict", "ok"), [(ReachVerdict.FAIL, False), (ReachVerdict.PASS, True)])
async def test_the_reach_section_says_its_verdict(
    monkeypatch: pytest.MonkeyPatch, verdict: ReachVerdict, ok: bool
) -> None:
    async def probe(self: PasswordlessReachProbe, dsn: str) -> PasswordlessReachFinding:
        return PasswordlessReachFinding(verdict, "tried the socket")

    monkeypatch.setattr(PasswordlessReachProbe, "probe", probe)
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://app@db/x")

    lines, passed = await LOCAL_DATABASE_DOCTOR.passwordless_lines()

    assert lines == [f"{verdict.mark} {'db-passwordless':<20} tried the socket"]
    assert passed is ok


async def test_the_printing_forms_print_what_the_line_forms_return(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)

    assert await LOCAL_DATABASE_DOCTOR.security() is True
    assert await LOCAL_DATABASE_DOCTOR.passwordless() is True

    assert capsys.readouterr().out.splitlines() == [
        f"UNKNOWN {'ledger-guard':<20} VIBEY_PG_URL is not set; nothing to check",
        f"UNKNOWN {'db-passwordless':<20} VIBEY_PG_URL is not set; nothing to check",
    ]


async def test_the_editor_reads_whether_a_local_engine_is_on_from_the_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    asked = _quiet_ollama(monkeypatch)
    monkeypatch.chdir(tmp_path)
    ollama = next(p for p in LOCAL_DOCTOR_PROBES if p.name == "ollama")

    monkeypatch.setenv("VIBEY_FEATURE_GPTOSSLOOP", "0")
    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "0")
    monkeypatch.setenv("VIBEY_FEATURE_CLAUDELOOP_LOCAL", "0")
    assert await ollama.run() == ()
    monkeypatch.setenv("VIBEY_FEATURE_GPTOSSLOOP", "1")
    assert [r.mark for r in await ollama.run()] == ["PASS"]
    assert asked == [1]


def test_the_probes_satisfy_their_interfaces() -> None:
    assert isinstance(LOCAL_DOCTOR, LocalDoctorProbesInterface)
    assert isinstance(LOCAL_DATABASE_DOCTOR, LocalDatabaseDoctorInterface)
    for probe in LOCAL_DOCTOR_PROBES:
        assert isinstance(probe, LocalDoctorProbeInterface)
        assert isinstance(probe, DoctorProbeInterface)
    assert json.dumps([p.name for p in LOCAL_DOCTOR_PROBES])  # names are plain strings


async def test_output_without_a_final_newline_keeps_its_last_line() -> None:
    import sys

    def unterminated() -> bool:
        sys.stdout.write("PASS hub-exposure  loopback")
        return True

    results = await SectionProbe.printed_sync("hub-exposure", unterminated).run()

    assert [r.lines for r in results] == [("PASS hub-exposure  loopback",)]


def test_the_editor_set_swaps_stdout_for_no_section(monkeypatch: pytest.MonkeyPatch) -> None:
    import contextlib as real

    def never(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the editor's set redirected sys.stdout")

    monkeypatch.setattr(real, "redirect_stdout", never)
    _quiet_ollama(monkeypatch)
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)

    results = asyncio.run(DoctorChecks(LOCAL_DOCTOR_PROBES).run())

    assert "hub-exposure" in {r.name for r in results}
