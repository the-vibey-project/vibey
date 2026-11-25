# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey install --database`, `vibey install --model` and `vibey models --default-tag`.

Fakes stand in for PostgreSQL, the setup and Ollama: nothing here installs, connects or pulls.
What is held: each prints what it did and the next step, the database's settings are printed as
the lines to keep and never with a password, and every failure exits non-zero.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from vibey.cli.interfaces.local_install_interface import LocalInstallCommandInterface
from vibey.cli.local_install import LOCAL_INSTALL, LocalInstallCommand
from vibey.cli.main import app
from vibey.cli.models import ModelsCommand
from vibey.domain.local_database import LocalDatabaseNames
from vibey.infrastructure.db.database_setup import MigrationReport
from vibey.infrastructure.db.ledger_guard import LedgerGuardStatus
from vibey.infrastructure.db.local_database_setup import (
    DatabaseSetupRefused,
    LocalDatabaseReport,
)
from vibey.infrastructure.ollama_pull import ModelInstallResult
from vibey.infrastructure.postgres import (
    PostgresInstallResult,
    PostgresStatus,
    PostgresVersion,
)

runner = CliRunner()
READY = PostgresStatus(True, True, True, PostgresVersion(18, 1), "PostgreSQL 18.1 is accepting")
STOPPED = PostgresStatus(True, False, True, PostgresVersion(18, 1), "not accepting connections")
HEROIC = "hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE"


class _Service:
    def __init__(self, status: PostgresStatus = READY, *, installs: bool = True) -> None:
        self._status = status
        self._installs = installs
        self.installed = 0

    def status(self) -> PostgresStatus:
        return self._status

    def tool(self, name: str) -> str | None:
        return f"/usr/bin/{name}"

    def package_manager(self) -> str | None:
        return "brew"

    def install(self) -> PostgresInstallResult:
        self.installed += 1
        return PostgresInstallResult(self._installs, True, "installed it", self._status)


class _Setup:
    def __init__(self, report: LocalDatabaseReport | Exception) -> None:
        self._report = report

    def apply(self) -> LocalDatabaseReport:
        if isinstance(self._report, Exception):
            raise self._report
        return self._report


def _report(*, problems: tuple[str, ...] = (), created: bool = True) -> LocalDatabaseReport:
    names = LocalDatabaseNames("vibey", "vibey", "vibey_app", "localhost", 5432)
    return LocalDatabaseReport(
        names=names,
        created_roles=names.roles if created else (),
        database_created=created,
        password_file=Path("/home/adam/.pgpass"),
        migration=MigrationReport(
            ("0001_a", "0002_b") if created else (),
            "vibey_app",
            LedgerGuardStatus("vibey_app", problems),
        ),
    )


class _Puller:
    def __init__(self, result: ModelInstallResult) -> None:
        self.result = result
        self.calls: list[tuple[str, str | None]] = []

    def install(self, tag: str, say: Any, size: str | None) -> ModelInstallResult:
        self.calls.append((tag, size))
        say(f"Pulling {tag}")
        return self.result


def _command(
    *,
    service: _Service | None = None,
    setup: _Setup | None = None,
    puller: _Puller | None = None,
    environ: dict[str, str] | None = None,
    made: list[dict[str, Any]] | None = None,
) -> LocalInstallCommand:
    built = made if made is not None else []

    def setup_factory(admin: Any, pgpass: Any, names: LocalDatabaseNames) -> _Setup:
        built.append({"admin": admin, "pgpass": pgpass, "names": names})
        return setup or _Setup(_report())

    def puller_factory(url: str, *, wait_seconds: float) -> _Puller:
        built.append({"url": url, "wait_seconds": wait_seconds})
        return puller or _Puller(ModelInstallResult(True, True, f"{HEROIC} is in the Ollama"))

    return LocalInstallCommand(
        service_factory=lambda: service or _Service(),
        setup_factory=setup_factory,
        puller_factory=puller_factory,
        environ=environ if environ is not None else {},
        current_user=lambda: "adam",
    )


def _invoke(monkeypatch: pytest.MonkeyPatch, command: LocalInstallCommand, *args: str) -> Any:
    monkeypatch.setattr("vibey.cli.main.LOCAL_INSTALL", command)
    return runner.invoke(app, ["install", *args])


def test_the_command_satisfies_its_interface() -> None:
    assert isinstance(LOCAL_INSTALL, LocalInstallCommandInterface)


def test_install_with_no_target_names_every_target() -> None:
    res = runner.invoke(app, ["install"])
    assert res.exit_code == 2
    for target in ("install --postgres", "--database", "--model"):
        assert target in res.output


def test_the_database_is_made_and_the_lines_to_keep_are_printed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    made: list[dict[str, Any]] = []
    res = _invoke(monkeypatch, _command(made=made), "--database")
    assert res.exit_code == 0, res.output
    assert "created the roles vibey and vibey_app and the database vibey" in res.output
    assert "/home/adam/.pgpass" in res.output
    assert "applied 2 migration(s)" in res.output
    assert "ledger guard in force" in res.output
    assert "export VIBEY_PG_URL=postgresql://vibey_app@localhost:5432/vibey" in res.output
    assert "VIBEY_PG_MIGRATE_URL=postgresql://vibey@localhost:5432/vibey vibey migrate" in (
        res.output
    )
    assert "export VIBEY_PG_MIGRATE_URL" not in res.output  # the owner's DSN is never exported
    assert "scram-sha-256" in res.output  # what is still the person's (10.j)
    assert made[0]["names"] == LocalDatabaseNames("vibey", "vibey", "vibey_app", "localhost", 5432)
    assert made[0]["admin"].argv == ("/usr/bin/psql",)


def test_the_names_can_be_chosen(monkeypatch: pytest.MonkeyPatch) -> None:
    made: list[dict[str, Any]] = []
    res = _invoke(
        monkeypatch,
        _command(made=made),
        "--database",
        "--db-name",
        "work",
        "--owner-role",
        "work_owner",
        "--app-role",
        "work_app",
        "--admin-user",
        "pgadmin",
    )
    assert res.exit_code == 0, res.output
    assert made[0]["names"].roles == ("work_owner", "work_app")
    assert made[0]["admin"].argv == ("sudo", "-u", "pgadmin", "/usr/bin/psql")


def test_a_second_run_says_nothing_was_created(monkeypatch: pytest.MonkeyPatch) -> None:
    res = _invoke(monkeypatch, _command(setup=_Setup(_report(created=False))), "--database")
    assert res.exit_code == 0, res.output
    assert "already there" in res.output and "applied 0 migration(s)" in res.output


def test_a_guard_not_in_force_fails_the_step(monkeypatch: pytest.MonkeyPatch) -> None:
    setup = _Setup(_report(problems=("it may CREATE in schema public",)))
    res = _invoke(monkeypatch, _command(setup=setup), "--database")
    assert res.exit_code == 1
    assert "NOT in force" in res.output


def test_a_refused_setup_exits_one_and_says_why(monkeypatch: pytest.MonkeyPatch) -> None:
    setup = _Setup(DatabaseSetupRefused("the role 'vibey' already exists"))
    res = _invoke(monkeypatch, _command(setup=setup), "--database")
    assert res.exit_code == 1
    assert "already exists" in res.output


def test_a_server_that_is_not_ready_is_named_with_the_command_that_starts_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    res = _invoke(monkeypatch, _command(service=_Service(STOPPED)), "--database")
    assert res.exit_code == 1
    assert "vibey install --postgres" in res.output and "not accepting" in res.output


def test_a_name_that_is_not_an_identifier_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    res = _invoke(monkeypatch, _command(), "--database", "--db-name", "Bad-Name")
    assert res.exit_code == 2
    assert "plain lowercase identifier" in res.output


def test_the_default_model_is_pulled_with_its_size(monkeypatch: pytest.MonkeyPatch) -> None:
    puller = _Puller(ModelInstallResult(True, True, "pulled"))
    made: list[dict[str, Any]] = []
    res = _invoke(monkeypatch, _command(puller=puller, made=made), "--model")
    assert res.exit_code == 0, res.output
    assert puller.calls == [(HEROIC, "about 12.1 GB")]
    assert made == [{"url": "http://127.0.0.1:11434", "wait_seconds": 30.0}]
    assert f"Pulling {HEROIC}" in res.output and "pulled" in res.output


def test_the_model_follows_vibey_s_own_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    puller = _Puller(ModelInstallResult(True, False, "already there"))
    made: list[dict[str, Any]] = []
    command = _command(
        puller=puller,
        made=made,
        environ={"VIBEY_SOVEREIGN_MODEL": "stock", "VIBEY_OLLAMA_URL": "http://gpu:11434"},
    )
    res = _invoke(monkeypatch, command, "--model", "--wait-seconds", "5")
    assert res.exit_code == 0, res.output
    assert puller.calls == [("gpt-oss:20b", "about 14 GB")]
    assert made == [{"url": "http://gpu:11434", "wait_seconds": 5.0}]
    other = _Puller(ModelInstallResult(True, True, "pulled"))
    _invoke(
        monkeypatch, _command(puller=other, environ={"VIBEY_OLLAMA_MODEL": "qwen3:14b"}), "--model"
    )
    assert other.calls == [("qwen3:14b", None)]


def test_a_failed_pull_exits_one(monkeypatch: pytest.MonkeyPatch) -> None:
    puller = _Puller(ModelInstallResult(False, False, "Ollama is not installed here"))
    res = _invoke(monkeypatch, _command(puller=puller), "--model")
    assert res.exit_code == 1
    assert "not installed" in res.output


def test_a_bad_ollama_url_is_a_usage_error(monkeypatch: pytest.MonkeyPatch) -> None:
    command = LocalInstallCommand(environ={"VIBEY_OLLAMA_URL": "file:///x"})
    res = _invoke(monkeypatch, command, "--model")
    assert res.exit_code == 2
    assert "VIBEY_OLLAMA_URL" in res.output


def test_several_targets_run_in_order_and_stop_at_the_first_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _Service(installs=False)
    puller = _Puller(ModelInstallResult(True, True, "pulled"))
    monkeypatch.setattr("vibey.cli.main.PostgresLocalService", lambda: service)
    res = _invoke(monkeypatch, _command(puller=puller), "--postgres", "--database", "--model")
    assert res.exit_code == 1
    assert service.installed == 1 and puller.calls == []
    ok = _Service()
    monkeypatch.setattr("vibey.cli.main.PostgresLocalService", lambda: ok)
    res = _invoke(monkeypatch, _command(puller=puller), "--postgres", "--database", "--model")
    assert res.exit_code == 0, res.output
    assert (
        res.output.index("installed it")
        < res.output.index("VIBEY_PG_URL=")
        < (res.output.index("Pulling"))
    )


def test_a_failed_database_step_stops_before_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    puller = _Puller(ModelInstallResult(True, True, "pulled"))
    setup = _Setup(DatabaseSetupRefused("no"))
    res = _invoke(monkeypatch, _command(setup=setup, puller=puller), "--database", "--model")
    assert res.exit_code == 1 and puller.calls == []


def test_the_default_command_builds_its_real_parts() -> None:
    command = LocalInstallCommand(environ={})
    assert isinstance(command, LocalInstallCommandInterface)


# ------------------------------------------------------------------ vibey models --default-tag


def test_models_prints_the_tag_the_local_loop_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    res = runner.invoke(
        app,
        ["models", "--default-tag"],
        env={"VIBEY_OLLAMA_MODEL": "", "VIBEY_SOVEREIGN_MODEL": ""},
    )
    assert res.exit_code == 0
    assert res.output == f"{HEROIC}\n"
    assert ModelsCommand(environ={"VIBEY_SOVEREIGN_MODEL": "stock"}).default_tag() == (
        "gpt-oss:20b"
    )
    assert ModelsCommand(environ={"VIBEY_OLLAMA_MODEL": "qwen3:14b"}).default_tag() == "qwen3:14b"


def test_one_new_role_is_named_alone_and_an_unchecked_guard_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = LocalDatabaseNames("vibey", "vibey", "vibey_app", "localhost", 5432)
    one = LocalDatabaseReport(
        names, ("vibey_app",), False, Path("/p"), MigrationReport((), "vibey_app", None)
    )
    res = _invoke(monkeypatch, _command(setup=_Setup(one)), "--database")
    assert res.exit_code == 1
    assert "created the role vibey_app\n" in res.output
    assert "not checked" in res.output


def test_the_real_setup_is_the_local_database_setup(tmp_path: Path) -> None:
    from vibey.infrastructure.db.local_database_setup import LocalDatabaseSetup
    from vibey.infrastructure.db.pgpass_file import PgPassFile
    from vibey.infrastructure.db.postgres_admin import PostgresAdmin

    names = LocalDatabaseNames("vibey", "vibey", "vibey_app", "localhost", 5432)
    built = LocalInstallCommand._real_setup(
        PostgresAdmin(("psql",)), PgPassFile(environ={}, home=lambda: tmp_path), names
    )
    assert isinstance(built, LocalDatabaseSetup)
