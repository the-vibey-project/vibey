# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`StateKeyStore`: where the state key is looked for, in what order, and how one is made.

The keychain is reached only through the injected runner, so these tests never touch the
machine's keychain: a fake runner records each argument vector and its stdin.
"""

import stat
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from vibey.domain.errors import VibeyError
from vibey.infrastructure.state.aes_gcm_cipher import KEY_BYTES, StateKey
from vibey.infrastructure.state.interfaces.state_key_interface import StateKeyStoreInterface
from vibey.infrastructure.state.settings import StateSyncSettings
from vibey.infrastructure.state.state_key import (
    KEYCHAIN_SERVICE,
    SECURITY,
    StateKeyMissing,
    StateKeyStore,
    run_security,
)

ENV_KEY = StateKey.new()
CHAIN_KEY = StateKey.new()
FILE_KEY = StateKey.new()


class FakeSecurity:
    """Answers `security` from a script: the keychain's key (or none), and whether an add works."""

    def __init__(self, found: str | None = None, *, adds: bool = True) -> None:
        self.found = found
        self.adds = adds
        self.calls: list[tuple[tuple[str, ...], str | None]] = []

    def __call__(self, argv: Sequence[str], stdin: str | None) -> tuple[int, str]:
        self.calls.append((tuple(argv), stdin))
        if "find-generic-password" in argv:
            return (0, self.found + "\n") if self.found is not None else (44, "")
        return (0, "") if self.adds else (1, "")


def settings(tmp_path: Path, **values: str) -> StateSyncSettings:
    values.setdefault("key_file", str(tmp_path / "config" / "vibey" / "state.key"))
    return StateSyncSettings(**values)  # type: ignore[arg-type]


def key_file(tmp_path: Path, text: str = FILE_KEY, mode: int = 0o600) -> Path:
    path = tmp_path / "config" / "vibey" / "state.key"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    path.chmod(mode)
    return path


def test_the_store_satisfies_its_interface(tmp_path: Path) -> None:
    assert isinstance(StateKeyStore(settings(tmp_path), keychain=False), StateKeyStoreInterface)
    assert issubclass(StateKeyMissing, VibeyError)


def test_the_keychain_is_used_by_default_only_on_macos_with_security(tmp_path: Path) -> None:
    store = StateKeyStore(settings(tmp_path))
    assert store._keychain is (sys.platform == "darwin" and Path(SECURITY).exists())


def test_a_repository_containing_a_quote_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no quotes"):
        StateKeyStore(settings(tmp_path, repository='o/r" -w "x'), keychain=False)


def test_the_environment_key_wins_and_nothing_else_is_asked(tmp_path: Path) -> None:
    key_file(tmp_path)
    security = FakeSecurity(CHAIN_KEY)
    store = StateKeyStore(settings(tmp_path, key=ENV_KEY), keychain=True, runner=security)
    assert store.where() == "VIBEY_STATE_KEY"
    assert store.text() == ENV_KEY
    assert store.load() == StateKey.parse(ENV_KEY)
    assert security.calls == []


def test_the_keychain_is_asked_for_the_repository_account(tmp_path: Path) -> None:
    key_file(tmp_path)
    security = FakeSecurity(CHAIN_KEY)
    store = StateKeyStore(settings(tmp_path, repository="o/r"), keychain=True, runner=security)
    assert store.where() == f"the keychain ({KEYCHAIN_SERVICE}, o/r)"
    assert store.text() == CHAIN_KEY
    assert security.calls[0] == (
        (SECURITY, "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", "o/r", "-w"),
        None,
    )


def test_with_no_repository_the_keychain_account_is_default(tmp_path: Path) -> None:
    security = FakeSecurity(CHAIN_KEY)
    store = StateKeyStore(settings(tmp_path), keychain=True, runner=security)
    assert store.where() == f"the keychain ({KEYCHAIN_SERVICE}, default)"
    assert security.calls[0][0][5] == "default"


def test_the_keychain_is_not_asked_when_it_is_off(tmp_path: Path) -> None:
    path = key_file(tmp_path)
    security = FakeSecurity(CHAIN_KEY)
    store = StateKeyStore(settings(tmp_path), keychain=False, runner=security)
    assert store.where() == str(path)
    assert store.text() == FILE_KEY
    assert security.calls == []


def test_a_keychain_miss_falls_back_to_the_key_file(tmp_path: Path) -> None:
    path = key_file(tmp_path)
    security = FakeSecurity(None)
    store = StateKeyStore(settings(tmp_path, repository="o/r"), keychain=True, runner=security)
    assert store.where() == str(path)
    assert store.text() == FILE_KEY
    assert len(store.load()) == KEY_BYTES
    assert all("find-generic-password" in argv for argv, _ in security.calls)


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o644, 0o660])
def test_a_key_file_others_can_read_is_refused(tmp_path: Path, mode: int) -> None:
    path = key_file(tmp_path, mode=mode)
    store = StateKeyStore(settings(tmp_path), keychain=False)
    with pytest.raises(StateKeyMissing, match=f"chmod 600 {path}"):
        store.text()
    with pytest.raises(StateKeyMissing, match="can be read by others"):
        store.where()


def test_with_no_key_anywhere_text_says_how_to_make_one(tmp_path: Path) -> None:
    store = StateKeyStore(settings(tmp_path), keychain=True, runner=FakeSecurity(None))
    assert store.where() == ""
    with pytest.raises(StateKeyMissing, match="vibey state key --new"):
        store.text()
    with pytest.raises(StateKeyMissing):
        store.load()


def test_a_key_that_is_not_a_key_is_refused_by_text(tmp_path: Path) -> None:
    key_file(tmp_path, text="not a key")
    store = StateKeyStore(settings(tmp_path), keychain=False)
    with pytest.raises(ValueError, match="32 bytes as base64url"):
        store.text()
    with pytest.raises(ValueError, match="32 bytes as base64url"):
        StateKeyStore(settings(tmp_path, key="short"), keychain=False).load()


@pytest.mark.parametrize("where", ["env", "keychain", "file"])
def test_create_refuses_while_a_key_exists_anywhere(tmp_path: Path, where: str) -> None:
    path = key_file(tmp_path) if where == "file" else tmp_path / "config" / "vibey" / "state.key"
    security = FakeSecurity(CHAIN_KEY if where == "keychain" else None)
    store = StateKeyStore(
        settings(tmp_path, key=ENV_KEY if where == "env" else ""),
        keychain=True,
        runner=security,
    )
    before = path.read_text() if path.exists() else None
    with pytest.raises(StateKeyMissing, match="already exists.*never replaced"):
        store.create()
    assert not any(argv == (SECURITY, "-i") for argv, _ in security.calls)
    assert (path.read_text() if path.exists() else None) == before


def test_create_keeps_the_key_in_the_keychain_through_stdin(tmp_path: Path) -> None:
    security = FakeSecurity(None)
    store = StateKeyStore(settings(tmp_path, repository="o/r"), keychain=True, runner=security)
    assert store.create() == f"the keychain ({KEYCHAIN_SERVICE}, o/r)"
    argv, stdin = security.calls[-1]
    assert argv == (SECURITY, "-i")
    assert stdin is not None
    assert stdin.startswith(f'add-generic-password -s "{KEYCHAIN_SERVICE}" -a "o/r" -w "')
    assert stdin.endswith('"\n')
    key = stdin.split('-w "', 1)[1].rstrip('"\n')
    assert len(StateKey.parse(key)) == KEY_BYTES
    # The key is on stdin only: never on any argument vector `ps` could read.
    assert all(key not in part for call, _ in security.calls for part in call)
    assert not (tmp_path / "config").exists()


def _assert_kept_in_a_private_file(path: Path) -> None:
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert len(StateKey.parse(text)) == KEY_BYTES


def test_create_falls_back_to_a_private_file_when_the_keychain_refuses(tmp_path: Path) -> None:
    security = FakeSecurity(None, adds=False)
    store = StateKeyStore(settings(tmp_path), keychain=True, runner=security)
    kept = store.create()
    path = tmp_path / "config" / "vibey" / "state.key"
    assert kept == str(path)
    assert security.calls[-1][0] == (SECURITY, "-i")
    _assert_kept_in_a_private_file(path)
    assert store.where() == str(path)


def test_create_writes_a_private_file_without_a_keychain(tmp_path: Path) -> None:
    security = FakeSecurity(None)
    store = StateKeyStore(settings(tmp_path), keychain=False, runner=security)
    path = tmp_path / "config" / "vibey" / "state.key"
    assert store.create() == str(path)
    _assert_kept_in_a_private_file(path)
    assert security.calls == []
    assert store.load() == StateKey.parse(path.read_text())
    with pytest.raises(StateKeyMissing, match="already exists"):
        store.create()


def test_run_security_runs_an_argument_vector_with_stdin() -> None:
    code, out = run_security([sys.executable, "-c", "import sys; print(sys.stdin.read())"], "hi")
    assert (code, out) == (0, "hi\n")
    code, _ = run_security([sys.executable, "-c", "raise SystemExit(3)"], None)
    assert code == 3
