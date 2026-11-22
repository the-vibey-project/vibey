# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`SupervisorInstaller`: where a supervised unit's paths come from, and how its file is written
(#1189, ADR-0101).

`vibey supervisor install` writes with `overwrite=True` (today's behaviour); `vibey acp` with
`overwrite=False`, which never replaces a unit the operator edited. Either way a unit is written
atomically, readable by all and writable by its owner only, inside the directory it was meant
for and never through a symbolic link. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import os
import stat
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from vibey.domain.supervisor import SupervisorPlanner, SupervisorSettings
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.interfaces.supervisor_installer_interface import (
    SupervisorInstallerInterface,
)
from vibey.infrastructure.supervisor import SupervisorHost
from vibey.infrastructure.supervisor_installer import ENV_TEMPLATE, SupervisorInstaller


def _no_manager(argv: Sequence[str]) -> tuple[int, str]:
    raise AssertionError(f"the installer asked the service manager: {argv}")


def _host(tmp_path: Path, platform: str = "launchd") -> SupervisorHost:
    return SupervisorHost(
        platform,
        home=tmp_path / "home",
        environ={},
        uid=501,
        run=_no_manager,
        temp_roots=lambda: (Path("/volatile"),),
    )


def _installer(tmp_path: Path, platform: str = "launchd", **kw: object) -> SupervisorInstaller:
    return SupervisorInstaller(
        _host(tmp_path, platform),
        SupervisorPlanner(),
        TimerUnitRenderer(),
        which=lambda name: "/opt/vibey/bin/vibey",
        python="/opt/vibey/bin/python",
        **kw,  # type: ignore[arg-type]
    )


def _services(tmp_path: Path, installer: SupervisorInstaller, names: tuple[str, ...] = ("hub",)):
    workdir = tmp_path / "work"
    workdir.mkdir(exist_ok=True)
    settings = SupervisorSettings(delivery=False)
    paths = installer.paths(settings, workdir)
    return settings, SupervisorPlanner().acp_services(
        settings, paths, names=names, restart="always"
    )


def test_the_installer_is_its_interface(tmp_path: Path) -> None:
    assert isinstance(_installer(tmp_path), SupervisorInstallerInterface)


def test_a_new_unit_is_created_owner_writable_and_readable(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    assert (outcome.label, outcome.path, outcome.action) == ("dev.vibey.hub", str(unit), "created")
    assert "<string>serve</string>" in unit.read_text()
    assert stat.S_IMODE(unit.stat().st_mode) == 0o644
    assert [p.name for p in unit.parent.iterdir()] == [unit.name]  # no staged file left behind


def test_the_same_unit_again_is_unchanged(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    assert outcome.action == "unchanged"


def test_overwrite_false_keeps_a_differing_operator_unit(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    operator_text = unit.read_text().replace("<integer>30</integer>", "<integer>90</integer>")
    unit.write_text(operator_text)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    assert outcome.action == "kept-differing" and unit.read_text() == operator_text
    assert "edited" in outcome.detail


def test_overwrite_true_replaces_a_differing_unit(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    unit.parent.mkdir(parents=True)
    unit.write_text("old")

    (outcome,) = installer.write(services, settings, out=None, overwrite=True, path_env="/usr/bin")

    assert outcome.action == "updated"
    assert "<string>serve</string>" in unit.read_text()


def test_overwrite_false_never_replaces_a_unit_that_appears_while_it_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The operator's file lands between the check and the write: the write must not win.
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    unit.parent.mkdir(parents=True)
    real_open = os.open

    def racing_open(path: str, flags: int, *args: object, **kw: object) -> int:
        if str(path).startswith(".dev.vibey.hub.plist") and not unit.exists():
            unit.write_text("the operator's own")
        return real_open(path, flags, *args, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", racing_open)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    assert unit.read_text() == "the operator's own"
    assert outcome.action == "kept-differing"
    assert [p.name for p in unit.parent.iterdir()] == [unit.name]


def test_a_unit_that_is_a_symbolic_link_is_never_written_through(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    outside = tmp_path / "outside.plist"
    outside.write_text("someone else's")
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    unit.parent.mkdir(parents=True)
    unit.symlink_to(outside)

    for overwrite in (False, True):
        (outcome,) = installer.write(
            services, settings, out=None, overwrite=overwrite, path_env="/usr/bin"
        )
        assert outcome.action == "failed"
        assert "symbolic link" in outcome.detail
    assert outside.read_text() == "someone else's"
    assert unit.is_symlink()


def test_a_unit_that_is_a_dangling_link_is_never_created_through(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    target = tmp_path / "elsewhere" / "planted.plist"
    target.parent.mkdir()
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    unit.parent.mkdir(parents=True)
    unit.symlink_to(target)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    assert outcome.action == "failed"
    assert not target.exists()


def test_a_unit_path_that_is_no_regular_file_is_refused(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    unit.mkdir(parents=True)

    (outcome,) = installer.write(services, settings, out=None, overwrite=True, path_env="/usr/bin")

    assert outcome.action == "failed"
    assert "not a regular file" in outcome.detail


def test_a_unit_directory_swapped_for_a_link_after_it_was_resolved_is_not_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    real_realpath = os.path.realpath

    def swapped(path: object) -> str:
        resolved = real_realpath(path)  # type: ignore[arg-type]
        if resolved == str(agents) and not agents.is_symlink():
            agents.rmdir()
            agents.symlink_to(elsewhere)
        return resolved

    monkeypatch.setattr(os.path, "realpath", swapped)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    assert outcome.action == "failed"
    assert list(elsewhere.iterdir()) == []


def test_one_unit_that_fails_leaves_the_others_written(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer, names=("hub", "worker"))
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    (agents / "dev.vibey.hub.plist").mkdir(parents=True)

    hub, worker = installer.write(
        services, settings, out=None, overwrite=False, path_env="/usr/bin"
    )

    assert (hub.action, worker.action) == ("failed", "created")


def test_a_value_no_unit_can_carry_writes_nothing(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer, names=("hub", "worker"))
    bad = (services[0], replace(services[1], working_directory="/x\nExecStartPre=/bin/evil"))

    with pytest.raises(ValueError, match="control character"):
        installer.write(bad, settings, out=None, overwrite=False, path_env="/usr/bin")

    assert not (tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist").exists()


def test_systemd_always_units_carry_the_start_limit_from_the_settings(tmp_path: Path) -> None:
    installer = _installer(tmp_path, "systemd")
    settings, services = _services(tmp_path, installer)
    settings = replace(settings, start_limit_interval_seconds=120, start_limit_burst=3)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    text = Path(outcome.path).read_text()
    assert "StartLimitIntervalSec=120" in text.splitlines()
    assert "StartLimitBurst=3" in text.splitlines()
    assert "Restart=always" in text.splitlines()
    assert outcome.path.endswith("/.config/systemd/user/dev.vibey.hub.service")


def test_units_go_where_out_says(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)

    (outcome,) = installer.write(
        services, settings, out=tmp_path / "review", overwrite=True, path_env="/usr/bin"
    )

    assert outcome.path == str(tmp_path / "review" / "dev.vibey.hub.plist")


def test_the_env_file_is_created_private_and_never_through_a_link(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    env_file = tmp_path / "cfg" / "supervisor.env"

    assert installer.env_file(env_file, ENV_TEMPLATE) is True
    assert env_file.read_text() == ENV_TEMPLATE
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert installer.env_file(env_file, "other") is False
    assert env_file.read_text() == ENV_TEMPLATE

    target = tmp_path / "planted.env"
    link = tmp_path / "cfg" / "linked.env"
    link.symlink_to(target)
    assert installer.env_file(link, ENV_TEMPLATE) is False  # an existing name, even dangling
    assert not target.exists()


def test_paths_refuses_what_the_cli_refused(tmp_path: Path) -> None:
    installer = SupervisorInstaller(
        _host(tmp_path),
        SupervisorPlanner(),
        TimerUnitRenderer(),
        which=lambda name: None,
        python="/opt/vibey/bin/python",
    )
    with pytest.raises(ValueError, match="vibey is not on PATH"):
        installer.paths(SupervisorSettings(delivery=False), tmp_path)


def test_an_env_file_that_appears_while_it_is_created_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "supervisor.env"
    env_file.write_text("the operator's own")
    monkeypatch.setattr(os.path, "lexists", lambda path: False)  # it lands after the check

    assert _installer(tmp_path).env_file(env_file, ENV_TEMPLATE) is False
    assert env_file.read_text() == "the operator's own"


def test_a_unit_directory_vibey_may_not_write_is_a_failed_outcome(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    agents.mkdir(parents=True)
    agents.chmod(0o500)
    try:
        (outcome,) = installer.write(
            services, settings, out=None, overwrite=False, path_env="/usr/bin"
        )
    finally:
        agents.chmod(0o700)
    assert outcome.action == "failed" and "denied" in outcome.detail.lower()


def test_a_write_that_breaks_leaves_no_staged_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)

    def broken(fd: int) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "fsync", broken)
    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    agents = tmp_path / "home" / "Library" / "LaunchAgents"
    assert outcome.action == "failed" and "No space left" in outcome.detail
    assert list(agents.iterdir()) == []


@pytest.mark.parametrize("appears", ["the same unit", "a link"])
def test_what_appears_while_a_new_unit_is_written_decides_the_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, appears: str
) -> None:
    installer = _installer(tmp_path)
    settings, services = _services(tmp_path, installer)
    rendered = TimerUnitRenderer().launchd_service(
        services[0], path_env="/usr/bin", restart_seconds=settings.restart_seconds
    )
    unit = tmp_path / "home" / "Library" / "LaunchAgents" / "dev.vibey.hub.plist"
    unit.parent.mkdir(parents=True)
    outside = tmp_path / "outside"
    real_open = os.open

    def racing_open(path: str, flags: int, *args: object, **kw: object) -> int:
        if str(path).startswith(".dev.vibey.hub.plist") and not os.path.lexists(unit):
            if appears == "a link":
                unit.symlink_to(outside)
            else:
                unit.write_text(rendered)
        return real_open(path, flags, *args, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "open", racing_open)

    (outcome,) = installer.write(services, settings, out=None, overwrite=False, path_env="/usr/bin")

    if appears == "a link":
        assert outcome.action == "failed"
        assert not outside.exists()
    else:
        assert outcome.action == "unchanged"
    assert sorted(p.name for p in unit.parent.iterdir()) == [unit.name]
