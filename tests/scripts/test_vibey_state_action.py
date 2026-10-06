# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/vibey_state_action.py`: any workflow opens the synced state only through the gate.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import runpy
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from scripts import vibey_state_action as sa
from scripts.interfaces.vibey_state_action_interface import StateDeclarationError

KEY = "k" * 43
PUBLIC_MESSAGE = (
    "vibey-state: the synced state is not restored: a public repository needs "
    "`public = true` in .github/vibey-state.toml\n"
)


class FakeRunner:
    def __init__(self, *answers: tuple[int, str, str]) -> None:
        self.answers = list(answers)
        self.calls: list[tuple[list[str], dict[str, str]]] = []

    def run(
        self, argv: Sequence[str], env: Mapping[str, str], timeout_s: float
    ) -> tuple[int, str, str]:
        self.calls.append((list(argv), dict(env)))
        return self.answers.pop(0)


class FakeGate:
    def __init__(self, allowed: bool = True, note: str = "", broken: str = "") -> None:
        self.allowed, self.note, self.broken = allowed, note, broken

    def decide(self) -> tuple[bool, str]:
        if self.broken:
            raise StateDeclarationError(self.broken)
        return self.allowed, self.note


class FakePostgres:
    def __init__(self, problem: str = "") -> None:
        self.problem = problem
        self.started = 0

    def start(self) -> str:
        self.started += 1
        return self.problem


def declaration(tmp_path: Path, text: str | bytes | None) -> sa.StateDeclaration:
    path = tmp_path / "vibey-state.toml"
    if isinstance(text, bytes):
        path.write_bytes(text)
    elif text is not None:
        path.write_text(text)
    return sa.StateDeclaration(path)


def action(
    environ: dict[str, str],
    runner: FakeRunner,
    *,
    gate: FakeGate | None = None,
    postgres: FakePostgres | None = None,
) -> sa.StateAction:
    return sa.StateAction(
        environ,
        gate=gate or FakeGate(),
        postgres=postgres or FakePostgres(),
        commands=sa.StateCommands(runner, environ),
    )


def github_files(tmp_path: Path) -> dict[str, str]:
    return {
        "GITHUB_ENV": str(tmp_path / "github_env"),
        "GITHUB_OUTPUT": str(tmp_path / "github_output"),
    }


def written(tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    return path.read_text() if path.exists() else ""


# ------------------------------------------------------------------- the declaration


def test_an_absent_or_empty_declaration_keeps_a_public_repository_closed(tmp_path: Path) -> None:
    assert declaration(tmp_path, None).public() is False
    assert declaration(tmp_path, "").public() is False
    assert declaration(tmp_path, "[state]\n").public() is False
    assert declaration(tmp_path, "[state]\npublic = false\n").public() is False
    assert declaration(tmp_path, "# yes\n[state]\npublic = true\n").public() is True


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("[state\n", "vibey-state.toml:"),
        (b"\xff\xfe[state]\n", "vibey-state.toml:"),
        ("[stat]\npublic = true\n", "unknown table(s) stat"),
        ("state = 1\n", "`state` must be a table"),
        ("[state]\npublic = true\nprivate = 1\n", "unknown key(s) state.private"),
        ('[state]\npublic = "yes"\n', "`state.public` must be true or false, not str"),
    ],
)
def test_a_declaration_that_cannot_be_read_as_declared_is_refused_by_name(
    tmp_path: Path, text: str | bytes, named: str
) -> None:
    with pytest.raises(StateDeclarationError) as refused:
        declaration(tmp_path, text).public()
    assert named in str(refused.value)


# ---------------------------------------------------------------------------- the gate


def test_the_gate_needs_a_key_then_a_private_repository_or_the_declaration(
    tmp_path: Path,
) -> None:
    closed, opened = declaration(tmp_path, None), sa.StateDeclaration(tmp_path / "public.toml")
    (tmp_path / "public.toml").write_text("[state]\npublic = true\n")
    assert sa.StateGate({"STATE_KEY": "  "}, opened).decide() == (False, "")
    assert sa.StateGate({"STATE_KEY": KEY, "REPOSITORY_PRIVATE": "true"}, closed).decide() == (
        True,
        "",
    )
    assert sa.StateGate({"STATE_KEY": KEY, "REPOSITORY_PRIVATE": "false"}, opened).decide() == (
        True,
        "",
    )
    assert sa.StateGate({"STATE_KEY": KEY}, closed).decide() == (False, PUBLIC_MESSAGE)
    allowed, note = sa.StateGate({"STATE_KEY": KEY}, closed, prefix="vibey-remote").decide()
    assert not allowed and note.startswith("vibey-remote: the synced state is not restored")


def test_the_gate_reads_the_declaration_even_without_a_key(tmp_path: Path) -> None:
    with pytest.raises(StateDeclarationError):
        sa.StateGate({}, declaration(tmp_path, "[x]\n")).decide()


# ------------------------------------------------------------------------ the commands

ENVIRON = {
    "HOME": "/home/runner",
    "PATH": "/usr/bin",
    "STATE_KEY": f" {KEY} ",
    "GH_TOKEN": "ghs_x",
    "GITHUB_REPOSITORY": "o/r",
    "VIBEY_STATE_BRANCH": "state",
    "VIBEY_STATE_CONFLICTS": "  ",
    "ACTIONS_RUNTIME_TOKEN": "t",
    "PG_URL": "postgresql://own@db/v",
}


def test_state_commands_get_a_filtered_environment_and_vibey_commands_a_narrower_one() -> None:
    commands = sa.StateCommands(FakeRunner(), ENVIRON)
    env = commands.state_environment("postgresql://own@db/v")
    assert env == {
        "HOME": "/home/runner",
        "PATH": "/usr/bin",
        "GH_TOKEN": "ghs_x",
        "VIBEY_STATE_BRANCH": "state",
        "VIBEY_STATE_PG_URL": "postgresql://own@db/v",
        "VIBEY_STATE_KEY": KEY,
        "VIBEY_STATE_REPOSITORY": "o/r",
    }
    other = sa.StateCommands(FakeRunner(), {"VIBEY_STATE_REPOSITORY": " o/elsewhere "})
    got = other.state_environment("u")
    assert got["VIBEY_STATE_REPOSITORY"] == "o/elsewhere" and "GH_TOKEN" not in got
    assert commands.environment("app", "own", migrate=False) == {
        "HOME": "/home/runner",
        "PATH": "/usr/bin",
        "VIBEY_PG_URL": "app",
    }
    assert commands.environment("app", "own", migrate=True)["VIBEY_PG_MIGRATE_URL"] == "own"
    assert "VIBEY_PG_MIGRATE_URL" not in commands.environment("app", "", migrate=True)


def test_migrate_and_run_report_what_happened() -> None:
    runner = FakeRunner((0, "", ""), (1, "", "down\n"), (0, "ok\n", ""))
    commands = sa.StateCommands(runner, ENVIRON, prefix="p")
    assert commands.migrate("app", "own") == ""
    assert commands.migrate("app", "own") == "p: migrating the runner's database failed:\ndown\n"
    assert commands.run(["vibey", "state", "status"], "own") == (0, "ok\n", "")
    assert runner.calls[2][1]["VIBEY_STATE_PG_URL"] == "own"


def test_write_back_migrates_imports_then_syncs_and_stops_at_the_first_failure(
    tmp_path: Path,
) -> None:
    state = tmp_path / sa.STATE_FILE
    commands = sa.StateCommands(FakeRunner(), ENVIRON)
    assert commands.write_back(state, "app", "own") == (
        1,
        f"vibey-state: no export at {state}\n",
    )
    state.write_bytes(b"sealed")
    runner = FakeRunner((0, "", ""), (0, "imported\n", ""), (0, "synced\n", ""))
    assert sa.StateCommands(runner, ENVIRON).write_back(state, "app", "own") == (
        0,
        "imported\nsynced\n",
    )
    assert [argv for argv, _ in runner.calls] == [
        ["vibey", "migrate"],
        ["vibey", "state", "import", str(state)],
        ["vibey", "state", "sync"],
    ]
    runner = FakeRunner((0, "", ""), (1, "", "not empty\n"))
    assert sa.StateCommands(runner, ENVIRON).write_back(state, "a", "o") == (1, "not empty\n")
    runner = FakeRunner((1, "", "down\n"))
    code, said = sa.StateCommands(runner, ENVIRON).write_back(state, "a", "o")
    assert code == 1 and "migrating the runner's database failed" in said


# ------------------------------------------------------------------ the runner's database

STARTED = (0, "", "")


def test_the_runners_postgresql_is_started_waited_for_and_given_its_role_and_database() -> None:
    runner = FakeRunner(
        STARTED, (2, "", ""), (2, "", ""), (0, "", ""), (0, "", ""), (0, "", ""), (0, "", "")
    )
    slept: list[float] = []
    environ = {"PATH": "/usr/bin", "STATE_KEY": KEY}
    assert sa.RunnerPostgres(runner, environ, sleep=slept.append).start() == ""
    argvs = [argv for argv, _ in runner.calls]
    assert argvs[0] == ["sudo", "systemctl", "start", "postgresql.service"]
    assert argvs[1:4] == [["pg_isready", "-h", "localhost", "-p", "5432"]] * 3
    assert slept == [1.0, 1.0]
    assert argvs[4][:6] == ["sudo", "-u", "postgres", "psql", "-v", "ON_ERROR_STOP=1"]
    assert "CREATE ROLE \"vibey\" LOGIN SUPERUSER PASSWORD 'vibey'" in argvs[4][-1]
    assert 'ALTER ROLE "vibey"' in argvs[4][-1]
    assert argvs[5][-1] == "SELECT 1 FROM pg_database WHERE datname = 'vibey'"
    assert argvs[6] == ["sudo", "-u", "postgres", "createdb", "-O", "vibey", "vibey"]
    # Its commands get the system basics, never the key.
    assert all(env == {"PATH": "/usr/bin"} for _, env in runner.calls)


def test_a_database_that_is_already_there_is_not_created_twice() -> None:
    runner = FakeRunner(STARTED, (0, "", ""), (0, "", ""), (0, "1\n", ""))
    assert sa.RunnerPostgres(runner, {}, sleep=lambda _: None).start() == ""
    assert len(runner.calls) == 4


@pytest.mark.parametrize(
    ("answers", "said"),
    [
        ([(1, "", "no unit\n")], "starting the runner's PostgreSQL failed:\nno unit"),
        ([STARTED] + [(2, "", "")] * sa.READY_ATTEMPTS, "did not answer within 30s"),
        ([STARTED, (0, "", ""), (1, "", "denied\n")], "creating the vibey role failed:\ndenied"),
        (
            [STARTED, (0, "", ""), (0, "", ""), (1, "", "gone\n")],
            "looking for the vibey database failed:\ngone",
        ),
        (
            [STARTED, (0, "", ""), (0, "", ""), (0, "", ""), (1, "", "full\n")],
            "creating the vibey database failed:\nfull",
        ),
    ],
)
def test_each_step_of_starting_the_runners_postgresql_says_how_it_failed(
    answers: list[tuple[int, str, str]], said: str
) -> None:
    runner = FakeRunner(*answers)
    assert said in sa.RunnerPostgres(runner, {}, sleep=lambda _: None).start()
    assert runner.answers == []


def test_sql_names_and_literals_are_quoted() -> None:
    assert sa.RunnerPostgres._identifier('a"b') == '"a""b"'
    assert sa.RunnerPostgres._literal("it's") == "'it''s'"


# ---------------------------------------------------------------------------- open


def test_open_on_the_runners_postgresql_restores_and_tells_later_steps(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRunner((0, "", ""), (0, "pulled 3 rows\n", "note\n"))
    postgres = FakePostgres()
    environ = {**ENVIRON, **github_files(tmp_path)}
    del environ["PG_URL"]
    assert action(environ, runner, postgres=postgres).open() == 0
    assert postgres.started == 1
    (migrate, migrate_env), (restore, restore_env) = runner.calls
    assert migrate == ["vibey", "migrate"]
    assert migrate_env["VIBEY_PG_MIGRATE_URL"] == sa.EPHEMERAL_OWNER_URL
    assert restore == ["vibey", "state", "sync", "--no-push"]
    assert restore_env["VIBEY_STATE_PG_URL"] == sa.EPHEMERAL_OWNER_URL
    assert restore_env["VIBEY_STATE_KEY"] == KEY
    assert written(tmp_path, "github_env") == (
        f"VIBEY_PG_URL={sa.EPHEMERAL_APP_URL}\nVIBEY_STATE_PG_URL={sa.EPHEMERAL_OWNER_URL}\n"
    )
    assert written(tmp_path, "github_output") == "opened=true\n"
    said = capsys.readouterr()
    assert said.out == "pulled 3 rows\n" and said.err == "note\n"


def test_open_on_a_declared_database_derives_the_application_dsn_unless_given(
    tmp_path: Path,
) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""))
    postgres = FakePostgres()
    environ = {**ENVIRON, **github_files(tmp_path), "PG_URL": "postgresql://o:p@db:6543/v?x=1"}
    assert action(environ, runner, postgres=postgres).open() == 0
    assert postgres.started == 0
    app = "postgresql://vibey_app:vibey-remote-app@db:6543/v?x=1"
    assert runner.calls[0][1]["VIBEY_PG_URL"] == app
    assert written(tmp_path, "github_env").splitlines()[0] == f"VIBEY_PG_URL={app}"
    runner = FakeRunner((0, "", ""), (0, "", ""))
    environ["APP_PG_URL"] = "postgresql://mine@db/v"
    assert action(environ, runner).open() == 0
    assert runner.calls[0][1]["VIBEY_PG_URL"] == "postgresql://mine@db/v"


def test_the_application_dsn_keeps_the_owners_server() -> None:
    app = sa.StateAction._app_url
    assert app("postgresql://o:p@[::1]:5432/v") == (
        "postgresql://vibey_app:vibey-remote-app@[::1]:5432/v"
    )
    assert app("postgresql://o@db/v") == "postgresql://vibey_app:vibey-remote-app@db/v"
    assert app("postgresql://o@/v?host=/run/pg") == (
        "postgresql://vibey_app:vibey-remote-app@/v?host=/run/pg"
    )


def test_open_without_the_gate_opens_nothing_and_says_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = github_files(tmp_path)
    runner = FakeRunner()
    assert action(files, runner, gate=FakeGate(False, PUBLIC_MESSAGE)).open() == 0
    assert capsys.readouterr().err == PUBLIC_MESSAGE
    assert action(files, runner, gate=FakeGate(False)).open() == 0
    assert "no state key was given" in capsys.readouterr().err
    assert action(files, runner, gate=FakeGate(broken="x.toml: unknown")).open() == 2
    assert capsys.readouterr().err == "vibey-state: x.toml: unknown\n"
    assert runner.calls == [] and written(tmp_path, "github_env") == ""
    assert written(tmp_path, "github_output") == "opened=false\n" * 3


@pytest.mark.parametrize(
    ("environ", "postgres", "answers", "said"),
    [
        ({}, FakePostgres("vibey-state: no unit\n"), [], "vibey-state: no unit\n"),
        ({"PG_URL": "postgresql://o@db/v\nX=1"}, None, [], "cannot hold a line break"),
        ({"PG_URL": "postgresql://o@db/v"}, None, [(1, "", "down\n")], "database failed:\ndown"),
        (
            {"PG_URL": "postgresql://o@db/v"},
            None,
            [(0, "", ""), (1, "", "bad key\n")],
            "bad key\nvibey-state: restoring the synced state failed",
        ),
    ],
)
def test_an_open_that_cannot_finish_fails_its_step_and_exports_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    environ: dict[str, str],
    postgres: FakePostgres | None,
    answers: list[tuple[int, str, str]],
    said: str,
) -> None:
    runner = FakeRunner(*answers)
    assert action({**environ, **github_files(tmp_path)}, runner, postgres=postgres).open() == 1
    assert said in capsys.readouterr().err
    assert written(tmp_path, "github_env") == "" and written(tmp_path, "github_output") == ""


def test_without_githubs_files_nothing_is_written(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""))
    assert action({"PG_URL": "postgresql://o@db/v"}, runner).open() == 0


# --------------------------------------------------------------------------- close

OPENED = {"VIBEY_STATE_PG_URL": "postgresql://o@db/v", "STATE_KEY": KEY}


def test_close_exports_the_sealed_state_under_a_name_unique_to_the_job(tmp_path: Path) -> None:
    runner = FakeRunner((0, "exported\n", ""))
    environ = {
        **OPENED,
        **github_files(tmp_path),
        "GITHUB_RUN_ID": "77",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_JOB": "nightly",
    }
    out = tmp_path / "out"
    assert action(environ, runner).close(out, push=False) == 0
    [(argv, env)] = runner.calls
    assert argv == ["vibey", "state", "export", "--out", str(out / sa.STATE_FILE)]
    assert env["VIBEY_STATE_PG_URL"] == "postgresql://o@db/v"
    assert written(tmp_path, "github_output") == (
        f"state=true\npath={out / sa.STATE_FILE}\ndir={out}\nartifact=vibey-state-77-2-nightly\n"
    )


def test_close_names_the_artifact_as_asked(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""))
    environ = {**OPENED, **github_files(tmp_path), "ARTIFACT": " mine "}
    assert action(environ, runner).close(tmp_path, push=False) == 0
    assert written(tmp_path, "github_output").endswith("artifact=mine\n")
    del environ["ARTIFACT"]
    assert action(environ, runner).close(tmp_path, push=False) == 0
    assert written(tmp_path, "github_output").endswith("artifact=vibey-state\n")


def test_close_with_push_syncs_the_branch_directly(tmp_path: Path) -> None:
    runner = FakeRunner((0, "pushed\n", ""), (1, "", "conflict\n"))
    environ = {**OPENED, **github_files(tmp_path)}
    assert action(environ, runner).close(tmp_path, push=True) == 0
    assert runner.calls[0][0] == ["vibey", "state", "sync"]
    assert action(environ, runner).close(tmp_path, push=True) == 1
    assert written(tmp_path, "github_output") == (
        "state=false\npushed=true\nstate=false\npushed=false\n"
    )


def test_a_close_that_cannot_export_fails_its_step(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRunner((1, "", "disk\n"))
    environ = {**OPENED, **github_files(tmp_path)}
    assert action(environ, runner).close(tmp_path, push=False) == 1
    assert capsys.readouterr().err == "disk\n"
    assert written(tmp_path, "github_output") == "state=false\n"


def test_close_without_an_open_state_or_with_a_bad_name_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRunner()
    assert action({"STATE_KEY": KEY}, runner).close(tmp_path, push=False) == 1
    assert "open the state in this job first" in capsys.readouterr().err
    assert action({**OPENED, "ARTIFACT": "a\nb"}, runner).close(tmp_path, push=False) == 2
    assert "cannot hold a line break" in capsys.readouterr().err
    assert runner.calls == []


def test_close_without_the_gate_hands_nothing_on(tmp_path: Path) -> None:
    files = github_files(tmp_path)
    runner = FakeRunner()
    assert action({**OPENED, **files}, runner, gate=FakeGate(False)).close(tmp_path, push=True) == 0
    assert action({**files}, runner, gate=FakeGate(broken="b")).close(tmp_path, push=False) == 2
    assert runner.calls == [] and written(tmp_path, "github_output") == "state=false\n" * 2


# ----------------------------------------------------------------------- write-back


def test_write_back_merges_the_export_into_a_fresh_database(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = tmp_path / sa.STATE_FILE
    state.write_bytes(b"sealed")
    runner = FakeRunner((0, "", ""), (0, "imported\n", ""), (0, "synced\n", ""))
    postgres = FakePostgres()
    assert action(dict(ENVIRON), runner, postgres=postgres).write_back(state) == 0
    assert postgres.started == 0 and capsys.readouterr().out == "imported\nsynced\n"
    assert runner.calls[1][1]["VIBEY_STATE_PG_URL"] == "postgresql://own@db/v"
    runner = FakeRunner((0, "", ""), (3, "", "conflict\n"))
    environ = {k: v for k, v in ENVIRON.items() if k != "PG_URL"}
    postgres = FakePostgres()
    assert action(environ, runner, postgres=postgres).write_back(state) == 3
    assert postgres.started == 1
    assert runner.calls[1][1]["VIBEY_STATE_PG_URL"] == sa.EPHEMERAL_OWNER_URL


def test_write_back_refused_or_without_a_database_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRunner()
    state = tmp_path / sa.STATE_FILE
    assert action({}, runner, gate=FakeGate(False, PUBLIC_MESSAGE)).write_back(state) == 1
    assert action({}, runner, gate=FakeGate(broken="b")).write_back(state) == 2
    assert action({}, runner, postgres=FakePostgres("no unit\n")).write_back(state) == 1
    assert capsys.readouterr().err.endswith("no unit\n") and runner.calls == []


# ------------------------------------------------------------------- the process runner


def test_the_subprocess_runner_runs_an_argument_vector_and_reports_a_timeout() -> None:
    runner = sa.SubprocessRunner()
    assert runner.run([sys.executable, "-c", "print('hi')"], {}, 30) == (0, "hi\n", "")
    code, _, err = runner.run([sys.executable, "-c", "import time; time.sleep(5)"], {}, 0.2)
    assert code == 124 and err == "vibey-state: the command ran past 0s and was stopped\n"
    _, _, err = sa.SubprocessRunner("p").run(
        [sys.executable, "-c", "import time; time.sleep(5)"], {}, 0.2
    )
    assert err.startswith("p: ")


# ---------------------------------------------------------------------------- main


def test_main_runs_the_step_it_is_given(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[tuple[str, object]] = []
    monkeypatch.setattr(sa.StateAction, "open", lambda self: seen.append(("open", None)) or 5)
    monkeypatch.setattr(
        sa.StateAction,
        "close",
        lambda self, out, *, push: seen.append(("close", (out, push))) or 6,
    )
    monkeypatch.setattr(
        sa.StateAction, "write_back", lambda self, state: seen.append(("back", state)) or 7
    )
    assert sa.main(["open"]) == 5
    assert sa.main(["close", "--out", str(tmp_path)]) == 6
    assert sa.main(["close", "--out", str(tmp_path), "--push", "true"]) == 6
    assert sa.main(["write-back", str(tmp_path / "f")]) == 7
    assert seen == [
        ("open", None),
        ("close", (tmp_path, False)),
        ("close", (tmp_path, True)),
        ("back", tmp_path / "f"),
    ]
    with pytest.raises(SystemExit):
        sa.main(["close", "--out", str(tmp_path), "--push", "yes"])


def test_run_directly_it_finds_its_interfaces_beside_it_and_exits_with_the_steps_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The composite action runs the file, not the module: `scripts.` is not importable."""
    script = Path(sa.__file__)
    monkeypatch.syspath_prepend(str(script.parent))
    monkeypatch.setitem(sys.modules, "scripts.interfaces.vibey_state_action_interface", None)
    monkeypatch.setattr(sys, "argv", [str(script), "open"])
    for name in ("STATE_KEY", "GITHUB_OUTPUT", "GITHUB_ENV"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    # Another script run directly may have left its own `interfaces` behind: start clean.
    for name in [n for n in sys.modules if n.split(".")[0] in {"interfaces", "vibey_state_action"}]:
        monkeypatch.delitem(sys.modules, name)
    before = set(sys.modules)
    try:
        with pytest.raises(SystemExit) as exited:
            runpy.run_path(str(script), run_name="__main__")
    finally:
        for name in set(sys.modules) - before:
            if name == "interfaces" or name.startswith("interfaces."):
                del sys.modules[name]
    assert exited.value.code == 0


def test_an_event_that_does_not_say_whether_the_repository_is_private_is_asked_of_github(
    tmp_path: Path,
) -> None:
    """A `schedule` run's payload names no repository, so `REPOSITORY_PRIVATE` is empty."""
    closed = declaration(tmp_path, None)
    environ = {"STATE_KEY": KEY, "GITHUB_REPOSITORY": "o/r", "GH_TOKEN": "ghs", "HOME": "/h"}
    runner = FakeRunner((0, "true\n", ""))
    assert sa.StateGate(environ, closed, runner=runner).decide() == (True, "")
    [(argv, env)] = runner.calls
    assert argv == ["gh", "api", "repos/o/r", "--jq", ".private"]
    assert env == {"GH_TOKEN": "ghs", "HOME": "/h"}
    for answer in ((0, "false\n", ""), (1, "", "HTTP 404\n")):
        runner = FakeRunner(answer)
        no_token = {k: v for k, v in environ.items() if k != "GH_TOKEN"}
        assert sa.StateGate(no_token, closed, runner=runner).decide() == (False, PUBLIC_MESSAGE)
        assert "GH_TOKEN" not in runner.calls[0][1]
    # Said by the event, or nobody to ask: GitHub is not asked.
    runner = FakeRunner()
    assert (
        sa.StateGate({**environ, "REPOSITORY_PRIVATE": "false"}, closed, runner=runner).decide()[0]
        is False
    )
    assert sa.StateGate({"STATE_KEY": KEY}, closed, runner=runner).decide()[0] is False
    assert runner.calls == []
