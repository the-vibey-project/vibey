# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/vibey_remote.py`: the runner-side half of `vibey -w` always writes a report.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from scripts import vibey_remote as vr

ID = "0123456789abcdef"


class FakeRunner:
    def __init__(self, *answers: tuple[int, str, str]) -> None:
        self.answers = list(answers)
        self.calls: list[tuple[list[str], dict[str, str]]] = []

    def run(
        self, argv: Sequence[str], env: Mapping[str, str], timeout_s: float
    ) -> tuple[int, str, str]:
        self.calls.append((list(argv), dict(env)))
        return self.answers.pop(0)


def report(out: Path) -> dict[str, object]:
    return json.loads((out / "result.json").read_text())


def test_the_runners_own_database_is_migrated_then_the_command_runs(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (3, "out\n", "err\n"))
    environ = {"ARGV": "x", "REQUEST": ID, "HOME": "/home/runner", "ACTIONS_RUNTIME_TOKEN": "t"}
    vr.VibeyRemoteRunner(runner, environ).run('["status", "--json"]', ID, tmp_path)
    (migrate, migrate_env), (command, command_env) = runner.calls
    assert migrate == ["vibey", "migrate"] and command == ["vibey", "status", "--json"]
    assert migrate_env["VIBEY_PG_MIGRATE_URL"] == vr.EPHEMERAL_OWNER_URL
    # The owner's DSN reaches `vibey migrate` only, never another command (ADR-0055).
    assert "VIBEY_PG_MIGRATE_URL" not in command_env
    assert command_env["VIBEY_PG_URL"] == vr.EPHEMERAL_APP_URL
    # The command gets the system basics, never the runner's whole environment.
    assert command_env["HOME"] == "/home/runner"
    assert not {"ARGV", "REQUEST", "ACTIONS_RUNTIME_TOKEN"} & set(command_env)
    assert report(tmp_path) == {
        "exit_code": 3,
        "stdout": "out\n",
        "stderr": "err\n",
        "state_exported": False,
    }


def test_a_failed_migration_is_reported_and_the_command_still_runs(tmp_path: Path) -> None:
    runner = FakeRunner((1, "", "no server\n"), (0, "vibey 4.1.0\n", ""))
    vr.VibeyRemoteRunner(runner, {}).run('["--version"]', ID, tmp_path)
    got = report(tmp_path)
    assert got["exit_code"] == 0 and got["stdout"] == "vibey 4.1.0\n"
    assert "migrating the runner's database failed:\nno server" in str(got["stderr"])


DECLARED = {
    "DECLARED_PG_URL": "postgresql://app@db/v",
    "DECLARED_PG_MIGRATE_URL": "postgresql://own@db/v",
}


def test_a_private_repository_uses_its_declared_database_and_never_migrates_it_unasked(
    tmp_path: Path,
) -> None:
    runner = FakeRunner((0, "[]\n", ""))
    environ = {**DECLARED, "REPOSITORY_PRIVATE": "true"}
    vr.VibeyRemoteRunner(runner, environ).run('["projects", "--json"]', ID, tmp_path)
    [(argv, env)] = runner.calls
    assert argv == ["vibey", "projects", "--json"]
    assert env["VIBEY_PG_URL"] == "postgresql://app@db/v" and "VIBEY_PG_MIGRATE_URL" not in env
    assert "DECLARED_PG_URL" not in env
    runner = FakeRunner((0, "", ""))
    vr.VibeyRemoteRunner(runner, environ).run('["migrate"]', ID, tmp_path)
    assert runner.calls[0][1]["VIBEY_PG_MIGRATE_URL"] == "postgresql://own@db/v"


def test_a_public_repository_never_uses_its_declared_database(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (0, "[]\n", ""))
    environ = {**DECLARED, "REPOSITORY_PRIVATE": "false"}
    got = vr.VibeyRemoteRunner(runner, environ).run('["projects"]', ID, tmp_path)
    assert runner.calls[1][1]["VIBEY_PG_URL"] == vr.EPHEMERAL_APP_URL
    assert "not used on a public repository" in str(got["stderr"])


def test_what_cannot_run_is_reported_with_exit_2_and_nothing_runs(tmp_path: Path) -> None:
    for raw, why in (
        ("not json", "Expecting value"),
        ('{"a": 1}', "JSON array of strings"),
        ("[1, 2]", "JSON array of strings"),
        ('["-w", "status"]', "cannot itself carry -w"),
        ("[]", "name a command"),
    ):
        runner = FakeRunner()
        got = vr.VibeyRemoteRunner(runner, {}).run(raw, ID, tmp_path)
        assert got["exit_code"] == 2 and why in str(got["stderr"]) and runner.calls == []
    assert "not a request id" in str(
        vr.VibeyRemoteRunner(FakeRunner(), {}).run('["x"]', "bad id", tmp_path)["stderr"]
    )


def test_a_runaway_stream_is_cut_and_says_so() -> None:
    long = "x" * (vr.MAX_STREAM + 5)
    cut = vr.VibeyRemoteRunner._cut(long)
    assert cut.startswith("x" * vr.MAX_STREAM) and f"cut at {vr.MAX_STREAM} of {len(long)}" in cut
    assert vr.VibeyRemoteRunner._cut("short") == "short"


def test_the_subprocess_runner_runs_an_argument_vector_and_reports_a_timeout() -> None:
    runner = vr.SubprocessRunner()
    assert runner.run([sys.executable, "-c", "print('hi')"], {}, 30) == (0, "hi\n", "")
    code, _, err = runner.run([sys.executable, "-c", "import time; time.sleep(5)"], {}, 0.2)
    assert code == 124 and "ran past 0s" in err


def test_main_always_exits_0_once_a_report_is_written(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ARGV", '["-w"]')
    monkeypatch.setenv("REQUEST", ID)
    assert vr.main(["run", "--out", str(tmp_path)]) == 0
    assert report(tmp_path)["exit_code"] == 2
    assert "the command exited 2" in capsys.readouterr().out


STATE = {"STATE_KEY": "k" * 43, "GITHUB_REPOSITORY": "o/r", "GH_TOKEN": "ghs_read", "HOME": "/h"}


def test_a_private_repository_with_a_state_key_restores_runs_and_exports(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""), (0, "ran\n", ""), (0, "", ""))
    environ = {**STATE, "REPOSITORY_PRIVATE": "true", "VIBEY_STATE_BRANCH": "state"}
    got = vr.VibeyRemoteRunner(runner, environ).run('["status"]', ID, tmp_path, tmp_path / "s")
    (migrate, _), (restore, restore_env), (command, command_env), (export, export_env) = (
        runner.calls
    )
    assert migrate == ["vibey", "migrate"]
    assert restore == ["vibey", "state", "sync", "--no-push"]
    assert export == ["vibey", "state", "export", "--out", str(tmp_path / "s" / vr.STATE_FILE)]
    assert restore_env == export_env
    assert restore_env["VIBEY_STATE_PG_URL"] == vr.EPHEMERAL_OWNER_URL
    assert restore_env["VIBEY_STATE_KEY"] == "k" * 43
    assert restore_env["VIBEY_STATE_REPOSITORY"] == "o/r"
    assert restore_env["GH_TOKEN"] == "ghs_read" and restore_env["VIBEY_STATE_BRANCH"] == "state"
    # The command never holds the key, the owner's DSN or the token.
    assert not {"VIBEY_STATE_KEY", "VIBEY_STATE_PG_URL", "GH_TOKEN", "STATE_KEY"} & set(command_env)
    assert got["state_exported"] is True and got["stdout"] == "ran\n"


def test_a_public_repository_never_restores_the_state_and_says_so(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""))
    got = vr.VibeyRemoteRunner(runner, {**STATE, "REPOSITORY_PRIVATE": "false"}).run(
        '["status"]', ID, tmp_path, tmp_path / "s"
    )
    assert [argv for argv, _ in runner.calls] == [["vibey", "migrate"], ["vibey", "status"]]
    assert "not restored on a public repository" in str(got["stderr"])
    assert got["state_exported"] is False


def test_without_a_state_key_or_with_a_declared_database_nothing_is_restored(
    tmp_path: Path,
) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""))
    vr.VibeyRemoteRunner(runner, {"REPOSITORY_PRIVATE": "true"}).run('["status"]', ID, tmp_path)
    assert len(runner.calls) == 2
    runner = FakeRunner((0, "", ""))
    environ = {**STATE, **DECLARED, "REPOSITORY_PRIVATE": "true"}
    got = vr.VibeyRemoteRunner(runner, environ).run('["status"]', ID, tmp_path, tmp_path / "s")
    assert [argv for argv, _ in runner.calls] == [["vibey", "status"]]
    assert got["state_exported"] is False


def test_a_failed_migration_restores_nothing(tmp_path: Path) -> None:
    runner = FakeRunner((1, "", "down\n"), (0, "", ""))
    got = vr.VibeyRemoteRunner(runner, {**STATE, "REPOSITORY_PRIVATE": "true"}).run(
        '["status"]', ID, tmp_path, tmp_path / "s"
    )
    assert [argv for argv, _ in runner.calls][1] == ["vibey", "status"]
    assert got["state_exported"] is False


def test_a_failed_restore_is_said_and_nothing_is_exported(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (1, "", "bad key\n"), (0, "", ""))
    got = vr.VibeyRemoteRunner(runner, {**STATE, "REPOSITORY_PRIVATE": "true"}).run(
        '["status"]', ID, tmp_path, tmp_path / "s"
    )
    assert len(runner.calls) == 3
    assert "restoring the synced state failed:\nbad key" in str(got["stderr"])
    assert got["state_exported"] is False


def test_a_failed_export_is_said(tmp_path: Path) -> None:
    runner = FakeRunner((0, "", ""), (0, "", ""), (0, "", ""), (1, "", "disk\n"))
    got = vr.VibeyRemoteRunner(runner, {**STATE, "REPOSITORY_PRIVATE": "true"}).run(
        '["status"]', ID, tmp_path, tmp_path / "s"
    )
    assert "exporting the state for sync-back failed:\ndisk" in str(got["stderr"])
    assert got["state_exported"] is False


def test_sync_back_imports_then_syncs_and_stops_at_the_first_failure(tmp_path: Path) -> None:
    state = tmp_path / vr.STATE_FILE
    assert vr.VibeyRemoteRunner(FakeRunner(), STATE).sync_back(state) == (
        1,
        f"vibey-remote: no export at {state}\n",
    )
    state.write_bytes(b"sealed")
    runner = FakeRunner((0, "", ""), (0, "imported\n", ""), (0, "synced\n", ""))
    assert vr.VibeyRemoteRunner(runner, STATE).sync_back(state) == (0, "imported\nsynced\n")
    assert [argv for argv, _ in runner.calls] == [
        ["vibey", "migrate"],
        ["vibey", "state", "import", str(state)],
        ["vibey", "state", "sync"],
    ]
    runner = FakeRunner((0, "", ""), (1, "", "not empty\n"))
    assert vr.VibeyRemoteRunner(runner, STATE).sync_back(state) == (1, "not empty\n")
    runner = FakeRunner((1, "", "down\n"))
    code, said = vr.VibeyRemoteRunner(runner, STATE).sync_back(state)
    assert code == 1 and "migrating the runner's database failed" in said


def test_main_runs_sync_back_and_tells_the_workflow_the_state_was_exported(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(vr.VibeyRemoteRunner, "sync_back", lambda self, state: (3, "said\n"))
    assert vr.main(["sync-back", "--state", str(tmp_path / "x")]) == 3
    assert capsys.readouterr().out == "said\n"

    output = tmp_path / "github_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        vr.VibeyRemoteRunner,
        "run",
        lambda self, *a: {"exit_code": 0, "state_exported": True},
    )
    assert vr.main(["run", "--out", str(tmp_path), "--state-out", str(tmp_path / "s")]) == 0
    assert output.read_text() == "state=true\n"
    monkeypatch.setattr(
        vr.VibeyRemoteRunner, "run", lambda self, *a: {"exit_code": 0, "state_exported": False}
    )
    assert vr.main(["run", "--out", str(tmp_path)]) == 0
    assert output.read_text() == "state=true\n"
