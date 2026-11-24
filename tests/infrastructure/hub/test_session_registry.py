# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The session principals the worker minted, as the hub finds them (SP-LOOPS Phase 6, Task 2).

The worker and the hub are separate processes on one host, so the registry is files in the
hub's own owner-only state folder -- `<state_dir>/sessions/<sha-256 hex>.json`, one per session,
read afresh on every lookup, the way `devices.json` is. Each holds the principal, never the token.

Real files in a temporary folder; the modes are POSIX, so the module is skipped elsewhere.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from uuid import UUID

import pytest

from vibey.application.interfaces.session_web_principals_interface import (
    SessionPrincipalRegistryInterface,
)
from vibey.domain.session_principal import SessionPrincipal
from vibey.infrastructure.hub.interfaces.session_registry_interface import (
    SessionRegistryInterface,
)
from vibey.infrastructure.hub.session_registry import SESSIONS_FOLDER, SessionRegistry

pytestmark = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")

RUN = UUID("00000000-0000-4000-8000-000000000001")
TOKEN = "tok-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
DIGEST = hashlib.sha256(TOKEN.encode()).hexdigest()
PRINCIPAL = SessionPrincipal(name=f"session:{RUN}", run_id=RUN, expires_at=1_800_007_200.0)


def _state(tmp_path: Path) -> Path:
    state = tmp_path / "hub"
    state.mkdir(mode=0o700)
    os.chmod(state, 0o700)
    return state


def _mode(path: Path) -> int:
    return stat.S_IMODE(os.lstat(path).st_mode)


def test_the_registry_meets_both_seams(tmp_path: Path) -> None:
    registry = SessionRegistry(tmp_path)
    assert isinstance(registry, SessionRegistryInterface)
    assert isinstance(registry, SessionPrincipalRegistryInterface)


def test_record_then_find_gives_the_principal_back(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)

    registry.record(DIGEST, PRINCIPAL)

    assert registry.find(DIGEST) == PRINCIPAL
    # Another process -- the hub -- reads the same folder afresh.
    assert SessionRegistry(state).find(DIGEST) == PRINCIPAL


def test_the_entry_is_owner_only_and_holds_no_token(tmp_path: Path) -> None:
    state = _state(tmp_path)
    old = os.umask(0)
    try:
        SessionRegistry(state).record(DIGEST, PRINCIPAL)
    finally:
        os.umask(old)

    folder = state / SESSIONS_FOLDER
    entry = folder / f"{DIGEST}.json"
    assert SESSIONS_FOLDER == "sessions"
    assert _mode(folder) == 0o700
    assert _mode(entry) == 0o600
    assert sorted(os.listdir(folder)) == [f"{DIGEST}.json"]  # no staged file left behind
    text = entry.read_text()
    assert TOKEN not in text
    assert json.loads(text) == {
        "name": f"session:{RUN}",
        "run_id": str(RUN),
        "expires_at": 1_800_007_200.0,
    }


def test_the_state_folder_is_made_owner_only_when_missing(tmp_path: Path) -> None:
    state = tmp_path / "fresh" / "hub"

    SessionRegistry(state).record(DIGEST, PRINCIPAL)

    assert _mode(state / SESSIONS_FOLDER) == 0o700
    assert SessionRegistry(state).find(DIGEST) == PRINCIPAL


def test_an_unknown_digest_is_nobody(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)

    assert registry.find(DIGEST) is None  # no sessions folder yet
    registry.record(DIGEST, PRINCIPAL)
    assert registry.find("0" * 64) is None


@pytest.mark.parametrize(
    "digest",
    ["", "abc", "../" + "a" * 61, "A" * 64, "g" * 64, "a" * 63 + "/", "a" * 65, DIGEST + ".json"],
)
def test_a_name_that_is_not_a_digest_is_never_a_path(tmp_path: Path, digest: str) -> None:
    registry = SessionRegistry(_state(tmp_path))

    assert registry.find(digest) is None
    assert registry.forget(digest) is False
    with pytest.raises(ValueError, match="digest"):
        registry.record(digest, PRINCIPAL)


def test_forget_takes_the_entry_away_once(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record(DIGEST, PRINCIPAL)

    assert registry.forget(DIGEST) is True
    assert registry.find(DIGEST) is None
    assert registry.forget(DIGEST) is False
    assert SessionRegistry(tmp_path / "never").forget(DIGEST) is False


def test_forget_never_follows_a_symlink(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record("1" * 64, PRINCIPAL)  # makes the folder
    target = tmp_path / "precious"
    target.write_text("keep me")
    (state / SESSIONS_FOLDER / f"{DIGEST}.json").symlink_to(target)

    assert registry.forget(DIGEST) is True  # the link is removed, never what it points at
    assert target.read_text() == "keep me"


def test_an_entry_open_to_other_accounts_is_refused(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record(DIGEST, PRINCIPAL)
    os.chmod(state / SESSIONS_FOLDER / f"{DIGEST}.json", 0o644)

    with pytest.raises(PermissionError, match="open to other accounts"):
        registry.find(DIGEST)


def test_an_entry_of_another_account_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record(DIGEST, PRINCIPAL)
    mine = os.getuid()
    monkeypatch.setattr(os, "getuid", lambda: mine + 1)

    with pytest.raises(PermissionError, match="another account"):
        registry.find(DIGEST)


def test_an_entry_that_is_a_symlink_is_never_read(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record("1" * 64, PRINCIPAL)
    planted = tmp_path / "planted.json"
    planted.write_text(json.dumps({"name": "session:x", "run_id": str(RUN), "expires_at": 1.0}))
    os.chmod(planted, 0o600)
    (state / SESSIONS_FOLDER / f"{DIGEST}.json").symlink_to(planted)

    with pytest.raises(OSError):
        registry.find(DIGEST)


@pytest.mark.parametrize("mode", [0o750, 0o755, 0o705])
def test_a_sessions_folder_open_to_other_accounts_is_refused(tmp_path: Path, mode: int) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record(DIGEST, PRINCIPAL)
    os.chmod(state / SESSIONS_FOLDER, mode)

    with pytest.raises(PermissionError, match="open to other accounts"):
        registry.find(DIGEST)
    with pytest.raises(PermissionError, match="open to other accounts"):
        registry.record("1" * 64, PRINCIPAL)


def test_a_sessions_folder_that_is_a_symlink_is_refused(tmp_path: Path) -> None:
    state = _state(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir(mode=0o700)
    os.chmod(elsewhere, 0o700)
    (state / SESSIONS_FOLDER).symlink_to(elsewhere)
    registry = SessionRegistry(state)

    with pytest.raises(PermissionError, match="not a folder"):
        registry.record(DIGEST, PRINCIPAL)
    with pytest.raises(PermissionError, match="not a folder"):
        registry.find(DIGEST)
    assert os.listdir(elsewhere) == []


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        json.dumps({"name": "session:x", "run_id": str(RUN)}),
        json.dumps({"name": 1, "run_id": str(RUN), "expires_at": 1.0}),
        json.dumps({"name": "session:x", "run_id": 7, "expires_at": 1.0}),
        json.dumps({"name": "session:x", "run_id": "not-a-uuid", "expires_at": 1.0}),
        json.dumps({"name": "session:x", "run_id": str(RUN), "expires_at": "soon"}),
        json.dumps({"name": "session:x", "run_id": str(RUN), "expires_at": True}),
        json.dumps({"name": "device:x", "run_id": str(RUN), "expires_at": 1.0}),
        '{"name": "session:x", "run_id": "' + str(RUN) + '", "expires_at": Infinity}',
    ],
)
def test_a_malformed_entry_is_not_the_same_fact_as_none(tmp_path: Path, content: str) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record("1" * 64, PRINCIPAL)
    entry = state / SESSIONS_FOLDER / f"{DIGEST}.json"
    fd = os.open(entry, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(content)

    with pytest.raises(ValueError, match=DIGEST):
        registry.find(DIGEST)


def test_an_entry_that_is_not_a_regular_file_is_refused(tmp_path: Path) -> None:
    state = _state(tmp_path)
    registry = SessionRegistry(state)
    registry.record("1" * 64, PRINCIPAL)
    (state / SESSIONS_FOLDER / f"{DIGEST}.json").mkdir(mode=0o700)

    with pytest.raises(PermissionError, match="not a regular file"):
        registry.find(DIGEST)


def test_an_entry_that_cannot_be_put_in_place_leaves_no_staged_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(tmp_path)

    def refuse(source: object, target: object) -> None:
        raise OSError("read-only file system")

    monkeypatch.setattr(os, "replace", refuse)

    with pytest.raises(OSError, match="read-only"):
        SessionRegistry(state).record(DIGEST, PRINCIPAL)

    assert os.listdir(state / SESSIONS_FOLDER) == []
