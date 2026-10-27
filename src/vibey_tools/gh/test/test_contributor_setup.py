# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh setup`: one command from a fresh clone to a working contributor environment (#1689).

The runner is scripted, so no test touches the real machine; the order rule that used to live in
CONTRIBUTING.md prose ("`pre-commit install` refuses to run while `core.hooksPath` is set") is
asserted here as the order of the calls.
"""

from __future__ import annotations

import argparse
import socket
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest

from vibey_gh import cli
from vibey_gh.config import GhConfig
from vibey_gh.contributor_setup import (
    ContributorSetup,
    SetupReport,
    SetupStep,
    SubprocessRunner,
)
from vibey_gh.install import Action
from vibey_gh.interfaces.command_runner_interface import CommandResult, CommandRunnerInterface
from vibey_gh.interfaces.contributor_setup_interface import ContributorSetupInterface

STAGES_INSTALLED = {"pre-commit": "installed", "commit-msg": "installed", "pre-push": "installed"}
STAGES_MISSING = dict.fromkeys(STAGES_INSTALLED, "missing")


class ScriptedRunner:
    """Answers by the longest matching argv prefix; records every call and its env."""

    def __init__(
        self,
        script: Mapping[tuple[str, ...], CommandResult | Callable[[], CommandResult]] | None = None,
    ):
        self.script = dict(script or {})
        self.calls: list[tuple[str, ...]] = []
        self.envs: list[Mapping[str, str] | None] = []

    def run(
        self, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None
    ) -> CommandResult:
        key = tuple(argv)
        self.calls.append(key)
        self.envs.append(env)
        for size in range(len(key), 0, -1):
            answer = self.script.get(key[:size])
            if answer is not None:
                return answer() if callable(answer) else answer
        return CommandResult(0)


class SequencedInspector:
    """Returns its states in turn, the last one forever."""

    def __init__(self, *states: dict[str, str]):
        self.states = list(states)

    def common_dir(self, cfg: GhConfig) -> Path | None:
        return None

    def stages(self, cfg: GhConfig) -> dict[str, str]:
        return self.states.pop(0) if len(self.states) > 1 else self.states[0]

    def problems(self, cfg: GhConfig) -> list[str]:
        return []


def make(
    tmp_path: Path,
    runner: ScriptedRunner | None = None,
    *,
    stages: SequencedInspector | None = None,
    installer: Callable[[GhConfig], list[Action]] | None = None,
    checker: Callable[..., tuple[bool, list[str]]] | None = None,
    which: Callable[[str], str | None] | None = None,
    connect: Callable[[str, int], bool] | None = None,
    environ: Mapping[str, str] | None = None,
    python: tuple[int, int] = (3, 12),
) -> ContributorSetup:
    return ContributorSetup(
        GhConfig(root=tmp_path),
        runner=runner or ScriptedRunner(),
        inspector=stages or SequencedInspector(STAGES_INSTALLED),
        installer=installer or (lambda cfg: [Action("commit-msg", "unchanged")]),
        checker=checker or (lambda cfg, local: (True, [])),
        which=which or (lambda tool: f"/usr/bin/{tool}"),
        connect=connect or (lambda host, port: True),
        environ={"USER": "dev"} if environ is None else environ,
        python=python,
    )


def by_name(report: SetupReport) -> dict[str, SetupStep]:
    return {step.name: step for step in report.steps}


def test_the_setup_and_its_runner_honour_their_interfaces(tmp_path: Path) -> None:
    assert isinstance(make(tmp_path), ContributorSetupInterface)
    assert isinstance(SubprocessRunner(), CommandRunnerInterface)


# --------------------------------------------------------------------------- prerequisites


@pytest.mark.parametrize("missing", ["git", "uv"])
def test_a_missing_tool_stops_setup_before_anything_runs(tmp_path: Path, missing: str) -> None:
    runner = ScriptedRunner()
    setup = make(tmp_path, runner, which=lambda tool: None if tool == missing else "/bin/x")
    report = setup.run()
    assert [s.status for s in report.steps] == ["failed"] and not report.ok
    assert missing in report.steps[0].detail
    assert runner.calls == []
    assert ("astral.sh" in report.steps[0].detail) == (missing == "uv")


def test_an_old_python_stops_setup(tmp_path: Path) -> None:
    report = make(tmp_path, python=(3, 11)).run()
    assert not report.ok and "3.12+" in report.steps[0].detail and "3.11" in report.steps[0].detail


# ------------------------------------------------------------------------------------ sync


def test_sync_is_done_when_uv_changed_something_and_unchanged_when_it_only_audited(
    tmp_path: Path,
) -> None:
    changed = ScriptedRunner({("uv", "sync"): CommandResult(0, "", "Installed 4 packages in 1s")})
    assert by_name(make(tmp_path, changed).run())["environment sync"].status == "done"
    audited = ScriptedRunner({("uv", "sync"): CommandResult(0, "", "Audited 90 packages in 2ms")})
    assert by_name(make(tmp_path, audited).run())["environment sync"].status == "unchanged"


def test_a_failed_sync_is_reported_with_the_end_of_its_output(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        {("uv", "sync"): CommandResult(2, "", "\n".join(f"line {n}" for n in range(20)))}
    )
    step = by_name(make(tmp_path, runner).run())["environment sync"]
    assert step.status == "failed" and "line 19" in step.detail and "line 5" not in step.detail


def test_a_failed_sync_with_no_output_still_says_something(tmp_path: Path) -> None:
    runner = ScriptedRunner({("uv", "sync"): CommandResult(9)})
    assert by_name(make(tmp_path, runner).run())["environment sync"].detail == "exit 9"


# ---------------------------------------------------------------------------- framework hooks


def install_calls(runner: ScriptedRunner) -> list[tuple[str, ...]]:
    return [call for call in runner.calls if call[:3] == ("uv", "run", "pre-commit")]


def test_a_repository_without_the_framework_is_skipped(tmp_path: Path) -> None:
    step = by_name(make(tmp_path, stages=SequencedInspector({})).run())[
        "pre-commit framework hooks"
    ]
    assert step.status == "skipped" and ".pre-commit-config.yaml" in step.detail


def test_hooks_already_installed_are_left_alone(tmp_path: Path) -> None:
    runner = ScriptedRunner()
    step = by_name(make(tmp_path, runner).run())["pre-commit framework hooks"]
    assert step.status == "unchanged" and install_calls(runner) == []


def test_all_three_stages_are_installed_when_core_hookspath_is_unset(tmp_path: Path) -> None:
    runner = ScriptedRunner({("git", "config"): CommandResult(1)})
    setup = make(
        tmp_path,
        runner,
        stages=SequencedInspector(STAGES_MISSING, STAGES_INSTALLED),
    )
    step = by_name(setup.run())["pre-commit framework hooks"]
    assert step.status == "done"
    (call,) = install_calls(runner)
    assert [call[i + 1] for i, word in enumerate(call) if word == "--hook-type"] == [
        "pre-commit",
        "commit-msg",
        "pre-push",
    ]
    assert not any("--unset" in c for c in runner.calls)


def test_a_rerun_lifts_our_hookspath_for_the_install_and_puts_it_back(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        {
            ("git", "config", "--local", "--get"): CommandResult(0, ".githooks\n"),
            ("git", "config", "--get"): CommandResult(0, ".githooks\n"),
        }
    )
    setup = make(
        tmp_path,
        runner,
        stages=SequencedInspector(STAGES_MISSING, STAGES_INSTALLED),
    )
    assert by_name(setup.run())["pre-commit framework hooks"].status == "done"
    order = [
        c
        for c in runner.calls
        if "--unset" in c
        or c[:3] == ("uv", "run", "pre-commit")
        or c[-2:] == ("core.hooksPath", ".githooks")
    ]
    assert [c[3] if "--unset" in c else c[0] for c in order] == ["--unset", "uv", "git"]


def test_hookspath_is_restored_even_when_the_install_blows_up(tmp_path: Path) -> None:
    def explode() -> CommandResult:
        raise RuntimeError("boom")

    runner = ScriptedRunner(
        {
            ("git", "config", "--local", "--get"): CommandResult(0, ".githooks\n"),
            ("git", "config", "--get"): CommandResult(0, ".githooks\n"),
            ("uv", "run", "pre-commit"): explode,
        }
    )
    setup = make(tmp_path, runner, stages=SequencedInspector(STAGES_MISSING))
    with pytest.raises(RuntimeError, match="boom"):
        setup.run()
    assert runner.calls[-1] == ("git", "config", "--local", "core.hooksPath", ".githooks")


def test_a_global_hookspath_is_named_and_nothing_is_changed(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        {
            ("git", "config", "--local", "--get"): CommandResult(1),
            ("git", "config", "--get"): CommandResult(0, "/home/me/.githooks\n"),
        }
    )
    step = by_name(make(tmp_path, runner, stages=SequencedInspector(STAGES_MISSING)).run())[
        "pre-commit framework hooks"
    ]
    assert (
        step.status == "failed" and "/home/me/.githooks" in step.detail and "global" in step.detail
    )
    assert install_calls(runner) == []


def test_a_local_hookspath_that_is_not_ours_is_never_overwritten(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        {
            ("git", "config", "--local", "--get"): CommandResult(0, ".husky\n"),
            ("git", "config", "--get"): CommandResult(0, ".husky\n"),
        }
    )
    step = by_name(make(tmp_path, runner, stages=SequencedInspector(STAGES_MISSING)).run())[
        "pre-commit framework hooks"
    ]
    assert (
        step.status == "failed"
        and "'.husky'" in step.detail
        and "does not overwrite" in step.detail
    )
    assert install_calls(runner) == [] and not any("--unset" in c for c in runner.calls)


@pytest.mark.parametrize("code", [0, 1])
def test_an_install_that_left_hooks_missing_is_failed_whatever_the_command_said(
    tmp_path: Path, code: int
) -> None:
    runner = ScriptedRunner(
        {
            ("git", "config"): CommandResult(1),
            ("uv", "run", "pre-commit"): CommandResult(code, "", "no thanks"),
        }
    )
    step = by_name(make(tmp_path, runner, stages=SequencedInspector(STAGES_MISSING)).run())[
        "pre-commit framework hooks"
    ]
    assert step.status == "failed" and "commit-msg" in step.detail
    assert ("no thanks" in step.detail) == (code != 0)


# ------------------------------------------------------------------- provenance and wiring


def test_provenance_hooks_unchanged_when_nothing_moved(tmp_path: Path) -> None:
    assert (
        by_name(make(tmp_path).run())["provenance hooks (vibey-gh install)"].status == "unchanged"
    )


def test_provenance_hooks_report_what_changed_and_that_nothing_was_committed(
    tmp_path: Path,
) -> None:
    states = iter([CommandResult(0, ""), CommandResult(0, " M .gitattributes\n?? x\nM\n")])
    runner = ScriptedRunner({("git", "status"): lambda: next(states)})
    setup = make(
        tmp_path,
        runner,
        installer=lambda cfg: [Action("commit-msg", "updated"), Action("pre-push", "unchanged")],
    )
    step = by_name(setup.run())["provenance hooks (vibey-gh install)"]
    assert step.status == "done"
    assert "commit-msg: updated" in step.detail and "pre-push" not in step.detail
    assert ".gitattributes" in step.detail and "nothing was committed" in step.detail


def test_a_hook_that_changed_without_touching_a_tracked_file_says_only_that(tmp_path: Path) -> None:
    setup = make(tmp_path, installer=lambda cfg: [Action("pre-push", "installed")])
    step = by_name(setup.run())["provenance hooks (vibey-gh install)"]
    assert step.status == "done" and step.detail == "pre-push: installed"


def test_tracked_changes_alone_are_enough_to_say_done(tmp_path: Path) -> None:
    states = iter([CommandResult(0, ""), CommandResult(0, " M a.yml\n")])
    runner = ScriptedRunner({("git", "status"): lambda: next(states)})
    step = by_name(make(tmp_path, runner).run())["provenance hooks (vibey-gh install)"]
    assert step.status == "done" and "a.yml" in step.detail


def test_the_wiring_is_read_back_from_the_same_check_vibey_gh_check_makes(tmp_path: Path) -> None:
    seen: list[bool] = []

    def checker(cfg: GhConfig, local: bool) -> tuple[bool, list[str]]:
        seen.append(local)
        return False, ["core.hooksPath is not .githooks — run `vibey-gh setup`", "second problem"]

    report = make(tmp_path, checker=checker).run()
    step = by_name(report)["wiring (vibey-gh check, hook half)"]
    assert seen == [True] and step.status == "failed" and "second problem" in step.detail
    assert not report.ok


# ------------------------------------------------------------------------------ PostgreSQL

PG = "PostgreSQL for the test suite"
PSQL = ("psql",)


def test_a_reachable_role_that_can_create_databases_is_done(tmp_path: Path) -> None:
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    step = by_name(make(tmp_path, runner).run())[PG]
    assert (
        step.status == "unchanged"
        and "vibey_test" in step.detail
        and "localhost:5432" in step.detail
    )
    assert runner.envs[runner.calls.index(next(c for c in runner.calls if c[0] == "psql"))] == {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "vibey_test",
        "PGCONNECT_TIMEOUT": "5",
        "PGUSER": "dev",
    }


def test_the_dsn_comes_from_the_environment_and_the_password_never_reaches_argv(
    tmp_path: Path,
) -> None:
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    dsn = "postgresql://ci%40x:p%40ss@db.example:6543/mytests"
    make(tmp_path, runner, environ={"VIBEY_TEST_DATABASE_URL": dsn}).run()
    call = next(c for c in runner.calls if c[0] == "psql")
    env = runner.envs[runner.calls.index(call)]
    assert env == {
        "PGHOST": "db.example",
        "PGPORT": "6543",
        "PGDATABASE": "mytests",
        "PGCONNECT_TIMEOUT": "5",
        "PGUSER": "ci@x",
        "PGPASSWORD": "p@ss",
    }
    assert not any("p@ss" in word or "p%40ss" in word for word in call)


def test_a_bare_dsn_falls_back_to_the_documented_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import getpass

    monkeypatch.setattr(getpass, "getuser", lambda: "fallback")
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    make(tmp_path, runner, environ={"VIBEY_TEST_DATABASE_URL": "postgresql://"}).run()
    env = runner.envs[runner.calls.index(next(c for c in runner.calls if c[0] == "psql"))]
    assert env is not None and env["PGHOST"] == "localhost" and env["PGDATABASE"] == "vibey_test"
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    make(tmp_path, runner, environ={}).run()
    env = runner.envs[runner.calls.index(next(c for c in runner.calls if c[0] == "psql"))]
    assert env is not None and env["PGUSER"] == "fallback"


def test_psql_is_told_never_to_prompt_for_a_password(tmp_path: Path) -> None:
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    make(tmp_path, runner).run()
    assert "-w" in next(call for call in runner.calls if call[0] == "psql")


def test_a_role_that_cannot_create_databases_is_failed_with_the_commands_to_fix_it(
    tmp_path: Path,
) -> None:
    step = by_name(make(tmp_path, ScriptedRunner({PSQL: CommandResult(0, "f\n")})).run())[PG]
    assert step.status == "failed" and "cannot create databases" in step.detail
    assert "createuser --createdb" in step.detail and "~/.pgpass" in step.detail


def test_a_refused_connection_is_failed_with_psqls_own_first_line(tmp_path: Path) -> None:
    runner = ScriptedRunner({PSQL: CommandResult(2, "", "psql: error: connection refused\nmore")})
    step = by_name(make(tmp_path, runner).run())[PG]
    assert step.status == "failed" and step.detail.startswith("psql: error: connection refused")
    assert "more" not in step.detail.splitlines()[0]


def test_psql_failing_with_no_words_still_fails_plainly(tmp_path: Path) -> None:
    step = by_name(make(tmp_path, ScriptedRunner({PSQL: CommandResult(2)})).run())[PG]
    assert step.status == "failed" and step.detail.startswith("psql failed")


def test_without_psql_an_open_port_is_unknown_not_done(tmp_path: Path) -> None:
    step = by_name(make(tmp_path, which=lambda t: None if t == "psql" else "/bin/x").run())[PG]
    assert step.status == "unknown" and "were not checked" in step.detail


def test_without_psql_a_closed_port_is_failed(tmp_path: Path) -> None:
    setup = make(
        tmp_path, which=lambda t: None if t == "psql" else "/bin/x", connect=lambda h, p: False
    )
    step = by_name(setup.run())[PG]
    assert step.status == "failed" and "nothing is listening on localhost:5432" in step.detail


def test_postgres_flag_installs_the_server_first_and_never_creates_a_role(tmp_path: Path) -> None:
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    report = make(tmp_path, runner).run(postgres=True)
    assert by_name(report)[PG].status == "done"
    assert ("uv", "run", "vibey", "install", "--postgres") in runner.calls
    assert runner.calls.index(("uv", "run", "vibey", "install", "--postgres")) < runner.calls.index(
        next(c for c in runner.calls if c[0] == "psql")
    )
    assert not any("createuser" in " ".join(c) or "pgpass" in " ".join(c) for c in runner.calls)


def test_a_failed_server_install_is_failed(tmp_path: Path) -> None:
    runner = ScriptedRunner({("uv", "run", "vibey", "install"): CommandResult(1, "", "no brew")})
    step = by_name(make(tmp_path, runner).run(postgres=True))[PG]
    assert step.status == "failed" and "no brew" in step.detail


# --------------------------------------------------------------------------------- doctor


def test_doctor_is_shown_in_full_and_never_fails_setup(tmp_path: Path) -> None:
    runner = ScriptedRunner(
        {
            ("uv", "run", "vibey", "doctor"): CommandResult(1, "FAIL sabbath  no location\n", ""),
            PSQL: CommandResult(0, "t\n"),
        }
    )
    report = make(tmp_path, runner).run()
    step = by_name(report)["vibey doctor"]
    assert step.status == "advisory" and "exit 1" in step.detail and "FAIL sabbath" in step.detail
    assert report.ok


def test_doctor_with_no_output_says_so_and_skip_doctor_skips_it(tmp_path: Path) -> None:
    assert "(no output)" in by_name(make(tmp_path).run())["vibey doctor"].detail
    runner = ScriptedRunner()
    step = by_name(make(tmp_path, runner).run(doctor=False))["vibey doctor"]
    assert step.status == "skipped" and ("uv", "run", "vibey", "doctor") not in runner.calls


# ----------------------------------------------------------------------------------- check


def test_check_reports_state_and_changes_and_runs_nothing(tmp_path: Path) -> None:
    runner = ScriptedRunner({PSQL: CommandResult(0, "t\n")})
    setup = make(tmp_path, runner, stages=SequencedInspector(STAGES_MISSING))
    report = setup.check()
    steps = by_name(report)
    assert steps["pre-commit framework hooks"].status == "failed"
    assert "commit-msg" in steps["pre-commit framework hooks"].detail
    assert (
        steps["environment sync"].status == "skipped" and steps["vibey doctor"].status == "skipped"
    )
    assert all(call[0] == "psql" for call in runner.calls)


def test_check_on_a_healthy_clone_is_ready_and_on_a_repo_without_the_framework_skips_it(
    tmp_path: Path,
) -> None:
    assert make(tmp_path, ScriptedRunner({PSQL: CommandResult(0, "t\n")})).check().ok
    steps = by_name(make(tmp_path, stages=SequencedInspector({})).check())
    assert steps["pre-commit framework hooks"].status == "skipped"


def test_check_stops_at_a_missing_prerequisite_only_by_reporting_it(tmp_path: Path) -> None:
    report = make(tmp_path, which=lambda t: None).check()
    assert not report.ok and report.steps[0].status == "failed"


# ---------------------------------------------------------------------------------- render


def test_render_indents_a_multiline_detail_and_ends_with_the_verdict(tmp_path: Path) -> None:
    setup = make(tmp_path)
    lines = setup.render(
        SetupReport((SetupStep("a", "failed", "first\nsecond"), SetupStep("b", "done")))
    )
    assert lines[:3] == ["  [failed] a: first", "      second", "  [done] b"]
    assert lines[-1].startswith("vibey-gh setup: not ready")
    assert setup.render(SetupReport((SetupStep("b", "done"),)))[-1] == "vibey-gh setup: ready"


# ------------------------------------------------------------------------------- the runner


def test_the_real_runner_runs_a_command_merges_env_and_reports_a_missing_binary(
    tmp_path: Path,
) -> None:
    runner = SubprocessRunner()
    done = runner.run(
        ["sh", "-c", "echo out; echo err >&2; echo $SETUP_TEST; exit 3"],
        tmp_path,
        {"SETUP_TEST": "yes"},
    )
    assert (
        done.returncode == 3
        and done.stdout.split() == ["out", "yes"]
        and done.stderr.strip() == "err"
    )
    assert done.output.count("err") == 1
    missing = runner.run(["definitely-not-a-binary-xyz"], tmp_path)
    assert missing.returncode == 127 and missing.output


def test_the_default_port_probe_sees_a_listener_and_a_closed_port() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        assert ContributorSetup._tcp_open("127.0.0.1", port) is True
    assert ContributorSetup._tcp_open("127.0.0.1", port) is False


# ------------------------------------------------------------------------------------ the CLI


class FakeSetup:
    def __init__(self, ok: bool) -> None:
        self.ok = ok
        self.calls: list[tuple[str, ...]] = []

    def run(self, *, postgres: bool = False, doctor: bool = True) -> SetupReport:
        self.calls.append(("run", str(postgres), str(doctor)))
        return SetupReport((SetupStep("s", "done" if self.ok else "failed"),))

    def check(self) -> SetupReport:
        self.calls.append(("check",))
        return SetupReport((SetupStep("s", "done" if self.ok else "failed"),))

    def render(self, report: SetupReport) -> list[str]:
        return ["rendered"]


@pytest.mark.parametrize(
    "flags, expected, ok, code",
    [
        ([], ("run", "False", "True"), True, 0),
        (["--postgres", "--skip-doctor"], ("run", "True", "False"), True, 0),
        (["--check"], ("check",), False, 1),
    ],
)
def test_the_subcommand_passes_its_flags_through_and_exits_with_the_report(
    flags: list[str],
    expected: tuple[str, ...],
    ok: bool,
    code: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = argparse.Namespace(
        postgres="--postgres" in flags,
        skip_doctor="--skip-doctor" in flags,
        check="--check" in flags,
    )
    fake = FakeSetup(ok)
    assert cli._setup(args, fake) == code
    assert fake.calls == [expected] and capsys.readouterr().out == "rendered\n"


def test_setup_is_a_registered_subcommand(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[argparse.Namespace] = []
    monkeypatch.setattr(cli, "_setup", lambda args: seen.append(args) or 0)
    assert cli.main(["setup", "--check", "--postgres", "--skip-doctor"]) == 0
    assert (seen[0].check, seen[0].postgres, seen[0].skip_doctor) == (True, True, True)
    with pytest.raises(SystemExit):
        cli.main(["setup", "--help"])
    assert "contributor environment" in " ".join(capsys.readouterr().out.split())


def test_the_default_wiring_builds_a_real_setup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    built: list[object] = []

    class Spy(FakeSetup):
        def __init__(self, cfg: object) -> None:
            super().__init__(True)
            built.append(cfg)

    monkeypatch.setattr(cli, "ContributorSetup", Spy)
    assert cli._setup(argparse.Namespace(postgres=False, skip_doctor=True, check=False)) == 0
    assert len(built) == 1
