# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The restart policy a supervised unit is rendered with (ADR-0101).

`always` is what `vibey acp` loads: launchd `KeepAlive` true, systemd `Restart=always`, each
throttled so a crash loop never spins. `on-failure` is what `vibey supervisor install` renders,
and its output is pinned byte for byte to the text it had before `always` existed. Every value
a unit takes from settings or the environment is escaped for its format, and a value no format
can carry (a control character) is refused rather than written."""

import plistlib
from dataclasses import replace

import pytest

from vibey.domain.supervisor import SupervisedService
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer

WORKER = SupervisedService(
    name="worker",
    label="dev.vibey.worker",
    argv=(
        "/opt/vibey/bin/vibey",
        "supervisor",
        "exec",
        "--env-file",
        "/home/op/a b/supervisor.env",
        "--",
        "/opt/vibey/bin/vibey",
        "worker",
        "--all-projects",
    ),
    working_directory="/srv/git/vibey",
    log_path="/home/op/logs/worker.log",
)
HUB = replace(
    WORKER,
    name="hub",
    label="dev.vibey.hub",
    argv=(*WORKER.argv[:6], "/opt/vibey/bin/vibey", "serve"),
    log_path="/home/op/logs/hub.log",
    restart="always",
)

GOLDEN_LAUNCHD = (
    '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<!-- Rendered by `vibey supervisor install`'
    " from [supervisor] in vibey.toml. Edit the table and install again. -->\n"
    '<plist version="1.0">\n<dict>\n  <key>Label</key>\n  <string>dev.vibey.worker</string>\n'
    "  <key>ProgramArguments</key>\n  <array>\n    <string>/opt/vibey/bin/vibey</string>\n"
    "    <string>supervisor</string>\n    <string>exec</string>\n    <string>--env-file</string>\n"
    "    <string>/home/op/a b/supervisor.env</string>\n    <string>--</string>\n"
    "    <string>/opt/vibey/bin/vibey</string>\n    <string>worker</string>\n"
    "    <string>--all-projects</string>\n  </array>\n  <key>WorkingDirectory</key>\n"
    "  <string>/srv/git/vibey</string>\n  <key>EnvironmentVariables</key>\n  <dict>\n"
    "    <key>PATH</key>\n    <string>/opt/vibey/bin:/usr/bin</string>\n  </dict>\n"
    "  <key>RunAtLoad</key>\n  <true/>\n  <key>KeepAlive</key>\n  <dict>\n"
    "    <key>SuccessfulExit</key>\n    <false/>\n  </dict>\n  <key>ThrottleInterval</key>\n"
    "  <integer>30</integer>\n  <key>StandardOutPath</key>\n  <string>/home/op/logs/worker.log</string>\n"
    "  <key>StandardErrorPath</key>\n  <string>/home/op/logs/worker.log</string>\n</dict>\n</plist>\n"
)
GOLDEN_SYSTEMD = (
    "# Rendered by `vibey supervisor install` from [supervisor] in vibey.toml.\n"
    "# Edit the table and install again.\n[Unit]\nDescription=vibey worker (supervised; #1189)\n"
    "After=network-online.target\nWants=network-online.target\n\n[Service]\nType=simple\n"
    'WorkingDirectory=/srv/git/vibey\nEnvironment="PATH=/opt/vibey/bin:/usr/bin"\n'
    'ExecStart="/opt/vibey/bin/vibey" "supervisor" "exec" "--env-file" '
    '"/home/op/a b/supervisor.env" "--" "/opt/vibey/bin/vibey" "worker" "--all-projects"\n'
    "Restart=on-failure\nRestartSec=30\nStandardOutput=append:/home/op/logs/worker.log\n"
    "StandardError=append:/home/op/logs/worker.log\n\n[Install]\nWantedBy=default.target\n"
)
PATH_ENV = "/opt/vibey/bin:/usr/bin"


def test_on_failure_output_is_unchanged() -> None:
    renderer = TimerUnitRenderer()
    assert renderer.launchd_service(WORKER, path_env=PATH_ENV, restart_seconds=30) == GOLDEN_LAUNCHD
    assert renderer.systemd_service(WORKER, path_env=PATH_ENV, restart_seconds=30) == GOLDEN_SYSTEMD
    # The throttle keys an `always` unit takes leave an `on-failure` unit byte for byte as it was.
    assert (
        renderer.systemd_service(
            WORKER,
            path_env=PATH_ENV,
            restart_seconds=30,
            start_limit_interval_seconds=600,
            start_limit_burst=5,
        )
        == GOLDEN_SYSTEMD
    )


def test_always_renders_keepalive_true_and_restart_always() -> None:
    renderer = TimerUnitRenderer()
    launchd = renderer.launchd_service(HUB, path_env=PATH_ENV, restart_seconds=30)
    assert "  <key>KeepAlive</key>\n  <true/>\n" in launchd
    plist = plistlib.loads(launchd.encode())
    assert plist["KeepAlive"] is True
    assert plist["ThrottleInterval"] == 30
    assert plist["ProgramArguments"][-2:] == ["/opt/vibey/bin/vibey", "serve"]
    assert "Rendered by `vibey acp`" in launchd

    systemd = renderer.systemd_service(
        HUB,
        path_env=PATH_ENV,
        restart_seconds=30,
        start_limit_interval_seconds=600,
        start_limit_burst=5,
    )
    lines = systemd.splitlines()
    assert "Restart=always" in lines
    assert "Restart=on-failure" not in lines
    assert "RestartSec=30" in lines
    unit = systemd.split("[Service]")[0]
    assert "StartLimitIntervalSec=600" in unit.splitlines()
    assert "StartLimitBurst=5" in unit.splitlines()
    assert "Rendered by `vibey acp`" in systemd


def test_an_always_unit_without_a_start_limit_leaves_systemds_own() -> None:
    systemd = TimerUnitRenderer().systemd_service(HUB, path_env=PATH_ENV, restart_seconds=30)
    assert "StartLimit" not in systemd
    assert "Restart=always" in systemd.splitlines()


HOSTILE = '/home/o p/"q" & <r> 100% $HOME ${X} \\ `id`'


def test_hostile_values_are_escaped_for_launchd_and_read_back_intact() -> None:
    service = replace(
        HUB,
        argv=(HOSTILE, "--env-file", HOSTILE),
        working_directory=HOSTILE,
        log_path=HOSTILE + "/hub.log",
    )
    text = TimerUnitRenderer().launchd_service(service, path_env=HOSTILE, restart_seconds=30)
    plist = plistlib.loads(text.encode())  # well-formed: nothing broke out of its element
    assert plist["ProgramArguments"] == [HOSTILE, "--env-file", HOSTILE]
    assert plist["WorkingDirectory"] == HOSTILE
    assert plist["EnvironmentVariables"] == {"PATH": HOSTILE}
    assert plist["StandardOutPath"] == HOSTILE + "/hub.log"
    assert set(plist) == {
        "Label",
        "ProgramArguments",
        "WorkingDirectory",
        "EnvironmentVariables",
        "RunAtLoad",
        "KeepAlive",
        "ThrottleInterval",
        "StandardOutPath",
        "StandardErrorPath",
    }


def test_hostile_values_are_quoted_for_systemd_with_specifiers_and_variables_escaped() -> None:
    service = replace(
        HUB, argv=(HOSTILE, "serve"), working_directory=HOSTILE, log_path=HOSTILE + "/hub.log"
    )
    text = TimerUnitRenderer().systemd_service(service, path_env=HOSTILE, restart_seconds=30)
    lines = text.splitlines()
    # ExecStart expands $VAR and ${VAR} and % specifiers: each is doubled, quotes and
    # backslashes escaped, so the argument reaches the process exactly as planned.
    exec_start = '"/home/o p/\\"q\\" & <r> 100%% $$HOME $${X} \\\\ `id`" "serve"'
    assert f"ExecStart={exec_start}" in lines
    # Environment= expands specifiers but no variables, so `$` is left as it is.
    assert 'Environment="PATH=/home/o p/\\"q\\" & <r> 100%% $HOME ${X} \\\\ `id`"' in lines
    assert 'WorkingDirectory=/home/o p/"q" & <r> 100%% $HOME ${X} \\ `id`' in lines
    assert any(line.startswith("StandardOutput=append:/home/o p/") for line in lines)
    directives = [line.split("=", 1)[0] for line in lines if "=" in line and line[0] != "#"]
    assert directives.count("ExecStart") == 1


@pytest.mark.parametrize("bad", ["/x\nExecStartPre=/bin/sh -c evil", "/x\rY", "/x\x00y", "/x\x1by"])
@pytest.mark.parametrize("field", ["argv", "working_directory", "log_path", "path_env"])
@pytest.mark.parametrize("platform", ["launchd", "systemd"])
def test_a_control_character_in_any_value_is_refused_never_written(
    bad: str, field: str, platform: str
) -> None:
    renderer = TimerUnitRenderer()
    service = HUB
    path_env = PATH_ENV
    if field == "argv":
        service = replace(HUB, argv=(*HUB.argv[:-1], bad))
    elif field == "path_env":
        path_env = bad
    else:
        service = replace(HUB, **{field: bad})
    render = renderer.launchd_service if platform == "launchd" else renderer.systemd_service
    with pytest.raises(ValueError, match="control character"):
        render(service, path_env=path_env, restart_seconds=30)


def test_a_value_that_cannot_be_encoded_is_refused() -> None:
    service = replace(HUB, working_directory="/x\udcffy")  # an undecodable byte, kept by fsdecode
    with pytest.raises(ValueError, match="control character"):
        TimerUnitRenderer().systemd_service(service, path_env=PATH_ENV, restart_seconds=30)
