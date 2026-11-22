# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`SearxngFiles`: the settings and the provision record, written atomically, 0600, in a 0700
folder of the person's own, never through a link (ADR-0102)."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from vibey.domain.searxng import SearxngProvision
from vibey.infrastructure.searxng.interfaces.searxng_files_interface import SearxngFilesInterface
from vibey.infrastructure.searxng.searxng_files import RECORD_FILE, SETTINGS_FILE, SearxngFiles

IMAGE = "docker.io/searxng/searxng@sha256:" + "ab" * 32
_REAL_PERSONAL = SearxngFiles.__dict__["personal"]
"""Read at import, before the suite's hermetic fixture stands in for it."""


def _hex(counter: list[int]) -> object:
    def token_hex(n: int) -> str:
        counter.append(n)
        return f"{len(counter):x}" * (2 * n) if len(counter) < 10 else "f" * (2 * n)

    return token_hex


def _files(tmp_path: Path, calls: list[int] | None = None) -> SearxngFiles:
    return SearxngFiles(
        tmp_path / "config" / "searxng", token_hex=_hex(calls if calls is not None else [])
    )  # type: ignore[arg-type]


def _ensure(files: SearxngFiles, **changes: object) -> SearxngProvision:
    values: dict[str, object] = {
        "image": IMAGE,
        "port": 28180,
        "label": "dev.vibey.searxng",
        "runtime": "/usr/bin/podman",
        **changes,
    }
    return files.ensure(**values)  # type: ignore[arg-type]


def test_the_files_are_their_interface(tmp_path: Path) -> None:
    assert isinstance(_files(tmp_path), SearxngFilesInterface)


def test_nothing_is_provisioned_until_a_record_is_written(tmp_path: Path) -> None:
    files = _files(tmp_path)
    assert files.read() is None
    assert not files.folder.exists()


def test_ensure_writes_both_files_0600_in_a_0700_folder(tmp_path: Path) -> None:
    files = _files(tmp_path)
    provision = _ensure(files)

    assert provision.marker.startswith("vibey-") and len(provision.marker) == 38
    assert stat.S_IMODE(files.folder.stat().st_mode) == 0o700
    for name in (SETTINGS_FILE, RECORD_FILE):
        assert stat.S_IMODE((files.folder / name).stat().st_mode) == 0o600
    record = json.loads((files.folder / RECORD_FILE).read_text("utf-8"))
    assert record == {
        "image": IMAGE,
        "port": 28180,
        "marker": provision.marker,
        "label": "dev.vibey.searxng",
        "runtime": "/usr/bin/podman",
    }
    settings = (files.folder / SETTINGS_FILE).read_text("utf-8")
    assert f'instance_name: "{provision.marker}"' in settings
    assert files.read() == provision
    assert files.settings_path == files.folder / SETTINGS_FILE
    assert not [p for p in files.folder.iterdir() if p.name.startswith(".")]  # no staged leftovers


def test_the_secret_and_marker_are_made_once_and_kept(tmp_path: Path) -> None:
    calls: list[int] = []
    files = _files(tmp_path, calls)
    first = _ensure(files)
    settings = (files.folder / SETTINGS_FILE).read_text("utf-8")
    again = _ensure(files, port=28181, runtime="/usr/local/bin/docker")

    assert again.marker == first.marker
    assert (again.port, again.runtime) == (28181, "/usr/local/bin/docker")
    assert (files.folder / SETTINGS_FILE).read_text("utf-8") == settings
    # Staging names each time; the marker and the secret once, on the first install only.
    assert (calls.count(16), calls.count(32)) == (1, 1)
    assert set(calls) == {8, 16, 32}


def test_settings_lost_are_made_again_with_a_new_marker(tmp_path: Path) -> None:
    files = _files(tmp_path)
    first = _ensure(files)
    (files.folder / SETTINGS_FILE).unlink()
    again = _ensure(files)
    assert again.marker != first.marker
    assert f'"{again.marker}"' in (files.folder / SETTINGS_FILE).read_text("utf-8")


def test_a_bad_provision_writes_nothing(tmp_path: Path) -> None:
    files = _files(tmp_path)
    with pytest.raises(ValueError, match="image"):
        _ensure(files, image="docker.io/searxng/searxng:latest")
    assert not (files.folder / SETTINGS_FILE).exists()
    assert not (files.folder / RECORD_FILE).exists()


def test_a_linked_folder_is_refused(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    files = _files(tmp_path)
    files.folder.parent.mkdir(parents=True)
    files.folder.symlink_to(elsewhere)
    with pytest.raises(ValueError, match="link"):
        _ensure(files)
    assert list(elsewhere.iterdir()) == []


@pytest.mark.parametrize("name", [SETTINGS_FILE, RECORD_FILE])
def test_a_linked_file_is_replaced_never_written_through(tmp_path: Path, name: str) -> None:
    files = _files(tmp_path)
    files.folder.mkdir(parents=True, mode=0o700)
    target = tmp_path / "target"
    target.write_text("keep me", "utf-8")
    (files.folder / name).symlink_to(target)
    _ensure(files)
    assert target.read_text("utf-8") == "keep me"
    assert not (files.folder / name).is_symlink()


def test_a_linked_record_is_never_read(tmp_path: Path) -> None:
    files = _files(tmp_path)
    provision = _ensure(files)
    real = tmp_path / "record.json"
    os.replace(files.folder / RECORD_FILE, real)
    (files.folder / RECORD_FILE).symlink_to(real)
    with pytest.raises(ValueError, match="link"):
        files.read()
    assert json.loads(real.read_text("utf-8"))["marker"] == provision.marker


def test_a_wider_folder_is_narrowed(tmp_path: Path) -> None:
    files = _files(tmp_path)
    files.folder.mkdir(parents=True, mode=0o755)
    os.chmod(files.folder, 0o755)
    _ensure(files)
    assert stat.S_IMODE(files.folder.stat().st_mode) == 0o700


@pytest.mark.parametrize(
    "text",
    ["not json", "[]", json.dumps({"image": IMAGE}), json.dumps({"port": 1}) + "x"],
)
def test_a_record_vibey_did_not_write_is_refused(tmp_path: Path, text: str) -> None:
    files = _files(tmp_path)
    files.folder.mkdir(parents=True, mode=0o700)
    (files.folder / RECORD_FILE).write_text(text, "utf-8")
    with pytest.raises(ValueError):
        files.read()


def test_settings_ready_only_for_a_regular_file(tmp_path: Path) -> None:
    files = _files(tmp_path)
    assert not files.settings_ready()
    _ensure(files)
    assert files.settings_ready()
    (files.folder / SETTINGS_FILE).unlink()
    (files.folder / SETTINGS_FILE).symlink_to(tmp_path)
    assert not files.settings_ready()


def test_purge_removes_both_files_and_the_folder(tmp_path: Path) -> None:
    files = _files(tmp_path)
    assert files.purge() == ()
    _ensure(files)
    assert files.purge() == (SETTINGS_FILE, RECORD_FILE)
    assert not files.folder.exists()
    assert files.read() is None


def test_purge_keeps_a_folder_that_holds_something_else(tmp_path: Path) -> None:
    files = _files(tmp_path)
    _ensure(files)
    (files.folder / "mine.txt").write_text("x", "utf-8")
    assert files.purge() == (SETTINGS_FILE, RECORD_FILE)
    assert (files.folder / "mine.txt").exists()


def test_the_personal_folder_is_in_the_persons_configuration_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(SearxngFiles, "personal", _REAL_PERSONAL)
    monkeypatch.setattr(
        "vibey.infrastructure.user_config_folder.user_config_path", lambda name: tmp_path / name
    )
    assert SearxngFiles.personal().folder == tmp_path / "vibey" / "searxng"
    assert SearxngFiles.personal(tmp_path / "mine").folder == tmp_path / "mine" / "searxng"


def test_a_linked_folder_is_never_read(tmp_path: Path) -> None:
    files = _files(tmp_path)
    _ensure(files)
    elsewhere = tmp_path / "moved"
    os.replace(files.folder, elsewhere)
    files.folder.symlink_to(elsewhere)
    with pytest.raises(ValueError, match="link"):
        files.read()


def test_a_folder_someone_else_owns_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _files(tmp_path)
    files.folder.mkdir(parents=True, mode=0o700)
    real = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: real + 1)
    with pytest.raises(ValueError, match="not yours"):
        _ensure(files)
    assert list(files.folder.iterdir()) == []
