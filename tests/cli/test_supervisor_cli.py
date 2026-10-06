# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey supervisor` and its doctor lines (#1189)."""

import plistlib
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from typer.testing import CliRunner

import vibey.cli.supervisor as supervisor_module
from vibey.cli.interfaces.supervisor_interface import SupervisorCommandInterface
from vibey.cli.main import app
from vibey.cli.supervisor import ENV_TEMPLATE, STATE_ENV_TEMPLATE, SupervisorCommand
from vibey.infrastructure.supervisor import SupervisorHost

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


class _Manager:
    """The service manager: `running` names the labels it reports running."""

    def __init__(self, running: set[str] | None = None, stopped: set[str] | None = None) -> None:
        self.running = running or set()
        self.stopped = stopped or set()
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.calls.append(tuple(argv))
        label = argv[-1].split("/")[-1].removesuffix(".service")
        if label in self.running:
            return 0, "active" if argv[0] == "systemctl" else "state = running"
        if label in self.stopped:
            return (3, "failed") if argv[0] == "systemctl" else (0, "state = not running")
        return (3, "inactive") if argv[0] == "systemctl" else (113, "")


class _Exec:
    def __init__(self, error: OSError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, list[str], dict[str, str]]] = []

    def __call__(self, file: str, args: list[str], env: Mapping[str, str]) -> None:
        self.calls.append((file, args, dict(env)))
        if self.error is not None:
            raise self.error


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    (checkout / "scripts" / "triaged_delivery.py").write_text("# the bridge\n")
    return checkout


def _command(
    tmp_path: Path,
    manager: _Manager | None = None,
    *,
    which: str | None = "/opt/vibey/bin/vibey",
    execute: _Exec | None = None,
    roots: tuple[Path, ...] = (Path("/volatile"),),
) -> SupervisorCommand:
    home = tmp_path / "home"

    def host(platform: str) -> SupervisorHost:
        return SupervisorHost(
            platform,
            home=home,
            environ={},
            uid=501,
            run=manager or _Manager(),
            temp_roots=lambda: roots,
        )

    return SupervisorCommand(
        host_factory=host,
        which=lambda name: which,
        python="/opt/vibey/bin/python",
        environ={"PATH": "/opt/vibey/bin:/usr/bin", "INHERITED": "1", "SHARED": "outer"},
        execute=execute or _Exec(),
        root=tmp_path,
    )


def test_the_command_is_its_interface(tmp_path: Path) -> None:
    # The interface is not runtime-checkable (as SabbathCommandInterface is not); the
    # class inherits it, so its MRO names it.
    assert SupervisorCommandInterface in type(_command(tmp_path)).__mro__


# --- install ----------------------------------------------------------------------------


def test_install_writes_both_launchd_agents_the_env_template_and_the_log_dir(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None)

    assert code == 0
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    worker = plistlib.loads((agents / "dev.vibey.worker.plist").read_bytes())
    delivery = plistlib.loads((agents / "dev.vibey.delivery.plist").read_bytes())
    env_file = tmp_path / "home" / "Library" / "Application Support" / "vibey" / "supervisor.env"
    assert worker["ProgramArguments"] == [
        "/opt/vibey/bin/vibey",
        "supervisor",
        "exec",
        "--env-file",
        str(env_file),
        "--",
        "/opt/vibey/bin/vibey",
        "worker",
        "--all-projects",
    ]
    assert worker["KeepAlive"] == {"SuccessfulExit": False}
    assert worker["EnvironmentVariables"] == {"PATH": "/opt/vibey/bin:/usr/bin"}
    assert delivery["ProgramArguments"][6:] == [
        "/opt/vibey/bin/python",
        f"{repo}/scripts/triaged_delivery.py",
        "--repo",
        str(repo),
        "--interval",
        "300",
    ]
    assert env_file.read_text() == ENV_TEMPLATE
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert (tmp_path / "home" / "Library" / "Logs" / "vibey").is_dir()

    out = capsys.readouterr().out
    assert "(created from the template: fill it in)" in out
    assert "launchctl bootstrap gui/501" in out
    assert "note:" not in out


def test_install_keeps_an_env_file_that_exists(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / "declared.env"
    env_file.write_text("VIBEY_PG_URL=postgresql://example\n")
    (repo / "vibey.toml").write_text(f'[supervisor]\nenv_file = "{env_file}"\n')

    assert _command(tmp_path).install(platform="systemd", repo=repo, out=None, config=None) == 0

    assert env_file.read_text() == "VIBEY_PG_URL=postgresql://example\n"
    units = tmp_path / "home" / ".config" / "systemd" / "user"
    assert "Restart=on-failure" in (units / "dev.vibey.worker.service").read_text()
    out = capsys.readouterr().out
    assert "(kept as it was)" in out
    assert (
        "systemctl --user enable --now dev.vibey.worker.service dev.vibey.delivery.service" in out
    )


def test_install_to_another_directory_says_where_the_manager_looks(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "review"
    assert _command(tmp_path).install(platform="launchd", repo=repo, out=out_dir, config=None) == 0
    assert (out_dir / "dev.vibey.worker.plist").is_file()
    assert "note: the service manager reads" in capsys.readouterr().out


def test_install_supervises_the_worker_alone_without_a_bridge_to_run(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    config = tmp_path / "vibey.toml"
    config.write_text("[supervisor]\ndelivery = false\n")
    assert _command(tmp_path).install(platform="launchd", repo=bare, out=None, config=config) == 0
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    assert sorted(p.name for p in agents.iterdir()) == ["dev.vibey.worker.plist"]


def test_install_refuses_an_unknown_platform(tmp_path: Path, repo: Path) -> None:
    assert _command(tmp_path).install(platform="upstart", repo=repo, out=None, config=None) == 2


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("[supervisor]\nlogdir = 'x'\n", "unknown keys: logdir"),
        ("[supervisor]\ndelivery_interval_seconds = 0\n", "delivery_interval_seconds"),
    ],
)
def test_install_refuses_a_setting_no_service_could_run_with(
    tmp_path: Path, repo: Path, body: str, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "vibey.toml").write_text(body)
    assert _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None) == 78
    assert message in capsys.readouterr().err


def test_install_refuses_when_vibey_cannot_be_found(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command = _command(tmp_path, which=None)
    assert command.install(platform="launchd", repo=repo, out=None, config=None) == 78
    assert "set [supervisor] vibey" in capsys.readouterr().err


def test_install_refuses_a_bridge_it_cannot_find(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    code = _command(tmp_path).install(platform="launchd", repo=elsewhere, out=None, config=None)
    assert code == 78
    assert "delivery = false" in capsys.readouterr().err


def test_install_refuses_logs_on_volatile_storage(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "vibey.toml").write_text('[supervisor]\nlog_dir = "/volatile/vibey/logs"\n')
    assert _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None) == 78
    err = capsys.readouterr().err
    assert "/volatile/vibey/logs is under /volatile, which a reboot empties" in err
    assert "[supervisor] log_dir" in err
    assert not (tmp_path / "home" / "Library" / "LaunchAgents").exists()


def test_install_sees_through_a_link_into_volatile_storage(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (tmp_path / "looks-durable").symlink_to(scratch)
    (repo / "vibey.toml").write_text(f'[supervisor]\nlog_dir = "{tmp_path}/looks-durable/logs"\n')
    command = _command(tmp_path, roots=(scratch,))
    assert command.install(platform="launchd", repo=repo, out=None, config=None) == 78
    assert "which a reboot empties" in capsys.readouterr().err


def test_install_sees_a_path_named_under_a_root_that_resolves_elsewhere(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (tmp_path / "volatile-link").symlink_to(real)
    root = tmp_path / "volatile-link"
    (repo / "vibey.toml").write_text(f'[supervisor]\nlog_dir = "{root}/logs"\n')
    command = _command(tmp_path, roots=(root,))
    assert command.install(platform="launchd", repo=repo, out=None, config=None) == 78
    assert f"is under {root}" in capsys.readouterr().err


def test_install_refuses_a_vibey_inside_a_linked_worktree(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lane = tmp_path / "lane"
    (lane / ".venv" / "bin").mkdir(parents=True)
    (lane / ".git").write_text("gitdir: /somewhere/else\n")
    command = _command(tmp_path, which=str(lane / ".venv" / "bin" / "vibey"))
    assert command.install(platform="launchd", repo=repo, out=None, config=None) == 78
    err = capsys.readouterr().err
    assert f"inside the linked worktree {lane}" in err
    assert "[supervisor] vibey" in err


# --- the state sync (ADR-0086) ----------------------------------------------------------


def test_install_with_the_state_sync_gives_it_its_own_private_env_file(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "vibey.toml").write_text(
        "[supervisor]\nstate_sync = true\nstate_sync_interval_seconds = 60\n"
    )
    assert _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None) == 0

    support = tmp_path / "home" / "Library" / "Application Support" / "vibey"
    state_env = support / "state-sync.env"
    assert state_env.read_text() == STATE_ENV_TEMPLATE
    assert stat.S_IMODE(state_env.stat().st_mode) == 0o600
    assert (support / "supervisor.env").read_text() == ENV_TEMPLATE
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    assert sorted(p.name for p in agents.iterdir()) == [
        "dev.vibey.delivery.plist",
        "dev.vibey.state-sync.plist",
        "dev.vibey.worker.plist",
    ]
    sync = plistlib.loads((agents / "dev.vibey.state-sync.plist").read_bytes())
    assert sync["ProgramArguments"] == [
        "/opt/vibey/bin/vibey",
        "supervisor",
        "exec",
        "--env-file",
        str(state_env),
        "--",
        "/opt/vibey/bin/vibey",
        "state",
        "sync",
        "--every",
        "60",
    ]
    out = capsys.readouterr().out
    assert f"environment: {state_env} (created from the template: fill it in)" in out
    assert "wrote " + str(agents / "dev.vibey.state-sync.plist") in out


def test_install_keeps_a_declared_state_env_file_and_says_nothing_of_it(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state_env = tmp_path / "secrets" / "state.env"
    state_env.parent.mkdir()
    state_env.write_text("VIBEY_STATE_PG_URL=postgresql://example\n")
    (repo / "vibey.toml").write_text(
        f'[supervisor]\nstate_sync = true\nstate_sync_env_file = "{state_env}"\n'
    )
    assert _command(tmp_path).install(platform="systemd", repo=repo, out=None, config=None) == 0

    assert state_env.read_text() == "VIBEY_STATE_PG_URL=postgresql://example\n"
    units = tmp_path / "home" / ".config" / "systemd" / "user"
    unit = (units / "dev.vibey.state-sync.service").read_text()
    assert "--env-file" in unit and str(state_env) in unit
    assert not (tmp_path / "home" / ".config" / "vibey" / "state-sync.env").exists()
    out = capsys.readouterr().out
    assert str(state_env) not in out
    assert "dev.vibey.state-sync.service" in out


def test_install_without_the_state_sync_makes_no_state_env_file(tmp_path: Path, repo: Path) -> None:
    assert _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None) == 0
    support = tmp_path / "home" / "Library" / "Application Support" / "vibey"
    assert sorted(p.name for p in support.iterdir()) == ["supervisor.env"]


def test_install_refuses_a_state_env_file_on_volatile_storage(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (repo / "vibey.toml").write_text(
        '[supervisor]\nstate_sync = true\nstate_sync_env_file = "/volatile/state.env"\n'
    )
    assert _command(tmp_path).install(platform="launchd", repo=repo, out=None, config=None) == 78
    err = capsys.readouterr().err
    assert "/volatile/state.env is under /volatile, which a reboot empties" in err
    assert "[supervisor] state_sync_env_file" in err
    assert not (tmp_path / "home" / "Library" / "LaunchAgents").exists()


# --- status and doctor ------------------------------------------------------------------


def _installed(tmp_path: Path, repo: Path, manager: _Manager, platform: str = "launchd") -> None:
    assert (
        _command(tmp_path, manager).install(platform=platform, repo=repo, out=None, config=None)
        == 0
    )


def test_status_is_zero_only_when_every_service_runs(
    tmp_path: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manager = _Manager(running={"dev.vibey.worker", "dev.vibey.delivery"})
    _installed(tmp_path, repo, manager)
    capsys.readouterr()

    assert _command(tmp_path, manager).status(platform="launchd", config=None) == 0
    assert "worker    running" in capsys.readouterr().out

    manager.running.discard("dev.vibey.delivery")
    assert _command(tmp_path, manager).status(platform="launchd", config=None) == 1


def test_status_names_what_is_not_installed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _command(tmp_path).status(platform="systemd", config=None) == 1
    assert "not installed" in capsys.readouterr().out


def test_status_refuses_an_unreadable_table(tmp_path: Path) -> None:
    config = tmp_path / "vibey.toml"
    config.write_text("[supervisor]\nrequired = 'yes'\n")
    assert _command(tmp_path).status(platform="launchd", config=config) == 78


def test_doctor_passes_running_services(tmp_path: Path, repo: Path) -> None:
    manager = _Manager(running={"dev.vibey.worker", "dev.vibey.delivery"})
    _installed(tmp_path, repo, manager, platform=supervisor_module.DEFAULT_PLATFORM)
    lines, ok = _command(tmp_path, manager).doctor_lines()
    assert ok
    assert [line.split()[0] for line in lines] == ["PASS", "PASS"]


def test_doctor_warns_out_loud_when_nothing_is_supervised(tmp_path: Path) -> None:
    lines, ok = _command(tmp_path).doctor_lines()
    assert ok
    assert lines[0].startswith("WARN supervisor-worker")
    assert "not installed: nothing restarts it after a crash or a reboot" in lines[0]


def test_doctor_fails_a_required_supervisor_that_is_missing_or_stopped(
    tmp_path: Path, repo: Path
) -> None:
    manager = _Manager(stopped={"dev.vibey.worker"})
    _installed(tmp_path, repo, manager, platform=supervisor_module.DEFAULT_PLATFORM)
    (tmp_path / "vibey.toml").write_text("[supervisor]\nrequired = true\n")

    lines, ok = _command(tmp_path, manager).doctor_lines()

    assert not ok
    assert lines[0].startswith("FAIL supervisor-worker")
    assert "installed but stopped" in lines[0]
    assert lines[1].startswith("FAIL supervisor-delivery")


def test_doctor_warns_on_a_stopped_service_it_does_not_require(tmp_path: Path, repo: Path) -> None:
    manager = _Manager(stopped={"dev.vibey.worker", "dev.vibey.delivery"})
    _installed(tmp_path, repo, manager, platform=supervisor_module.DEFAULT_PLATFORM)
    lines, ok = _command(tmp_path, manager).doctor_lines()
    assert ok
    assert lines[0].startswith("WARN supervisor-worker")


def test_doctor_fails_an_unreadable_table(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text("[supervisor]\nnope = 1\n")
    lines, ok = _command(tmp_path).doctor_lines()
    assert not ok
    assert lines == ["FAIL supervisor           [supervisor] has unknown keys: nope"]


def test_the_real_host_is_built_from_this_machine(tmp_path: Path) -> None:
    lines, ok = SupervisorCommand(root=tmp_path).doctor_lines()
    assert isinstance(ok, bool)
    assert lines


def test_the_real_service_manager_runner_returns_code_and_stdout() -> None:
    assert SupervisorCommand.service_manager((sys.executable, "-c", "print('ok')")) == (0, "ok\n")


# --- exec -------------------------------------------------------------------------------


def test_exec_replaces_itself_with_the_command_in_the_declared_environment(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "supervisor.env"
    env_file.write_text("# comment\nSHARED=declared\nVIBEY_PG_URL='postgresql://x'\n")
    execute = _Exec()

    code = _command(tmp_path, execute=execute).exec_(
        env_file, ["vibey", "worker", "--all-projects"]
    )

    assert code == 0
    ((file, args, env),) = execute.calls
    assert (file, args) == ("vibey", ["vibey", "worker", "--all-projects"])
    assert env["SHARED"] == "declared"
    assert env["INHERITED"] == "1"
    assert env["VIBEY_PG_URL"] == "postgresql://x"


def test_exec_without_a_command_is_a_usage_error(tmp_path: Path) -> None:
    assert _command(tmp_path).exec_(tmp_path / "e", []) == 2


def test_exec_refuses_a_missing_env_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _command(tmp_path).exec_(tmp_path / "missing.env", ["true"]) == 78
    assert "creates it from a template" in capsys.readouterr().err


def test_exec_refuses_a_malformed_env_file_without_quoting_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / "bad.env"
    env_file.write_text("API KEY=hunter2\n")
    assert _command(tmp_path).exec_(env_file, ["true"]) == 78
    err = capsys.readouterr().err
    assert "line 1" in err
    assert "hunter2" not in err


def test_exec_says_when_the_command_cannot_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / "ok.env"
    env_file.write_text("")
    execute = _Exec(FileNotFoundError(2, "No such file or directory"))
    assert _command(tmp_path, execute=execute).exec_(env_file, ["nope"]) == 127
    assert "cannot run nope" in capsys.readouterr().err


# --- the command line -------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def install(self, **kwargs: object) -> int:
        self.calls.append(("install", kwargs))
        return 0

    def status(self, **kwargs: object) -> int:
        self.calls.append(("status", kwargs))
        return 1

    def exec_(self, env_file: Path, argv: Sequence[str]) -> int:
        self.calls.append(("exec", (env_file, list(argv))))
        return 78

    def doctor_lines(self) -> tuple[list[str], bool]:
        return ["FAIL supervisor-worker stub"], False


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    recording = _Recorder()
    monkeypatch.setattr(supervisor_module, "SUPERVISOR", recording)
    return recording


def test_the_subcommands_reach_the_command(recorder: _Recorder) -> None:
    assert runner.invoke(app, ["supervisor", "install", "--platform", "systemd"]).exit_code == 0
    assert runner.invoke(app, ["supervisor", "status"]).exit_code == 1
    res = runner.invoke(
        app,
        ["supervisor", "exec", "--env-file", "e.env", "--", "vibey", "worker", "--all-projects"],
    )
    assert res.exit_code == 78
    assert recorder.calls[0] == (
        "install",
        {"platform": "systemd", "repo": Path("."), "out": None, "config": None},
    )
    assert recorder.calls[1][0] == "status"
    assert recorder.calls[2] == ("exec", (Path("e.env"), ["vibey", "worker", "--all-projects"]))


def test_exec_with_nothing_after_the_separator_reaches_the_command(recorder: _Recorder) -> None:
    runner.invoke(app, ["supervisor", "exec", "--env-file", "e.env"])
    assert recorder.calls == [("exec", (Path("e.env"), []))]
