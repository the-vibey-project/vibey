# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared supervisor's host half (#1189): settings, places, units and states."""

import plistlib
from collections.abc import Sequence
from pathlib import Path

import pytest

from vibey.domain.supervisor import SupervisedService, SupervisorSettings
from vibey.infrastructure.driver.interfaces.timer_units_interface import (
    TimerUnitRendererInterface,
)
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.interfaces.supervisor_interface import (
    SupervisorHostInterface,
    SupervisorSettingsLoaderInterface,
)
from vibey.infrastructure.supervisor import SupervisorHost, SupervisorSettingsLoader

SERVICE = SupervisedService(
    name="worker",
    label="dev.vibey.worker",
    argv=("/opt/vibey/bin/vibey", "supervisor", "exec", "--", "vibey", "worker", "a & b"),
    working_directory="/srv/git/vibey",
    log_path="/home/op/Library/Logs/vibey/worker.log",
)


class _Runner:
    def __init__(self, answer: tuple[int, str] | Exception) -> None:
        self.answer = answer
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        self.calls.append(tuple(argv))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def _host(
    platform: str,
    run: _Runner | None = None,
    environ: dict[str, str] | None = None,
) -> SupervisorHost:
    return SupervisorHost(
        platform,
        home=Path("/home/op"),
        environ=environ or {},
        uid=501,
        run=run or _Runner((0, "")),
        temp_roots=lambda: (Path("/scratch"),),
    )


# --- settings ---------------------------------------------------------------------------


def test_the_loader_is_its_interface() -> None:
    assert isinstance(SupervisorSettingsLoader(), SupervisorSettingsLoaderInterface)


def test_a_missing_file_is_every_default(tmp_path: Path) -> None:
    assert SupervisorSettingsLoader().load(tmp_path / "vibey.toml") == SupervisorSettings()


def test_every_key_is_read(tmp_path: Path) -> None:
    config = tmp_path / "vibey.toml"
    config.write_text(
        "[supervisor]\n"
        'log_dir = "/srv/logs"\nenv_file = "/srv/env"\nvibey = "/opt/v"\npython = "/opt/p"\n'
        'label_prefix = "org.example"\ndelivery_interval_seconds = 60\nrestart_seconds = 5\n'
        "delivery = false\nrequired = true\n"
        'worker_args = ["-j", "2"]\ndelivery_args = ["--answer-design-defaults"]\n'
    )
    assert SupervisorSettingsLoader().load(config) == SupervisorSettings(
        log_dir="/srv/logs",
        env_file="/srv/env",
        vibey="/opt/v",
        python="/opt/p",
        label_prefix="org.example",
        delivery_interval_seconds=60,
        restart_seconds=5,
        delivery=False,
        required=True,
        worker_args=("-j", "2"),
        delivery_args=("--answer-design-defaults",),
    )


def test_a_file_without_the_table_is_every_default(tmp_path: Path) -> None:
    config = tmp_path / "vibey.toml"
    config.write_text("[failover]\nenabled = true\n")
    assert SupervisorSettingsLoader().load(config) == SupervisorSettings()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("supervisor = 3\n", "must be a table"),
        ("[supervisor]\nlogdir = '/x'\n", "unknown keys: logdir"),
        ("[supervisor]\nrestart_seconds = true\n", "restart_seconds must be a int"),
        ("[supervisor]\ndelivery = 'yes'\n", "delivery must be a bool"),
        ("[supervisor]\nlog_dir = 3\n", "log_dir must be a str"),
        ("[supervisor]\nworker_args = '-j 2'\n", "worker_args must be a list of strings"),
        ("[supervisor]\ndelivery_args = [1]\n", "delivery_args must be a list of strings"),
    ],
)
def test_a_mistyped_setting_is_refused_by_name(tmp_path: Path, body: str, message: str) -> None:
    config = tmp_path / "vibey.toml"
    config.write_text(body)
    with pytest.raises(ValueError, match=message):
        SupervisorSettingsLoader().load(config)


# --- places -----------------------------------------------------------------------------


def test_the_host_is_its_interface() -> None:
    assert isinstance(_host("launchd"), SupervisorHostInterface)


def test_an_unknown_platform_is_refused() -> None:
    with pytest.raises(ValueError, match="use launchd or systemd"):
        _host("upstart")


def test_launchd_places() -> None:
    host = _host("launchd")
    assert host.unit_dir() == Path("/home/op/Library/LaunchAgents")
    assert host.unit_path("dev.vibey.worker") == Path(
        "/home/op/Library/LaunchAgents/dev.vibey.worker.plist"
    )
    assert host.unit_path("x", Path("/review")) == Path("/review/x.plist")
    assert host.default_log_dir() == Path("/home/op/Library/Logs/vibey")
    assert host.default_env_file() == Path(
        "/home/op/Library/Application Support/vibey/supervisor.env"
    )
    assert host.volatile_roots() == ("/scratch",)


def test_systemd_places_follow_xdg_when_it_is_absolute() -> None:
    host = _host("systemd", environ={"XDG_CONFIG_HOME": "/cfg", "XDG_STATE_HOME": "relative"})
    assert host.unit_dir() == Path("/cfg/systemd/user")
    assert host.unit_path("dev.vibey.worker") == Path("/cfg/systemd/user/dev.vibey.worker.service")
    assert host.default_log_dir() == Path("/home/op/.local/state/vibey/logs")
    assert host.default_env_file() == Path("/cfg/vibey/supervisor.env")


def test_the_default_temp_roots_are_vibey_ghs() -> None:
    host = SupervisorHost("systemd", home=Path("/h"), environ={}, uid=1, run=_Runner((0, "")))
    assert host.volatile_roots()
    assert all(root.startswith("/") for root in host.volatile_roots())


# --- states -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("answer", "state"),
    [
        ((0, "gui/501/dev.vibey.worker = {\n\tstate = running\n\tpid = 42\n}"), "running"),
        ((0, "gui/501/dev.vibey.worker = {\n\tstate = not running\n}"), "stopped"),
        ((113, "Could not find service"), "not loaded"),
    ],
)
def test_launchd_state(answer: tuple[int, str], state: str) -> None:
    run = _Runner(answer)
    assert _host("launchd", run).state("dev.vibey.worker") == state
    assert run.calls == [("launchctl", "print", "gui/501/dev.vibey.worker")]


@pytest.mark.parametrize(
    ("answer", "state"),
    [
        ((0, "active\n"), "running"),
        ((3, "inactive\n"), "not loaded"),
        ((4, "unknown\n"), "not loaded"),
        ((3, "failed\n"), "stopped (failed)"),
        ((3, "activating\n"), "stopped (activating)"),
    ],
)
def test_systemd_state(answer: tuple[int, str], state: str) -> None:
    run = _Runner(answer)
    assert _host("systemd", run).state("dev.vibey.worker") == state
    assert run.calls == [("systemctl", "--user", "is-active", "dev.vibey.worker.service")]


def test_a_service_manager_that_cannot_be_asked_is_unknown_never_a_guess() -> None:
    state = _host("launchd", _Runner(FileNotFoundError("launchctl"))).state("x")
    assert state.startswith("unknown: ")


def test_launchd_load_commands_quote_the_unit() -> None:
    lines = _host("launchd").load_commands(
        ["dev.vibey.worker"], [Path("/home/op/Library/Launch Agents/dev.vibey.worker.plist")]
    )
    assert lines[0] == (
        "launchctl bootout gui/501/dev.vibey.worker 2>/dev/null; launchctl bootstrap gui/501 "
        "'/home/op/Library/Launch Agents/dev.vibey.worker.plist'"
    )
    assert lines[-1].startswith("restart one with: launchctl kickstart -k gui/501/")


def test_systemd_load_commands_enable_every_service_and_linger() -> None:
    lines = _host("systemd").load_commands(["a", "b"], [Path("/u/a.service"), Path("/u/b.service")])
    assert lines[0] == "systemctl --user daemon-reload"
    assert lines[1] == "systemctl --user enable --now a.service b.service"
    assert lines[2].startswith('loginctl enable-linger "$USER"')


# --- units ------------------------------------------------------------------------------


def test_the_renderer_declares_the_service_methods() -> None:
    assert isinstance(TimerUnitRenderer(), TimerUnitRendererInterface)


def test_the_launchd_agent_restarts_on_failure_only_and_logs_durably() -> None:
    text = TimerUnitRenderer().launchd_service(
        SERVICE, path_env="/opt/bin:/usr/bin", restart_seconds=30
    )
    plist = plistlib.loads(text.encode())
    assert plist["Label"] == "dev.vibey.worker"
    assert plist["ProgramArguments"] == list(SERVICE.argv)
    assert plist["WorkingDirectory"] == "/srv/git/vibey"
    assert plist["EnvironmentVariables"] == {"PATH": "/opt/bin:/usr/bin"}
    assert plist["RunAtLoad"] is True
    assert plist["KeepAlive"] == {"SuccessfulExit": False}
    assert plist["ThrottleInterval"] == 30
    assert plist["StandardOutPath"] == plist["StandardErrorPath"] == SERVICE.log_path


def test_the_systemd_unit_restarts_on_failure_only_and_logs_durably() -> None:
    service = SupervisedService(
        name="delivery",
        label="dev.vibey.delivery",
        argv=('/opt/vibey/bin/py "x"', "--interval", "300"),
        working_directory="/srv/100%/vibey",
        log_path="/home/op/logs/delivery.log",
    )
    text = TimerUnitRenderer().systemd_service(service, path_env="/opt/bin", restart_seconds=7)
    lines = text.splitlines()
    assert "Description=vibey delivery (supervised; #1189)" in lines
    assert "WorkingDirectory=/srv/100%%/vibey" in lines
    assert 'Environment="PATH=/opt/bin"' in lines
    assert 'ExecStart="/opt/vibey/bin/py \\"x\\"" "--interval" "300"' in lines
    assert "Restart=on-failure" in lines
    assert "RestartSec=7" in lines
    assert "StandardOutput=append:/home/op/logs/delivery.log" in lines
    assert "StandardError=append:/home/op/logs/delivery.log" in lines
    assert "WantedBy=default.target" in lines
