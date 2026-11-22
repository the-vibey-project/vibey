# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`HostInstaller.apply_plan`'s writes: atomic, no wider than before, never out of home (S-4).

`vibey acp` applies these plans unattended, and a client's config may hold other servers' API
keys. Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest

from vibey.domain.host_clients import ConnectPlanItem, HostClientError
from vibey.infrastructure.mcp.host_installer import HostInstaller


def _installer(tmp_path: Path) -> tuple[HostInstaller, Path]:
    home = tmp_path / "home"
    (home / ".cursor").mkdir(parents=True)
    installer = HostInstaller(
        home_dir=lambda: home,
        project_dir=lambda: tmp_path / "project",
        platform="linux",
        which=lambda _name: "/usr/local/bin/vibey",
    )
    return installer, home


def _connect(installer: HostInstaller) -> None:
    installer.apply_plan(installer.build_plan(["cursor"]))


def test_a_new_config_is_owner_only_and_no_temporary_file_is_left(tmp_path: Path) -> None:
    installer, home = _installer(tmp_path)

    _connect(installer)

    target = home / ".cursor" / "mcp.json"
    assert json.loads(target.read_text())["mcpServers"]["vibey"]["args"] == ["mcp"]
    assert target.stat().st_mode & 0o777 == 0o600
    assert sorted(p.name for p in (home / ".cursor").iterdir()) == ["mcp.json"]


def test_a_changed_config_and_its_backup_keep_the_originals_permissions(tmp_path: Path) -> None:
    installer, home = _installer(tmp_path)
    target = home / ".cursor" / "mcp.json"
    target.write_text('{"mcpServers": {"other": {"env": {"KEY": "secret"}}}}')
    target.chmod(0o600)
    backup = home / ".cursor" / "mcp.json.vibey.bak"
    backup.write_text("stale")
    backup.chmod(0o644)  # a backup left wider by an older vibey is narrowed

    _connect(installer)

    assert target.stat().st_mode & 0o777 == 0o600
    assert backup.stat().st_mode & 0o777 == 0o600
    assert "secret" in backup.read_text()
    assert json.loads(target.read_text())["mcpServers"]["other"]["env"]["KEY"] == "secret"


def test_a_config_folder_symlinked_inside_home_is_written_where_it_points(tmp_path: Path) -> None:
    installer, home = _installer(tmp_path)
    dotfiles = home / "dotfiles" / "cursor"
    dotfiles.mkdir(parents=True)
    (home / ".cursor").rmdir()
    (home / ".cursor").symlink_to(dotfiles, target_is_directory=True)

    _connect(installer)

    assert (home / ".cursor").is_symlink()
    assert "vibey" in json.loads((dotfiles / "mcp.json").read_text())["mcpServers"]


def test_a_config_file_that_is_a_symlink_is_refused_even_inside_home(tmp_path: Path) -> None:
    installer, home = _installer(tmp_path)
    (home / "dotfiles").mkdir()
    (home / "dotfiles" / "cursor.json").write_text("{}")
    (home / ".cursor" / "mcp.json").symlink_to(home / "dotfiles" / "cursor.json")

    with pytest.raises(HostClientError, match="symbolic link"):
        _connect(installer)

    assert (home / "dotfiles" / "cursor.json").read_text() == "{}"


@pytest.mark.parametrize("linked", ["file", "folder"])
def test_a_user_config_that_resolves_outside_home_is_refused(tmp_path: Path, linked: str) -> None:
    installer, home = _installer(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "mcp.json").write_text("{}")
    if linked == "file":
        (home / ".cursor" / "mcp.json").symlink_to(outside / "mcp.json")
    else:
        (home / ".cursor").rmdir()
        (home / ".cursor").symlink_to(outside, target_is_directory=True)

    with pytest.raises(HostClientError, match="not inside your home folder|symbolic link"):
        _connect(installer)

    assert (outside / "mcp.json").read_text() == "{}"


def _item(installer: HostInstaller, client: str, target: Path) -> ConnectPlanItem:
    planned = installer.build_plan([client])[0]
    return dataclasses.replace(planned, target_path=str(target), action="create", backup_path=None)


def test_a_user_config_spelled_outside_home_is_refused(tmp_path: Path) -> None:
    installer, _ = _installer(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    with pytest.raises(HostClientError, match="not inside your home folder"):
        installer.apply_plan([_item(installer, "cursor", elsewhere / "mcp.json")])

    assert list(elsewhere.iterdir()) == []


@pytest.mark.parametrize(
    ("client", "relative"), [("claude_code", ".mcp.json"), ("vscode", ".vscode/mcp.json")]
)
def test_a_project_config_resolving_outside_the_project_is_refused(
    tmp_path: Path, client: str, relative: str
) -> None:
    installer, _ = _installer(tmp_path)
    project, outside = tmp_path / "project", tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    target = project / relative
    if "/" in relative:
        target.parent.symlink_to(outside, target_is_directory=True)
    else:
        (outside / "mcp.json").write_text("{}")
        target.symlink_to(outside / "mcp.json")

    with pytest.raises(HostClientError, match="not inside the project folder|symbolic link"):
        installer.apply_plan(installer.build_plan([client]))

    assert [p.read_text() for p in outside.iterdir()] in ([], ["{}"])


def test_a_project_config_inside_the_project_is_written(tmp_path: Path) -> None:
    installer, _ = _installer(tmp_path)
    project = tmp_path / "project"
    (project / ".vscode").mkdir(parents=True)

    installer.apply_plan(installer.build_plan(["claude_code", "vscode"]))

    assert "vibey" in json.loads((project / ".mcp.json").read_text())["mcpServers"]
    assert "vibey" in json.loads((project / ".vscode" / "mcp.json").read_text())["servers"]


def test_a_backup_path_that_is_a_symlink_is_never_followed(tmp_path: Path) -> None:
    installer, home = _installer(tmp_path)
    (home / ".cursor" / "mcp.json").write_text("{}")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.write_text("untouched")
    (home / ".cursor" / "mcp.json.vibey.bak").symlink_to(elsewhere)

    with pytest.raises(HostClientError, match="symbolic link"):
        _connect(installer)

    assert elsewhere.read_text() == "untouched"


def test_a_link_swapped_in_after_the_check_is_never_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer, home = _installer(tmp_path)
    target = home / ".cursor" / "mcp.json"
    target.write_text("{}")
    outside = tmp_path / "outside.json"
    outside.write_text("untouched")
    checked = installer._folder

    def then_swap(item: ConnectPlanItem) -> Path:
        folder = checked(item)
        target.unlink()
        target.symlink_to(outside)  # a race: the check passed, then the file became a link
        return folder

    monkeypatch.setattr(installer, "_folder", then_swap)
    with pytest.raises(OSError):
        _connect(installer)

    assert outside.read_text() == "untouched"


def test_a_failed_write_leaves_the_old_config_and_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer, home = _installer(tmp_path)
    target = home / ".cursor" / "mcp.json"
    target.write_text("{}")

    def broken(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", broken)
    with pytest.raises(OSError, match="disk full"):
        _connect(installer)

    assert target.read_text() == "{}"
    assert sorted(p.name for p in target.parent.iterdir()) == ["mcp.json", "mcp.json.vibey.bak"]


def test_a_file_that_appeared_after_the_plan_is_replaced_keeping_its_permissions(
    tmp_path: Path,
) -> None:
    installer, home = _installer(tmp_path)
    plan = installer.build_plan(["cursor"])  # planned as a create: no file yet, no backup
    target = home / ".cursor" / "mcp.json"
    target.write_text("{}")
    target.chmod(0o640)

    installer.apply_plan(plan)

    assert target.stat().st_mode & 0o777 == 0o640
    assert not (home / ".cursor" / "mcp.json.vibey.bak").exists()


def test_a_staged_file_that_cannot_be_written_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer, home = _installer(tmp_path)

    def broken(*args: object) -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr(os, "fchmod", broken)
    with pytest.raises(OSError, match="read-only"):
        _connect(installer)

    assert list((home / ".cursor").iterdir()) == []


def test_a_backup_that_cannot_be_written_leaves_the_config_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installer, home = _installer(tmp_path)
    target = home / ".cursor" / "mcp.json"
    target.write_text("{}")

    def broken(*args: object) -> None:
        raise OSError("quota exceeded")

    monkeypatch.setattr(os, "fchmod", broken)
    with pytest.raises(OSError, match="quota"):
        _connect(installer)

    assert target.read_text() == "{}"
