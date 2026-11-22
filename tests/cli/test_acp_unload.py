# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp unload`: stop the services `vibey acp` loaded for good (ADR-0101, review M4).

`launchctl bootout` alone lasts until the next login; the plist goes too, but only one that is
still exactly what vibey wrote. Real unit files and a real record, a recording service manager.
Module-level test functions (ADR-0016)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibey.application.acp.dto import UnitOutcome
from vibey.bootstrap import AcpMachine
from vibey.cli.acp_unload import AcpUnloadCommand
from vibey.cli.interfaces.acp_unload_interface import AcpUnloadCommandInterface
from vibey.cli.main import app
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.supervisor import SupervisorPlanner
from vibey.infrastructure.acp.acp_service_units import AcpServiceUnits
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.supervisor import SupervisorHost, SupervisorSettingsLoader
from vibey.infrastructure.supervisor_installer import SupervisorInstaller

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


class Manager:
    def __init__(self, *, loaded: set[str] | None = None) -> None:
        self.loaded = set(loaded or ())
        self.calls: list[tuple[str, str]] = []
        self.fail: set[str] = set()
        self.refusal = ""
        self.reload_fails = False

    def refused(self) -> str:
        return self.refusal

    def unload(self, label: str) -> UnitOutcome:
        self.calls.append(("unload", label))
        if label in self.fail:
            return UnitOutcome(label, "", "failed", "bootout exited 5")
        if label in self.loaded:
            self.loaded.discard(label)
            return UnitOutcome(label, "", "unloaded")
        return UnitOutcome(label, "", "not-loaded")

    def forget_unit_files(self) -> UnitOutcome:
        self.calls.append(("forget", ""))
        return UnitOutcome("", "", "failed" if self.reload_fails else "unchanged", "no bus")

    def unload_commands(self, labels: Iterable[str]) -> tuple[str, ...]:
        return ()


def _no_manager(argv: Sequence[str]) -> tuple[int, str]:
    raise AssertionError(argv)


def _units(tmp_path: Path) -> AcpServiceUnits:
    host = SupervisorHost(
        "launchd",
        home=tmp_path / "home",
        environ={},
        uid=501,
        run=_no_manager,
        temp_roots=lambda: (Path("/volatile"),),
    )
    config = tmp_path / "cfg" / "vibey.toml"
    config.parent.mkdir(exist_ok=True)
    return AcpServiceUnits(
        host,
        SupervisorInstaller(
            host,
            SupervisorPlanner(),
            TimerUnitRenderer(),
            which=lambda n: None,
            python="/opt/vibey/bin/vibey",
        ),
        SupervisorPlanner(),
        SupervisorSettingsLoader(),
        config_path=config,
        workdir="",
        state_dir=tmp_path / "hub",
        launcher="/opt/vibey/bin/vibey",
        roots=(tmp_path,),
    )


def _command(
    tmp_path: Path, manager: Manager, units: AcpServiceUnits | None, said: list[str]
) -> AcpUnloadCommand:
    def machine(settings: AcpSettings, *, user_config: Path) -> AcpMachine:
        assert user_config == tmp_path / "cfg" / "vibey.toml"
        return AcpMachine(
            connector=None,  # type: ignore[arg-type]
            postgres=None,  # type: ignore[arg-type]
            lock=None,  # type: ignore[arg-type]
            units=units,
            loader=manager if units is not None else None,  # type: ignore[arg-type]
        )

    return AcpUnloadCommand(
        machine=machine, user_config=lambda: tmp_path / "cfg" / "vibey.toml", echo=said.append
    )


def test_the_command_is_its_interface(tmp_path: Path) -> None:
    assert isinstance(_command(tmp_path, Manager(), None, []), AcpUnloadCommandInterface)


def test_unload_stops_each_unit_and_removes_only_what_vibey_wrote(tmp_path: Path) -> None:
    units = _units(tmp_path)
    hub, worker = units.write(("hub", "worker"), "always")
    Path(worker.path).write_text("edited by you")
    manager, said = Manager(loaded={"dev.vibey.hub", "dev.vibey.worker"}), []

    assert _command(tmp_path, manager, units, said).run() == 0

    assert manager.calls == [
        ("unload", "dev.vibey.hub"),
        ("unload", "dev.vibey.worker"),
        ("forget", ""),
    ]
    assert not Path(hub.path).exists()
    assert Path(worker.path).read_text() == "edited by you"  # the operator's edit stays
    assert "dev.vibey.hub: unloaded; unit file removed" in said
    assert any("dev.vibey.worker: unloaded;" in s and "is kept" in s for s in said)
    assert "auto_services = false" in said[-1]


def test_unload_is_idempotent(tmp_path: Path) -> None:
    units = _units(tmp_path)
    units.write(("hub",), "always")
    said: list[str] = []
    assert _command(tmp_path, Manager(loaded={"dev.vibey.hub"}), units, said).run() == 0
    again: list[str] = []
    assert _command(tmp_path, Manager(), units, again).run() == 0
    assert again == ["vibey acp loaded no service here; nothing to unload"]


def test_a_unit_that_would_not_unload_keeps_its_file_and_fails(tmp_path: Path) -> None:
    units = _units(tmp_path)
    (hub,) = units.write(("hub",), "always")
    manager = Manager(loaded={"dev.vibey.hub"})
    manager.fail = {"dev.vibey.hub"}
    said: list[str] = []
    assert _command(tmp_path, manager, units, said).run() == 1
    assert Path(hub.path).exists()
    assert "not unloaded" in said[0]


def test_a_file_that_cannot_be_removed_or_a_manager_that_will_not_reload_fails(
    tmp_path: Path,
) -> None:
    units = _units(tmp_path)
    units.write(("hub",), "always")
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.chmod(0o500)
    manager, said = Manager(loaded={"dev.vibey.hub"}), []
    manager.reload_fails = True
    try:
        assert _command(tmp_path, manager, units, said).run() == 1
    finally:
        agents.chmod(0o700)
    assert any("dev.vibey.hub: unloaded;" in s for s in said)
    assert any("did not reload" in s for s in said)


def test_root_is_refused_and_no_machine_means_nothing(tmp_path: Path) -> None:
    manager, said = Manager(), []
    manager.refusal = "vibey acp is running as root"
    assert _command(tmp_path, manager, _units(tmp_path), said).run() == 1
    assert "root" in said[0]
    nothing: list[str] = []
    assert _command(tmp_path, Manager(), None, nothing).run() == 0
    assert "nothing to unload" in nothing[0]


def test_vibey_acp_unload_reaches_the_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class _Recorder:
        def run(self) -> int:
            calls.append("unload")
            return 0

    monkeypatch.setattr("vibey.cli.acp.ACP_UNLOAD", _Recorder())
    result = runner.invoke(app, ["acp", "unload"])
    assert result.exit_code == 0 and calls == ["unload"]


def test_an_unknown_action_is_a_usage_error() -> None:
    result = runner.invoke(app, ["acp", "reload"])
    assert result.exit_code == 2
    assert "unload" in result.output


def test_the_real_command_reads_the_users_own_file() -> None:
    from vibey.bootstrap import acp_user_config
    from vibey.cli.acp_unload import ACP_UNLOAD

    assert ACP_UNLOAD._user_config is acp_user_config  # type: ignore[attr-defined]
