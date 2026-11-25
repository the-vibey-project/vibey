# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An engine session's token file (SP-LOOPS Phase 6, Task 2; R1): `<run folder>/web-token`,
0600 in the run's own 0700 folder, made exclusively and never through a symlink, read only when
it is this account's own owner-only file, and removed without following a link.

Real files in a temporary folder; the modes are POSIX, so the module is skipped elsewhere.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from vibey.application.interfaces.session_web_principals_interface import (
    SessionTokenFilesInterface,
    SessionTokenSourceInterface,
)
from vibey.domain.errors import SessionGrantRefused
from vibey.infrastructure.hub.interfaces.session_token_store_interface import (
    SessionTokenStoreInterface,
)
from vibey.infrastructure.hub.local_token import TOKEN_BYTES
from vibey.infrastructure.hub.session_token_source import SecretsSessionTokenSource
from vibey.infrastructure.hub.session_token_store import WEB_TOKEN_FILE, SessionTokenStore

pytestmark = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")

TOKEN = "tok-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _run_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "run-x"
    folder.mkdir(mode=0o700)
    os.chmod(folder, 0o700)
    return folder


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_the_store_meets_both_seams() -> None:
    store = SessionTokenStore()
    assert isinstance(store, SessionTokenStoreInterface)
    assert isinstance(store, SessionTokenFilesInterface)


def test_write_makes_an_owner_only_file_in_an_owner_only_folder(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    old = os.umask(0)  # a permissive umask must not widen the file
    try:
        path = SessionTokenStore().write(folder, TOKEN)
    finally:
        os.umask(old)

    assert path == folder / WEB_TOKEN_FILE == folder / "web-token"
    assert path.read_text() == TOKEN
    assert _mode(path) == 0o600
    assert _mode(folder) == 0o700
    assert SessionTokenStore().read(path) == TOKEN


def test_write_refuses_a_file_that_is_already_there_and_leaves_it(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    store = SessionTokenStore()
    store.write(folder, TOKEN)

    with pytest.raises(SessionGrantRefused, match="already") as refused:
        store.write(folder, "tok-other")

    assert (folder / WEB_TOKEN_FILE).read_text() == TOKEN
    assert TOKEN not in str(refused.value)
    assert "tok-other" not in str(refused.value)


def test_write_refuses_a_symlink_where_the_file_goes(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    target = tmp_path / "elsewhere"
    (folder / WEB_TOKEN_FILE).symlink_to(target)  # dangling: O_EXCL still refuses it

    with pytest.raises(SessionGrantRefused, match="already"):
        SessionTokenStore().write(folder, TOKEN)

    assert not target.exists()


@pytest.mark.parametrize("mode", [0o750, 0o705, 0o770, 0o755])
def test_write_refuses_a_folder_open_to_other_accounts(tmp_path: Path, mode: int) -> None:
    folder = _run_folder(tmp_path)
    os.chmod(folder, mode)

    with pytest.raises(SessionGrantRefused, match="open to other accounts"):
        SessionTokenStore().write(folder, TOKEN)

    assert not (folder / WEB_TOKEN_FILE).exists()


def test_write_refuses_a_folder_that_is_a_symlink(tmp_path: Path) -> None:
    real = _run_folder(tmp_path)
    link = tmp_path / "run-link"
    link.symlink_to(real)

    with pytest.raises(SessionGrantRefused, match="not a folder"):
        SessionTokenStore().write(link, TOKEN)

    assert not (real / WEB_TOKEN_FILE).exists()


def test_write_refuses_a_file_where_the_folder_should_be(tmp_path: Path) -> None:
    plain = tmp_path / "run-file"
    plain.write_text("")

    with pytest.raises(SessionGrantRefused, match="not a folder"):
        SessionTokenStore().write(plain, TOKEN)


def test_write_refuses_a_missing_folder(tmp_path: Path) -> None:
    with pytest.raises(SessionGrantRefused, match="does not exist"):
        SessionTokenStore().write(tmp_path / "gone", TOKEN)


def test_write_refuses_a_folder_of_another_account(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _run_folder(tmp_path)
    mine = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: mine + 1)

    with pytest.raises(SessionGrantRefused, match="another account"):
        SessionTokenStore().write(folder, TOKEN)


def test_a_short_write_takes_the_file_away_and_names_only_the_path(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    store = SessionTokenStore(write=lambda fd, data: len(data) - 1)

    with pytest.raises(OSError, match="short write") as failed:
        store.write(folder, TOKEN)

    assert not (folder / WEB_TOKEN_FILE).exists()
    assert TOKEN not in str(failed.value)


def test_a_failing_write_takes_the_file_away(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)

    def broken(fd: int, data: bytes) -> int:
        raise OSError("no space left on device")

    with pytest.raises(OSError, match="no space"):
        SessionTokenStore(write=broken).write(folder, TOKEN)

    assert not (folder / WEB_TOKEN_FILE).exists()


def test_read_refuses_a_file_open_to_other_accounts(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    path = SessionTokenStore().write(folder, TOKEN)
    os.chmod(path, 0o640)

    with pytest.raises(SessionGrantRefused, match="open to other accounts") as refused:
        SessionTokenStore().read(path)

    assert TOKEN not in str(refused.value)


def test_read_refuses_a_file_of_another_account(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _run_folder(tmp_path)
    path = SessionTokenStore().write(folder, TOKEN)
    mine = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: mine + 1)

    with pytest.raises(SessionGrantRefused, match="another account"):
        SessionTokenStore().read(path)


def test_read_refuses_a_symlink(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    path = SessionTokenStore().write(folder, TOKEN)
    link = folder / "link"
    link.symlink_to(path)

    with pytest.raises(SessionGrantRefused, match="cannot be read"):
        SessionTokenStore().read(link)


def test_read_refuses_something_that_is_not_a_regular_file(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    inner = folder / WEB_TOKEN_FILE
    inner.mkdir(mode=0o700)

    with pytest.raises(SessionGrantRefused, match="not a regular file"):
        SessionTokenStore().read(inner)


def test_read_of_a_missing_file_is_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        SessionTokenStore().read(tmp_path / WEB_TOKEN_FILE)


def test_read_refuses_an_empty_file(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    path = folder / WEB_TOKEN_FILE
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)

    with pytest.raises(SessionGrantRefused, match="holds no token"):
        SessionTokenStore().read(path)


def test_remove_takes_the_file_away_and_is_idempotent(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    store = SessionTokenStore()
    path = store.write(folder, TOKEN)

    assert store.remove(path) is True
    assert not path.exists()
    assert store.remove(path) is True  # already gone is removed


def test_remove_leaves_a_symlink_and_what_it_points_at(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    target = tmp_path / "precious"
    target.write_text("keep me")
    link = folder / WEB_TOKEN_FILE
    link.symlink_to(target)

    assert SessionTokenStore().remove(link) is False
    assert link.is_symlink()
    assert target.read_text() == "keep me"


def test_remove_leaves_a_folder(tmp_path: Path) -> None:
    folder = _run_folder(tmp_path)
    inner = folder / WEB_TOKEN_FILE
    inner.mkdir()

    assert SessionTokenStore().remove(inner) is False
    assert inner.is_dir()


def test_remove_says_so_when_the_file_cannot_be_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _run_folder(tmp_path)
    path = SessionTokenStore().write(folder, TOKEN)

    def refuse(target: object) -> None:
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(os, "unlink", refuse)

    assert SessionTokenStore().remove(path) is False


def test_remove_of_a_path_that_cannot_be_looked_at_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(target: object) -> os.stat_result:
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(os, "lstat", refuse)

    assert SessionTokenStore().remove(tmp_path / WEB_TOKEN_FILE) is False


def test_the_token_source_asks_for_the_hub_token_strength() -> None:
    asked: list[int] = []

    def make(nbytes: int) -> str:
        asked.append(nbytes)
        return f"fixed-{nbytes}"

    source = SecretsSessionTokenSource(make=make)

    assert isinstance(source, SessionTokenSourceInterface)
    assert source.token() == f"fixed-{TOKEN_BYTES}"
    assert asked == [TOKEN_BYTES] == [32]


def test_remove_of_a_file_removed_meanwhile_counts_as_gone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = _run_folder(tmp_path)
    path = SessionTokenStore().write(folder, TOKEN)

    def raced(target: object) -> None:
        raise FileNotFoundError(target)

    monkeypatch.setattr(os, "unlink", raced)

    assert SessionTokenStore().remove(path) is True
