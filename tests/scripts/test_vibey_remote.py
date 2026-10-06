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
    environ = {"ARGV": "x", "REQUEST": ID, "HOME": "/home/runner"}
    vr.VibeyRemoteRunner(runner, environ).run('["status", "--json"]', ID, tmp_path)
    (migrate, migrate_env), (command, command_env) = runner.calls
    assert migrate == ["vibey", "migrate"] and command == ["vibey", "status", "--json"]
    assert command_env["VIBEY_PG_URL"] == vr.EPHEMERAL_APP_URL
    assert command_env["VIBEY_PG_MIGRATE_URL"] == vr.EPHEMERAL_OWNER_URL
    assert "ARGV" not in command_env and "REQUEST" not in command_env
    assert report(tmp_path) == {"exit_code": 3, "stdout": "out\n", "stderr": "err\n"}


def test_a_failed_migration_is_reported_and_the_command_still_runs(tmp_path: Path) -> None:
    runner = FakeRunner((1, "", "no server\n"), (0, "vibey 4.1.0\n", ""))
    vr.VibeyRemoteRunner(runner, {}).run('["--version"]', ID, tmp_path)
    got = report(tmp_path)
    assert got["exit_code"] == 0 and got["stdout"] == "vibey 4.1.0\n"
    assert "migrating the runner's database failed:\nno server" in str(got["stderr"])


def test_a_declared_database_is_used_as_it_is_and_never_migrated_here(tmp_path: Path) -> None:
    runner = FakeRunner((0, "[]\n", ""))
    environ = {
        "DECLARED_PG_URL": "postgresql://app@db/v",
        "DECLARED_PG_MIGRATE_URL": "postgresql://own@db/v",
    }
    vr.VibeyRemoteRunner(runner, environ).run('["projects", "--json"]', ID, tmp_path)
    [(argv, env)] = runner.calls
    assert argv == ["vibey", "projects", "--json"]
    assert (env["VIBEY_PG_URL"], env["VIBEY_PG_MIGRATE_URL"]) == (
        "postgresql://app@db/v",
        "postgresql://own@db/v",
    )
    assert "DECLARED_PG_URL" not in env
    runner = FakeRunner((0, "", ""))
    vr.VibeyRemoteRunner(runner, {"DECLARED_PG_URL": "postgresql://app@db/v"}).run(
        '["x"]', ID, tmp_path
    )
    assert "VIBEY_PG_MIGRATE_URL" not in runner.calls[0][1]


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
