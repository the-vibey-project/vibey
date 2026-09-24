# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The heartbeat timer, stood up from the tree: launchd on macOS, a systemd user timer on Linux.

Nothing here touches a real service manager or installs anything on the machine running the
suite: every unit is written under a scratch home, and launchctl and systemctl are a seam
that records what it was asked.
"""

from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

import pytest

from vibey_gh.config import (
    GhConfig,
    PlatformConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
    RunnersConfig,
)
from vibey_gh.heartbeat_timer import LAUNCHD, SYSTEMD, BeatRecord, HeartbeatPlan, HeartbeatTimer
from vibey_gh.interfaces.heartbeat_timer_interface import (
    HeartbeatPlanInterface,
    HeartbeatTimerInterface,
)

UID = 501
PYTHON = "/opt/vibey-tool/bin/python"
ORIGIN = "/opt/vibey-tool/lib/python3.12/site-packages/vibey_gh"
LABEL = "org.vibey.runner-heartbeat-r"


class _Service:
    """Records every service-manager argv and answers from a table keyed on the argv."""

    def __init__(self, answers: dict[str, tuple[int, str]] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.answers = answers or {}

    def __call__(self, argv: tuple[str, ...]) -> tuple[int, str]:
        self.calls.append(argv)
        for key, answer in self.answers.items():
            if key in argv:
                return answer
        return 0, ""


class _Timer(HeartbeatTimer):
    """No temporary directory counts as temporary: the scratch tree the suite writes into
    usually IS one, and the refusal is tested on its own below."""

    @staticmethod
    def temp_roots() -> tuple[Path, ...]:
        return ()


def _cfg(tmp_path: Path, fallback: dict | None = None, **runners: object) -> GhConfig:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    home = tmp_path / "home"
    return GhConfig(
        root=repo,
        platform=PlatformConfig(kind="github"),
        runners=RunnersConfig(
            **{  # type: ignore[arg-type]
                "repository": "o/r",
                "launch_agents_dir": str(home / "Library/LaunchAgents"),
                "log_dir": str(home / "Library/Logs"),
                "install_dir": str(home / ".local/share/vibey-runner"),
                "systemd_user_dir": str(home / ".config/systemd/user"),
                **runners,
            }
        ),
        pr_automation=PrAutomationConfig(
            fallback=PrAutomationFallbackConfig(
                **{"runner_label": "vibey-local-r", **(fallback or {})}
            )
        ),
    )


def _timer(
    tmp_path: Path,
    cfg: GhConfig | None = None,
    *,
    platform: str = "darwin",
    python: str = PYTHON,
    service: _Service | None = None,
    origin: str | None = ORIGIN,
    clock: float = 10_000.0,
    kind: type[HeartbeatTimer] = _Timer,
) -> HeartbeatTimer:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return kind(
        cfg or _cfg(tmp_path),
        home=home,
        uid=UID,
        platform=platform,
        python=python,
        service=service or _Service(),
        origin=lambda interpreter, checkout: origin,
        clock=lambda: clock,
    )


def _plan(timer: HeartbeatTimer, python: str | None = None) -> HeartbeatPlan:
    plan, problem = timer.render(python)
    assert problem == "" and plan is not None
    return plan


# --- rendering ---------------------------------------------------------------------------


def test_the_timer_and_its_plan_satisfy_their_interfaces(tmp_path):
    timer = _timer(tmp_path)
    assert isinstance(timer, HeartbeatTimerInterface)
    assert isinstance(_plan(timer), HeartbeatPlanInterface)


def test_on_macos_it_renders_a_launch_agent_that_beats_every_half_window(tmp_path):
    plan = _plan(_timer(tmp_path))
    assert plan.scheduler == LAUNCHD and plan.label == LABEL
    (unit,) = plan.files
    assert unit.path == tmp_path / "home/Library/LaunchAgents" / f"{LABEL}.plist"
    agent = plistlib.loads(unit.text.encode("utf-8"))
    record = tmp_path / "home/Library/Logs" / f"{LABEL}.last.json"
    assert agent["Label"] == LABEL
    assert agent["ProgramArguments"] == [
        PYTHON,
        "-m",
        "vibey_gh.cli",
        "sovereign",
        "--beat",
        "--record",
        str(record),
    ]
    assert agent["WorkingDirectory"] == str(tmp_path / "repo")
    # The default trust window is 15 minutes, so a beat every 7: one missed beat never
    # stales the lane.
    assert agent["StartInterval"] == 7 * 60 and plan.interval_minutes == 7
    assert agent["EnvironmentVariables"]["PYTHONSAFEPATH"] == "1"
    assert agent["StandardOutPath"] == str(tmp_path / "home/Library/Logs" / f"{LABEL}.log")
    assert "--no-verify" not in unit.text


def test_on_linux_it_renders_a_systemd_user_service_and_timer(tmp_path):
    cfg = _cfg(tmp_path, heartbeat_log_dir="")
    plan = _plan(_timer(tmp_path, cfg, platform="linux"))
    assert plan.scheduler == SYSTEMD
    service, timer = plan.files
    units = tmp_path / "home/.config/systemd/user"
    assert (service.path, timer.path) == (units / f"{LABEL}.service", units / f"{LABEL}.timer")
    # The Linux default keeps the log and the record out of ~/Library.
    record = tmp_path / "home/.local/state/vibey-gh" / f"{LABEL}.last.json"
    assert plan.record == record
    assert (
        f'ExecStart="{PYTHON}" "-m" "vibey_gh.cli" "sovereign" "--beat" "--record" "{record}"'
        in service.text
    )
    assert f"WorkingDirectory={tmp_path / 'repo'}" in service.text
    assert "Type=oneshot" in service.text and "Environment=PYTHONSAFEPATH=1" in service.text
    assert "OnUnitActiveSec=7min" in timer.text and f"Unit={LABEL}.service" in timer.text
    assert "WantedBy=timers.target" in timer.text
    assert "--no-verify" not in service.text + timer.text


def test_systemd_values_are_quoted_not_spliced(tmp_path):
    word = HeartbeatTimer._unit_word('a b"c\\d$e%f')
    assert word == '"a b\\"c\\\\d$$e%%f"'
    assert HeartbeatTimer._unit_text("50%") == "50%%"


@pytest.mark.parametrize(
    "platform, declared, expected",
    [
        ("darwin", "", LAUNCHD),
        ("linux", "", SYSTEMD),
        ("win32", "systemd", SYSTEMD),
        ("linux", "launchd", LAUNCHD),
    ],
)
def test_the_scheduler_follows_the_platform_unless_declared(tmp_path, platform, declared, expected):
    cfg = _cfg(tmp_path, heartbeat_scheduler=declared)
    assert _plan(_timer(tmp_path, cfg, platform=platform)).scheduler == expected


def test_a_platform_with_neither_scheduler_is_refused(tmp_path):
    plan, problem = _timer(tmp_path, platform="win32").render()
    assert plan is None and "set [runners] heartbeat_scheduler" in problem


@pytest.mark.parametrize(
    "window, interval, expected",
    [(15, 0, 7), (15, 5, 5), (60, 30, 30), (2, 0, 1)],
)
def test_the_interval_is_at_most_half_the_trust_window(tmp_path, window, interval, expected):
    cfg = _cfg(
        tmp_path,
        fallback={"heartbeat_max_age_minutes": window},
        heartbeat_interval_minutes=interval,
    )
    assert _timer(tmp_path, cfg).interval_minutes() == (expected, "")


@pytest.mark.parametrize("window, interval", [(15, 8), (1, 0), (10, 6)])
def test_an_interval_that_could_stale_the_lane_is_refused(tmp_path, window, interval):
    cfg = _cfg(
        tmp_path,
        fallback={"heartbeat_max_age_minutes": window},
        heartbeat_interval_minutes=interval,
    )
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "at most half the window" in problem


def test_a_declared_interpreter_is_used_and_expanded(tmp_path):
    cfg = _cfg(tmp_path, heartbeat_python="~/.local/share/uv/tools/vibey/bin/python")
    plan = _plan(_timer(tmp_path, cfg))
    assert plan.python == str(tmp_path / "home/.local/share/uv/tools/vibey/bin/python")
    # An explicit one (what status passes: the interpreter the installed unit runs) wins.
    assert _plan(_timer(tmp_path, cfg), "/usr/bin/python3").python == "/usr/bin/python3"


def test_an_interpreter_under_a_temporary_directory_is_refused(tmp_path):
    timer = _timer(
        tmp_path,
        python=str(Path(os.path.realpath("/tmp")) / "venv/bin/python"),
        kind=HeartbeatTimer,
    )
    plan, problem = timer.render()
    assert plan is None and "which a reboot empties" in problem


def test_an_interpreter_inside_a_git_work_tree_is_refused(tmp_path):
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    plan, problem = _timer(tmp_path, python=str(clone / ".venv/bin/python")).render()
    assert plan is None and f"inside the git work tree {clone}" in problem
    assert "uv tool install" in problem


def test_a_vibey_gh_imported_from_a_checkout_is_refused(tmp_path):
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    plan, problem = _timer(tmp_path, origin=str(clone / "src/vibey_gh")).render()
    assert plan is None and "the vibey_gh it runs" in problem


def test_an_interpreter_that_cannot_import_vibey_gh_is_refused(tmp_path):
    plan, problem = _timer(tmp_path, origin=None).render()
    assert plan is None and "cannot import vibey_gh" in problem


def test_a_relative_interpreter_is_refused(tmp_path):
    plan, problem = _timer(tmp_path, python="python3").render()
    assert plan is None and "absolute path" in problem


def test_a_log_directory_inside_a_git_work_tree_is_refused(tmp_path):
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True)
    cfg = _cfg(tmp_path, heartbeat_log_dir=str(clone / "logs"))
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "the heartbeat log directory" in problem


def test_a_linked_worktree_is_no_checkout_to_beat_from(tmp_path):
    cfg = _cfg(tmp_path)
    (cfg.root / ".git").rmdir()
    (cfg.root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/lane\n", encoding="utf-8")
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "is not a main clone" in problem


def test_no_timer_without_a_sovereign_lane_or_a_repository(tmp_path):
    plan, problem = _timer(tmp_path, _cfg(tmp_path, fallback={"enabled": False})).render()
    assert plan is None and "[pr_automation.fallback] is disabled" in problem
    cfg = _cfg(tmp_path, repository="")
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "runners.repository is empty" in problem


# --- install ------------------------------------------------------------------------------


def test_install_writes_the_unit_and_loads_nothing_unasked(tmp_path):
    service = _Service()
    timer = _timer(tmp_path, service=service)
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=False)
    assert ok and lines == [f"wrote {plan.files[0].path}"]
    assert plan.files[0].path.read_text(encoding="utf-8") == plan.files[0].text
    assert plan.log.parent.is_dir()
    assert service.calls == []


def test_install_with_load_replaces_the_running_launch_agent(tmp_path):
    service = _Service({"bootout": (3, "not loaded")})
    timer = _timer(tmp_path, service=service)
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=True)
    assert ok and lines[-1] == f"loaded {LABEL}: a beat every 7m"
    assert service.calls == [
        ("launchctl", "bootout", f"gui/{UID}/{LABEL}"),
        ("launchctl", "bootstrap", f"gui/{UID}", str(plan.files[0].path)),
    ]


def test_install_with_load_enables_the_systemd_timer(tmp_path):
    service = _Service()
    timer = _timer(tmp_path, platform="linux", service=service)
    _lines, ok = timer.install(_plan(timer), load=True)
    assert ok
    assert service.calls == [
        ("systemctl", "--user", "daemon-reload"),
        ("systemctl", "--user", "enable", "--now", f"{LABEL}.timer"),
    ]


def test_a_refused_load_is_reported(tmp_path):
    timer = _timer(tmp_path, service=_Service({"bootstrap": (5, "Input/output error")}))
    lines, ok = timer.install(_plan(timer), load=True)
    assert not ok and lines[-1] == "launchctl bootstrap failed (exit 5): Input/output error"


def test_next_steps_are_the_exact_commands(tmp_path):
    timer = _timer(tmp_path)
    plan = _plan(timer)
    assert timer.next_steps(plan) == [
        (
            f"launchctl bootout gui/{UID}/{LABEL} 2>/dev/null;"
            f" launchctl bootstrap gui/{UID} {plan.files[0].path}"
        ),
        "vibey-gh heartbeat status",
    ]
    linux = _timer(tmp_path, platform="linux")
    steps = linux.next_steps(_plan(linux))
    assert steps[1] == f"systemctl --user enable --now {LABEL}.timer"
    assert steps[2].startswith('loginctl enable-linger "$USER"')


# --- status -------------------------------------------------------------------------------


def _installed(tmp_path: Path, **kwargs: object) -> tuple[HeartbeatTimer, HeartbeatPlan]:
    timer = _timer(tmp_path, **kwargs)  # type: ignore[arg-type]
    plan = _plan(timer)
    timer.install(plan, load=False)
    return timer, plan


def test_status_of_nothing_installed_says_what_is_missing(tmp_path):
    lines, healthy = _timer(tmp_path).status()
    assert not healthy
    assert lines[0] == f"missing: {tmp_path / 'home/Library/LaunchAgents' / f'{LABEL}.plist'}"
    assert lines[-1] == "last beat: none recorded"


def test_status_is_healthy_only_after_a_fresh_published_beat(tmp_path):
    timer, plan = _installed(tmp_path, clock=10_000.0)
    BeatRecord(10_000.0 - 125, True, "heartbeat published to refs/x at T: 1 runner").write(
        plan.record
    )
    lines, healthy = timer.status()
    assert healthy, lines
    assert f"{LABEL}: loaded (launchd)" in lines
    assert "last beat: 2m05s ago, published: heartbeat published to refs/x at T: 1 runner" in lines


def test_status_reads_the_interpreter_the_installed_unit_runs(tmp_path):
    """Drift is judged against what is on the host: `status` run from a checkout's own
    virtualenv must not call a timer installed with a tool interpreter drifted."""
    _, plan = _installed(tmp_path)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    other = _timer(tmp_path, python="/somewhere/else/python")
    assert other.status()[1] is True


@pytest.mark.parametrize(
    "record, expected",
    [
        (
            BeatRecord(10_000.0 - 60, False, "heartbeat withheld: no runner"),
            "withheld: heartbeat withheld",
        ),
        (BeatRecord(10_000.0 - 16 * 60, True, "ok"), "older than the 15m window"),
    ],
)
def test_status_is_unhealthy_after_a_withheld_or_stale_beat(tmp_path, record, expected):
    timer, plan = _installed(tmp_path)
    record.write(plan.record)
    lines, healthy = timer.status()
    assert not healthy and any(expected in line for line in lines), lines


def test_status_names_drift_and_a_timer_that_is_not_loaded(tmp_path):
    timer, plan = _installed(tmp_path, service=_Service({"print": (113, "")}))
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    unit = plan.files[0].path
    unit.write_text(unit.read_text(encoding="utf-8").replace("420", "421"), encoding="utf-8")
    lines, healthy = timer.status()
    assert not healthy
    assert f"drift: {unit}" in lines and f"{LABEL}: not loaded (launchd)" in lines


def test_status_on_linux_asks_systemd(tmp_path):
    service = _Service({"is-active": (3, "")})
    timer, plan = _installed(tmp_path, platform="linux", service=service)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    lines, healthy = timer.status()
    assert not healthy and f"{LABEL}: not loaded (systemd)" in lines
    assert ("systemctl", "--user", "is-active", "--quiet", f"{LABEL}.timer") in service.calls
    assert _timer(tmp_path, platform="linux").status()[1] is True


def test_status_of_a_unit_it_cannot_parse_or_render(tmp_path):
    _, plan = _installed(tmp_path)
    plan.files[0].path.write_text("not a plist", encoding="utf-8")
    lines, healthy = _timer(tmp_path, origin=None).status()
    assert not healthy and any("cannot render" in line for line in lines)
    assert _timer(tmp_path).status()[0][0] == f"drift: {plan.files[0].path}"


def test_status_without_a_lane_says_why(tmp_path):
    lines, healthy = _timer(tmp_path, _cfg(tmp_path, fallback={"enabled": False})).status()
    assert not healthy and "is disabled" in lines[0]


def test_the_installed_interpreter_is_read_back_from_either_unit(tmp_path):
    timer, plan = _installed(tmp_path, platform="linux", python="/opt/a b/python")
    assert timer._installed_python(plan.files[0].path, SYSTEMD) == "/opt/a b/python"
    plan.files[0].path.write_text("[Service]\n", encoding="utf-8")
    assert timer._installed_python(plan.files[0].path, SYSTEMD) is None
    assert timer._installed_python(tmp_path / "absent.plist", LAUNCHD) is None


# --- uninstall ----------------------------------------------------------------------------


def test_uninstall_is_a_dry_run_unless_applied_and_moves_units_aside(tmp_path):
    service = _Service()
    timer, plan = _installed(tmp_path, service=service)
    unit = plan.files[0].path
    retired = tmp_path / "home/.local/share/vibey-runner/retired-units" / unit.name
    assert timer.uninstall(apply=False) == [
        f"would run: launchctl bootout gui/{UID}/{LABEL}",
        f"would move {unit} to {retired}",
    ]
    assert unit.exists() and service.calls == []
    assert timer.uninstall(apply=True) == [f"unloaded {LABEL}", f"moved {unit} to {retired}"]
    assert retired.is_file() and not unit.exists()
    assert timer.uninstall(apply=True) == ["no heartbeat timer is installed"]


def test_uninstall_on_linux_disables_the_timer_and_reloads(tmp_path):
    service = _Service({"disable": (1, "Unit not loaded")})
    timer, plan = _installed(tmp_path, platform="linux", service=service)
    lines = timer.uninstall(apply=True)
    assert lines[0] == f"{LABEL} was not loaded (Unit not loaded)"
    assert service.calls[-1] == ("systemctl", "--user", "daemon-reload")
    assert not any(rendered.path.exists() for rendered in plan.files)


def test_uninstall_without_a_lane_says_why(tmp_path):
    lines = _timer(tmp_path, _cfg(tmp_path, fallback={"enabled": False})).uninstall(apply=True)
    assert "is disabled" in lines[0]


# --- the beat record and the default seams ------------------------------------------------


def test_a_beat_record_round_trips_and_a_bad_one_reads_as_none(tmp_path):
    path = tmp_path / "logs" / "beat.last.json"
    BeatRecord(12.5, False, "heartbeat withheld: x").write(path)
    assert BeatRecord.read(path) == BeatRecord(12.5, False, "heartbeat withheld: x")
    assert not list(path.parent.glob(".*partial"))
    path.write_text("{", encoding="utf-8")
    assert BeatRecord.read(path) is None
    assert BeatRecord.read(tmp_path / "absent.json") is None


def test_the_default_service_seam_runs_without_a_shell(tmp_path):
    assert HeartbeatTimer._run((sys.executable, "-c", "print('ok')")) == (0, "ok")
    assert HeartbeatTimer._run((str(tmp_path / "no-such-binary"),))[0] == 127


def test_the_default_origin_asks_the_interpreter_itself(tmp_path):
    origin = HeartbeatTimer._module_origin(sys.executable, tmp_path)
    assert origin is not None and origin.endswith("vibey_gh")
    assert HeartbeatTimer._module_origin(str(tmp_path / "no-python"), tmp_path) is None


def test_the_default_temporary_roots_include_this_machines_own(tmp_path):
    import tempfile

    assert Path(os.path.realpath(tempfile.gettempdir())) in HeartbeatTimer.temp_roots()


def test_the_defaults_are_the_running_platform_and_interpreter(tmp_path):
    timer = HeartbeatTimer(_cfg(tmp_path), home=tmp_path, uid=UID)
    assert timer._platform == sys.platform and timer._python == sys.executable


# --- the command line ---------------------------------------------------------------------


def _fake_python(tmp_path: Path) -> Path:
    """An 'interpreter' that answers the origin probe from outside any checkout."""
    python = tmp_path / "tool" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text(f"#!/bin/sh\necho {ORIGIN}\n", encoding="utf-8")
    python.chmod(0o755)
    return python


def _toml_repo(tmp_path: Path, monkeypatch) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    python = _fake_python(tmp_path)
    (repo / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "github"\n\n[runners]\nrepository = "o/r"\n'
        f'heartbeat_scheduler = "launchd"\nheartbeat_python = "{python}"\n',
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)
    monkeypatch.setattr(HeartbeatTimer, "temp_roots", staticmethod(lambda: ()))
    return home


def test_cli_heartbeat_install_writes_and_prints_the_next_commands(tmp_path, monkeypatch, capsys):
    from vibey_gh.cli import main

    home = _toml_repo(tmp_path, monkeypatch)
    assert main(["heartbeat", "install"]) == 0
    out = capsys.readouterr().out
    plist = home / "Library/LaunchAgents" / f"{LABEL}.plist"
    assert f"wrote {plist}" in out and plist.is_file()
    assert "the heartbeat timer was not loaded" in out
    assert f"launchctl bootstrap gui/{os.getuid()} {plist}" in out


def test_cli_heartbeat_refuses_what_it_cannot_render(tmp_path, monkeypatch, capsys):
    from vibey_gh.cli import main

    _toml_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(HeartbeatTimer, "temp_roots", staticmethod(lambda: (tmp_path,)))
    assert main(["heartbeat", "install"]) == 1
    assert "which a reboot empties" in capsys.readouterr().err


def test_cli_heartbeat_status_and_uninstall_go_through_the_service_seam(
    tmp_path, monkeypatch, capsys
):
    import argparse

    from vibey_gh import cli

    home = _toml_repo(tmp_path, monkeypatch)
    service = _Service()
    install = argparse.Namespace(action="install", load=True, apply=False)
    assert cli._heartbeat(install, service=service) == 0
    assert f"loaded {LABEL}: a beat every 7m" in capsys.readouterr().out
    status = argparse.Namespace(action="status", load=False, apply=False)
    assert cli._heartbeat(status, service=service) == 1  # no beat recorded yet
    assert "last beat: none recorded" in capsys.readouterr().out
    record = home / "Library/Logs" / f"{LABEL}.last.json"
    BeatRecord(__import__("time").time(), True, "published").write(record)
    assert cli._heartbeat(status, service=service) == 0
    refused = _Service({"bootstrap": (5, "denied")})
    assert cli._heartbeat(install, service=refused) == 1
    dry = argparse.Namespace(action="uninstall", load=False, apply=False)
    assert cli._heartbeat(dry, service=service) == 0
    assert "dry run: nothing was changed" in capsys.readouterr().out
    applied = argparse.Namespace(action="uninstall", load=False, apply=True)
    assert cli._heartbeat(applied, service=service) == 0
    assert not (home / "Library/LaunchAgents" / f"{LABEL}.plist").exists()
