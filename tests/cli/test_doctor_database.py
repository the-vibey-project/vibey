# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey migrate` and `vibey doctor`'s database section (ADR-0055).

An install still running as one role is detected, not remembered: `vibey migrate`
exits 1 on it, `vibey doctor` fails on it, and the worker says so on every start. A
server that lets a password-less connection in as the owner or a superuser fails
doctor too, and one that cannot be checked is reported UNKNOWN, never PASS."""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import PreflightResult
from vibey.bootstrap import migrations_dir
from vibey.cli.main import _database_security_section, app
from vibey.infrastructure.cluster_preflight import ClusterCheck, DatabaseSecurityChecks
from vibey.infrastructure.db.local_auth import AuthVerdict, LocalAuthFinding, LocalAuthProbe

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
ROLES = TestDatabaseRoles.from_environ(os.environ)
split_only = pytest.mark.skipif(not ROLES.split, reason="the suite runs as one role")
OWNER_DSN = os.environ["VIBEY_TEST_DATABASE_URL"]


@pytest.fixture(autouse=True)
def _migrated() -> None:
    asyncio.run(ROLES.restore(OWNER_DSN, migrations_dir()))


def _probe_says(verdict: AuthVerdict, detail: str = "stub") -> object:
    return patch.object(
        LocalAuthProbe, "probe", new=AsyncMock(return_value=LocalAuthFinding(verdict, detail))
    )


# ── vibey migrate ───────────────────────────────────────────────────────────────


@split_only
def test_migrate_reconciles_the_application_role_and_reports_the_guard_in_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_PG_MIGRATE_URL", OWNER_DSN)

    res = runner.invoke(app, ["migrate"])

    assert res.exit_code == 0, res.output
    assert "applied 0 migration(s)" in res.output
    assert f"granted {ROLES.app_role} exactly the declared privileges" in res.output
    assert f"ledger guard in force: {ROLES.app_role}" in res.output


def test_migrate_needs_the_owners_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBEY_PG_MIGRATE_URL", raising=False)

    res = runner.invoke(app, ["migrate"])

    assert res.exit_code == 2
    assert "VIBEY_PG_MIGRATE_URL is not set" in res.output


def test_migrate_without_an_application_dsn_says_nothing_was_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_PG_MIGRATE_URL", OWNER_DSN)
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)

    res = runner.invoke(app, ["migrate"])

    assert res.exit_code == 1
    assert "the ledger guard was not checked" in res.output


def test_migrate_fails_while_the_application_still_connects_as_the_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_PG_MIGRATE_URL", OWNER_DSN)
    monkeypatch.setenv("VIBEY_PG_URL", OWNER_DSN)

    res = runner.invoke(app, ["migrate"])

    assert res.exit_code == 1
    assert "ledger guard NOT in force" in res.output
    assert "granted" not in res.output


# ── vibey doctor's database section ─────────────────────────────────────────────


@split_only
def test_the_section_passes_for_the_application_role(capsys: pytest.CaptureFixture[str]) -> None:
    with _probe_says(AuthVerdict.PASS, "refused"):
        assert asyncio.run(_database_security_section()) is True

    out = capsys.readouterr().out
    assert "PASS ledger-guard" in out
    assert "PASS local-auth" in out


def test_the_section_fails_for_the_owner(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", OWNER_DSN)
    with _probe_says(AuthVerdict.PASS):
        assert asyncio.run(_database_security_section()) is False

    assert "FAIL ledger-guard" in capsys.readouterr().out


@split_only
def test_a_password_less_owner_fails_the_section(capsys: pytest.CaptureFixture[str]) -> None:
    with _probe_says(AuthVerdict.FAIL, "accepted a password-less connection as postgres"):
        assert asyncio.run(_database_security_section()) is False

    assert "FAIL local-auth" in capsys.readouterr().out


@split_only
def test_an_undeterminable_server_is_unknown_never_pass(capsys: pytest.CaptureFixture[str]) -> None:
    with _probe_says(AuthVerdict.UNKNOWN, "could not confirm"):
        assert asyncio.run(_database_security_section()) is True

    out = capsys.readouterr().out
    assert "UNKNOWN local-auth" in out
    assert "PASS local-auth" not in out


def test_no_dsn_is_unknown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)

    assert asyncio.run(_database_security_section()) is True
    assert "UNKNOWN ledger-guard" in capsys.readouterr().out


def test_an_unreachable_database_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://nobody@127.0.0.1:1/none")

    assert asyncio.run(_database_security_section()) is False
    assert "FAIL ledger-guard" in capsys.readouterr().out


def test_doctor_exits_1_when_the_database_section_fails() -> None:
    ok = PreflightResult(installed=True, auth_ok=True, version="1.0.0", detail="")
    with (
        patch(
            "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
            new=AsyncMock(return_value=ok),
        ),
        patch("vibey.cli.main._database_security_section", new=AsyncMock(return_value=False)),
    ):
        res = runner.invoke(app, ["doctor", "--engine", "claudeloop"])

    assert res.exit_code == 1, res.output


def test_the_cluster_sweep_carries_both_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with (
        _probe_says(AuthVerdict.UNKNOWN, "could not confirm"),
        patch("shutil.which", side_effect=lambda binary: f"/app/.venv/bin/{binary}"),
    ):
        res = runner.invoke(app, ["doctor", "--cluster"])

    assert "ledger-guard" in res.output
    assert "UNKNOWN local-auth" in res.output


# ── the shared checks and the worker's warning ──────────────────────────────────


def test_a_check_is_marked_pass_fail_or_unknown() -> None:
    assert ClusterCheck("x", True).mark == "PASS"
    assert ClusterCheck("x", False).mark == "FAIL"
    assert ClusterCheck("x", True, unknown=True).mark == "UNKNOWN"


def test_the_worker_says_on_stderr_when_the_guard_is_not_in_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", OWNER_DSN)

    res = runner.invoke(app, ["worker", "--once"])

    assert "error: ledger guard NOT in force" in res.stderr


def test_the_security_checks_use_the_injected_seams() -> None:
    from vibey.infrastructure.db.ledger_guard import LedgerGuardStatus
    from vibey.infrastructure.interfaces import DatabaseSecurityChecksInterface

    class _Inspector:
        async def inspect(self, conn: object) -> LedgerGuardStatus:
            return LedgerGuardStatus("r", ("owns it",))

    class _Probe:
        def endpoints(self, app_url: str) -> tuple[tuple[str, int], ...]:
            return ()

        async def probe(self, app: object, app_url: str) -> LocalAuthFinding:
            return LocalAuthFinding(AuthVerdict.FAIL, "let in")

    checks = DatabaseSecurityChecks(inspector=_Inspector(), probe=_Probe())
    assert isinstance(checks, DatabaseSecurityChecksInterface)
    guard, auth = asyncio.run(checks.run(object(), "dsn"))  # type: ignore[arg-type]
    assert (guard.ok, auth.ok, auth.unknown) == (False, False, False)
