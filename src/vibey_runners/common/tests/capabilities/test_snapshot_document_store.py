# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the run's capability document lives: written once, 0600, into the run's own 0700
folder, and read back only from a folder and a file nobody else could have changed (SP-LOOPS
Phase 4, Task 2; R1, R14; Review Focus 5)."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from fakes import RecordingReader

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.interfaces.snapshot_document_store_interface import (
    SnapshotDocumentStoreInterface,
)
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.snapshot_document import (
    DOCUMENT_VERSION,
    SnapshotDocument,
)
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError
from vibey_runners.common.capabilities.snapshot_document_store import (
    DOCUMENT_MAX_BYTES,
    DOCUMENT_NAME,
    SnapshotDocumentStore,
)

DIGEST = "sha256:" + "0f" * 32


@pytest.fixture
def run(tmp_path: Path) -> Path:
    folder = Path(os.path.realpath(tmp_path)) / "run-1"
    folder.mkdir(mode=0o700)
    return folder


def _document(run: Path) -> SnapshotDocument:
    snapshot = CapabilitySnapshot((), SkillCatalog((), ()), (), DIGEST, run)
    return SnapshotDocument.of(snapshot, BundleSpec.default(), [run.parent / "input"])


def _written(run: Path) -> Path:
    return SnapshotDocumentStore().write(_document(run), run)


def test_a_written_document_is_0600_and_reads_back(run: Path) -> None:
    store = SnapshotDocumentStore()
    assert isinstance(store, SnapshotDocumentStoreInterface)
    path = store.write(_document(run), run)
    assert path == run / DOCUMENT_NAME == run / "capabilities.json"
    assert stat.S_IMODE(os.lstat(path).st_mode) == 0o600
    assert store.read(path) == _document(run)


def test_the_mode_is_0600_whatever_the_umask(run: Path) -> None:
    previous = os.umask(0o377)
    try:
        path = _written(run)
    finally:
        os.umask(previous)
    assert stat.S_IMODE(os.lstat(path).st_mode) == 0o600


def test_write_refuses_an_existing_document(run: Path) -> None:
    path = _written(run)
    before = path.read_bytes()
    with pytest.raises(SnapshotDocumentError, match="cannot be written"):
        _written(run)
    assert path.read_bytes() == before


def test_write_never_follows_a_symlink_in_the_documents_place(run: Path, tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.json"
    (run / DOCUMENT_NAME).symlink_to(target)
    with pytest.raises(SnapshotDocumentError, match="cannot be written"):
        _written(run)
    assert not target.exists()


def test_write_into_a_missing_folder_is_refused(run: Path) -> None:
    with pytest.raises(SnapshotDocumentError, match="cannot be written"):
        SnapshotDocumentStore().write(_document(run), run / "gone")


@pytest.mark.parametrize("mode", [0o770, 0o750, 0o705, 0o701, 0o720])
def test_a_group_writable_folder_is_refused(run: Path, mode: int) -> None:
    path = _written(run)
    run.chmod(mode)
    try:
        with pytest.raises(SnapshotDocumentError, match="group or others"):
            SnapshotDocumentStore().read(path)
    finally:
        run.chmod(0o700)


def test_a_folder_another_user_owns_is_refused(run: Path) -> None:
    path = _written(run)
    with pytest.raises(SnapshotDocumentError, match="not owned by"):
        SnapshotDocumentStore(uid=os.getuid() + 1).read(path)


def test_a_folder_that_is_a_symlink_is_refused(run: Path, tmp_path: Path) -> None:
    path = _written(run)
    link = tmp_path / "link"
    link.symlink_to(run, target_is_directory=True)
    with pytest.raises(SnapshotDocumentError, match="not a folder"):
        SnapshotDocumentStore().read(link / path.name)


@pytest.mark.parametrize("mode", [0o644, 0o640, 0o400, 0o700, 0o604])
def test_a_document_that_is_not_0600_is_refused(run: Path, mode: int) -> None:
    path = _written(run)
    path.chmod(mode)
    with pytest.raises(SnapshotDocumentError, match="0600"):
        SnapshotDocumentStore().read(path)


def test_a_document_that_is_a_symlink_is_refused(run: Path) -> None:
    path = _written(run)
    path.rename(run / "real.json")
    path.symlink_to(run / "real.json")
    with pytest.raises(SnapshotDocumentError, match="not a regular file"):
        SnapshotDocumentStore().read(path)


def test_a_missing_document_is_refused(run: Path) -> None:
    with pytest.raises(SnapshotDocumentError, match="cannot be read"):
        SnapshotDocumentStore().read(run / DOCUMENT_NAME)


def test_a_document_over_four_mib_is_refused_unread(run: Path) -> None:
    assert DOCUMENT_MAX_BYTES == 4 * 1024 * 1024
    path = run / DOCUMENT_NAME
    path.touch(mode=0o600)
    os.truncate(path, DOCUMENT_MAX_BYTES + 1)
    reader = RecordingReader()
    with pytest.raises(SnapshotDocumentError, match="larger than 4194304 bytes"):
        SnapshotDocumentStore(reader=reader).read(path)
    assert reader.paths == []


def test_a_document_that_grows_past_the_cap_while_it_is_read_is_refused(run: Path) -> None:
    """The reader's own cap is the second guard, after the size the folder reported."""
    path = _written(run)
    with pytest.raises(SnapshotDocumentError, match="cannot be read"):
        SnapshotDocumentStore(reader=RecordingReader({path: ValueError("grew")})).read(path)


def test_a_document_that_is_not_utf8_is_refused(run: Path) -> None:
    path = run / DOCUMENT_NAME
    path.touch(mode=0o600)
    path.write_bytes(b'{"version": "\xff"}')
    with pytest.raises(SnapshotDocumentError, match="cannot be read"):
        SnapshotDocumentStore().read(path)


def test_a_document_whose_content_is_refused_says_why(run: Path) -> None:
    path = run / DOCUMENT_NAME
    path.touch(mode=0o600)
    text = _document(run).to_json()
    assert f'"version":{DOCUMENT_VERSION}' in text
    path.write_text(text.replace(f'"version":{DOCUMENT_VERSION}', '"version":9'), "utf-8")
    with pytest.raises(SnapshotDocumentError, match="version"):
        SnapshotDocumentStore().read(path)
