# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpServiceUnits`: the hub and worker units `vibey acp` writes, and the hub already running
(ADR-0101). Module-level test functions (ADR-0016)."""

from __future__ import annotations

import json
import os
import plistlib
import stat
from collections.abc import Sequence
from pathlib import Path

import pytest

from vibey.application.acp.interfaces.service_units_interface import ServiceUnitsInterface
from vibey.domain.supervisor import SupervisorPlanner
from vibey.infrastructure.acp.acp_service_units import AcpServiceUnits
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.supervisor import SupervisorHost, SupervisorSettingsLoader
from vibey.infrastructure.supervisor_installer import ENV_TEMPLATE, SupervisorInstaller


def _no_manager(argv: Sequence[str]) -> tuple[int, str]:
    raise AssertionError(f"asked the service manager: {argv}")


def _units(
    tmp_path: Path,
    *,
    workdir: str = "",
    config: str = "",
    started: list[str] | None = None,
    alive: object = None,
) -> AcpServiceUnits:
    host = SupervisorHost(
        "launchd",
        home=tmp_path / "home",
        environ={},
        uid=501,
        run=_no_manager,
        temp_roots=lambda: (Path("/volatile"),),
    )
    config_path = tmp_path / "vibey.toml"
    if config:
        config_path.write_text(config)
    installer = SupervisorInstaller(
        host,
        SupervisorPlanner(),
        TimerUnitRenderer(),
        which=lambda name: "/opt/vibey/bin/vibey",
        python="/opt/vibey/bin/python",
    )
    log: list[str] = started if started is not None else []

    def start() -> bool:
        log.append("hub start")
        return True

    return AcpServiceUnits(
        host,
        installer,
        SupervisorPlanner(),
        SupervisorSettingsLoader(),
        config_path=config_path,
        workdir=workdir,
        state_dir=tmp_path / "hub",
        path_env="/opt/vibey/bin:/usr/bin",
        start_hub=start,
        **({"alive": alive} if alive is not None else {}),  # type: ignore[arg-type]
    )


def test_the_units_are_their_port(tmp_path: Path) -> None:
    assert isinstance(_units(tmp_path), ServiceUnitsInterface)


def test_write_plans_the_hub_and_worker_with_the_env_file_and_never_the_bridge(
    tmp_path: Path,
) -> None:
    hub, worker = _units(tmp_path).write(("hub", "worker"), "always")

    support = tmp_path / "home" / "Library" / "Application Support" / "vibey"
    env_file = support / "supervisor.env"
    assert (hub.action, worker.action) == ("created", "created")
    plist = plistlib.loads(Path(hub.path).read_bytes())
    assert plist["ProgramArguments"] == [
        "/opt/vibey/bin/vibey",
        "supervisor",
        "exec",
        "--env-file",
        str(env_file),
        "--",
        "/opt/vibey/bin/vibey",
        "serve",
    ]
    assert plist["KeepAlive"] is True
    assert plist["WorkingDirectory"] == str(support)
    assert env_file.read_text() == ENV_TEMPLATE
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert (tmp_path / "home" / "Library" / "Logs" / "vibey").is_dir()
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    assert sorted(p.name for p in agents.iterdir()) == [
        "dev.vibey.hub.plist",
        "dev.vibey.worker.plist",
    ]


def test_a_unit_never_carries_a_secret_from_the_env_file(tmp_path: Path) -> None:
    units = _units(tmp_path)
    support = tmp_path / "home" / "Library" / "Application Support" / "vibey"
    support.mkdir(parents=True)
    (support / "supervisor.env").write_text("VIBEY_PG_URL=postgresql://app:s3cret@db/vibey\n")

    hub, worker = units.write(("hub", "worker"), "always")

    for outcome in (hub, worker):
        assert "s3cret" not in Path(outcome.path).read_text()
    assert "s3cret" in (support / "supervisor.env").read_text()  # kept as it was


def test_a_second_write_finds_them_unchanged(tmp_path: Path) -> None:
    units = _units(tmp_path)
    units.write(("hub",), "always")
    (again,) = units.write(("hub",), "always")
    assert again.action == "unchanged"


def test_the_workdir_setting_is_where_the_services_run(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    (hub,) = _units(tmp_path, workdir=str(work)).write(("hub",), "on-failure")
    plist = plistlib.loads(Path(hub.path).read_bytes())
    assert plist["WorkingDirectory"] == str(work)
    assert plist["KeepAlive"] == {"SuccessfulExit": False}


def test_a_workdir_that_is_no_folder_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="service_workdir"):
        _units(tmp_path, workdir=str(tmp_path / "missing")).write(("hub",), "always")


def test_a_restart_policy_outside_the_two_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="restart"):
        _units(tmp_path).write(("hub",), "sometimes")


def test_the_label_follows_the_prefix(tmp_path: Path) -> None:
    units = _units(tmp_path, config='[supervisor]\nlabel_prefix = "org.example"\n')
    assert units.label("hub") == "org.example.hub"
    (hub,) = units.write(("hub",), "always")
    assert hub.label == "org.example.hub"


def test_a_bad_label_prefix_writes_nothing(tmp_path: Path) -> None:
    units = _units(tmp_path, config='[supervisor]\nlabel_prefix = "../evil"\n')
    with pytest.raises(ValueError, match="label_prefix"):
        units.write(("hub",), "always")
    assert not (tmp_path / "home" / "Library" / "LaunchAgents").exists()


def _serving(tmp_path: Path, pid: object) -> None:
    (tmp_path / "hub").mkdir(exist_ok=True)
    (tmp_path / "hub" / "serving.json").write_text(
        json.dumps({"host": "127.0.0.1", "port": 8765, "pid": pid})
    )


def test_a_live_hub_in_serving_json_is_named_by_its_pid(tmp_path: Path) -> None:
    _serving(tmp_path, os.getpid())
    assert _units(tmp_path).detached_hub_pid() == os.getpid()


def test_no_record_a_malformed_one_or_a_dead_pid_is_none(tmp_path: Path) -> None:
    assert _units(tmp_path).detached_hub_pid() is None
    _serving(tmp_path, "not a pid")
    assert _units(tmp_path).detached_hub_pid() is None
    _serving(tmp_path, 4242)
    assert _units(tmp_path, alive=lambda pid: False).detached_hub_pid() is None


def test_alive_never_treats_a_group_id_as_a_process() -> None:
    assert AcpServiceUnits.alive(0) is False
    assert AcpServiceUnits.alive(-1) is False
    assert AcpServiceUnits.alive(os.getpid()) is True
    assert AcpServiceUnits.alive(2**22 + 12345) is False  # above any pid this host hands out


def test_alive_counts_another_users_process(monkeypatch: pytest.MonkeyPatch) -> None:
    def refused(pid: int, signal: int) -> None:
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(os, "kill", refused)
    assert AcpServiceUnits.alive(1) is True


def test_start_hub_runs_the_starter_once_per_call(tmp_path: Path) -> None:
    started: list[str] = []
    assert _units(tmp_path, started=started).start_hub() is True
    assert started == ["hub start"]
