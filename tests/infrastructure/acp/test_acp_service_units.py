# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpServiceUnits`: the hub and worker units `vibey acp` writes, what it wrote, and the hub
already running (ADR-0101). Module-level test functions (ADR-0016)."""

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
from vibey.infrastructure.acp.acp_service_units import UNIT_PATH, AcpServiceUnits
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.hub.serve_lock import ServeLock
from vibey.infrastructure.supervisor import SupervisorHost, SupervisorSettingsLoader
from vibey.infrastructure.supervisor_installer import ENV_TEMPLATE, SupervisorInstaller

LAUNCHER = "/opt/vibey/bin/vibey"


def _no_manager(argv: Sequence[str]) -> tuple[int, str]:
    raise AssertionError(f"asked the service manager: {argv}")


def _units(
    tmp_path: Path,
    *,
    workdir: str = "",
    config: str = "",
    started: list[str] | None = None,
    launcher: str | None = LAUNCHER,
) -> AcpServiceUnits:
    host = SupervisorHost(
        "launchd",
        home=tmp_path / "home",
        environ={},
        uid=501,
        run=_no_manager,
        temp_roots=lambda: (Path("/volatile"),),
    )
    config_path = tmp_path / "cfg" / "vibey.toml"
    config_path.parent.mkdir(exist_ok=True)
    if config:
        config_path.write_text(config)
    installer = SupervisorInstaller(
        host, SupervisorPlanner(), TimerUnitRenderer(), which=lambda name: None, python=LAUNCHER
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
        start_hub=start,
        launcher=launcher,
        roots=(tmp_path,),
    )


def _agents(tmp_path: Path) -> Path:
    return tmp_path / "home" / "Library" / "LaunchAgents"


def _env(tmp_path: Path) -> Path:
    return tmp_path / "home" / "Library" / "Application Support" / "vibey" / "supervisor.env"


def test_the_units_are_their_port(tmp_path: Path) -> None:
    assert isinstance(_units(tmp_path), ServiceUnitsInterface)


def test_write_plans_the_hub_and_worker_with_the_env_file_and_never_the_bridge(
    tmp_path: Path,
) -> None:
    hub, worker = _units(tmp_path).write(("hub", "worker"), "always")

    assert (hub.action, worker.action) == ("created", "created")
    plist = plistlib.loads(Path(hub.path).read_bytes())
    assert plist["ProgramArguments"] == [
        LAUNCHER,
        "supervisor",
        "exec",
        "--env-file",
        str(_env(tmp_path)),
        "--",
        LAUNCHER,
        "serve",
    ]
    assert plist["KeepAlive"] is True
    assert _env(tmp_path).read_text() == ENV_TEMPLATE
    assert stat.S_IMODE(_env(tmp_path).stat().st_mode) == 0o600
    assert (tmp_path / "home" / "Library" / "Logs" / "vibey").is_dir()
    assert sorted(p.name for p in _agents(tmp_path).iterdir()) == [
        "dev.vibey.hub.plist",
        "dev.vibey.worker.plist",
    ]


def test_the_unit_path_is_stable_never_the_editors(tmp_path: Path) -> None:
    (hub,) = _units(tmp_path).write(("hub",), "always")
    path = plistlib.loads(Path(hub.path).read_bytes())["EnvironmentVariables"]["PATH"]
    assert path == f"/opt/vibey/bin:{UNIT_PATH}"


def test_the_hub_runs_where_vibey_acp_reads_its_hub_and_the_worker_where_it_is_told(
    tmp_path: Path,
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    hub, worker = _units(tmp_path, workdir=str(work)).write(("hub", "worker"), "on-failure")
    # The hub reads `./vibey.toml`: the user's own, the one `vibey acp` read `[hub]` from (S3).
    hub_plist = plistlib.loads(Path(hub.path).read_bytes())
    assert hub_plist["WorkingDirectory"] == str(tmp_path / "cfg")
    worker_plist = plistlib.loads(Path(worker.path).read_bytes())
    assert worker_plist["WorkingDirectory"] == str(work)
    assert worker_plist["KeepAlive"] == {"SuccessfulExit": False}


def test_a_unit_never_carries_a_secret_from_the_env_file(tmp_path: Path) -> None:
    _env(tmp_path).parent.mkdir(parents=True)
    _env(tmp_path).write_text("VIBEY_PG_URL=postgresql://app:s3cret@db/vibey\n")
    for outcome in _units(tmp_path).write(("hub", "worker"), "always"):
        assert "s3cret" not in Path(outcome.path).read_text()


def test_a_second_write_finds_them_unchanged(tmp_path: Path) -> None:
    units = _units(tmp_path)
    units.write(("hub",), "always")
    (again,) = units.write(("hub",), "always")
    assert again.action == "unchanged"


def test_refusals_write_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="service_workdir"):
        _units(tmp_path, workdir=str(tmp_path / "missing")).write(("hub",), "always")
    with pytest.raises(ValueError, match="restart"):
        _units(tmp_path).write(("hub",), "sometimes")
    with pytest.raises(ValueError, match="label_prefix"):
        _units(tmp_path, config='[supervisor]\nlabel_prefix = "../evil"\n').write(
            ("hub",), "always"
        )
    assert not _agents(tmp_path).exists()


def test_the_label_follows_the_prefix(tmp_path: Path) -> None:
    units = _units(tmp_path, config='[supervisor]\nlabel_prefix = "org.example"\n')
    assert units.label("hub") == "org.example.hub"
    (hub,) = units.write(("hub",), "always")
    assert hub.label == "org.example.hub"


# -- trust (ADR-0101) ---------------------------------------------------------------------------


def test_the_unit_runs_the_running_install_never_a_configured_vibey(tmp_path: Path) -> None:
    units = _units(
        tmp_path, config='[supervisor]\nvibey = "/tmp/evil"\npython = "/tmp/evil-python"\n'
    )
    (hub,) = units.write(("hub",), "always")
    text = Path(hub.path).read_text()
    assert "/tmp/evil" not in text
    assert plistlib.loads(text.encode())["ProgramArguments"][0] == LAUNCHER


def test_without_a_launcher_to_pin_nothing_is_written(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="launcher"):
        _units(tmp_path, launcher=None).write(("hub",), "always")
    assert not _agents(tmp_path).exists()


@pytest.mark.parametrize(
    ("config", "key"),
    [
        ('[supervisor]\nlog_dir = "/etc"\n', "log_dir"),
        ('[supervisor]\nenv_file = "/etc/x.env"\n', "env_file"),
    ],
)
def test_a_path_outside_the_users_folders_writes_nothing(
    tmp_path: Path, config: str, key: str
) -> None:
    with pytest.raises(ValueError, match=key):
        _units(tmp_path, config=config).write(("hub", "worker"), "always")
    assert not _agents(tmp_path).exists()


def test_a_workdir_outside_the_users_folders_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="service_workdir"):
        _units(tmp_path, workdir="/").write(("hub",), "always")
    assert not _agents(tmp_path).exists()


def test_a_path_linked_out_of_the_users_folders_writes_nothing(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "logs").symlink_to(outside)
    with pytest.raises(ValueError, match="log_dir"):
        _units(tmp_path, config=f'[supervisor]\nlog_dir = "{tmp_path / "logs"}"\n').write(
            ("hub",), "always"
        )


# -- what vibey wrote (S1, M4) ------------------------------------------------------------------


def test_each_unit_written_is_recorded_by_its_digest(tmp_path: Path) -> None:
    units = _units(tmp_path)
    units.write(("hub", "worker"), "always")
    record_file = tmp_path / "hub" / "acp-units.json"
    assert sorted(json.loads(record_file.read_text())["units"]) == [
        "dev.vibey.hub",
        "dev.vibey.worker",
    ]
    assert stat.S_IMODE(record_file.stat().st_mode) == 0o600
    assert units.recorded() == ("dev.vibey.hub", "dev.vibey.worker")


def test_vibeys_own_older_rendering_is_replaced_not_called_an_edit(tmp_path: Path) -> None:
    units = _units(tmp_path)
    (hub,) = units.write(("hub",), "always")
    # An upgrade that changes the rendering: the file is still exactly what vibey wrote last.
    older = Path(hub.path).read_text().replace("ADR-0101", "ADR-0101 (an older vibey)")
    Path(hub.path).write_text(older)
    record_file = tmp_path / "hub" / "acp-units.json"
    record = json.loads(record_file.read_text())
    record["units"]["dev.vibey.hub"] = AcpServiceUnits._digest(older)
    record_file.write_text(json.dumps(record))

    (again,) = units.write(("hub",), "always")

    assert again.action == "updated"
    assert "an older vibey" not in Path(hub.path).read_text()


def test_an_operator_edit_is_kept_differing(tmp_path: Path) -> None:
    units = _units(tmp_path)
    (hub,) = units.write(("hub",), "always")
    edited = Path(hub.path).read_text().replace("<integer>30</integer>", "<integer>90</integer>")
    Path(hub.path).write_text(edited)

    (again,) = units.write(("hub",), "always")

    assert again.action == "kept-differing"
    assert Path(hub.path).read_text() == edited


def test_a_malformed_record_means_nothing_is_vibeys(tmp_path: Path) -> None:
    units = _units(tmp_path)
    (hub,) = units.write(("hub",), "always")
    Path(hub.path).write_text("someone's")
    for broken in ("not json", "[]", '{"units": 3}'):
        (tmp_path / "hub" / "acp-units.json").write_text(broken)
        assert units.recorded() == ()
        (again,) = units.write(("hub",), "always")
        assert again.action == "kept-differing"


def test_remove_deletes_only_what_vibey_wrote(tmp_path: Path) -> None:
    units = _units(tmp_path)
    hub, worker = units.write(("hub", "worker"), "always")
    Path(worker.path).write_text("edited by you")

    assert units.remove("dev.vibey.hub").action == "removed"
    kept = units.remove("dev.vibey.worker")

    assert not Path(hub.path).exists()
    assert kept.action == "kept-differing" and Path(worker.path).read_text() == "edited by you"
    assert units.recorded() == ("dev.vibey.worker",)
    assert units.remove("dev.vibey.hub").action == "absent"  # idempotent


def test_remove_refuses_a_link_and_a_bad_label(tmp_path: Path) -> None:
    units = _units(tmp_path)
    (hub,) = units.write(("hub",), "always")
    Path(hub.path).unlink()
    Path(hub.path).symlink_to(tmp_path / "elsewhere")
    assert units.remove("dev.vibey.hub").action == "failed"
    assert units.remove("a b").action == "failed"


def test_a_unit_that_cannot_be_removed_is_failed(tmp_path: Path) -> None:
    units = _units(tmp_path)
    (hub,) = units.write(("hub",), "always")
    _agents(tmp_path).chmod(0o500)
    try:
        assert units.remove("dev.vibey.hub").action == "failed"
    finally:
        _agents(tmp_path).chmod(0o700)
    assert Path(hub.path).exists()


# -- a worker that would only crash (S2) ----------------------------------------------------------


def test_the_worker_waits_for_a_database_in_the_env_file(tmp_path: Path) -> None:
    units = _units(tmp_path)
    assert units.waiting("hub") == ""
    assert "VIBEY_PG_URL" in units.waiting("worker")  # no env file yet
    _env(tmp_path).parent.mkdir(parents=True)
    _env(tmp_path).write_text(ENV_TEMPLATE)
    assert str(_env(tmp_path)) in units.waiting("worker")  # only the commented template
    _env(tmp_path).write_text("NOT A PAIR\n")
    assert units.waiting("worker")  # unreadable: still waiting
    _env(tmp_path).write_text("VIBEY_PG_URL=postgresql://app@localhost/vibey\n")
    assert units.waiting("worker") == ""


# -- a hub someone started (S6) -------------------------------------------------------------------


def test_a_hub_holding_its_lock_is_running_whatever_its_pid(tmp_path: Path) -> None:
    units = _units(tmp_path)
    assert units.detached_hub_pid() is None  # no lock file
    lock = ServeLock(tmp_path / "hub")
    assert lock.acquire()
    try:
        assert units.detached_hub_pid() == os.getpid()
        (tmp_path / "hub" / "serve.lock").write_text("")
        assert units.detached_hub_pid() == 0  # held, with no pid written
    finally:
        lock.release()
    assert units.detached_hub_pid() is None  # nothing holds it: a reused pid means nothing


def test_start_hub_runs_the_starter_once_per_call(tmp_path: Path) -> None:
    started: list[str] = []
    assert _units(tmp_path, started=started).start_hub() is True
    assert started == ["hub start"]
